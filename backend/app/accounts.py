from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass
from threading import RLock

from supabase import Client, create_client


class AccountAlreadyExistsError(ValueError):
    pass


class InvalidCredentialsError(ValueError):
    pass


class AccountServiceUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class AccountIdentity:
    id: str
    email: str
    name: str | None = None


class MemoryAccountService:
    """Small in-memory account provider used by local development and tests."""

    def __init__(self) -> None:
        self._accounts: dict[str, tuple[AccountIdentity, bytes, bytes]] = {}
        self._lock = RLock()

    def sign_up(self, name: str, email: str, password: str) -> AccountIdentity:
        normalized_email = email.strip().lower()
        with self._lock:
            if normalized_email in self._accounts:
                raise AccountAlreadyExistsError("An account with this email already exists.")
            salt = os.urandom(16)
            password_hash = hashlib.pbkdf2_hmac(
                "sha256", password.encode(), salt, 310_000
            )
            identity = AccountIdentity(
                id=f"local:{normalized_email}", email=normalized_email, name=name.strip()
            )
            self._accounts[normalized_email] = (identity, salt, password_hash)
            return identity

    def sign_in(self, email: str, password: str) -> AccountIdentity:
        normalized_email = email.strip().lower()
        with self._lock:
            stored = self._accounts.get(normalized_email)
        if not stored:
            raise InvalidCredentialsError("Incorrect email or password.")
        identity, salt, expected_hash = stored
        supplied_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt, 310_000
        )
        if not hmac.compare_digest(supplied_hash, expected_hash):
            raise InvalidCredentialsError("Incorrect email or password.")
        return identity


class SupabaseAccountService:
    """Server-only Supabase Auth adapter; secret keys never reach the browser."""

    def __init__(self, url: str, publishable_key: str, secret_key: str) -> None:
        if not url or not publishable_key or not secret_key:
            raise ValueError("Supabase URL, publishable key, and secret key are required")
        self.url = url
        self.publishable_key = publishable_key
        self.secret_key = secret_key

    def _admin_client(self) -> Client:
        return create_client(self.url, self.secret_key)

    def _public_client(self) -> Client:
        return create_client(self.url, self.publishable_key)

    def sign_up(self, name: str, email: str, password: str) -> AccountIdentity:
        normalized_email = email.strip().lower()
        try:
            response = self._admin_client().auth.admin.create_user(
                {
                    "email": normalized_email,
                    "password": password,
                    "email_confirm": True,
                    "user_metadata": {"name": name.strip()},
                }
            )
        except Exception as exc:
            message = str(exc).lower()
            if "already" in message or "registered" in message or "exists" in message:
                raise AccountAlreadyExistsError(
                    "An account with this email already exists."
                ) from exc
            raise AccountServiceUnavailableError(
                "Account creation is temporarily unavailable."
            ) from exc
        user = response.user
        if not user or not user.email:
            raise AccountServiceUnavailableError(
                "Account creation did not return a valid user."
            )
        metadata = user.user_metadata or {}
        return AccountIdentity(
            id=str(user.id),
            email=user.email,
            name=metadata.get("name") if isinstance(metadata.get("name"), str) else None,
        )

    def sign_in(self, email: str, password: str) -> AccountIdentity:
        normalized_email = email.strip().lower()
        try:
            response = self._public_client().auth.sign_in_with_password(
                {"email": normalized_email, "password": password}
            )
        except Exception as exc:
            message = str(exc).lower()
            if any(term in message for term in ("invalid", "credentials", "password")):
                raise InvalidCredentialsError("Incorrect email or password.") from exc
            raise AccountServiceUnavailableError(
                "Sign in is temporarily unavailable."
            ) from exc
        user = response.user
        if not user or not user.email:
            raise InvalidCredentialsError("Incorrect email or password.")
        metadata = user.user_metadata or {}
        return AccountIdentity(
            id=str(user.id),
            email=user.email,
            name=metadata.get("name") if isinstance(metadata.get("name"), str) else None,
        )
