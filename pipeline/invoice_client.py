from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

BILLING_API_ENABLED = os.getenv("BILLING_API_ENABLED", "true").lower() == "true"
BILLING_API_BASE_URL = os.getenv(
    "BILLING_API_BASE_URL",
    "http://10.103.0.203:94/api/BillingManagement/Billing",
)
BILLING_API_TIMEOUT = float(os.getenv("BILLING_API_TIMEOUT", "15"))
BILLING_API_RETRIES = int(os.getenv("BILLING_API_RETRIES", "2"))

# Circuit breaker — trips on connection/timeout/5xx failures only (server-health
# signals), never on 4xx (that just means "server is up, data not found").
BILLING_API_BREAKER_THRESHOLD = int(os.getenv("BILLING_API_BREAKER_THRESHOLD", "5"))
BILLING_API_BREAKER_COOLDOWN_SECONDS = float(
    os.getenv("BILLING_API_BREAKER_COOLDOWN_SECONDS", "60")
)

logger = logging.getLogger("pipeline.invoice_client")

_breaker_lock = threading.Lock()
_breaker_failures = 0
_breaker_opened_at: Optional[float] = None


def _breaker_is_open() -> bool:
    """True if the breaker is OPEN and still within its cooldown window.

    Once cooldown elapses, this returns False (half-open) so exactly one
    probe call is allowed through to test if the API has recovered.
    """
    with _breaker_lock:
        if _breaker_opened_at is None:
            return False
        return (time.monotonic() - _breaker_opened_at) < BILLING_API_BREAKER_COOLDOWN_SECONDS


def _breaker_record_success() -> None:
    global _breaker_failures, _breaker_opened_at
    with _breaker_lock:
        if _breaker_opened_at is not None or _breaker_failures > 0:
            logger.info("Billing API circuit breaker CLOSED — service healthy again")
        _breaker_failures = 0
        _breaker_opened_at = None


def _breaker_record_failure() -> None:
    global _breaker_failures, _breaker_opened_at
    with _breaker_lock:
        _breaker_failures += 1
        if _breaker_failures >= BILLING_API_BREAKER_THRESHOLD and _breaker_opened_at is None:
            _breaker_opened_at = time.monotonic()
            logger.error(
                "Billing API circuit breaker OPEN after %d consecutive failures — "
                "skipping calls for %ss",
                _breaker_failures, BILLING_API_BREAKER_COOLDOWN_SECONDS,
            )


def fetch_invoice(claim_id: str, service_date: str, receiver_id: str) -> dict:
    """Call the Billing API for one (claim_id, service_date) pair.

    Never raises — failures are captured in ok/error so a bad call
    never blocks the ERA save.
    """
    fetched_at = datetime.now(timezone.utc).isoformat()

    if not BILLING_API_ENABLED:
        return {
            "claim_id": claim_id,
            "service_date": service_date,
            "http_status": None,
            "ok": False,
            "invoice_response": None,
            "error": "billing_api_disabled",
            "fetched_at": fetched_at,
        }

    if _breaker_is_open():
        return {
            "claim_id": claim_id,
            "service_date": service_date,
            "http_status": None,
            "ok": False,
            "invoice_response": None,
            "error": "circuit_open",
            "fetched_at": fetched_at,
        }

    params = {
        "PatientAccountNumber": claim_id,
        "DateOfService": service_date,
        "ReceiverId": receiver_id,
    }

    last_error: Optional[str] = None
    attempts = BILLING_API_RETRIES + 1
    for attempt in range(1, attempts + 1):
        try:
            resp = requests.get(BILLING_API_BASE_URL, params=params, timeout=BILLING_API_TIMEOUT)
            try:
                body = resp.json()
            except ValueError:
                body = None

            if resp.ok:
                _breaker_record_success()
                return {
                    "claim_id": claim_id,
                    "service_date": service_date,
                    "http_status": resp.status_code,
                    "ok": True,
                    "invoice_response": body,
                    "error": None,
                    "fetched_at": fetched_at,
                }

            last_error = f"http_{resp.status_code}"
            if 400 <= resp.status_code < 500:
                # Client error (bad params, not found) — server is reachable,
                # retrying won't help, and this is not a health signal.
                _breaker_record_success()
                return {
                    "claim_id": claim_id,
                    "service_date": service_date,
                    "http_status": resp.status_code,
                    "ok": False,
                    "invoice_response": body,
                    "error": last_error,
                    "fetched_at": fetched_at,
                }
            # 5xx — treat as a health failure, retry loop continues below.
        except requests.RequestException as exc:
            last_error = str(exc)
            logger.warning(
                "Billing API attempt %d/%d failed for claim_id=%s service_date=%s: %s",
                attempt, attempts, claim_id, service_date, exc,
            )

    _breaker_record_failure()
    return {
        "claim_id": claim_id,
        "service_date": service_date,
        "http_status": None,
        "ok": False,
        "invoice_response": None,
        "error": last_error,
        "fetched_at": fetched_at,
    }
