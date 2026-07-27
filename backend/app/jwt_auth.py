from __future__ import annotations

import hashlib
import hmac
import os
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ISSUER = os.getenv("JWT_ISSUER", "edi-835-converter")
JWT_ACCESS_AUD = "era-lookup"
JWT_REFRESH_AUD = "era-refresh"
JWT_ACCESS_EXPIRE = int(os.getenv("JWT_EXPIRE_SECONDS", "3600"))
JWT_REFRESH_EXPIRE = int(os.getenv("JWT_REFRESH_EXPIRE_SECONDS", "86400"))
JWT_ALGORITHM = "HS256"

_bearer = HTTPBearer(auto_error=False)

# JWT_CLIENTS=client_id:secret,other_id:other_secret
_CLIENTS: dict[str, bytes] = {}
for entry in os.getenv("JWT_CLIENTS", "").split(","):
    entry = entry.strip()
    if not entry or ":" not in entry:
        continue
    cid, _, secret = entry.partition(":")
    cid, secret = cid.strip(), secret.strip()
    if cid and secret:
        _CLIENTS[cid] = hashlib.sha256(secret.encode()).digest()


def _require_secret() -> str:
    if not JWT_SECRET:
        raise HTTPException(status_code=503, detail="JWT authentication is not configured.")
    return JWT_SECRET


def authenticate_client(client_id: str, client_secret: str) -> None:
    """Validate client credentials. Raises HTTPException on failure."""
    if not client_id or not client_secret:
        raise HTTPException(status_code=401, detail="Invalid client credentials.")

    stored = _CLIENTS.get(client_id)
    if stored is None:
        raise HTTPException(status_code=401, detail="Invalid client credentials.")

    incoming = hashlib.sha256(client_secret.encode()).digest()
    if not hmac.compare_digest(incoming, stored):
        raise HTTPException(status_code=401, detail="Invalid client credentials.")


def create_access_token(client_id: str) -> tuple[str, int]:
    secret = _require_secret()
    expires_in = JWT_ACCESS_EXPIRE
    now = datetime.now(timezone.utc)
    payload = {
        "sub": client_id,
        "iss": JWT_ISSUER,
        "aud": JWT_ACCESS_AUD,
        "typ": "access",
        "scope": "era:read",
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    token = jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)
    return token, expires_in


def create_refresh_token(client_id: str) -> tuple[str, str, datetime, int]:
    secret = _require_secret()
    expires_in = JWT_REFRESH_EXPIRE
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=expires_in)
    jti = str(uuid.uuid4())
    payload = {
        "sub": client_id,
        "iss": JWT_ISSUER,
        "aud": JWT_REFRESH_AUD,
        "typ": "refresh",
        "jti": jti,
        "iat": now,
        "exp": expires_at,
    }
    token = jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)
    return token, jti, expires_at, expires_in


def decode_access_token(token: str) -> dict:
    secret = _require_secret()
    try:
        return jwt.decode(
            token,
            secret,
            algorithms=[JWT_ALGORITHM],
            audience=JWT_ACCESS_AUD,
            issuer=JWT_ISSUER,
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Token expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid token.") from exc


def decode_refresh_token(token: str) -> dict:
    secret = _require_secret()
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[JWT_ALGORITHM],
            audience=JWT_REFRESH_AUD,
            issuer=JWT_ISSUER,
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=401,
            detail="Refresh token expired. Re-authenticate with client credentials.",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid refresh token.") from exc

    if payload.get("typ") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token.")

    jti = payload.get("jti")
    if not jti:
        raise HTTPException(status_code=401, detail="Invalid refresh token.")

    return payload


def validate_bearer_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")

    payload = decode_access_token(credentials.credentials)
    if payload.get("typ") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type.")

    client_id = payload.get("sub")
    if not client_id:
        raise HTTPException(status_code=401, detail="Invalid token.")

    return str(client_id)
