from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path(os.getenv("AUDIT_LOG_PATH", "audit.log"))


def write(
    *,
    client_ip: str,
    key_id: str,
    trace_number: str,
    status_code: int,
    match_count: int,
    latency_ms: float,
) -> None:
    entry = {
        "ts":           datetime.now(timezone.utc).isoformat(),
        "ip":           client_ip,
        "key_id":       key_id,
        "trace_number": trace_number,
        "status":       status_code,
        "matches":      match_count,
        "latency_ms":   round(latency_ms, 2),
    }
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass  # Audit log failure must never crash the request
