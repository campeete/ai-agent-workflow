"""Text to speech for the Judge's verdict (ElevenLabs).

- The API key stays on the server (ELEVENLABS_API_KEY); the browser only ever
  receives the finished audio.
- Voice: ELEVENLABS_VOICE_ID if set, otherwise the first stock voice in your
  ElevenLabs library labelled with a British accent. Stock library voices only,
  never a clone of a real person.
- Cost guard: each request is capped at MAX_CHARS, and the whole server at
  DAILY_CHAR_BUDGET characters per day, so a bug or a stranger can't drain credits.
"""

import os
import threading
import time

import httpx

API = "https://api.elevenlabs.io/v1"
MAX_CHARS = 600
DAILY_CHAR_BUDGET = 20_000
TIMEOUT_SECONDS = 30

_lock = threading.Lock()
_usage = {"day": "", "chars": 0}
_cached_voice: dict[str, str] = {}


class VoiceError(Exception):
    """Plain-English reason the verdict couldn't be spoken."""


def _key() -> str:
    key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not key:
        raise VoiceError("ELEVENLABS_API_KEY is not set")
    return key


def _reserve(chars: int) -> None:
    today = time.strftime("%Y-%m-%d")
    with _lock:
        if _usage["day"] != today:
            _usage.update(day=today, chars=0)
        if _usage["chars"] + chars > DAILY_CHAR_BUDGET:
            raise VoiceError("Daily voice budget used up; try again tomorrow")
        _usage["chars"] += chars


def _british_voice(client: httpx.Client, key: str) -> str:
    configured = os.environ.get("ELEVENLABS_VOICE_ID", "")
    if configured:
        return configured
    if "id" in _cached_voice:
        return _cached_voice["id"]
    r = client.get(f"{API}/voices", headers={"xi-api-key": key})
    if r.status_code in (401, 403):
        raise VoiceError("Key can't list voices: set ELEVENLABS_VOICE_ID to a British voice id")
    r.raise_for_status()
    for v in r.json().get("voices", []):
        labels = {k: str(val).lower() for k, val in (v.get("labels") or {}).items()}
        if "british" in labels.get("accent", "") and v.get("category") != "cloned":
            _cached_voice["id"] = v["voice_id"]
            return v["voice_id"]
    raise VoiceError("No British voice found: set ELEVENLABS_VOICE_ID")


def speak(text: str) -> bytes:
    """Return MP3 audio of `text` (trimmed to MAX_CHARS)."""
    text = " ".join(text.split())[:MAX_CHARS]
    if not text:
        raise VoiceError("Nothing to say")
    key = _key()
    _reserve(len(text))
    model = os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2")
    try:
        with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
            voice = _british_voice(client, key)
            r = client.post(
                f"{API}/text-to-speech/{voice}",
                headers={"xi-api-key": key, "accept": "audio/mpeg"},
                json={"text": text, "model_id": model},
            )
    except httpx.TimeoutException as exc:
        raise VoiceError("Voice service timed out") from exc
    except httpx.HTTPError as exc:
        raise VoiceError("Could not reach the voice service") from exc
    if r.status_code in (401, 403):
        raise VoiceError("ElevenLabs rejected the key or its permissions")
    if r.status_code == 429:
        raise VoiceError("ElevenLabs rate limit or quota reached")
    if r.status_code >= 400:
        raise VoiceError(f"ElevenLabs error {r.status_code}")
    return r.content
