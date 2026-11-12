"""One place for every AI model call.

All providers here speak the OpenAI chat format, so one client library
talks to all of them; only the address (base_url) and the key change.
API keys come from environment variables (Railway Variables or a local
.env), never from code.

To add a model: add one entry to MODELS. To move a model to local Ollama
later: change its provider to "ollama". Nothing else changes.
"""

import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from openai import OpenAI
from pydantic import BaseModel

PROVIDERS: dict[str, dict[str, str]] = {
    "nvidia": {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "key_env": "NVIDIA_API_KEY",
    },
    "google": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "key_env": "GEMINI_API_KEY",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "key_env": "OPENAI_API_KEY",
    },
}


@dataclass(frozen=True)
class ModelSpec:
    id: str  # short name used by the API and dashboard
    provider: str
    model: str  # the provider's own model name
    label: str
    best_for: str
    cost: str  # "free tier", "low", "medium"


MODELS: tuple[ModelSpec, ...] = (
    ModelSpec(
        id="nemotron-lightning",
        provider="nvidia",
        model="nvidia/nemotron-3.5-lightning-30b-a3b",
        label="Nemotron 3.5 Lightning",
        best_for="Fast, cheap summaries",
        cost="free tier",
    ),
    ModelSpec(
        id="nemotron-super",
        provider="nvidia",
        model="nvidia/nemotron-3.5-super-vl-120b-a12b",
        label="Nemotron 3.5 Super",
        best_for="Careful reasoning, code, agent tasks",
        cost="free tier",
    ),
    ModelSpec(
        id="gemini-flash",
        provider="google",
        model="gemini-flash-latest",
        label="Gemini Flash",
        best_for="Fast general writing",
        cost="free tier",
    ),
)

TIMEOUT_SECONDS = 45
MAX_OUTPUT_TOKENS = 800


class ModelInfo(BaseModel):
    id: str
    label: str
    provider: str
    best_for: str
    cost: str
    available: bool  # True when its API key is set. The key itself is never returned.


class ModelResult(BaseModel):
    model_id: str
    label: str
    ok: bool
    text: str
    ms: int
    error: str | None = None


def get_model(model_id: str) -> ModelSpec | None:
    return next((m for m in MODELS if m.id == model_id), None)


def _key_for(spec: ModelSpec) -> str | None:
    return os.environ.get(PROVIDERS[spec.provider]["key_env"]) or None


def list_models() -> list[ModelInfo]:
    return [
        ModelInfo(
            id=m.id,
            label=m.label,
            provider=m.provider,
            best_for=m.best_for,
            cost=m.cost,
            available=_key_for(m) is not None,
        )
        for m in MODELS
    ]


def call_model(model_id: str, system: str, user: str) -> ModelResult:
    """Ask one model. Never raises: failures come back as ok=False with a short reason."""
    spec = get_model(model_id)
    if spec is None:
        return ModelResult(model_id=model_id, label=model_id, ok=False, text="", ms=0,
                           error="Unknown model")
    key = _key_for(spec)
    if key is None:
        env = PROVIDERS[spec.provider]["key_env"]
        return ModelResult(model_id=spec.id, label=spec.label, ok=False, text="", ms=0,
                           error=f"{env} is not set")
    start = time.perf_counter()
    try:
        client = OpenAI(base_url=PROVIDERS[spec.provider]["base_url"], api_key=key,
                        timeout=TIMEOUT_SECONDS, max_retries=1)
        response = client.chat.completions.create(
            model=spec.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.3,
            max_tokens=MAX_OUTPUT_TOKENS,
        )
        text = (response.choices[0].message.content or "").strip()
        return ModelResult(model_id=spec.id, label=spec.label, ok=True, text=text,
                           ms=int((time.perf_counter() - start) * 1000))
    except Exception as exc:  # report the error type only, never request details or keys
        return ModelResult(model_id=spec.id, label=spec.label, ok=False, text="",
                           ms=int((time.perf_counter() - start) * 1000),
                           error=f"{type(exc).__name__}")


def call_panel(model_ids: list[str], system: str, user: str) -> list[ModelResult]:
    """Ask several models at once. The step takes as long as the slowest model."""
    with ThreadPoolExecutor(max_workers=max(1, len(model_ids))) as pool:
        return list(pool.map(lambda mid: call_model(mid, system, user), model_ids))
