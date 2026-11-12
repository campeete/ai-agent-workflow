"""Round-table judge endpoint: `uv run pytest`."""

import pytest
from fastapi.testclient import TestClient

import agents.referee as referee
from agents.models import ModelResult
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def open_locally(monkeypatch):
    monkeypatch.delenv("DASHBOARD_PASSWORD", raising=False)
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)


def r(mid, text="x", ok=True):
    return {"model_id": mid, "label": mid, "ok": ok, "text": text, "ms": 1}


def test_judges_collected_answers(monkeypatch):
    monkeypatch.setattr(referee, "call_model", lambda m, s, u: ModelResult(
        model_id=m, label=m, ok=True, text='{"best":"B","reason":"ok"}', ms=1))
    body = {"commit_messages": ["c"], "results": [r("nemotron-lightning"), r("nemotron-super")]}
    out = client.post("/agents/progress_reporter/judge", json=body).json()
    assert out["ok"] and out["best_model"] == "nemotron-super" and out["referee_model"] == "nemotron-bolt"


def test_rejects_unknown_or_referee_model():
    for bad in ["gpt-9", "nemotron-bolt"]:
        body = {"commit_messages": ["c"], "results": [r(bad), r("nemotron-super")]}
        assert client.post("/agents/progress_reporter/judge", json=body).status_code == 422


def test_rejects_absurdly_long_answer():
    body = {"commit_messages": ["c"], "results": [r("nemotron-lightning", "x" * 20_001), r("nemotron-super")]}
    assert client.post("/agents/progress_reporter/judge", json=body).status_code == 422


def test_trims_wordy_answer_instead_of_rejecting(monkeypatch):
    seen = {}

    def fake(m, s, u):
        seen["prompt"] = u
        return ModelResult(model_id=m, label=m, ok=True, text='{"best":"A","reason":"ok"}', ms=1)

    monkeypatch.setattr(referee, "call_model", fake)
    body = {"commit_messages": ["c"], "results": [r("nemotron-lightning", "x" * 9000), r("nemotron-super")]}
    resp = client.post("/agents/progress_reporter/judge", json=body)
    assert resp.status_code == 200 and resp.json()["ok"]
    assert "x" * 6001 not in seen["prompt"]


def test_needs_password_when_set(monkeypatch):
    monkeypatch.setenv("DASHBOARD_PASSWORD", "pw")
    body = {"commit_messages": ["c"], "results": [r("nemotron-lightning"), r("nemotron-super")]}
    assert client.post("/agents/progress_reporter/judge", json=body).status_code == 401
