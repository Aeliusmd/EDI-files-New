from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.errors import BulkWriteError

from .invoice_client import fetch_invoice

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "edi835")
ERA_COLLECTION = "era_payments"

logger = logging.getLogger("pipeline.mongo_save")


def _collection() -> Collection:
    client: MongoClient = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    return db[ERA_COLLECTION]


def init_era_collection() -> None:
    """Create the uniqueness safety net on (source, source_filename, era_index).

    Multiple app-server instances can run the poller concurrently against the
    same MongoDB (active-active deployment). is_seen()/mark_seen() in
    tracker.py is a check-then-act pair, not atomic, so two instances can both
    see a brand-new file as "unseen" and both attempt to save it. This unique
    index turns that race into a rejected duplicate-key error on the second
    insert instead of a silent duplicate ERA document.
    """
    col = _collection()
    col.create_index(
        [("source", ASCENDING), ("source_filename", ASCENDING), ("era_index", ASCENDING)],
        name="unique_era",
        unique=True,
        background=True,
    )


def _unique_claim_service_pairs(rows: list[dict]) -> list[tuple[str, str]]:
    """Dedupe (claim_id, service_date) pairs from a transaction's flat rows.

    Rows missing either value are skipped — the Billing API requires both.
    """
    seen: set[tuple[str, str]] = set()
    pairs: list[tuple[str, str]] = []
    for row in rows:
        claim_id = row.get("claim_id")
        service_date = row.get("service_date")
        if not claim_id or not service_date:
            continue
        key = (claim_id, service_date)
        if key in seen:
            continue
        seen.add(key)
        pairs.append(key)
    return pairs


def _fetch_invoice_data(
    pairs: list[tuple[str, str]], receiver_id: str
) -> tuple[list[dict], dict]:
    """Call the Billing API for each pair and flatten successful responses.

    invoice_data stays a flat list of raw Billing API records (unchanged
    format — no wrapper metadata). Separately, invoice_fetch_status tracks
    what happened to every pair, split into:
      - successful : call succeeded, data attached
      - not_found  : 4xx (server reachable, no invoice for this claim/date —
                     a normal business outcome, not a health problem)
      - failed     : 5xx / timeout / connection error / circuit-open /
                     disabled — a real API-health problem, detailed in
                     "failures" so it's distinguishable from not_found
                     without having to grep log files.
    """
    invoice_data: list[dict] = []
    status = {
        "total_pairs": len(pairs),
        "successful": 0,
        "not_found": 0,
        "failed": 0,
        "failures": [],
    }

    for claim_id, service_date in pairs:
        result = fetch_invoice(claim_id, service_date, receiver_id)

        if result["ok"]:
            status["successful"] += 1
            response = result["invoice_response"]
            if isinstance(response, list):
                invoice_data.extend(response)
            elif response is not None:
                invoice_data.append(response)
            continue

        http_status = result["http_status"]
        if http_status is not None and 400 <= http_status < 500:
            status["not_found"] += 1
        else:
            status["failed"] += 1
            status["failures"].append(
                {
                    "claim_id": claim_id,
                    "service_date": service_date,
                    "error": result["error"],
                }
            )

    return invoice_data, status


def save_era_file(source: str, source_filename: str, parsed: dict) -> int:
    """Persist each transaction from a parsed 835 file as a separate MongoDB document.

    Args:
        source: Logical source name (e.g. "Matrix", "DMS").
        source_filename: Original filename on the SFTP server.
        parsed: Output of parse_835_text() — must contain keys:
                summary, envelope, transactions, flat_rows, file_type.

    Returns:
        Number of documents inserted.
    """
    summary = parsed.get("summary", {})
    transactions: list[dict] = parsed.get("transactions", [])
    flat_rows: list[dict] = parsed.get("flat_rows", [])
    file_type: str = parsed.get("file_type", "")
    envelope: dict = parsed.get("envelope", {})

    col = _collection()
    docs = []

    for era_index, transaction in enumerate(transactions, start=1):
        payment = transaction.get("payment", {})
        payer   = transaction.get("payer", {})
        payee   = transaction.get("payee", {})

        txn_flat_rows = [
            r for r in flat_rows
            if r.get("transaction_no") == era_index
        ]

        receiver_id = envelope.get("receiver_id", "")
        invoice_data, invoice_fetch_status = _fetch_invoice_data(
            _unique_claim_service_pairs(txn_flat_rows), receiver_id
        )

        doc = {
            "source": source,
            "source_filename": source_filename,
            "era_index": era_index,
            "imported_at": datetime.now(timezone.utc).isoformat(),
            "trace_number":   payment.get("trace_number", ""),
            "payment_date":   payment.get("date", ""),
            "payment_method": payment.get("method", ""),
            "payment_amount": payment.get("amount", ""),
            "payer_name": payer.get("name", ""),
            "payer_id":   payer.get("id", ""),
            "payee_name": payee.get("name", ""),
            "payee_id":   payee.get("id", ""),
            "claim_count": len(transaction.get("claims", [])),
            "transaction": transaction,
            "flat_rows": txn_flat_rows,
            "file_type": file_type,
            "envelope": envelope,
            "invoice_data": invoice_data,
            "invoice_fetch_status": invoice_fetch_status,
        }
        docs.append(doc)

    if not docs:
        return 0

    try:
        result = col.insert_many(docs, ordered=False)
        return len(result.inserted_ids)
    except BulkWriteError as bwe:
        write_errors = bwe.details.get("writeErrors", [])
        duplicate_errors = [e for e in write_errors if e.get("code") == 11000]
        other_errors = [e for e in write_errors if e.get("code") != 11000]
        if other_errors:
            raise

        inserted = bwe.details.get("nInserted", 0)
        logger.warning(
            "save_era_file: %d duplicate ERA doc(s) rejected by unique index for %s/%s "
            "(concurrent poller instance likely already saved them)",
            len(duplicate_errors), source, source_filename,
        )
        return inserted
