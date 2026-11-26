"""Supabase Auth token verification for protected API requests."""

from __future__ import annotations

from dataclasses import dataclass
import uuid

import requests


class InvalidAccessToken(Exception):
    """Raised when Supabase rejects or cannot identify an access token."""


class AuthProviderUnavailable(Exception):
    """Raised when Supabase Auth cannot be reached or is misconfigured."""


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    email: str | None
    access_token: str


class SupabaseAuthClient:
    def __init__(
        self,
        *,
        supabase_url: str,
        publishable_key: str,
        session: requests.Session | None = None,
    ):
        self.supabase_url = supabase_url.rstrip("/")
        self.publishable_key = publishable_key
        self.session = session or requests.Session()

    def get_user(self, access_token: str) -> AuthenticatedUser:
        if not self.supabase_url or not self.publishable_key:
            raise AuthProviderUnavailable("Supabase Auth is not configured.")
        try:
            response = self.session.get(
                f"{self.supabase_url}/auth/v1/user",
                headers={
                    "apikey": self.publishable_key,
                    "Authorization": f"Bearer {access_token}",
                },
                timeout=5,
            )
        except requests.RequestException as exc:
            raise AuthProviderUnavailable("Supabase Auth is temporarily unavailable.") from exc

        if response.status_code in {401, 403}:
            raise InvalidAccessToken("Access token is invalid or expired.")
        if response.status_code >= 500 or response.status_code == 429:
            raise AuthProviderUnavailable("Supabase Auth is temporarily unavailable.")
        if not response.ok:
            raise InvalidAccessToken("Access token could not be verified.")

        try:
            user = response.json()
            user_id = str(uuid.UUID(str(user["id"])))
        except (ValueError, KeyError, TypeError):
            raise InvalidAccessToken("Supabase returned an invalid user identity.")
        email = user.get("email") if isinstance(user, dict) else None
        return AuthenticatedUser(
            user_id=user_id,
            email=email if isinstance(email, str) else None,
            access_token=access_token,
        )
