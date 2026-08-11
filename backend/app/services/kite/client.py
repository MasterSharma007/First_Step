"""Kite Connect session/auth wrapper (SRD §2, §10).

`kite_api_key`/`kite_api_secret` come from your Kite Connect app
(https://developers.kite.trade/apps). The access token is generated fresh
every trading day via the login flow below - it is NOT the same as the API
secret and should never be hardcoded long-term.

Login flow:
  1. GET `login_url()` -> user logs in on Kite, gets redirected to
     `kite_redirect_url` with a `request_token` query param.
  2. POST that token to `/api/v1/kite/callback` (see
     `app/api/v1/endpoints/kite.py`), which calls `generate_session()` and
     stores the resulting access token (e.g. in Redis / .env) for the day.
"""

from __future__ import annotations

from functools import lru_cache

from kiteconnect import KiteConnect

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class KiteClientError(RuntimeError):
    pass


class KiteClient:
    def __init__(self, api_key: str, api_secret: str, access_token: str = ""):
        if not api_key or not api_secret:
            raise KiteClientError(
                "KITE_API_KEY / KITE_API_SECRET are not set. Add them to backend/.env "
                "(see backend/.env.example)."
            )
        self.api_key = api_key
        self.api_secret = api_secret
        self.kite = KiteConnect(api_key=api_key)
        if access_token:
            self.kite.set_access_token(access_token)

    def login_url(self) -> str:
        return self.kite.login_url()

    def generate_session(self, request_token: str) -> dict:
        """Exchange a login request_token for an access token. Call once
        per trading day after the user completes the Kite login redirect."""
        try:
            data = self.kite.generate_session(request_token, api_secret=self.api_secret)
        except Exception as exc:  # kiteconnect raises its own exception hierarchy
            logger.error("kite_session_generation_failed", error=str(exc))
            raise KiteClientError(str(exc)) from exc
        self.kite.set_access_token(data["access_token"])
        return data

    def set_access_token(self, access_token: str) -> None:
        self.kite.set_access_token(access_token)

    def profile(self) -> dict:
        return self.kite.profile()


@lru_cache
def get_kite_client() -> KiteClient:
    settings = get_settings()
    return KiteClient(
        api_key=settings.kite_api_key,
        api_secret=settings.kite_api_secret,
        access_token=settings.kite_access_token,
    )
