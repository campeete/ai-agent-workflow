"""Starter API for the Step 1 drills.

Run:  uv run uvicorn app.main:app --reload
Docs: http://127.0.0.1:8000/docs
"""
import logging
import time

from fastapi import FastAPI, Request
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("api")

app = FastAPI(title="ai-agent-workflow starter", version="0.1.0")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every request so the backend is visible in the terminal."""
    start = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - start) * 1000
    log.info("%s %s -> %d (%.1f ms)", request.method, request.url.path, response.status_code, ms)
    return response


class EchoIn(BaseModel):
    message: str = Field(min_length=1, max_length=280)
    author: str = Field(default="anonymous", max_length=40)


class EchoOut(BaseModel):
    message: str
    author: str
    length: int


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/echo")
def echo(body: EchoIn) -> EchoOut:
    return EchoOut(message=body.message, author=body.author, length=len(body.message))
