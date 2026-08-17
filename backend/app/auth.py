from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
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


@dataclass(frozen=True)
class SessionPrincipal:
    account_id: str
    username: str


def create_session(account_id: str, username: str, secret: str) -> str:
    return _encode(
        {
            "sub": account_id,
            "username": username,
            "exp": int(time.time()) + SESSION_SECONDS,
        },
        secret,
    )


def read_session(token: str | None, secret: str) -> SessionPrincipal | None:
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
    account_id = payload.get("sub")
    username = payload.get("username", account_id)
    if not isinstance(account_id, str) or not isinstance(username, str):
        return None
    return SessionPrincipal(account_id=account_id, username=username)


def require_user(
    request: Request,
    merit_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> str:
    settings = request.app.state.settings
    principal = read_session(merit_session, settings.merit_session_secret)
    if not principal:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please log in to continue.",
        )
    return principal.account_id


# Kept temporarily as an import-compatible alias for extensions built against Merit v1.
require_demo_user = require_user
