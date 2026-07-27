from __future__ import annotations

import os
import threading
from collections import deque
from time import time

from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()

# ── In-memory rate limiter ────────────────────────────────────────────────────
_rate_store: dict[str, deque] = {}
_lock = threading.Lock()

MAX_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))
WINDOW_SECS = int(os.getenv("RATE_LIMIT_WINDOW", "60"))


def check_rate_limit(client_id: str) -> None:
    """Raise 429 if client_id exceeds MAX_REQUESTS within WINDOW_SECS."""
    now = time()
    with _lock:
        if client_id not in _rate_store:
            _rate_store[client_id] = deque()
        dq = _rate_store[client_id]
        while dq and dq[0] < now - WINDOW_SECS:
            dq.popleft()
        if len(dq) >= MAX_REQUESTS:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Max {MAX_REQUESTS} requests per {WINDOW_SECS}s.",
                headers={"Retry-After": str(WINDOW_SECS)},
            )
        dq.append(now)
