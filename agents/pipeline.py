"""Run the stub agents in plan order.

Agents 1 and 2 read the request (challenge statements, then code and commits).
The repo summary is passed to the visuals agent. That summary plus the visuals
are passed to the slides agent. The progress reporter is not part of this chain:
call it on its own with a list of commit messages.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

from pydantic import BaseModel

from agents import brief_reader, progress_reporter, repo_reader, slides, visuals
from agents.brief_reader import BriefReaderInput, BriefReaderOutput
from agents.progress_reporter import ProgressReporterInput, ProgressReporterOutput
from agents.repo_reader import RepoReaderInput, RepoReaderOutput
from agents.slides import SlidesInput, SlidesOutput
from agents.visuals import VisualsInput, VisualsOutput

AgentOutput = (
    BriefReaderOutput
    | RepoReaderOutput
    | VisualsOutput
    | SlidesOutput
    | ProgressReporterOutput
)


class PipelineInput(BaseModel):
    """Starting inputs for the brief reader and the repo reader."""

    brief: BriefReaderInput
    repo: RepoReaderInput


class PipelineOutput(BaseModel):
    """Placeholder results from agents 1-4."""

    brief: BriefReaderOutput
    repo: RepoReaderOutput
    visuals: VisualsOutput
    slides: SlidesOutput


class AgentDescription(BaseModel):
    """Name, step, and what one agent reads and returns."""

    name: str
    step: int
    input: str
    output: str


@dataclass(frozen=True)
class AgentSpec:
    name: str
    step: int
    input: str
    output: str
    input_model: type[BaseModel]
    run: Callable[[Any], BaseModel]


AGENTS: tuple[AgentSpec, ...] = (
    AgentSpec(
        name="brief_reader",
        step=1,
        input="Track challenge statements",
        output="Requirements, judging criteria, track fit",
        input_model=BriefReaderInput,
        run=brief_reader.run,
    ),
    AgentSpec(
        name="repo_reader",
        step=2,
        input="Code and commits",
        output="Summary of the parts, data flow and endpoints",
        input_model=RepoReaderInput,
        run=repo_reader.run,
    ),
    AgentSpec(
        name="visuals",
        step=3,
        input="Repo summary",
        output="Architecture diagram, flow visual",
        input_model=VisualsInput,
        run=visuals.run,
    ),
    AgentSpec(
        name="slides",
        step=4,
        input="Summary plus visuals",
        output="Presentation deck",
        input_model=SlidesInput,
        run=slides.run,
    ),
    AgentSpec(
        name="progress_reporter",
        step=5,
        input="Git commits",
        output="Plain-English updates for teammates",
        input_model=ProgressReporterInput,
        run=progress_reporter.run,
    ),
)

_EXAMPLES: dict[str, dict[str, object]] = {
    "brief_reader": {
        "challenge_statements": ["Recommend the customer's smartest next move."],
    },
    "repo_reader": {
        "code": "def health(): return {'status': 'ok'}",
        "commits": ["add health endpoint"],
    },
    "visuals": {
        "repo_summary": "[placeholder] Summary of the parts, data flow and endpoints.",
    },
    "slides": {
        "summary": "[placeholder] Summary of the parts, data flow and endpoints.",
        "architecture_diagram": "[placeholder] architecture diagram",
        "flow_visual": "[placeholder] flow visual",
    },
    "progress_reporter": {
        "commit_messages": ["add health endpoint", "stub the agents"],
    },
}


def _validate_examples() -> None:
    for spec in AGENTS:
        spec.input_model.model_validate(_EXAMPLES[spec.name])


_validate_examples()


def list_agents() -> list[AgentDescription]:
    """Describe the five agents in step order."""
    ordered = sorted(AGENTS, key=lambda spec: spec.step)
    return [
        AgentDescription(name=spec.name, step=spec.step, input=spec.input, output=spec.output)
        for spec in ordered
    ]


def known_agent_names() -> list[str]:
    return [spec.name for spec in sorted(AGENTS, key=lambda spec: spec.step)]


def get_agent(name: str) -> AgentSpec | None:
    for spec in AGENTS:
        if spec.name == name:
            return spec
    return None


def run_agent(name: str, payload: object) -> AgentOutput:
    """Validate `payload` with that agent's input model and run the stub."""
    spec = get_agent(name)
    if spec is None:
        raise KeyError(name)
    parsed = spec.input_model.model_validate(payload)
    return cast(AgentOutput, spec.run(parsed))


def run_pipeline(data: PipelineInput) -> PipelineOutput:
    """Call agents 1-4 in order, passing each produced artifact to the next.

    The brief reader and the repo reader take the caller's inputs, because
    the plan gives them different sources. From the repo reader onward, each
    output is handed to the next agent.
    """
    brief_out = brief_reader.run(data.brief)
    repo_out = repo_reader.run(data.repo)
    visuals_out = visuals.run(VisualsInput(repo_summary=repo_out.summary))
    slides_out = slides.run(
        SlidesInput(
            summary=repo_out.summary,
            architecture_diagram=visuals_out.architecture_diagram,
            flow_visual=visuals_out.flow_visual,
        )
    )
    return PipelineOutput(
        brief=brief_out,
        repo=repo_out,
        visuals=visuals_out,
        slides=slides_out,
    )


def agent_run_openapi_extra() -> dict[str, object]:
    """Request-body schema for POST /agents/{name}/run.

    The path name picks the model. OpenAPI lists every model's fields so
    /docs can show them.
    """
    return {
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"oneOf": [spec.input_model.model_json_schema() for spec in AGENTS]},
                    "examples": {
                        spec.name: {"summary": spec.input, "value": _EXAMPLES[spec.name]}
                        for spec in AGENTS
                    },
                }
            },
        }
    }
