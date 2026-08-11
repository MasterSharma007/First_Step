"""Kite Connect login handshake (SRD §2 / §10) - generates the daily access
token. See `app/services/kite/client.py` for the full flow explanation."""

from fastapi import APIRouter, Depends, HTTPException

from app.services.kite.client import KiteClient, KiteClientError, get_kite_client

router = APIRouter(prefix="/kite", tags=["kite"])


@router.get("/login-url")
async def login_url(client: KiteClient = Depends(get_kite_client)) -> dict:
    return {"login_url": client.login_url()}


@router.get("/callback")
async def callback(request_token: str, client: KiteClient = Depends(get_kite_client)) -> dict:
    try:
        session = client.generate_session(request_token)
    except KiteClientError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "access_token": session["access_token"],
        "note": "Store this in backend/.env as KITE_ACCESS_TOKEN - it is valid for today only.",
    }
