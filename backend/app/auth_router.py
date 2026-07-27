from __future__ import annotations

from pydantic import BaseModel, Field

from fastapi import APIRouter, HTTPException

from .jwt_auth import (
    authenticate_client,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from .mongo_refresh import is_refresh_jti_valid, revoke_refresh_jti, save_refresh_jti

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class TokenRequest(BaseModel):
    client_id: str = Field(..., min_length=1)
    client_secret: str = Field(..., min_length=1)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


def _token_response(client_id: str) -> dict:
    access_token, expires_in = create_access_token(client_id)
    refresh_token, jti, expires_at, refresh_expires_in = create_refresh_token(client_id)
    save_refresh_jti(jti, client_id, expires_at)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "refresh_expires_in": refresh_expires_in,
    }


@router.post("/token")
def issue_token(body: TokenRequest):
    authenticate_client(body.client_id, body.client_secret)
    return _token_response(body.client_id)


@router.post("/refresh")
def refresh_token(body: RefreshRequest):
    payload = decode_refresh_token(body.refresh_token)
    jti = str(payload["jti"])
    client_id = str(payload["sub"])

    if not is_refresh_jti_valid(jti):
        raise HTTPException(status_code=401, detail="Invalid refresh token.")

    revoke_refresh_jti(jti)
    return _token_response(client_id)
