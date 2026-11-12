"""Hackathon agent API, including the Step 1 drill endpoints.

Run:  uv run uvicorn app.main:app --reload
Docs: http://127.0.0.1:8000/docs
"""
import logging
import time

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

from agents.models import ModelInfo, list_models
from agents.progress_reporter import JudgeInput, judge_results
from agents.referee import RefereeVerdict
from agents.voice import MAX_CHARS, VoiceError, speak
from app.auth import require_password

from agents.pipeline import (
    AGENTS,
    AgentDescription,
    AgentSpec,
    PipelineInput,
    PipelineOutput,
    known_agent_names,
    list_agents,
    run_pipeline,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("api")

app = FastAPI(
    title="AI Agent Workflow",
    version="0.2.0",
    description="Five hackathon agents. Open /dashboard for the visual version.",
)

DASHBOARD_HTML = (Path(__file__).parent / "dashboard.html").read_text(encoding="utf-8")


# Password check runs first (registered first = inner), logging wraps it,
# so refused requests are still logged.
app.middleware("http")(require_password)


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


@app.get("/models")
def read_models() -> list[ModelInfo]:
    """List the AI models and whether each one's API key is set (keys are never shown)."""
    return list_models()


@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def dashboard() -> HTMLResponse:
    """The visual dashboard for running agents."""
    return HTMLResponse(DASHBOARD_HTML, headers={
        "Content-Security-Policy": "default-src 'self'; style-src 'unsafe-inline'; "
                                   "script-src 'unsafe-inline'; connect-src 'self'; media-src 'self' blob:",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
    })


@app.get("/agents")
def read_agents() -> list[AgentDescription]:
    """List the five agents with name, step, input, and output."""
    return list_agents()


def _agent_run_route(spec: AgentSpec):
    """Build a POST handler whose body is that agent's input model."""
    output_model = spec.run.__annotations__["return"]

    def run_stub(body: spec.input_model):
        return spec.run(body)

    run_stub.__name__ = f"run_{spec.name}"
    run_stub.__doc__ = f"Run the {spec.name} agent."
    run_stub.__annotations__["return"] = output_model
    return run_stub


for _spec in AGENTS:
    app.add_api_route(
        f"/agents/{_spec.name}/run",
        _agent_run_route(_spec),
        methods=["POST"],
        response_model=_spec.run.__annotations__["return"],
    )


@app.post("/agents/{name}/run", include_in_schema=False)
def unknown_agent(name: str) -> None:
    """Reject a name that is not one of the five agents."""
    raise HTTPException(
        status_code=404,
        detail=f"Unknown agent. Known agents: {', '.join(known_agent_names())}",
    )


@app.post("/agents/progress_reporter/judge")
def judge_progress(body: JudgeInput) -> RefereeVerdict | None:
    """Referee judges answers the dashboard collected one model at a time."""
    return judge_results(body)


class SpeakIn(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_CHARS)


@app.post("/speak", responses={200: {"content": {"audio/mpeg": {}}}})
def speak_text(body: SpeakIn) -> Response:
    """Read text aloud in a British voice (used for the Judge's verdict)."""
    try:
        audio = speak(body.text)
    except VoiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return Response(audio, media_type="audio/mpeg", headers={"Cache-Control": "no-store"})


@app.post("/pipeline/run")
def run_full_pipeline(body: PipelineInput) -> PipelineOutput:
    """Run agents 1-4. The progress reporter is not part of this call."""
    return run_pipeline(body)
