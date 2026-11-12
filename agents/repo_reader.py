"""Repo reader.

Reads the code and the commit list and describes how the project is put together.

Input: code and commits.
Output: summary of the parts, data flow and endpoints.

TODO: real implementation
"""

from typing import Annotated

from pydantic import BaseModel, Field

CommitMessage = Annotated[str, Field(min_length=1, max_length=500)]


class RepoReaderInput(BaseModel):
    """Code and commits."""

    code: str = Field(min_length=1, max_length=50_000)
    commits: list[CommitMessage] = Field(min_length=1, max_length=200)


class RepoReaderOutput(BaseModel):
    """Summary of the parts, data flow and endpoints."""

    parts: list[str]
    data_flow: str
    endpoints: list[str]
    summary: str


def run(agent_input: RepoReaderInput) -> RepoReaderOutput:
    """Return a placeholder repo summary.

    `summary` is the short text the visuals agent receives. It stays short
    so it fits that agent's input limit.
    """
    return RepoReaderOutput(
        parts=["[placeholder] API", "[placeholder] agents"],
        data_flow=(
            "[placeholder] data flow "
            f"({len(agent_input.commits)} commits, {len(agent_input.code)} characters of code)"
        ),
        endpoints=["[placeholder] GET /example"],
        summary="[placeholder] Summary of the parts, data flow and endpoints.",
    )
