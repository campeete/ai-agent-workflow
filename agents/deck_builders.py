"""Deck builders: designed slide decks from the chosen outline.

Each builder is a third-party presentation service with its own API key.
They all get the same outline and each returns links to its own deck, so you
compare finished decks side by side, like the model round table.

| id        | Service   | How it works                                      | Key variable        |
|-----------|-----------|---------------------------------------------------|---------------------|
| presenton | Presenton | one call, waits for the deck                      | PRESENTON_API_KEY   |
| twoslides | 2Slides   | starts a job, we poll it                          | TWOSLIDES_API_KEY   |
| gamma     | Gamma     | starts a generation, we poll it (paid plan)       | GAMMA_API_KEY       |
| plusai    | Plus AI   | starts an agent session, we poll it (paid plan)   | PLUSAI_API_KEY      |

Security:
- Keys stay on the server and are only sent to their own service's fixed host.
- Poll addresses are built from our fixed base URL plus an id that must look like
  an id; we never follow a URL the service hands back (no SSRF).
- Links coming back are only shown if they are https://, so a bad response can't
  put a javascript: link on the dashboard. The server never downloads them.
- The outline goes to these companies: it is pitch content built from text that
  was already scrubbed of secrets, but don't put anything private in it.
- A daily cap on builds protects paid credits.
"""

import os
import re
import threading
import time
from dataclasses import dataclass
from datetime import date
from typing import Callable
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel

from agents.slides import Outline

POLL_EVERY_SECONDS = 4
MAX_WAIT_SECONDS = 240
DAILY_BUILD_CAP = int(os.environ.get("DECK_BUILDS_PER_DAY", "40"))
JOB_ID = re.compile(r"^[A-Za-z0-9_-]{1,120}$")


class BuildError(Exception):
    """Plain-English reason a build failed."""


class BuildResult(BaseModel):
    builder: str
    label: str
    ok: bool
    ms: int = 0
    download_url: str | None = None  # .pptx (or .pdf if that's all the service gives)
    pdf_url: str | None = None
    edit_url: str | None = None  # open the deck in the service's own editor
    error: str | None = None


class BuilderInfo(BaseModel):
    id: str
    label: str
    notes: str
    available: bool


@dataclass(frozen=True)
class Builder:
    id: str
    label: str
    key_env: str
    notes: str
    build: Callable[[httpx.Client, str, Outline], dict]


def outline_to_text(o: Outline) -> str:
    """The outline as plain markdown, which every service accepts as content."""
    parts = [f"# {o.title}"]
    for i, s in enumerate(o.slides, 1):
        parts.append(f"\n## Slide {i}: {s.title}")
        parts += [f"- {b}" for b in s.bullets]
        if s.visual and s.visual.lower() != "none":
            parts.append(f"Visual: {s.visual}")
        if s.notes:
            parts.append(f"Speaker notes: {s.notes}")
    return "\n".join(parts)


def safe_link(url: object) -> str | None:
    """Only plain https links get through to the dashboard."""
    if not isinstance(url, str) or len(url) > 2000:
        return None
    p = urlparse(url)
    return url if p.scheme == "https" and p.netloc else None


def _check(r: httpx.Response, service: str) -> dict:
    if r.status_code in (401, 403):
        raise BuildError(f"{service} rejected the API key (or the plan has no API access)")
    if r.status_code == 402:
        raise BuildError(f"{service} says the account is out of credits")
    if r.status_code == 429:
        raise BuildError(f"{service} rate limit reached; try again in a minute")
    if r.status_code >= 400:
        raise BuildError(f"{service} error {r.status_code}")
    try:
        return r.json()
    except ValueError as exc:
        raise BuildError(f"{service} sent back something that isn't JSON") from exc


def _job_id(value: object, service: str) -> str:
    if not isinstance(value, str) or not JOB_ID.match(value):
        raise BuildError(f"{service} didn't return a usable job id")
    return value


def _poll(client: httpx.Client, url: str, service: str, done: Callable[[dict], bool], failed: Callable[[dict], bool]) -> dict:
    deadline = time.monotonic() + MAX_WAIT_SECONDS
    while time.monotonic() < deadline:
        time.sleep(POLL_EVERY_SECONDS)
        data = _check(client.get(url), service)
        if failed(data):
            raise BuildError(f"{service} couldn't finish the deck")
        if done(data):
            return data
    raise BuildError(f"{service} took longer than {MAX_WAIT_SECONDS // 60} minutes")


# ---- each service -------------------------------------------------------------

def _presenton(client: httpx.Client, key: str, o: Outline) -> dict:
    client.headers["Authorization"] = f"Bearer {key}"
    data = _check(client.post("https://api.presenton.ai/api/v3/presentation/generate", json={
        "content": outline_to_text(o), "n_slides": len(o.slides), "language": "English", "export_as": "pptx",
    }), "Presenton")
    return {"download_url": data.get("path"), "edit_url": data.get("edit_path")}


def _twoslides(client: httpx.Client, key: str, o: Outline) -> dict:
    base = "https://2slides.com/api/v1"
    client.headers["Authorization"] = f"Bearer {key}"
    client.headers["x-api-key"] = key  # their docs show both styles
    body = {"userInput": outline_to_text(o), "responseLanguage": "English", "mode": "async"}
    if os.environ.get("TWOSLIDES_THEME_ID"):
        body["themeId"] = os.environ["TWOSLIDES_THEME_ID"]
    data = _check(client.post(f"{base}/slides/generate", json=body), "2Slides")
    data = data.get("data", data)
    if data.get("downloadUrl"):
        return {"download_url": data["downloadUrl"]}
    job = _job_id(data.get("jobId") or data.get("id"), "2Slides")
    def unwrap(d: dict) -> dict:
        return d.get("data", d)
    result = unwrap(_poll(client, f"{base}/jobs/{job}", "2Slides",
                          done=lambda d: bool(unwrap(d).get("downloadUrl")),
                          failed=lambda d: str(unwrap(d).get("status", "")).lower() in {"failed", "error"}))
    return {"download_url": result.get("downloadUrl")}


def _gamma(client: httpx.Client, key: str, o: Outline) -> dict:
    base = "https://public-api.gamma.app/v1.0"
    client.headers["X-API-KEY"] = key
    data = _check(client.post(f"{base}/generations", json={
        "inputText": outline_to_text(o), "textMode": "preserve", "format": "presentation",
        "numCards": len(o.slides), "exportAs": "pptx",
    }), "Gamma")
    gen = _job_id(data.get("generationId"), "Gamma")
    result = _poll(client, f"{base}/generations/{gen}", "Gamma",
                   done=lambda d: d.get("status") == "completed",
                   failed=lambda d: d.get("status") == "failed")
    return {"download_url": result.get("exportUrl"), "edit_url": result.get("gammaUrl")}


def _plusai(client: httpx.Client, key: str, o: Outline) -> dict:
    base = "https://api.plusdocs.com/r/v0"
    client.headers["Authorization"] = f"Bearer {key}"
    prompt = (f"Create a {len(o.slides)}-slide hackathon pitch deck that follows this outline exactly, "
              f"one slide per section:\n\n{outline_to_text(o)}")
    data = _check(client.post(f"{base}/agent/sessions", json={"prompt": prompt}), "Plus AI")
    session = _job_id(data.get("sessionId"), "Plus AI")
    result = _poll(client, f"{base}/agent/sessions/{session}", "Plus AI",  # our URL, not their pollingUrl
                   done=lambda d: d.get("status") == "DONE",
                   failed=lambda d: d.get("status") in {"FAILED", "ERROR", "CANCELLED"})
    return {"download_url": result.get("pptxUrl"), "pdf_url": result.get("pdfUrl")}


BUILDERS: dict[str, Builder] = {b.id: b for b in [
    Builder("presenton", "Presenton", "PRESENTON_API_KEY", "Open source; editable PPTX", _presenton),
    Builder("twoslides", "2Slides", "TWOSLIDES_API_KEY", "Credits from $5; PPTX", _twoslides),
    Builder("gamma", "Gamma", "GAMMA_API_KEY", "Needs a Gamma Pro plan or higher", _gamma),
    Builder("plusai", "Plus AI", "PLUSAI_API_KEY", "Needs a Plus AI Pro or Team plan", _plusai),
]}

_builds = {"day": date.today(), "count": 0}
_lock = threading.Lock()


def list_builders() -> list[BuilderInfo]:
    return [BuilderInfo(id=b.id, label=b.label, notes=b.notes, available=bool(os.environ.get(b.key_env)))
            for b in BUILDERS.values()]


def _reserve() -> None:
    with _lock:
        if _builds["day"] != date.today():
            _builds.update(day=date.today(), count=0)
        if _builds["count"] >= DAILY_BUILD_CAP:
            raise BuildError(f"Daily cap of {DAILY_BUILD_CAP} deck builds reached (protects paid credits)")
        _builds["count"] += 1


def build_deck(builder_id: str, outline: Outline) -> BuildResult:
    b = BUILDERS[builder_id]
    start = time.perf_counter()
    result = BuildResult(builder=b.id, label=b.label, ok=False)
    key = os.environ.get(b.key_env)
    if not key:
        result.error = f"{b.key_env} is not set on the server"
        return result
    try:
        _reserve()
        with httpx.Client(timeout=httpx.Timeout(MAX_WAIT_SECONDS, connect=15), follow_redirects=False,
                          headers={"Content-Type": "application/json", "User-Agent": "ai-agent-workflow"}) as client:
            links = b.build(client, key, outline)
    except BuildError as exc:
        result.error = str(exc)
    except httpx.TimeoutException:
        result.error = f"{b.label} took too long to answer"
    except httpx.HTTPError:
        result.error = f"Could not reach {b.label}"
    else:
        result.download_url = safe_link(links.get("download_url"))
        result.pdf_url = safe_link(links.get("pdf_url"))
        result.edit_url = safe_link(links.get("edit_url"))
        result.ok = bool(result.download_url or result.edit_url or result.pdf_url)
        if not result.ok:
            result.error = f"{b.label} finished but sent no usable link"
    result.ms = int((time.perf_counter() - start) * 1000)
    return result
