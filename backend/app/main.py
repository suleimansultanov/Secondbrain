"""SecondBrain API — entry point."""
from fastapi import FastAPI

app = FastAPI(title="SecondBrain API", version="0.0.1")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok", "service": "secondbrain-api"}
