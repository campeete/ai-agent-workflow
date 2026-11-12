"""Progress reporter.

Turns git commits into plain-English updates teammates can read.

Input: git commits (a list of commit messages).
Output: plain-English updates for teammates.

TODO: real implementation
"""

from typing import Annotated

from pydantic import BaseModel, Field

CommitMessage = Annotated[str, Field(min_length=1, max_length=500)]


class ProgressReporterInput(BaseModel):
    """Git commits."""

    commit_messages: list[CommitMessage] = Field(min_length=1, max_length=200)


class ProgressReporterOutput(BaseModel):
    """Plain-English updates for teammates."""

    updates: list[str]


def run(agent_input: ProgressReporterInput) -> ProgressReporterOutput:
    """Return one placeholder update per commit message."""
    return ProgressReporterOutput(
        updates=[
            f"[placeholder] Update for commit: {message}"
            for message in agent_input.commit_messages
        ]
    )
