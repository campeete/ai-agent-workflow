"""Slides agent.

Turns the repo summary and the visuals into a presentation deck.

Input: summary plus visuals.
Output: presentation deck.

TODO: real implementation
"""

from pydantic import BaseModel, Field


class SlidesInput(BaseModel):
    """Summary plus visuals."""

    summary: str = Field(min_length=1, max_length=20_000)
    architecture_diagram: str = Field(min_length=1, max_length=20_000)
    flow_visual: str = Field(min_length=1, max_length=20_000)


class Slide(BaseModel):
    """One placeholder slide."""

    title: str
    body: str


class SlidesOutput(BaseModel):
    """Presentation deck."""

    deck: list[Slide]


def run(agent_input: SlidesInput) -> SlidesOutput:
    """Return a placeholder deck. This is not a real presentation."""
    return SlidesOutput(
        deck=[
            Slide(
                title="[placeholder] Overview",
                body=f"[placeholder] summary ({len(agent_input.summary)} characters)",
            ),
            Slide(
                title="[placeholder] Architecture",
                body=f"[placeholder] diagram ({len(agent_input.architecture_diagram)} characters)",
            ),
            Slide(
                title="[placeholder] Flow",
                body=f"[placeholder] flow ({len(agent_input.flow_visual)} characters)",
            ),
        ]
    )
