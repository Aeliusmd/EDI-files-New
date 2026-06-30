from __future__ import annotations

import hashlib
import hmac
import os
import threading
from collections import deque
from time import time

from dotenv import load_dotenv
from fastapi import Header, HTTPException

load_dotenv()

# Comma-separated list of valid keys, e.g. "era_live_abc,era_live_xyz"
_RAW_KEYS: list[str] = [
    k.strip() for k in os.getenv("API_KEYS", "").split(",") if k.strip()
]
_HASHED_KEYS: list[bytes] = [
    hashlib.sha256(k.encode()).digest() for k in _RAW_KEYS
]


def _key_id(key: str) -> str:
    """Safe identifier for logs — first 8 chars only, never the full key."""
    return key[:8] + "..."


def validate_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """FastAPI dependency — validates X-API-Key header. Returns key_id for logging."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing API key.")

    incoming_hash = hashlib.sha256(x_api_key.encode()).digest()

    for stored_hash in _HASHED_KEYS:
        if hmac.compare_digest(incoming_hash, stored_hash):
            return _key_id(x_api_key)

    raise HTTPException(status_code=401, detail="Invalid API key.")


# ── In-memory rate limiter ────────────────────────────────────────────────────
_rate_store: dict[str, deque] = {}
_lock = threading.Lock()

MAX_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))
WINDOW_SECS  = int(os.getenv("RATE_LIMIT_WINDOW",   "60"))


def check_rate_limit(key_id: str) -> None:
    """Raise 429 if key_id exceeds MAX_REQUESTS within WINDOW_SECS."""
    now = time()
    with _lock:
        if key_id not in _rate_store:
            _rate_store[key_id] = deque()
        dq = _rate_store[key_id]
        while dq and dq[0] < now - WINDOW_SECS:
            dq.popleft()
        if len(dq) >= MAX_REQUESTS:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Max {MAX_REQUESTS} requests per {WINDOW_SECS}s.",
                headers={"Retry-After": str(WINDOW_SECS)},
            )
        dq.append(now)
