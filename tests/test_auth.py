"""Login tests: run with `uv run pytest`."""

import base64

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def basic(password: str, user: str = "team") -> dict[str, str]:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


@pytest.fixture(autouse=True)
def reset(monkeypatch):
    import app.auth as auth
    auth._failures.clear()
    monkeypatch.setenv("DASHBOARD_PASSWORD", "correct horse")
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)


def test_health_is_always_open():
    assert client.get("/health").status_code == 200


def test_dashboard_asks_for_password():
    r = client.get("/dashboard")
    assert r.status_code == 401
    assert r.headers["www-authenticate"].startswith("Basic")


def test_wrong_password_refused():
    assert client.get("/models", headers=basic("wrong")).status_code == 401


def test_right_password_any_username():
    assert client.get("/models", headers=basic("correct horse", user="rihanna")).status_code == 200


def test_model_endpoints_protected():
    r = client.post("/agents/progress_reporter/run", json={"commit_messages": ["x"]})
    assert r.status_code == 401


def test_garbage_header_refused():
    r = client.get("/models", headers={"Authorization": "Basic !!!notbase64"})
    assert r.status_code == 401


def test_lockout_after_ten_failures():
    for _ in range(10):
        client.get("/models", headers=basic("wrong"))
    r = client.get("/models", headers=basic("correct horse"))
    assert r.status_code == 429


def test_spoofed_forwarded_for_does_not_bypass_lockout():
    for i in range(10):
        client.get("/models", headers={**basic("wrong"), "X-Forwarded-For": f"1.2.3.{i}, 9.9.9.9"})
    r = client.get("/models", headers={**basic("correct horse"), "X-Forwarded-For": "5.5.5.5, 9.9.9.9"})
    assert r.status_code == 429


def test_railway_without_password_fails_closed(monkeypatch):
    monkeypatch.delenv("DASHBOARD_PASSWORD")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    assert client.get("/dashboard").status_code == 503
    assert client.get("/health").status_code == 200


def test_local_without_password_is_open(monkeypatch):
    monkeypatch.delenv("DASHBOARD_PASSWORD")
    assert client.get("/models").status_code == 200
