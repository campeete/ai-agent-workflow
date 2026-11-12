"""Voice tests with a fake ElevenLabs: `uv run pytest`."""

import httpx
import pytest
from fastapi.testclient import TestClient

import agents.voice as voice
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    monkeypatch.delenv("DASHBOARD_PASSWORD", raising=False)
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    monkeypatch.delenv("ELEVENLABS_VOICE_ID", raising=False)
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")
    voice._usage.update(day="", chars=0)
    voice._cached_voice.clear()


def fake_transport(handler):
    real = httpx.Client
    return lambda **kw: real(transport=httpx.MockTransport(handler), **kw)


def eleven(request):
    if request.url.path == "/v1/voices":
        return httpx.Response(200, json={"voices": [
            {"voice_id": "clone1", "category": "cloned", "labels": {"accent": "british"}},
            {"voice_id": "us1", "category": "premade", "labels": {"accent": "american"}},
            {"voice_id": "uk1", "category": "premade", "labels": {"accent": "British"}}]})
    assert request.headers["xi-api-key"] == "k"
    return httpx.Response(200, content=b"MP3" + request.url.path.encode())


def test_speaks_with_british_stock_voice(monkeypatch):
    monkeypatch.setattr(voice.httpx, "Client", fake_transport(eleven))
    r = client.post("/speak", json={"text": "The Judge picks Super."})
    assert r.status_code == 200 and r.headers["content-type"] == "audio/mpeg"
    assert r.content.endswith(b"/uk1")  # skipped the clone and the American voice


def test_configured_voice_wins(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "chosen")
    monkeypatch.setattr(voice.httpx, "Client", fake_transport(eleven))
    assert client.post("/speak", json={"text": "hi"}).content.endswith(b"/chosen")


def test_too_long_rejected():
    assert client.post("/speak", json={"text": "x" * 601}).status_code == 422


def test_missing_key(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY")
    r = client.post("/speak", json={"text": "hi"})
    assert r.status_code == 503 and "ELEVENLABS_API_KEY" in r.json()["detail"]


def test_daily_budget(monkeypatch):
    monkeypatch.setattr(voice.httpx, "Client", fake_transport(eleven))
    monkeypatch.setattr(voice, "DAILY_CHAR_BUDGET", 10)
    assert client.post("/speak", json={"text": "12345678"}).status_code == 200
    r = client.post("/speak", json={"text": "12345"})
    assert r.status_code == 503 and "budget" in r.json()["detail"]


def test_bad_key(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "v")
    monkeypatch.setattr(voice.httpx, "Client", fake_transport(lambda req: httpx.Response(401)))
    assert "rejected" in client.post("/speak", json={"text": "hi"}).json()["detail"]


def test_needs_password_when_set(monkeypatch):
    monkeypatch.setenv("DASHBOARD_PASSWORD", "pw")
    assert client.post("/speak", json={"text": "hi"}).status_code == 401
