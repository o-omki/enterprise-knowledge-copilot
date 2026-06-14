import datetime
import logging
import os
import uuid
from typing import Literal

from celery.result import AsyncResult
from fastapi import APIRouter, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import desc, select
from sqlalchemy.orm import selectinload

from apps.api.app.middleware.auth import MultiAuthMiddleware
from apps.api.app.middleware.rate_limiter import RateLimiterMiddleware
from apps.api.app.middleware.safety import SafetyGuardrailsMiddleware
from apps.api.app.routers.auth import router as auth_router
from apps.api.app.schemas import (
    AskRequest,
    AskResponse,
    FeedbackRequest,
    FeedbackResponse,
    JobStatusResponse,
    MessageResponse,
    SearchRequest,
    SearchResponse,
    SessionResponse,
    UploadResponse,
)
from apps.worker.celery_app import app as celery_app
from apps.worker.tasks import ingest_document
from packages.agents.orchestrator import QueryOrchestrator
from packages.observability import setup_tracing
from packages.rag.generation import GenerationService
from packages.rag.reranker import RerankerService
from packages.rag.search import SearchService
from packages.shared.database import async_session_maker
from packages.shared.feedback import FeedbackService
from packages.shared.orm_models import Message, Session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Enterprise Knowledge Copilot API", version="0.3.0")

setup_tracing(app)

# Middlewares are executed in reverse order of addition:
# Request -> ApiKeyAuth -> RateLimiter -> Safety -> Router
guardrails_url = os.getenv("GUARDRAILS_SERVICE_URL", "http://guardrails:8001")
app.add_middleware(SafetyGuardrailsMiddleware, service_url=guardrails_url)
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(MultiAuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

search_service = SearchService()
generation_service = GenerationService()
reranker_service = RerankerService()
orchestrator = QueryOrchestrator(
    search_service=search_service,
    generation_service=generation_service,
    reranker_service=reranker_service,
)

v1_router = APIRouter(prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@v1_router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest) -> SearchResponse:
    """Global retrieval endpoint with optional payload filtering and reranking."""
    try:
        fetch_limit = req.limit * 2 if req.rerank else req.limit
        results = await search_service.search(
            query=req.query,
            limit=fetch_limit,
            domain=req.domain,
            doc_type=req.doc_type,
            method=req.method,
        )
        if req.rerank:
            results = await reranker_service.arerank(
                query=req.query, results=results, top_k=req.limit
            )
        return SearchResponse(query=req.query, results=[res.model_dump() for res in results])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v1_router.post("/ask", response_model=AskResponse)
async def ask(request: Request, req: AskRequest):
    """Answers a question using LLM generation and knowledge base context with citations."""
    try:
        logger.info(f"Processing query: {req.query}")

        user_id = getattr(request.state, "user_id", None)
        api_key_id = getattr(request.state, "api_key_id", None)

        session_id = req.session_id
        chat_history = []

        async with async_session_maker() as db:
            if session_id:
                query = select(Session).where(Session.id == session_id)
                res = await db.execute(query)
                session_obj = res.scalar_one_or_none()
                if not session_obj:
                    raise HTTPException(status_code=404, detail="Session not found")

                if user_id and session_obj.user_id != user_id:
                    raise HTTPException(status_code=403, detail="Unauthorized session access")
                if api_key_id and session_obj.api_key_id != api_key_id:
                    raise HTTPException(status_code=403, detail="Unauthorized session access")

                msg_query = (
                    select(Message)
                    .where(Message.session_id == session_id)
                    .order_by(Message.created_at)
                )
                msg_res = await db.execute(msg_query)
                messages = msg_res.scalars().all()
                for msg in messages:
                    chat_history.append({"role": msg.role, "content": msg.content})
            else:
                session_obj = Session(user_id=user_id, api_key_id=api_key_id)
                db.add(session_obj)
                await db.flush()
                session_id = session_obj.id

            user_msg = Message(session_id=session_id, role="user", content=req.query)
            db.add(user_msg)
            await db.commit()

            # Re-fetch session_obj to attach it to the new transaction after commit
            query = select(Session).where(Session.id == session_id)
            res = await db.execute(query)
            session_obj = res.scalar_one()

            response = await orchestrator.answer_query(
                query=req.query,
                domain=req.domain,
                doc_type=req.doc_type,
                limit=req.limit,
                method=req.method,
                rerank=req.rerank,
                chat_history=chat_history,
            )

            assistant_msg = Message(
                session_id=session_id,
                role="assistant",
                content=response.answer,
                citations_json=[c.model_dump() for c in response.citations]
                if response.citations
                else None,
            )
            db.add(assistant_msg)

            session_obj.last_active = datetime.datetime.now(datetime.UTC)
            await db.commit()

            response_dict = response.model_dump()
            response_dict["session_id"] = session_id
            response_dict["message_id"] = assistant_msg.id
            return AskResponse(**response_dict)

    except Exception as e:
        logger.error(f"Error in ask endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@v1_router.get("/sessions", response_model=list[SessionResponse])
async def get_sessions(request: Request):
    user_id = getattr(request.state, "user_id", None)
    api_key_id = getattr(request.state, "api_key_id", None)

    async with async_session_maker() as db:
        if user_id:
            query = (
                select(Session)
                .where(Session.user_id == user_id)
                .order_by(desc(Session.last_active))
            )
        elif api_key_id:
            query = (
                select(Session)
                .where(Session.api_key_id == api_key_id)
                .order_by(desc(Session.last_active))
            )
        else:
            return []

        res = await db.execute(query)
        sessions = res.scalars().all()

        results = []
        for s in sessions:
            msg_query = (
                select(Message)
                .where(Message.session_id == s.id, Message.role == "user")
                .order_by(Message.created_at)
                .limit(1)
            )
            msg_res = await db.execute(msg_query)
            first_msg = msg_res.scalar_one_or_none()

            title = (
                first_msg.content[:50] + "..."
                if first_msg and len(first_msg.content) > 50
                else (first_msg.content if first_msg else "New Chat")
            )

            results.append(
                SessionResponse(id=s.id, last_active=s.last_active.isoformat(), first_message=title)
            )

        return results


@v1_router.get("/sessions/{session_id}/messages", response_model=list[MessageResponse])
async def get_session_messages(session_id: str, request: Request):
    user_id = getattr(request.state, "user_id", None)
    api_key_id = getattr(request.state, "api_key_id", None)

    async with async_session_maker() as db:
        query = select(Session).where(Session.id == session_id)
        res = await db.execute(query)
        session_obj = res.scalar_one_or_none()
        if not session_obj:
            raise HTTPException(status_code=404, detail="Session not found")

        if user_id and session_obj.user_id != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized")
        if api_key_id and session_obj.api_key_id != api_key_id:
            raise HTTPException(status_code=403, detail="Unauthorized")

        msg_query = (
            select(Message)
            .options(selectinload(Message.feedback))
            .where(Message.session_id == session_id)
            .order_by(Message.created_at)
        )
        msg_res = await db.execute(msg_query)
        messages = msg_res.scalars().all()

        results = []
        for msg in messages:
            citations = msg.citations_json
            feedback_resp = None
            if msg.feedback:
                fb = msg.feedback[0]
                feedback_resp = FeedbackResponse(
                    id=fb.id,
                    message_id=fb.message_id,
                    session_id=fb.session_id,
                    rating=fb.rating,
                    comment=fb.comment,
                    created_at=fb.created_at.isoformat(),
                )

            results.append(
                MessageResponse(
                    id=msg.id,
                    role=msg.role,
                    content=msg.content,
                    citations=citations,
                    created_at=msg.created_at.isoformat(),
                    feedback=feedback_resp,
                )
            )

        return results


@v1_router.post("/messages/{message_id}/feedback", response_model=FeedbackResponse)
async def submit_feedback(message_id: str, req: FeedbackRequest, request: Request):
    user_id = getattr(request.state, "user_id", None)
    api_key_id = getattr(request.state, "api_key_id", None)

    async with async_session_maker() as db:
        query = select(Session).where(Session.id == req.session_id)
        res = await db.execute(query)
        session_obj = res.scalar_one_or_none()
        if not session_obj:
            raise HTTPException(status_code=404, detail="Session not found")

        if user_id and session_obj.user_id != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized")
        if api_key_id and session_obj.api_key_id != api_key_id:
            raise HTTPException(status_code=403, detail="Unauthorized")

        try:
            feedback_service = FeedbackService(db)
            feedback = await feedback_service.add_feedback(
                session_id=req.session_id,
                message_id=message_id,
                rating=req.rating,
                comment=req.comment,
            )
            return FeedbackResponse(
                id=feedback.id,
                message_id=feedback.message_id,
                session_id=feedback.session_id,
                rating=feedback.rating,
                comment=feedback.comment,
                created_at=feedback.created_at.isoformat(),
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Failed to submit feedback: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to submit feedback")


UPLOAD_DIR = os.getenv("UPLOAD_DIR", "data/uploads")


@v1_router.post("/upload", status_code=202, response_model=UploadResponse)
async def upload_document(
    domain: str = Form(...),
    doc_type: str = Form(...),
    file: UploadFile = File(...),
) -> UploadResponse:
    """Accepts document uploads, saves them, and dispatches an ingestion task."""
    filename = file.filename or "uploaded_file"
    _, ext = os.path.splitext(filename)
    if ext.lower() not in (".md", ".txt"):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file extension. Only .md and .txt files are supported.",
        )

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    unique_filename = f"{uuid.uuid4()}_{os.path.basename(filename)}"
    dest_path = os.path.join(UPLOAD_DIR, unique_filename)

    try:
        with open(dest_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                buffer.write(chunk)
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save uploaded file.")

    abs_path = os.path.abspath(dest_path)
    try:
        task = ingest_document.delay(abs_path, {"domain": domain, "doc_type": doc_type})
        logger.info(f"Dispatched ingestion task {task.id} for file {abs_path}")
        return UploadResponse(
            job_id=task.id, status="queued", message="Document ingestion successfully queued."
        )
    except Exception as e:
        logger.error(f"Failed to dispatch Celery task: {e}", exc_info=True)
        if os.path.exists(dest_path):
            os.remove(dest_path)
        raise HTTPException(status_code=500, detail="Failed to dispatch background ingestion task.")


@v1_router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str) -> JobStatusResponse:
    """Queries the status and result of a Celery background task."""
    try:
        res = AsyncResult(job_id, app=celery_app)

        status: Literal["queued", "processing", "completed", "failed"] = "queued"
        result = None
        error = None

        if res.state == "SUCCESS":
            status = "completed"
            result = res.result
        elif res.state == "FAILURE":
            status = "failed"
            error = str(res.result)
        elif res.state in ("STARTED", "RETRY"):
            status = "processing"
        elif res.state == "PENDING":
            status = "queued"
        else:
            status = "failed"
            error = f"Unhandled task state: {res.state}"

        return JobStatusResponse(job_id=job_id, status=status, result=result, error=error)
    except Exception as e:
        logger.error(f"Failed to query job status for {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve status for job: {job_id}")


app.include_router(v1_router)
