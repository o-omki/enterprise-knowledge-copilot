import asyncio
import os
import signal
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, Request
from google import genai
from nemoguardrails import LLMRails, RailsConfig
from prometheus_client import make_asgi_app
from pydantic import BaseModel, Field

from packages.observability import configure_logging, setup_tracing
from packages.safety import contains_jailbreak_local, contains_off_topic_local, redact_local_pii

configure_logging("guardrails", os.getenv("LOG_LEVEL", "INFO"))
logger = structlog.get_logger(__name__)

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "config")

rails_app = None
genai_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global rails_app, genai_client
    logger.info("guardrails.engine.initializing")
    try:
        gcp_project = os.getenv("GCP_PROJECT_ID")
        gcp_location = os.getenv("GCP_LOCATION", "us-central1")
        if gcp_project:
            os.environ["GOOGLE_CLOUD_PROJECT"] = gcp_project
            os.environ["GCP_PROJECT"] = gcp_project
            logger.info("guardrails.gcp_mapped", project=gcp_project)

        if not os.path.exists(CONFIG_DIR):
            logger.error("guardrails.config_dir_missing", path=CONFIG_DIR)
        else:
            config = RailsConfig.from_path(CONFIG_DIR)
            rails_app = LLMRails(config)
            logger.info("guardrails.engine.initialized")

        # Initialize Vertex AI/GenAI Client
        genai_client = genai.Client(
            vertexai=True,
            project=gcp_project,
            location=gcp_location,
        )
        logger.info("guardrails.genai_client.initialized")
    except Exception as e:
        logger.error("guardrails.engine.init_failed", error=str(e), exc_info=True)

    app.state.shutting_down = False
    app.state.active_requests = 0

    async def graceful_shutdown():
        logger.info("guardrails.shutdown.graceful_start")
        app.state.shutting_down = True
        shutdown_grace_period = float(os.getenv("SHUTDOWN_GRACE_PERIOD", "20"))
        logger.info(
            "guardrails.shutdown.sleeping_for_grace_period",
            period=shutdown_grace_period,
        )
        await asyncio.sleep(shutdown_grace_period)

        drain_timeout = float(os.getenv("SHUTDOWN_DRAIN_TIMEOUT", "10"))
        start_time = asyncio.get_event_loop().time()
        logger.info(
            "guardrails.shutdown.draining_active_requests",
            active_requests=app.state.active_requests,
        )
        while app.state.active_requests > 0:
            if asyncio.get_event_loop().time() - start_time > drain_timeout:
                logger.warning(
                    "guardrails.shutdown.drain_timeout_reached",
                    active_requests=app.state.active_requests,
                )
                break
            logger.info(
                "guardrails.shutdown.waiting_for_active_requests",
                active_requests=app.state.active_requests,
            )
            await asyncio.sleep(0.5)

        logger.info("guardrails.shutdown.triggering_uvicorn_exit")
        os.kill(os.getpid(), signal.SIGINT)

    def handle_sigterm():
        logger.info("guardrails.shutdown.sigterm_received")
        asyncio.create_task(graceful_shutdown())

    try:
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGTERM, handle_sigterm)
        logger.info("guardrails.shutdown.sigterm_handler_registered")
    except ValueError as e:
        logger.warning("guardrails.shutdown.sigterm_handler_registration_failed", error=str(e))

    yield
    logger.info("guardrails.shutdown.completed")


app = FastAPI(title="Safety Guardrails Microservice", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def track_active_requests(request: Request, call_next):
    if not hasattr(request.app.state, "active_requests"):
        request.app.state.active_requests = 0

    path = request.url.path
    is_probe = path in ("/health", "/health/live", "/health/ready", "/readiness", "/metrics")

    if not is_probe:
        request.app.state.active_requests += 1

    try:
        response = await call_next(request)
        return response
    finally:
        if not is_probe:
            request.app.state.active_requests -= 1


setup_tracing(app, service_name="guardrails")
app.mount("/metrics", make_asgi_app())


class InputValidationRequest(BaseModel):
    query: str


class InputValidationResponse(BaseModel):
    is_safe: bool = Field(
        description="Flag indicating if the query is safe from jailbreaks and prompt injection."
    )
    is_off_topic: bool = Field(description="Flag indicating if the query is off-topic.")
    filtered_query: str = Field(
        description=("Masked or redacted query if PII was detected, otherwise original query.")
    )
    refusal_message: str | None = Field(
        default=None, description="The refusal message to return if query is blocked."
    )


class OutputValidationRequest(BaseModel):
    query: str
    response: str
    context: list[str] = Field(description="List of text chunks retrieved as grounding context.")


class OutputValidationResponse(BaseModel):
    is_grounded: bool = Field(
        description="Flag indicating if the generated answer is fully grounded in context."
    )
    refusal_message: str | None = Field(
        default=None,
        description="Fallback refusal message to return if hallucination is detected.",
    )


@app.get("/health")
@app.get("/health/live")
async def liveness():
    """Simple check if container is running."""
    return {"status": "ok"}


@app.get("/readiness")
@app.get("/health/ready")
async def readiness():
    """Check if guardrails model, engine and Vertex AI are fully initialized and connected."""
    if getattr(app.state, "shutting_down", False):
        raise HTTPException(status_code=503, detail="Service is shutting down")

    if rails_app is None:
        raise HTTPException(status_code=503, detail="Guardrails engine not ready")

    try:
        if genai_client is None:
            raise ValueError("Vertex AI client is not initialized")
        # List models with page_size=1
        await genai_client.aio.models.list(config={"page_size": 1})
    except Exception as e:
        logger.error("guardrails.readiness.vertex_ai_failed", error=str(e))
        raise HTTPException(status_code=503, detail=f"Vertex AI connectivity failed: {str(e)}")

    return {"status": "ready"}


@app.post("/validate/input", response_model=InputValidationResponse)
async def validate_input(request: InputValidationRequest):
    """Evaluates query against input rails: jailbreaks, off-topic, and PII masking."""
    if rails_app is None:
        raise HTTPException(status_code=503, detail="Guardrails engine not ready")

    try:
        logger.info("guardrails.input.checking", query=request.query)

        if contains_jailbreak_local(request.query):
            logger.warning("guardrails.blocked", check_type="local_jailbreak", query=request.query)
            return InputValidationResponse(
                is_safe=False,
                is_off_topic=False,
                filtered_query=request.query,
                refusal_message=(
                    "I cannot fulfill this request as it violates enterprise security policies."
                ),
            )

        if contains_off_topic_local(request.query):
            logger.warning("guardrails.blocked", check_type="local_off_topic", query=request.query)
            return InputValidationResponse(
                is_safe=True,
                is_off_topic=True,
                filtered_query=request.query,
                refusal_message=(
                    "I am only authorized to assist with internal enterprise documentation queries."
                ),
            )

        res_obj = await rails_app.generate_async(
            messages=[{"role": "user", "content": request.query}]
        )

        if res_obj and not isinstance(res_obj, str) and not isinstance(res_obj, dict):
            # Internal object response fallback
            try:
                res = res_obj[0].get("content")
            except Exception:
                res = str(res_obj)
        else:
            res = res_obj.get("content", "") if isinstance(res_obj, dict) else str(res_obj)

        filtered_query = redact_local_pii(request.query)

        is_safe = True
        is_off_topic = False
        refusal_message = None

        if "I cannot fulfill this request" in res or "violates enterprise security policies" in res:
            is_safe = False
            refusal_message = res
            logger.warning(
                "guardrails.blocked", check_type="rails_jailbreak", query=request.query, reason=res
            )
        elif (
            "only authorized to assist with internal enterprise" in res or "refuse off topic" in res
        ):
            is_off_topic = True
            refusal_message = res
            logger.warning(
                "guardrails.blocked", check_type="rails_off_topic", query=request.query, reason=res
            )

        logger.info(
            "guardrails.input.validated",
            is_safe=is_safe,
            is_off_topic=is_off_topic,
            filtered=filtered_query,
        )
        return InputValidationResponse(
            is_safe=is_safe,
            is_off_topic=is_off_topic,
            filtered_query=filtered_query,
            refusal_message=refusal_message,
        )
    except Exception as e:
        logger.error("guardrails.input.error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/validate/output", response_model=OutputValidationResponse)
async def validate_output(request: OutputValidationRequest):
    """Evaluates generated answer against grounding/fact-checking rails."""
    if rails_app is None:
        raise HTTPException(status_code=503, detail="Guardrails engine not ready")

    try:
        logger.info("guardrails.output.checking", query=request.query)

        evidence_str = "\n".join(
            [f"Evidence {i + 1}: {chunk}" for i, chunk in enumerate(request.context)]
        )

        is_grounded = True
        refusal_message = None

        if hasattr(rails_app, "generate_async"):
            try:
                # Trigger the Colang 2 custom output validation flow defined in main.co
                # using generate_async and injecting $evidence and $response via context role
                res_obj = await rails_app.generate_async(
                    messages=[
                        {
                            "role": "context",
                            "content": {"evidence": evidence_str, "response": request.response},
                        },
                        {"role": "user", "content": "validate output please"},
                    ]
                )
                res = res_obj.get("content", "") if isinstance(res_obj, dict) else str(res_obj)

                # Check the refusal message returned by the custom flow
                if "cannot verify this information" in res:
                    is_grounded = False
                    refusal_message = res

            except Exception as ev_err:
                logger.warning(
                    "guardrails.output.flow_failed",
                    error=str(ev_err),
                    reason="falling back to default evaluation",
                )
                res_obj = await rails_app.generate_async(
                    prompt=(
                        f"Facts:\n{evidence_str}\n\nStatement:\n{request.response}\n\n"
                        "Is the statement fully grounded? (yes/no):"
                    )
                )
                res = res_obj.get("content", "") if isinstance(res_obj, dict) else str(res_obj)
                if "no" in res.lower():
                    is_grounded = False
                    refusal_message = (
                        "I'm sorry, but I cannot verify this information with internal "
                        "sources. Please try rephrasing your query."
                    )

        logger.info("guardrails.output.validated", is_grounded=is_grounded)
        return OutputValidationResponse(is_grounded=is_grounded, refusal_message=refusal_message)
    except Exception as e:
        logger.error("guardrails.output.error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
