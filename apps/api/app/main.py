from fastapi import FastAPI

app = FastAPI(title="Enterprise Knowledge Copilot API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/queries/{query}")
def query(query: str) -> dict[str, object]:
    # Placeholder response for Phase 0 scaffolding.
    return {
        "query": query,
        "answer": "Phase 1 implementation pending",
        "citations": [],
    }
