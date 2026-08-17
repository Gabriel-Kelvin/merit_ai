from __future__ import annotations

import secrets

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field, model_validator

from app.accounts import (
    AccountAlreadyExistsError,
    AccountServiceUnavailableError,
    InvalidCredentialsError,
)
from app.auth import SESSION_COOKIE, SESSION_SECONDS, create_session, read_session

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class AuthUser(BaseModel):
    username: str
    email: str | None = None
    name: str | None = None


class SignupRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    confirm_password: str = Field(min_length=8, max_length=200)

    @model_validator(mode="after")
    def passwords_match(self) -> SignupRequest:
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match.")
        return self


def _set_session(
    response: Response, request: Request, account_id: str, username: str
) -> None:
    settings = request.app.state.settings
    response.set_cookie(
        SESSION_COOKIE,
        create_session(account_id, username, settings.merit_session_secret),
        httponly=True,
        samesite="lax",
        secure=settings.environment != "development",
        max_age=SESSION_SECONDS,
        path="/",
    )


@router.post(
    "/signup",
    response_model=AuthUser,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
    summary="Create a candidate account",
)
def signup(payload: SignupRequest, request: Request, response: Response) -> AuthUser:
    try:
        account = request.app.state.account_service.sign_up(
            payload.name, str(payload.email), payload.password
        )
    except AccountAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except AccountServiceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    _set_session(response, request, account.id, account.email)
    return AuthUser(username=account.email, email=account.email, name=account.name)


@router.post(
    "/login",
    response_model=AuthUser,
    response_model_exclude_none=True,
    summary="Log in to Merit AI",
)
def login(credentials: LoginRequest, request: Request, response: Response) -> AuthUser:
    settings = request.app.state.settings
    is_demo_username = secrets.compare_digest(
        credentials.username, settings.merit_demo_username
    )
    is_demo_password = secrets.compare_digest(
        credentials.password, settings.merit_demo_password
    )
    if is_demo_username:
        if not is_demo_password:
            raise HTTPException(status_code=401, detail="Incorrect email or password.")
        _set_session(
            response,
            request,
            settings.merit_demo_username,
            settings.merit_demo_username,
        )
        return AuthUser(username=settings.merit_demo_username)

    try:
        account = request.app.state.account_service.sign_in(
            credentials.username, credentials.password
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except AccountServiceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    _set_session(response, request, account.id, account.email)
    return AuthUser(username=account.email, email=account.email, name=account.name)


@router.get(
    "/me",
    response_model=AuthUser,
    response_model_exclude_none=True,
    summary="Read the active session",
)
def me(request: Request) -> AuthUser:
    settings = request.app.state.settings
    principal = read_session(
        request.cookies.get(SESSION_COOKIE), settings.merit_session_secret
    )
    if not principal:
        raise HTTPException(status_code=401, detail="Not logged in.")
    return AuthUser(
        username=principal.username,
        email=principal.username if "@" in principal.username else None,
    )


@router.post("/logout", summary="Log out")
def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(SESSION_COOKIE, path="/", samesite="lax")
    return {"logged_out": True}
