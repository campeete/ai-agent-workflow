"""Hackathon agent API, including the Step 1 drill endpoints.

Run:  uv run uvicorn app.main:app --reload
Docs: http://127.0.0.1:8000/docs
"""
import json
import logging
import time
from typing import Annotated

from fastapi import FastAPI, HTTPException, Path, Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, ValidationError

from agents.pipeline import (
    AgentDescription,
    AgentOutput,
    PipelineInput,
    PipelineOutput,
    agent_run_openapi_extra,
    get_agent,
    known_agent_names,
    list_agents,
    run_agent,
    run_pipeline,
)

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


def _body_validation_error(exc: ValidationError) -> RequestValidationError:
    """Shape a Pydantic error like FastAPI's own body validation errors."""
    errors = []
    for err in exc.errors():
        item = dict(err)
        item["loc"] = ("body", *item.get("loc", ()))
        errors.append(item)
    return RequestValidationError(errors)


@app.get("/agents")
def read_agents() -> list[AgentDescription]:
    """List the five agents with name, step, input, and output."""
    return list_agents()


@app.post(
    "/agents/{name}/run",
    response_model=AgentOutput,
    responses={404: {"description": "Unknown agent name"}},
    openapi_extra=agent_run_openapi_extra(),
)
async def run_one_agent(
    name: Annotated[
        str,
        Path(
            description="brief_reader, repo_reader, visuals, slides, or progress_reporter",
        ),
    ],
    request: Request,
) -> AgentOutput:
    """Run one stub agent. The path name selects that agent's input model."""
    if get_agent(name) is None:
        known = ", ".join(known_agent_names())
        raise HTTPException(
            status_code=404,
            detail=f"Unknown agent '{name}'. Known agents: {known}",
        )
    try:
        payload = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=422, detail="Request body must be JSON") from exc
    try:
        return run_agent(name, payload)
    except ValidationError as exc:
        raise _body_validation_error(exc) from exc


@app.post("/pipeline/run")
def run_full_pipeline(body: PipelineInput) -> PipelineOutput:
    """Run agents 1-4. The progress reporter is not part of this call."""
    return run_pipeline(body)
