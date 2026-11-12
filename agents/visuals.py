"""Visuals agent.

Turns the repo summary into pictures of the architecture and the request flow.

Input: repo summary.
Output: architecture diagram, flow visual.

TODO: real implementation
"""

from pydantic import BaseModel, Field


class VisualsInput(BaseModel):
    """Repo summary."""

    repo_summary: str = Field(min_length=1, max_length=20_000)


class VisualsOutput(BaseModel):
    """Architecture diagram, flow visual."""

    architecture_diagram: str
    flow_visual: str


def run(agent_input: VisualsInput) -> VisualsOutput:
    """Return placeholder diagram text. These are not real figures."""
    preview = agent_input.repo_summary[:200]
    return VisualsOutput(
        architecture_diagram=f"[placeholder] architecture diagram for: {preview}",
        flow_visual=f"[placeholder] flow visual for: {preview}",
    )
