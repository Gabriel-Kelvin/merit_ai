from __future__ import annotations

import secrets

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from app.auth import SESSION_COOKIE, SESSION_SECONDS, create_session, read_session

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class AuthUser(BaseModel):
    username: str


@router.post("/login", response_model=AuthUser, summary="Log in to the demo")
def login(credentials: LoginRequest, request: Request, response: Response) -> AuthUser:
    settings = request.app.state.settings
    valid_username = secrets.compare_digest(
        credentials.username, settings.merit_demo_username
    )
    valid_password = secrets.compare_digest(
        credentials.password, settings.merit_demo_password
    )
    if not (valid_username and valid_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
        )
    response.set_cookie(
        SESSION_COOKIE,
        create_session(settings.merit_demo_username, settings.merit_session_secret),
        httponly=True,
        samesite="lax",
        secure=settings.environment != "development",
        max_age=SESSION_SECONDS,
        path="/",
    )
    return AuthUser(username=settings.merit_demo_username)


@router.get("/me", response_model=AuthUser, summary="Read the active demo session")
def me(request: Request) -> AuthUser:
    settings = request.app.state.settings
    username = read_session(
        request.cookies.get(SESSION_COOKIE), settings.merit_session_secret
    )
    if username != settings.merit_demo_username:
        raise HTTPException(status_code=401, detail="Not logged in.")
    return AuthUser(username=username)


@router.post("/logout", summary="Log out")
def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(SESSION_COOKIE, path="/", samesite="lax")
    return {"logged_out": True}
