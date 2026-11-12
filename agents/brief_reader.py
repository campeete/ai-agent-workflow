"""Brief reader.

Reads the track challenge statements and lists what the team must build,
how the work will be judged, and how well it fits the track.

Input: track challenge statements.
Output: requirements, judging criteria, track fit.

TODO: real implementation
"""

from typing import Annotated

from pydantic import BaseModel, Field

ChallengeStatement = Annotated[str, Field(min_length=1, max_length=4_000)]


class BriefReaderInput(BaseModel):
    """Track challenge statements."""

    challenge_statements: list[ChallengeStatement] = Field(min_length=1, max_length=10)


class BriefReaderOutput(BaseModel):
    """Requirements, judging criteria, track fit."""

    requirements: list[str]
    judging_criteria: list[str]
    track_fit: str


def run(agent_input: BriefReaderInput) -> BriefReaderOutput:
    """Return placeholder requirements, judging criteria, and track fit."""
    count = len(agent_input.challenge_statements)
    return BriefReaderOutput(
        requirements=[f"[placeholder] requirement ({count} challenge statements received)"],
        judging_criteria=["[placeholder] judging criterion"],
        track_fit=f"[placeholder] track fit ({count} challenge statements received)",
    )
