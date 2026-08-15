from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Annotated

from fastapi import Cookie, HTTPException, Request, status

SESSION_COOKIE = "merit_session"
SESSION_SECONDS = 8 * 60 * 60


def _encode(payload: dict, secret: str) -> str:
    body = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode()
    ).decode().rstrip("=")
    signature = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{signature}"


def create_session(username: str, secret: str) -> str:
    return _encode({"sub": username, "exp": int(time.time()) + SESSION_SECONDS}, secret)


def read_session(token: str | None, secret: str) -> str | None:
    if not token or "." not in token:
        return None
    body, supplied_signature = token.rsplit(".", 1)
    expected_signature = hmac.new(
        secret.encode(), body.encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(supplied_signature, expected_signature):
        return None
    try:
        padded = body + "=" * (-len(body) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode())
    except (ValueError, TypeError, json.JSONDecodeError):
        return None
    if payload.get("exp", 0) <= int(time.time()):
        return None
    username = payload.get("sub")
    return username if isinstance(username, str) else None


def require_demo_user(
    request: Request,
    merit_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> str:
    settings = request.app.state.settings
    username = read_session(merit_session, settings.merit_session_secret)
    if username != settings.merit_demo_username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please log in to continue.",
        )
    return username
