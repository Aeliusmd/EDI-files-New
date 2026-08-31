"""Sync parsed 277/999 files to SQL Server and update BillingHeadersHistory."""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Generator, Iterable

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("pipeline.sql_sync")

SQL_SYNC_ENABLED = os.getenv("SQL_SYNC_ENABLED", "true").lower() == "true"
SQL_SERVER = os.getenv("CLINIC_DB_SERVER") or os.getenv("MASTER_DB_SERVER", "")
SQL_DATABASE = os.getenv("CLINIC_DB_NAME") or os.getenv("MASTER_DB_NAME", "")
SQL_USER = os.getenv("CLINIC_DB_USER") or os.getenv("MASTER_DB_USER", "")
SQL_PASSWORD = os.getenv("CLINIC_DB_PASSWORD") or os.getenv("MASTER_DB_PASSWORD", "")
SQL_DRIVER = os.getenv("CLINIC_DB_DRIVER") or os.getenv(
    "MASTER_DB_DRIVER", "ODBC Driver 17 for SQL Server"
)
SQL_CREATED_USER_ID = int(os.getenv("SQL_CREATED_USER_ID", "1"))
SQL_RECORD_STATUS_ID = int(os.getenv("SQL_RECORD_STATUS_ID", "1"))

# 277 STC category codes that mean rejected / unprocessable (X12 277).
_277_REJECTED_CATS = frozenset({"A3", "A4", "A7", "A8", "R", "E"})


def is_sql_sync_enabled() -> bool:
    return bool(
        SQL_SYNC_ENABLED
        and SQL_SERVER
        and SQL_DATABASE
        and SQL_USER
        and SQL_PASSWORD
    )


def _s(value: Any, max_len: int | None = None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if max_len is not None:
        return text[:max_len]
    return text


def _dec(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_imported_at(value: Any) -> datetime:
    text = _s(value)
    if not text:
        return datetime.utcnow()
    cleaned = text.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is not None:
            dt = dt.astimezone(tz=None).replace(tzinfo=None)
        return dt
    except ValueError:
        return datetime.utcnow()


def _control_variants(value: Any) -> list[str]:
    raw = _s(value)
    if not raw:
        return []
    variants = {raw}
    stripped = raw.lstrip("0")
    if stripped:
        variants.add(stripped)
    if raw.isdigit():
        variants.add(raw.zfill(4))
        variants.add(raw.zfill(9))
    return sorted(variants)


def _999_is_accepted(status999: str | None) -> bool | None:
    code = (_s(status999) or "").upper()
    if not code:
        return None
    return code == "A"


def _999_reason(ack: dict[str, Any]) -> str:
    parts: list[str] = []
    status = (_s(ack.get("status999")) or "").upper()
    overall = (_s(ack.get("overall_status999")) or "").upper()
    if status:
        parts.append(f"IK5={status}")
    if overall:
        parts.append(f"AK9={overall}")
    ik5_codes = [c for c in (ack.get("status999_error_codes") or []) if _s(c)]
    if ik5_codes:
        parts.append("IK5Codes=" + ",".join(ik5_codes))
    ak9_codes = [c for c in (ack.get("ak9_error_codes") or []) if _s(c)]
    if ak9_codes:
        parts.append("AK9Codes=" + ",".join(ak9_codes))
    for err in ack.get("errors") or []:
        seg = _s(err.get("segment_id"))
        code = _s(err.get("error_code"))
        if seg or code:
            parts.append(f"IK3 {seg or '?'}:{code or '?'}")
    if not parts:
        return "Accepted" if status == "A" else "Processed"
    return "; ".join(parts)[:500]


def _277_is_accepted(record: dict[str, Any]) -> bool | None:
    cat = (_s(record.get("claim_status_cat_code")) or "").upper()
    if not cat:
        full = (_s(record.get("claim_status_code_full")) or "").upper()
        if full:
            cat = full.split(":")[0]
    if not cat:
        return None
    if cat in _277_REJECTED_CATS or cat.startswith(("R", "E")):
        return False
    if cat.startswith("A"):
        return True
    return None


def _277_reason(record: dict[str, Any]) -> str:
    parts = [
        _s(record.get("claim_status_code_full")),
        _s(record.get("claim_status_cat_code")),
        _s(record.get("claim_status_code")),
        _s(record.get("remarks")),
        _s(record.get("remark_token")),
    ]
    text = " | ".join(p for p in parts if p)
    return (text or "277 claim status received")[:500]


@contextmanager
def _connection() -> Generator[Any, None, None]:
    import pyodbc

    conn_str = (
        f"DRIVER={{{SQL_DRIVER}}};SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};"
        f"UID={SQL_USER};PWD={SQL_PASSWORD};TrustServerCertificate=yes;"
    )
    conn = pyodbc.connect(conn_str, timeout=30, autocommit=False)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _file_exists(cur: Any, table: str, source: str, filename: str) -> int | None:
    cur.execute(
        f"SELECT id FROM dbo.{table} WHERE Source = ? AND SourceFilename = ?",
        source,
        filename,
    )
    row = cur.fetchone()
    return int(row[0]) if row else None


def _insert_edi277_file(cur: Any, source: str, filename: str, parsed: dict[str, Any]) -> int:
    env = parsed.get("envelope") or {}
    imported_at = _parse_imported_at(parsed.get("imported_at"))
    cur.execute(
        """
        INSERT INTO dbo.Edi277File (
            Source, SourceFilename, FileType, ImportedAt,
            SenderId, ReceiverId, InterchangeDate, InterchangeTime, InterchangeVersion,
            InterchangeControlNumber, UsageIndicator, FunctionalGroup, ApplicationSender,
            ApplicationReceiver, GroupDate, GroupTime, GroupControlNumber, ImplementationVersion,
            CreatedUserId, CreatedDateTime, UpdatedDateTime, UpdatedUserId, RecordStatusId, IsDeleted
        )
        OUTPUT INSERTED.id
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, SYSDATETIMEOFFSET(), NULL, NULL, ?, 0)
        """,
        source,
        filename,
        _s(parsed.get("file_type"), 100),
        imported_at,
        _s(env.get("sender_id"), 15),
        _s(env.get("receiver_id"), 15),
        _s(env.get("date"), 20),
        _s(env.get("time"), 10),
        _s(env.get("version"), 10),
        _s(env.get("control_number"), 20),
        _s(env.get("usage_indicator"), 1),
        _s(env.get("functional_group"), 5),
        _s(env.get("application_sender"), 15),
        _s(env.get("application_receiver"), 15),
        _s(env.get("group_date"), 20),
        _s(env.get("group_time"), 10),
        _s(env.get("group_control_number"), 20),
        _s(env.get("implementation_version"), 20),
        SQL_CREATED_USER_ID,
        SQL_RECORD_STATUS_ID,
    )
    return int(cur.fetchone()[0])


def _insert_edi277_status(
    cur: Any, file_id: int, record_index: int, record: dict[str, Any]
) -> None:
    cur.execute(
        """
        INSERT INTO dbo.Edi277Status (
            FileId, RecordIndex, TransactionControlNumber, GroupControlNumber, TranDate,
            PatientAccNo, PatientName, PayerName, SubmitterName, SubmitterEntityId,
            ProviderName, ProviderId, PayerTrace, ServiceDate, ReceivedDate, ProcessDate,
            HlId, HlParentId, HlLevelCode, HlLevelName, ClaimStatusCatCode, ClaimStatusCode,
            ClaimStatusCodeFull, RemarkToken, StatusDate, StatusQualifier, StatusAmount,
            Status, Remarks, SubmitterId, InsuredId,
            CreatedUserId, CreatedDateTime, UpdatedDateTime, UpdatedUserId, RecordStatusId, IsDeleted
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, SYSDATETIMEOFFSET(), NULL, NULL, ?, 0
        )
        """,
        file_id,
        record_index,
        _s(record.get("transaction_control_number"), 20),
        _s(record.get("group_control_number"), 20),
        _s(record.get("tran_date"), 30),
        _s(record.get("patient_acc_no"), 50),
        _s(record.get("patient_name"), 200),
        _s(record.get("payer_name"), 200),
        _s(record.get("submitter_name"), 200),
        _s(record.get("submitter_entity_id"), 80),
        _s(record.get("provider_name"), 200),
        _s(record.get("provider_id"), 80),
        _s(record.get("payer_trace"), 50),
        _s(record.get("service_date"), 30),
        _s(record.get("received_date"), 30),
        _s(record.get("process_date"), 30),
        _s(record.get("hl_id"), 12),
        _s(record.get("hl_parent_id"), 12),
        _s(record.get("hl_level_code"), 5),
        _s(record.get("hl_level_name"), 80),
        _s(record.get("claim_status_cat_code"), 10),
        _s(record.get("claim_status_code"), 10),
        _s(record.get("claim_status_code_full"), 50),
        _s(record.get("remark_token"), 20),
        _s(record.get("status_date"), 30),
        _s(record.get("status_qualifier"), 10),
        _dec(record.get("status_amount")),
        _s(record.get("status"), 50),
        _s(record.get("remarks"), 20),
        _s(record.get("submitter_id"), 80),
        _s(record.get("insured_id"), 80),
        SQL_CREATED_USER_ID,
        SQL_RECORD_STATUS_ID,
    )


def _update_billing_277(
    cur: Any, file_id: int, records: Iterable[dict[str, Any]]
) -> int:
    updated = 0
    seen_accounts: set[str] = set()
    for record in records:
        patient_acc = _s(record.get("patient_acc_no"), 50)
        if not patient_acc or patient_acc in seen_accounts:
            continue
        seen_accounts.add(patient_acc)
        accepted = _277_is_accepted(record)
        reason = _277_reason(record)
        cur.execute(
            """
            UPDATE dbo.BillingHeadersHistory
            SET [277FileHeaderId] = ?,
                [Is277FileAccepted] = ?,
                [277FileAcceptedOrRejectedReason] = ?,
                [UpdatedDateTime] = SYSDATETIMEOFFSET(),
                [UpdatedUserId] = ?
            WHERE [PatientAccountNumber] = ?
              AND [Id] = (
                  SELECT TOP 1 [Id]
                  FROM dbo.BillingHeadersHistory
                  WHERE [PatientAccountNumber] = ?
                    AND (IsDeleted IS NULL OR IsDeleted = 0)
                  ORDER BY [CreatedDateTime] DESC
              )
            """,
            file_id,
            accepted,
            reason,
            SQL_CREATED_USER_ID,
            patient_acc,
            patient_acc,
        )
        updated += cur.rowcount
    return updated


def _insert_edi999_file(cur: Any, source: str, filename: str, parsed: dict[str, Any]) -> int:
    env = parsed.get("envelope") or {}
    imported_at = _parse_imported_at(parsed.get("imported_at"))
    cur.execute(
        """
        INSERT INTO dbo.Edi999File (
            Source, SourceFilename, FileType, ImportedAt,
            SenderId, ReceiverId, InterchangeDate, InterchangeTime, InterchangeVersion,
            InterchangeControlNumber, UsageIndicator, FunctionalGroup, ApplicationSender,
            ApplicationReceiver, GroupDate, GroupTime, GroupControlNumber, ImplementationVersion,
            CreatedUserId, CreatedDateTime, UpdatedDateTime, UpdatedUserId, RecordStatusId, IsDeleted
        )
        OUTPUT INSERTED.id
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, SYSDATETIMEOFFSET(), NULL, NULL, ?, 0)
        """,
        source,
        filename,
        _s(parsed.get("file_type"), 100),
        imported_at,
        _s(env.get("sender_id"), 15),
        _s(env.get("receiver_id"), 15),
        _s(env.get("date"), 20),
        _s(env.get("time"), 10),
        _s(env.get("version"), 10),
        _s(env.get("control_number"), 20),
        _s(env.get("usage_indicator"), 1),
        _s(env.get("functional_group"), 5),
        _s(env.get("application_sender"), 15),
        _s(env.get("application_receiver"), 15),
        _s(env.get("group_date"), 20),
        _s(env.get("group_time"), 10),
        _s(env.get("group_control_number"), 20),
        _s(env.get("implementation_version"), 20),
        SQL_CREATED_USER_ID,
        SQL_RECORD_STATUS_ID,
    )
    return int(cur.fetchone()[0])


def _insert_edi999_ack(cur: Any, file_id: int, ack_index: int, ack: dict[str, Any]) -> int:
    cur.execute(
        """
        INSERT INTO dbo.Edi999Ack (
            FileId, AckIndex, TransactionControlNumber, GroupControlNumber, GroupControlId,
            Ak1FunctionalId, Ak1ImplementationVersion, AckedFileType, File837ControlNumber,
            Status999, OverallStatus999, Ak9IncludedCount, Ak9ReceivedCount, Ak9AcceptedCount, PatientNo,
            CreatedUserId, CreatedDateTime, UpdatedDateTime, UpdatedUserId, RecordStatusId, IsDeleted
        )
        OUTPUT INSERTED.id
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, SYSDATETIMEOFFSET(), NULL, NULL, ?, 0)
        """,
        file_id,
        ack_index,
        _s(ack.get("transaction_control_number"), 20),
        _s(ack.get("group_control_number"), 20),
        _s(ack.get("group_control_id"), 20),
        _s(ack.get("ak1_functional_id"), 5),
        _s(ack.get("ak1_implementation_version"), 20),
        _s(ack.get("file_type"), 10),
        _s(ack.get("file_837_control_number"), 20),
        _s(ack.get("status999"), 5),
        _s(ack.get("overall_status999"), 5),
        _int(ack.get("ak9_included_count")),
        _int(ack.get("ak9_received_count")),
        _int(ack.get("ak9_accepted_count")),
        _s(ack.get("patient_no"), 50),
        SQL_CREATED_USER_ID,
        SQL_RECORD_STATUS_ID,
    )
    return int(cur.fetchone()[0])


def _insert_edi999_children(cur: Any, ack_id: int, ack: dict[str, Any]) -> None:
    for i, code in enumerate(ack.get("status999_error_codes") or [], start=1):
        text = _s(code, 10)
        if not text:
            continue
        cur.execute(
            """
            INSERT INTO dbo.Edi999Ik5ErrorCode (
                AckId, CodeIndex, ErrorCode,
                CreatedUserId, CreatedDateTime, UpdatedDateTime, UpdatedUserId, RecordStatusId, IsDeleted
            ) VALUES (?, ?, ?, ?, SYSDATETIMEOFFSET(), NULL, NULL, ?, 0)
            """,
            ack_id,
            i,
            text,
            SQL_CREATED_USER_ID,
            SQL_RECORD_STATUS_ID,
        )

    for i, code in enumerate(ack.get("ak9_error_codes") or [], start=1):
        text = _s(code, 10)
        if not text:
            continue
        cur.execute(
            """
            INSERT INTO dbo.Edi999Ak9ErrorCode (
                AckId, CodeIndex, ErrorCode,
                CreatedUserId, CreatedDateTime, UpdatedDateTime, UpdatedUserId, RecordStatusId, IsDeleted
            ) VALUES (?, ?, ?, ?, SYSDATETIMEOFFSET(), NULL, NULL, ?, 0)
            """,
            ack_id,
            i,
            text,
            SQL_CREATED_USER_ID,
            SQL_RECORD_STATUS_ID,
        )

    for err_i, err in enumerate(ack.get("errors") or [], start=1):
        cur.execute(
            """
            INSERT INTO dbo.Edi999Error (
                AckId, ErrorIndex, SegmentId, SegmentPosition, LoopId, ErrorCode,
                CreatedUserId, CreatedDateTime, UpdatedDateTime, UpdatedUserId, RecordStatusId, IsDeleted
            )
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, ?, ?, ?, ?, SYSDATETIMEOFFSET(), NULL, NULL, ?, 0)
            """,
            ack_id,
            err_i,
            _s(err.get("segment_id"), 10),
            _s(err.get("segment_position"), 10),
            _s(err.get("loop_id"), 20),
            _s(err.get("error_code"), 10),
            SQL_CREATED_USER_ID,
            SQL_RECORD_STATUS_ID,
        )
        error_id = int(cur.fetchone()[0])

        for el_i, el in enumerate(err.get("element_errors") or [], start=1):
            cur.execute(
                """
                INSERT INTO dbo.Edi999ElementError (
                    ErrorId, ElementIndex, ElementPosition, ElementRef, ErrorCode, BadData,
                    CreatedUserId, CreatedDateTime, UpdatedDateTime, UpdatedUserId, RecordStatusId, IsDeleted
                ) VALUES (?, ?, ?, ?, ?, ?, ?, SYSDATETIMEOFFSET(), NULL, NULL, ?, 0)
                """,
                error_id,
                el_i,
                _s(el.get("element_position"), 20),
                _s(el.get("element_ref"), 20),
                _s(el.get("error_code"), 10),
                _s(el.get("bad_data"), 80),
                SQL_CREATED_USER_ID,
                SQL_RECORD_STATUS_ID,
            )

        for cx_i, cx in enumerate(err.get("context") or [], start=1):
            elements = cx.get("elements") or []
            csv = ",".join(str(x) for x in elements if _s(x))[:400]
            cur.execute(
                """
                INSERT INTO dbo.Edi999ErrorContext (
                    ErrorId, ContextIndex, ContextName, SegmentId, SegmentPosition, LoopId, ElementsCsv,
                    CreatedUserId, CreatedDateTime, UpdatedDateTime, UpdatedUserId, RecordStatusId, IsDeleted
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, SYSDATETIMEOFFSET(), NULL, NULL, ?, 0)
                """,
                error_id,
                cx_i,
                _s(cx.get("context_name"), 80),
                _s(cx.get("segment_id"), 10),
                _s(cx.get("segment_position"), 10),
                _s(cx.get("loop_id"), 20),
                csv or None,
                SQL_CREATED_USER_ID,
                SQL_RECORD_STATUS_ID,
            )

    for cx_i, cx in enumerate(ack.get("context") or [], start=1):
        elements = cx.get("elements") or []
        csv = ",".join(str(x) for x in elements if _s(x))[:400]
        cur.execute(
            """
            INSERT INTO dbo.Edi999AckContext (
                AckId, ContextIndex, ContextName, SegmentId, SegmentPosition, LoopId, ElementsCsv,
                CreatedUserId, CreatedDateTime, UpdatedDateTime, UpdatedUserId, RecordStatusId, IsDeleted
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, SYSDATETIMEOFFSET(), NULL, NULL, ?, 0)
            """,
            ack_id,
            cx_i,
            _s(cx.get("context_name"), 80),
            _s(cx.get("segment_id"), 10),
            _s(cx.get("segment_position"), 10),
            _s(cx.get("loop_id"), 20),
            csv or None,
            SQL_CREATED_USER_ID,
            SQL_RECORD_STATUS_ID,
        )


def _update_billing_999(
    cur: Any, file_id: int, acks: Iterable[dict[str, Any]], _envelope: dict[str, Any]
) -> int:
    updated = 0
    seen_controls: set[str] = set()

    for ack in acks:
        control = _s(ack.get("file_837_control_number"), 20)
        if not control:
            continue
        variants = _control_variants(control)
        if not variants:
            continue
        key = variants[0]
        if key in seen_controls:
            continue
        seen_controls.add(key)

        accepted = _999_is_accepted(ack.get("status999"))
        reason = _999_reason(ack)
        placeholders = ",".join("?" for _ in variants)
        match_sql = f"[TransactionSetControlNumber] IN ({placeholders})"
        match_params = list(variants)

        cur.execute(
            f"""
            UPDATE dbo.BillingHeadersHistory
            SET [999FileHeaderId] = ?,
                [Is999FileAccepted] = ?,
                [999FileAcceptedOrRejectedReason] = ?,
                [UpdatedDateTime] = SYSDATETIMEOFFSET(),
                [UpdatedUserId] = ?
            WHERE {match_sql}
              AND [Id] = (
                  SELECT TOP 1 [Id]
                  FROM dbo.BillingHeadersHistory
                  WHERE {match_sql}
                    AND (IsDeleted IS NULL OR IsDeleted = 0)
                  ORDER BY [CreatedDateTime] DESC
              )
            """,
            file_id,
            accepted,
            reason,
            SQL_CREATED_USER_ID,
            *match_params,
            *match_params,
        )
        updated += cur.rowcount
    return updated


def sync_277_file_to_sql(source: str, source_filename: str, parsed: dict[str, Any]) -> dict[str, Any]:
    """Insert Edi277* rows and update BillingHeadersHistory for one parsed file."""
    if not is_sql_sync_enabled():
        return {"enabled": False}

    records = parsed.get("transactions") or parsed.get("flat_rows") or []

    with _connection() as conn:
        cur = conn.cursor()
        existing = _file_exists(cur, "Edi277File", source, source_filename)
        if existing:
            logger.info("SQL 277 skip (already synced): %s/%s id=%d", source, source_filename, existing)
            return {"enabled": True, "skipped": True, "file_id": existing}

        file_id = _insert_edi277_file(cur, source, source_filename, parsed)
        for idx, record in enumerate(records, start=1):
            _insert_edi277_status(cur, file_id, idx, record)
        billing_updates = _update_billing_277(cur, file_id, records)

    logger.info(
        "SQL 277 synced %s/%s -> file_id=%d status_rows=%d billing_updates=%d",
        source,
        source_filename,
        file_id,
        len(records),
        billing_updates,
    )
    return {
        "enabled": True,
        "skipped": False,
        "file_id": file_id,
        "status_rows": len(records),
        "billing_updates": billing_updates,
    }


def sync_999_file_to_sql(source: str, source_filename: str, parsed: dict[str, Any]) -> dict[str, Any]:
    """Insert Edi999* rows and update BillingHeadersHistory for one parsed file."""
    if not is_sql_sync_enabled():
        return {"enabled": False}

    acks = parsed.get("acknowledgments") or parsed.get("flat_rows") or []
    envelope = parsed.get("envelope") or {}

    with _connection() as conn:
        cur = conn.cursor()
        existing = _file_exists(cur, "Edi999File", source, source_filename)
        if existing:
            logger.info("SQL 999 skip (already synced): %s/%s id=%d", source, source_filename, existing)
            return {"enabled": True, "skipped": True, "file_id": existing}

        file_id = _insert_edi999_file(cur, source, source_filename, parsed)
        for idx, ack in enumerate(acks, start=1):
            ack_id = _insert_edi999_ack(cur, file_id, idx, ack)
            _insert_edi999_children(cur, ack_id, ack)
        billing_updates = _update_billing_999(cur, file_id, acks, envelope)

    logger.info(
        "SQL 999 synced %s/%s -> file_id=%d ack_rows=%d billing_updates=%d",
        source,
        source_filename,
        file_id,
        len(acks),
        billing_updates,
    )
    return {
        "enabled": True,
        "skipped": False,
        "file_id": file_id,
        "ack_rows": len(acks),
        "billing_updates": billing_updates,
    }
