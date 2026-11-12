"""One place for every AI model call.

All providers here speak the OpenAI chat format, so one client library
talks to all of them; only the address (base_url) and the key change.
API keys come from environment variables (Railway Variables or a local
.env), never from code.

To add a model: add one entry to MODELS. To move a model to local Ollama
later: change its provider to "ollama". Nothing else changes.
"""

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from openai import OpenAI
from pydantic import BaseModel

# Free tiers reject too many requests at once, so each provider gets a limit.
# Extra calls wait their turn instead of failing.
MAX_AT_ONCE = {"nvidia": 3, "google": 2, "openai": 4}
_slots = {name: threading.BoundedSemaphore(n) for name, n in MAX_AT_ONCE.items()}

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
    extra_body: dict = field(default_factory=dict)  # provider-specific options
    timeout: int = 25  # seconds; big models get longer
    default_on: bool = True  # ticked on the dashboard by default


MODELS: tuple[ModelSpec, ...] = (
    ModelSpec(
        id="nemotron-lightning",
        provider="nvidia",
        model="nvidia/nemotron-3.5-lightning-30b-a3b",
        label="Nemotron 3.5 Lightning",
        best_for="Fast, cheap summaries",
        cost="free tier",
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    ),
    ModelSpec(
        id="nemotron-super",
        provider="nvidia",
        model="nvidia/nemotron-3.5-super-vl-120b-a12b",
        label="Nemotron 3.5 Super",
        best_for="Careful reasoning, code, agent tasks",
        cost="free tier",
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    ),
    ModelSpec(
        id="mistral-large-4",
        timeout=60,
        provider="nvidia",
        model="mistralai/mistral-large-4-1t-a52b",
        label="Mistral Large 4",
        best_for="Strong all-rounder, clean structured answers",
        cost="free tier",
    ),
    ModelSpec(
        id="deepseek-v4-flash",
        timeout=60,
        default_on=False,  # free endpoint often hangs; tick to try it
        provider="nvidia",
        model="deepseek-ai/deepseek-v4.1-flash",
        label="DeepSeek V4.1 Flash",
        best_for="Cheap and fast, good with code",
        cost="free tier",
    ),
    ModelSpec(
        id="minimax-m3-flash",
        provider="nvidia",
        model="minimaxai/minimax-m3.1-flash",
        label="MiniMax M3.1 Flash",
        best_for="Coding, agent work, cybersecurity",
        cost="free tier",
    ),
    ModelSpec(
        id="glm-5-flash",
        timeout=60,
        default_on=False,  # free endpoint often hangs; tick to try it
        provider="nvidia",
        model="z-ai/glm-5.3-flash",
        label="GLM 5.3 Flash",
        best_for="Fast reasoning",
        cost="free tier",
    ),
    ModelSpec(
        id="gemini-4-argon",
        timeout=60,
        default_on=False,  # free tier allows very few calls
        provider="google",
        model="gemini-4-argon",
        label="Gemini 4 Argon",
        best_for="Google's strongest, careful writing",
        cost="free tier",
    ),
    ModelSpec(
        id="gemini-flash",
        timeout=60,
        provider="google",
        model="gemini-flash-latest",
        label="Gemini Flash",
        best_for="Fast general writing",
        cost="free tier",
    ),
)

MAX_OUTPUT_TOKENS = 1200  # room for models that think before answering


class ModelInfo(BaseModel):
    id: str
    label: str
    provider: str
    best_for: str
    cost: str
    available: bool  # True when its API key is set. The key itself is never returned.
    default_on: bool


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
            default_on=m.default_on,
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
    with _slots[spec.provider]:  # wait for a free slot at this provider
        return _call(spec, key, system, user)


def _call(spec: ModelSpec, key: str, system: str, user: str) -> ModelResult:
    start = time.perf_counter()
    try:
        client = OpenAI(base_url=PROVIDERS[spec.provider]["base_url"], api_key=key,
                        timeout=spec.timeout, max_retries=0)
        response = client.chat.completions.create(
            model=spec.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.3,
            max_tokens=MAX_OUTPUT_TOKENS,
            extra_body=spec.extra_body or None,
        )
        text = (response.choices[0].message.content or "").strip()
        ms = int((time.perf_counter() - start) * 1000)
        if not text:
            return ModelResult(model_id=spec.id, label=spec.label, ok=False, text="", ms=ms,
                               error="Empty answer (the model used its budget without replying)")
        return ModelResult(model_id=spec.id, label=spec.label, ok=True, text=text, ms=ms)
    except Exception as exc:  # report the error type only, never request details or keys
        return ModelResult(model_id=spec.id, label=spec.label, ok=False, text="",
                           ms=int((time.perf_counter() - start) * 1000),
                           error=_friendly_error(exc))


def _friendly_error(exc: Exception) -> str:
    name = type(exc).__name__
    hints = {
        "APITimeoutError": "Timed out (provider busy or model too slow)",
        "InternalServerError": "Provider is down or overloaded, try again soon",
        "RateLimitError": "Rate limit hit, wait a minute",
        "AuthenticationError": "API key rejected",
        "PermissionDeniedError": "API key not allowed to use this model",
        "NotFoundError": "Model name not found at this provider",
    }
    return hints.get(name, name)


def call_panel(model_ids: list[str], system: str, user: str) -> list[ModelResult]:
    """Ask several models at once. The step takes as long as the slowest model."""
    with ThreadPoolExecutor(max_workers=max(1, len(model_ids))) as pool:
        return list(pool.map(lambda mid: call_model(mid, system, user), model_ids))
