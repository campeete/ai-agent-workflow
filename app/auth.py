"""Password protection for the dashboard and every endpoint that spends AI quota.

How it works:
- The team password lives in the DASHBOARD_PASSWORD environment variable
  (Railway Variables or local .env), never in code.
- The browser shows its built-in sign-in box (HTTP Basic auth). Any username
  works; only the password is checked.
- The password is compared in constant time, so response timing can't leak it.
- After too many wrong passwords from one address, that address is blocked
  for a few minutes, which makes guessing impractical.
- /health stays open so Railway's health check keeps working.
- On Railway with no password set, everything except /health is refused, so a
  missing variable can never leave the site open by accident.
"""

import base64
import os
import secrets
import threading
import time

from fastapi import Request
from fastapi.responses import JSONResponse

OPEN_PATHS = {"/health"}
MAX_FAILURES = 10
WINDOW_SECONDS = 300

_failures: dict[str, list[float]] = {}
_lock = threading.Lock()


def _client_ip(request: Request) -> str:
    # Railway's proxy appends the real client address as the LAST entry.
    # Earlier entries can be typed by the client, so they are not trusted.
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def _blocked(ip: str, now: float) -> bool:
    with _lock:
        recent = [t for t in _failures.get(ip, []) if now - t < WINDOW_SECONDS]
        _failures[ip] = recent
        return len(recent) >= MAX_FAILURES


def _record_failure(ip: str, now: float) -> None:
    with _lock:
        _failures.setdefault(ip, []).append(now)


def _password_from(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    scheme, _, encoded = header.partition(" ")
    if scheme.lower() != "basic" or not encoded:
        return None
    try:
        decoded = base64.b64decode(encoded, validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None
    _, sep, password = decoded.partition(":")
    return password if sep else None


def _ask_for_password() -> JSONResponse:
    return JSONResponse(
        {"detail": "Sign in required"},
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="AI Agent Workflow", charset="UTF-8"'},
    )


async def require_password(request: Request, call_next):
    if request.url.path in OPEN_PATHS:
        return await call_next(request)

    expected = os.environ.get("DASHBOARD_PASSWORD", "")
    if not expected:
        if os.environ.get("RAILWAY_ENVIRONMENT"):
            # Deployed without a password: fail closed.
            return JSONResponse({"detail": "Server not configured: set DASHBOARD_PASSWORD"},
                                status_code=503)
        return await call_next(request)  # local development without a password

    ip = _client_ip(request)
    now = time.time()
    if _blocked(ip, now):
        return JSONResponse({"detail": "Too many wrong passwords. Try again in a few minutes."},
                            status_code=429)

    given = _password_from(request)
    if given is None:
        return _ask_for_password()
    if not secrets.compare_digest(given.encode("utf-8"), expected.encode("utf-8")):
        _record_failure(ip, now)
        return _ask_for_password()
    return await call_next(request)
