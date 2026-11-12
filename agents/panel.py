"""Shared pieces for agents that ask the whole model panel.

Every live agent follows the same shape: the caller picks models, each model
answers, and the referee can judge the answers. This module keeps the model
checks and the "untrusted text goes inside tags" rule in one place.
"""

from pydantic import BaseModel, Field, field_validator

from agents.models import PANEL_MODELS, ModelResult

ALL_MODELS = [m.id for m in PANEL_MODELS]
DEFAULT_MODELS = [m.id for m in PANEL_MODELS if m.default_on]
JUDGE_TEXT_LIMIT = 6000  # answers longer than this are trimmed before judging
ABSURD_ANSWER = 20_000  # anything longer is refused outright


class PanelChoice(BaseModel):
    """Which models to ask, and whether the referee should judge."""

    models: list[str] = Field(default_factory=lambda: list(DEFAULT_MODELS),
                              min_length=1, max_length=len(PANEL_MODELS))
    referee: bool = True

    @field_validator("models")
    @classmethod
    def known_models(cls, value: list[str]) -> list[str]:
        unknown = [m for m in value if m not in ALL_MODELS]
        if unknown:
            raise ValueError(f"Unknown models. Choose from: {', '.join(ALL_MODELS)}")
        return list(dict.fromkeys(value))  # drop duplicates, keep order


def check_results(value: list[ModelResult]) -> list[ModelResult]:
    """Answers sent back by the browser: known models only, bounded size."""
    for r in value:
        if r.model_id not in ALL_MODELS:
            raise ValueError("Unknown model in results")
        if len(r.text) > ABSURD_ANSWER:
            raise ValueError("Answer too long")
        r.text = r.text[:JUDGE_TEXT_LIMIT]
    return value


def as_data(tag: str, items: list[str], separator: str = "\n") -> str:
    """Wrap untrusted text in <tag> ... </tag>, removing any closing tag inside it,
    so the text can't break out of the data block and pose as instructions."""
    closing = f"</{tag}>"
    body = separator.join(item.replace(closing, "") for item in items)
    return f"<{tag}>\n{body}\n</{tag}>"
