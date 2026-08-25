"""
Download 20 .277 and 20 .999 from SFTP, process with existing parsers,
save to Mongo edi_277_999, then copy all fields into SQL Server tables.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import tempfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

repo_root = Path(__file__).resolve().parents[1]
load_dotenv(repo_root / "backend" / ".env")

sys.path.insert(0, str(repo_root / "backend"))
sys.path.insert(0, str(repo_root))

from pymongo import MongoClient  # noqa: E402

from app.parser_277_999 import parse_277_text, parse_999_text  # noqa: E402
from pipeline.mongo_save import (  # noqa: E402
    CLAIM_STATUS_277_COLLECTION,
    FUNCTIONAL_ACK_999_COLLECTION,
    MONGO_277_999_DB,
    MONGO_DB,
    init_277_collection,
    init_999_collection,
    save_277_file,
    save_999_file,
)
from pipeline.sftp_client import (  # noqa: E402
    download_file,
    list_files_by_extension,
    sftp_connection,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger("process_20_mongo_sql")

FILE_LIMIT = 20
SOURCE = "SFTP-20"
DOWNLOAD_DIR = repo_root / "downloads" / "SFTP-20"

# SQL Server (ClaudMD_Development_Sithum) — user-provided master DB settings
SQL_SERVER = os.getenv("MASTER_DB_SERVER", "10.103.0.211")
SQL_DATABASE = os.getenv("MASTER_DB_NAME", "ClaudMD_Development_Sithum")
SQL_USER = os.getenv("MASTER_DB_USER", "testuser")
SQL_PASSWORD = os.getenv("MASTER_DB_PASSWORD", "Test@123")

CREATED_USER_ID = 1
RECORD_STATUS_ID = 1


def _mongo():
    client = MongoClient(os.environ["MONGO_URI"], serverSelectionTimeoutMS=8000)
    client.admin.command("ping")
    return client, client[MONGO_277_999_DB], client[MONGO_DB]


def wipe_mongo(db_277_999, db_835) -> None:
    for name in (CLAIM_STATUS_277_COLLECTION, FUNCTIONAL_ACK_999_COLLECTION):
        if name in db_277_999.list_collection_names():
            db_277_999.drop_collection(name)
            log.info("Dropped %s.%s", MONGO_277_999_DB, name)
    for name in list(db_835.list_collection_names()):
        if name in {"era_payments", "pipeline_tracker", "auth_refresh_tokens"}:
            continue
        if "277" in name or "999" in name:
            db_835.drop_collection(name)
            log.info("Dropped leftover %s.%s", MONGO_DB, name)
    tracker = os.getenv("MONGO_TRACKER_COLLECTION", "pipeline_tracker")
    if tracker in db_835.list_collection_names():
        deleted = db_835[tracker].delete_many(
            {"filename": {"$regex": r"\.(277|999)$", "$options": "i"}}
        )
        log.info("Cleared %d tracker rows for .277/.999", deleted.deleted_count)
    init_277_collection()
    init_999_collection()


def gather_files() -> tuple[list[Path], list[Path]]:
    host = os.getenv("SFTP_HOST", "Secure.edidrop.com")
    port = int(os.getenv("SFTP_PORT", "522"))
    user = os.getenv("SFTP_MATRIX_USER", "")
    password = os.getenv("SFTP_MATRIX_PASS", "")
    remote = os.getenv("SFTP_REMOTE_PATH", "/837P/OUT/")

    files_277: list[Path] = []
    files_999: list[Path] = []
    with sftp_connection(host, port, user, password) as sftp:
        all_277 = sorted(list_files_by_extension(sftp, remote, {".277"}))
        all_999 = sorted(list_files_by_extension(sftp, remote, {".999"}))
        remote_277 = all_277[:FILE_LIMIT]
        remote_999 = all_999[:FILE_LIMIT]
        log.info(
            "SFTP %s — taking %d/%d .277 and %d/%d .999",
            remote,
            len(remote_277),
            len(all_277),
            len(remote_999),
            len(all_999),
        )
        for name in remote_277:
            files_277.append(download_file(sftp, remote, name, DOWNLOAD_DIR))
        for name in remote_999:
            files_999.append(download_file(sftp, remote, name, DOWNLOAD_DIR))
    return files_277, files_999


def ingest_mongo(files_277: list[Path], files_999: list[Path]) -> tuple[int, int]:
    saved_277 = saved_999 = 0
    for path in files_277:
        count = save_277_file(SOURCE, path.name, parse_277_text(path.read_text(encoding="utf-8", errors="ignore")))
        saved_277 += count
        log.info("277 %s -> %d Mongo doc(s)", path.name, count)
    for path in files_999:
        count = save_999_file(SOURCE, path.name, parse_999_text(path.read_text(encoding="utf-8", errors="ignore")))
        saved_999 += count
        log.info("999 %s -> %d Mongo doc(s)", path.name, count)
    return saved_277, saved_999


def _s(value: Any, max_len: int | None = None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    if max_len is not None:
        text = text[:max_len]
    return text


def _sql_str(value: Any, max_len: int | None = None) -> str:
    text = _s(value, max_len)
    if text is None:
        return "NULL"
    return "N'" + text.replace("'", "''") + "'"


def _sql_int(value: Any) -> str:
    if value is None or value == "":
        return "NULL"
    try:
        return str(int(value))
    except (TypeError, ValueError):
        return "NULL"


def _sql_dec(value: Any) -> str:
    if value is None or value == "":
        return "NULL"
    try:
        return str(float(value))
    except (TypeError, ValueError):
        return "NULL"


def _sql_dt(value: Any) -> str:
    """Return a DATETIME2-safe literal, or SYSUTCDATETIME()."""
    text = _s(value)
    if not text:
        return "SYSUTCDATETIME()"
    cleaned = text.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is not None:
            dt = dt.astimezone(tz=None).replace(tzinfo=None)
        return "'" + dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + "'"
    except ValueError:
        return "SYSUTCDATETIME()"


def _audit_cols() -> str:
    return (
        f"{CREATED_USER_ID}, SYSDATETIMEOFFSET(), NULL, NULL, "
        f"{RECORD_STATUS_ID}, 0"
    )


def build_sql(db_277_999) -> str:
    lines: list[str] = [
        "SET NOCOUNT ON;",
        "SET XACT_ABORT ON;",
        "BEGIN TRAN;",
        "DECLARE @FileId277 BIGINT;",
        "DECLARE @FileId999 BIGINT;",
        "DECLARE @AckId BIGINT;",
        "DECLARE @ErrorId BIGINT;",
        "-- Clear previous load rows only (keep tables)",
        "DELETE FROM dbo.Edi999ElementError;",
        "DELETE FROM dbo.Edi999ErrorContext;",
        "DELETE FROM dbo.Edi999AckContext;",
        "DELETE FROM dbo.Edi999Ik5ErrorCode;",
        "DELETE FROM dbo.Edi999Ak9ErrorCode;",
        "DELETE FROM dbo.Edi999Error;",
        "DELETE FROM dbo.Edi999Ack;",
        "DELETE FROM dbo.Edi999File;",
        "DELETE FROM dbo.Edi277Status;",
        "DELETE FROM dbo.Edi277File;",
    ]

    # ---- 277 ----
    docs_277 = list(db_277_999[CLAIM_STATUS_277_COLLECTION].find({}).sort([("source", 1), ("source_filename", 1), ("record_index", 1)]))
    by_file_277: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for doc in docs_277:
        by_file_277[(doc.get("source", ""), doc.get("source_filename", ""))].append(doc)

    for (source, filename), docs in by_file_277.items():
        env = docs[0].get("envelope") or {}
        imported_at = docs[0].get("imported_at")
        file_type = docs[0].get("file_type")
        lines.append(
            "INSERT INTO dbo.Edi277File ("
            "Source, SourceFilename, FileType, ImportedAt, "
            "SenderId, ReceiverId, InterchangeDate, InterchangeTime, InterchangeVersion, "
            "InterchangeControlNumber, UsageIndicator, FunctionalGroup, ApplicationSender, "
            "ApplicationReceiver, GroupDate, GroupTime, GroupControlNumber, ImplementationVersion, "
            "CreatedUserId, CreatedDateTime, UpdatedDateTime, UpdatedUserId, RecordStatusId, IsDeleted"
            ") VALUES ("
            f"{_sql_str(source, 50)}, {_sql_str(filename, 260)}, {_sql_str(file_type, 100)}, {_sql_dt(imported_at)}, "
            f"{_sql_str(env.get('sender_id'), 15)}, {_sql_str(env.get('receiver_id'), 15)}, "
            f"{_sql_str(env.get('date'), 20)}, {_sql_str(env.get('time'), 10)}, {_sql_str(env.get('version'), 10)}, "
            f"{_sql_str(env.get('control_number'), 20)}, {_sql_str(env.get('usage_indicator'), 1)}, "
            f"{_sql_str(env.get('functional_group'), 5)}, {_sql_str(env.get('application_sender'), 15)}, "
            f"{_sql_str(env.get('application_receiver'), 15)}, {_sql_str(env.get('group_date'), 20)}, "
            f"{_sql_str(env.get('group_time'), 10)}, {_sql_str(env.get('group_control_number'), 20)}, "
            f"{_sql_str(env.get('implementation_version'), 20)}, {_audit_cols()}"
            ");"
        )
        lines.append("SET @FileId277 = SCOPE_IDENTITY();")
        for doc in docs:
            r = doc.get("record") or {}
            lines.append(
                "INSERT INTO dbo.Edi277Status ("
                "FileId, RecordIndex, TransactionControlNumber, GroupControlNumber, TranDate, "
                "PatientAccNo, PatientName, PayerName, SubmitterName, SubmitterEntityId, "
                "ProviderName, ProviderId, PayerTrace, ServiceDate, ReceivedDate, ProcessDate, "
                "HlId, HlParentId, HlLevelCode, HlLevelName, ClaimStatusCatCode, ClaimStatusCode, "
                "ClaimStatusCodeFull, RemarkToken, StatusDate, StatusQualifier, StatusAmount, "
                "Status, Remarks, SubmitterId, InsuredId, "
                "CreatedUserId, CreatedDateTime, UpdatedDateTime, UpdatedUserId, RecordStatusId, IsDeleted"
                ") VALUES ("
                f"@FileId277, {_sql_int(doc.get('record_index'))}, "
                f"{_sql_str(r.get('transaction_control_number'), 20)}, {_sql_str(r.get('group_control_number'), 20)}, "
                f"{_sql_str(r.get('tran_date'), 30)}, {_sql_str(r.get('patient_acc_no'), 50)}, "
                f"{_sql_str(r.get('patient_name'), 200)}, {_sql_str(r.get('payer_name'), 200)}, "
                f"{_sql_str(r.get('submitter_name'), 200)}, {_sql_str(r.get('submitter_entity_id'), 80)}, "
                f"{_sql_str(r.get('provider_name'), 200)}, {_sql_str(r.get('provider_id'), 80)}, "
                f"{_sql_str(r.get('payer_trace'), 50)}, {_sql_str(r.get('service_date'), 30)}, "
                f"{_sql_str(r.get('received_date'), 30)}, {_sql_str(r.get('process_date'), 30)}, "
                f"{_sql_str(r.get('hl_id'), 12)}, {_sql_str(r.get('hl_parent_id'), 12)}, "
                f"{_sql_str(r.get('hl_level_code'), 5)}, {_sql_str(r.get('hl_level_name'), 80)}, "
                f"{_sql_str(r.get('claim_status_cat_code'), 10)}, {_sql_str(r.get('claim_status_code'), 10)}, "
                f"{_sql_str(r.get('claim_status_code_full'), 50)}, {_sql_str(r.get('remark_token'), 20)}, "
                f"{_sql_str(r.get('status_date'), 30)}, {_sql_str(r.get('status_qualifier'), 10)}, "
                f"{_sql_dec(r.get('status_amount'))}, {_sql_str(r.get('status'), 50)}, "
                f"{_sql_str(r.get('remarks'), 20)}, {_sql_str(r.get('submitter_id'), 80)}, "
                f"{_sql_str(r.get('insured_id'), 80)}, {_audit_cols()}"
                ");"
            )

    # ---- 999 ----
    docs_999 = list(db_277_999[FUNCTIONAL_ACK_999_COLLECTION].find({}).sort([("source", 1), ("source_filename", 1), ("ack_index", 1)]))
    by_file_999: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for doc in docs_999:
        by_file_999[(doc.get("source", ""), doc.get("source_filename", ""))].append(doc)

    for (source, filename), docs in by_file_999.items():
        env = docs[0].get("envelope") or {}
        imported_at = docs[0].get("imported_at")
        file_type = docs[0].get("file_type")
        lines.append(
            "INSERT INTO dbo.Edi999File ("
            "Source, SourceFilename, FileType, ImportedAt, "
            "SenderId, ReceiverId, InterchangeDate, InterchangeTime, InterchangeVersion, "
            "InterchangeControlNumber, UsageIndicator, FunctionalGroup, ApplicationSender, "
            "ApplicationReceiver, GroupDate, GroupTime, GroupControlNumber, ImplementationVersion, "
            "CreatedUserId, CreatedDateTime, UpdatedDateTime, UpdatedUserId, RecordStatusId, IsDeleted"
            ") VALUES ("
            f"{_sql_str(source, 50)}, {_sql_str(filename, 260)}, {_sql_str(file_type, 100)}, {_sql_dt(imported_at)}, "
            f"{_sql_str(env.get('sender_id'), 15)}, {_sql_str(env.get('receiver_id'), 15)}, "
            f"{_sql_str(env.get('date'), 20)}, {_sql_str(env.get('time'), 10)}, {_sql_str(env.get('version'), 10)}, "
            f"{_sql_str(env.get('control_number'), 20)}, {_sql_str(env.get('usage_indicator'), 1)}, "
            f"{_sql_str(env.get('functional_group'), 5)}, {_sql_str(env.get('application_sender'), 15)}, "
            f"{_sql_str(env.get('application_receiver'), 15)}, {_sql_str(env.get('group_date'), 20)}, "
            f"{_sql_str(env.get('group_time'), 10)}, {_sql_str(env.get('group_control_number'), 20)}, "
            f"{_sql_str(env.get('implementation_version'), 20)}, {_audit_cols()}"
            ");"
        )
        lines.append("SET @FileId999 = SCOPE_IDENTITY();")
        for doc in docs:
            a = doc.get("ack") or {}
            lines.append(
                "INSERT INTO dbo.Edi999Ack ("
                "FileId, AckIndex, TransactionControlNumber, GroupControlNumber, GroupControlId, "
                "Ak1FunctionalId, Ak1ImplementationVersion, AckedFileType, File837ControlNumber, "
                "Status999, OverallStatus999, Ak9IncludedCount, Ak9ReceivedCount, Ak9AcceptedCount, PatientNo, "
                "CreatedUserId, CreatedDateTime, UpdatedDateTime, UpdatedUserId, RecordStatusId, IsDeleted"
                ") VALUES ("
                f"@FileId999, {_sql_int(doc.get('ack_index'))}, "
                f"{_sql_str(a.get('transaction_control_number'), 20)}, {_sql_str(a.get('group_control_number'), 20)}, "
                f"{_sql_str(a.get('group_control_id'), 20)}, {_sql_str(a.get('ak1_functional_id'), 5)}, "
                f"{_sql_str(a.get('ak1_implementation_version'), 20)}, {_sql_str(a.get('file_type'), 10)}, "
                f"{_sql_str(a.get('file_837_control_number'), 20)}, {_sql_str(a.get('status999'), 5)}, "
                f"{_sql_str(a.get('overall_status999'), 5)}, {_sql_int(a.get('ak9_included_count'))}, "
                f"{_sql_int(a.get('ak9_received_count'))}, {_sql_int(a.get('ak9_accepted_count'))}, "
                f"{_sql_str(a.get('patient_no'), 50)}, {_audit_cols()}"
                ");"
            )
            lines.append("SET @AckId = SCOPE_IDENTITY();")

            for i, code in enumerate(a.get("status999_error_codes") or [], start=1):
                lines.append(
                    "INSERT INTO dbo.Edi999Ik5ErrorCode (AckId, CodeIndex, ErrorCode, "
                    "CreatedUserId, CreatedDateTime, UpdatedDateTime, UpdatedUserId, RecordStatusId, IsDeleted) VALUES ("
                    f"@AckId, {i}, {_sql_str(code, 10)}, {_audit_cols()});"
                )
            for i, code in enumerate(a.get("ak9_error_codes") or [], start=1):
                lines.append(
                    "INSERT INTO dbo.Edi999Ak9ErrorCode (AckId, CodeIndex, ErrorCode, "
                    "CreatedUserId, CreatedDateTime, UpdatedDateTime, UpdatedUserId, RecordStatusId, IsDeleted) VALUES ("
                    f"@AckId, {i}, {_sql_str(code, 10)}, {_audit_cols()});"
                )
            for err_i, err in enumerate(a.get("errors") or [], start=1):
                lines.append(
                    "INSERT INTO dbo.Edi999Error (AckId, ErrorIndex, SegmentId, SegmentPosition, LoopId, ErrorCode, "
                    "CreatedUserId, CreatedDateTime, UpdatedDateTime, UpdatedUserId, RecordStatusId, IsDeleted) VALUES ("
                    f"@AckId, {err_i}, {_sql_str(err.get('segment_id'), 10)}, {_sql_str(err.get('segment_position'), 10)}, "
                    f"{_sql_str(err.get('loop_id'), 20)}, {_sql_str(err.get('error_code'), 10)}, {_audit_cols()});"
                )
                lines.append("SET @ErrorId = SCOPE_IDENTITY();")
                for el_i, el in enumerate(err.get("element_errors") or [], start=1):
                    lines.append(
                        "INSERT INTO dbo.Edi999ElementError (ErrorId, ElementIndex, ElementPosition, ElementRef, ErrorCode, BadData, "
                        "CreatedUserId, CreatedDateTime, UpdatedDateTime, UpdatedUserId, RecordStatusId, IsDeleted) VALUES ("
                        f"@ErrorId, {el_i}, {_sql_str(el.get('element_position'), 20)}, {_sql_str(el.get('element_ref'), 20)}, "
                        f"{_sql_str(el.get('error_code'), 10)}, {_sql_str(el.get('bad_data'), 80)}, {_audit_cols()});"
                    )
                for cx_i, cx in enumerate(err.get("context") or [], start=1):
                    elements = cx.get("elements") or []
                    csv = ",".join(str(x) for x in elements if x)[:400]
                    lines.append(
                        "INSERT INTO dbo.Edi999ErrorContext (ErrorId, ContextIndex, ContextName, SegmentId, SegmentPosition, LoopId, ElementsCsv, "
                        "CreatedUserId, CreatedDateTime, UpdatedDateTime, UpdatedUserId, RecordStatusId, IsDeleted) VALUES ("
                        f"@ErrorId, {cx_i}, {_sql_str(cx.get('context_name'), 80)}, {_sql_str(cx.get('segment_id'), 10)}, "
                        f"{_sql_str(cx.get('segment_position'), 10)}, {_sql_str(cx.get('loop_id'), 20)}, {_sql_str(csv, 400)}, {_audit_cols()});"
                    )
            for cx_i, cx in enumerate(a.get("context") or [], start=1):
                elements = cx.get("elements") or []
                csv = ",".join(str(x) for x in elements if x)[:400]
                lines.append(
                    "INSERT INTO dbo.Edi999AckContext (AckId, ContextIndex, ContextName, SegmentId, SegmentPosition, LoopId, ElementsCsv, "
                    "CreatedUserId, CreatedDateTime, UpdatedDateTime, UpdatedUserId, RecordStatusId, IsDeleted) VALUES ("
                    f"@AckId, {cx_i}, {_sql_str(cx.get('context_name'), 80)}, {_sql_str(cx.get('segment_id'), 10)}, "
                    f"{_sql_str(cx.get('segment_position'), 10)}, {_sql_str(cx.get('loop_id'), 20)}, {_sql_str(csv, 400)}, {_audit_cols()});"
                )

    lines.extend(
        [
            "COMMIT;",
            "SELECT 'Edi277File' AS t, COUNT(*) AS c FROM dbo.Edi277File",
            "UNION ALL SELECT 'Edi277Status', COUNT(*) FROM dbo.Edi277Status",
            "UNION ALL SELECT 'Edi999File', COUNT(*) FROM dbo.Edi999File",
            "UNION ALL SELECT 'Edi999Ack', COUNT(*) FROM dbo.Edi999Ack",
            "UNION ALL SELECT 'Edi999Error', COUNT(*) FROM dbo.Edi999Error",
            "UNION ALL SELECT 'Edi999ElementError', COUNT(*) FROM dbo.Edi999ElementError",
            "UNION ALL SELECT 'Edi999Ik5ErrorCode', COUNT(*) FROM dbo.Edi999Ik5ErrorCode",
            "UNION ALL SELECT 'Edi999Ak9ErrorCode', COUNT(*) FROM dbo.Edi999Ak9ErrorCode",
            "UNION ALL SELECT 'Edi999ErrorContext', COUNT(*) FROM dbo.Edi999ErrorContext",
            "UNION ALL SELECT 'Edi999AckContext', COUNT(*) FROM dbo.Edi999AckContext;",
        ]
    )
    return "\n".join(lines)


def run_sql(sql_text: str) -> str:
    with tempfile.NamedTemporaryFile("w", suffix=".sql", delete=False, encoding="utf-8") as fh:
        fh.write(sql_text)
        sql_path = fh.name
    try:
        result = subprocess.run(
            [
                "sqlcmd",
                "-S", SQL_SERVER,
                "-d", SQL_DATABASE,
                "-U", SQL_USER,
                "-P", SQL_PASSWORD,
                "-C",
                "-b",
                "-i", sql_path,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        out = (result.stdout or "") + (result.stderr or "")
        if result.returncode != 0:
            raise RuntimeError(f"sqlcmd failed ({result.returncode}):\n{out[-4000:]}")
        return out
    finally:
        Path(sql_path).unlink(missing_ok=True)


def verify(db_277_999) -> dict[str, Any]:
    mongo_277_files = sorted(
        {
            (d.get("source"), d.get("source_filename"))
            for d in db_277_999[CLAIM_STATUS_277_COLLECTION].find({}, {"source": 1, "source_filename": 1})
        }
    )
    mongo_999_files = sorted(
        {
            (d.get("source"), d.get("source_filename"))
            for d in db_277_999[FUNCTIONAL_ACK_999_COLLECTION].find({}, {"source": 1, "source_filename": 1})
        }
    )
    mongo_277_docs = db_277_999[CLAIM_STATUS_277_COLLECTION].count_documents({})
    mongo_999_docs = db_277_999[FUNCTIONAL_ACK_999_COLLECTION].count_documents({})

    check_sql = """
SET NOCOUNT ON;
SELECT 'files277' AS k, COUNT(*) FROM dbo.Edi277File
UNION ALL SELECT 'status277', COUNT(*) FROM dbo.Edi277Status
UNION ALL SELECT 'files999', COUNT(*) FROM dbo.Edi999File
UNION ALL SELECT 'ack999', COUNT(*) FROM dbo.Edi999Ack;
SELECT Source, SourceFilename FROM dbo.Edi277File ORDER BY SourceFilename;
SELECT Source, SourceFilename FROM dbo.Edi999File ORDER BY SourceFilename;
"""
    out = run_sql(check_sql)
    return {
        "mongo_277_files": len(mongo_277_files),
        "mongo_999_files": len(mongo_999_files),
        "mongo_277_docs": mongo_277_docs,
        "mongo_999_docs": mongo_999_docs,
        "mongo_277_file_names": [f[1] for f in mongo_277_files],
        "mongo_999_file_names": [f[1] for f in mongo_999_files],
        "sql_check_output": out,
    }


def main() -> None:
    client, db_277_999, db_835 = _mongo()
    log.info("Mongo OK — target db=%s (835 db=%s untouched for era)", MONGO_277_999_DB, MONGO_DB)

    wipe_mongo(db_277_999, db_835)
    files_277, files_999 = gather_files()
    if len(files_277) != FILE_LIMIT or len(files_999) != FILE_LIMIT:
        raise SystemExit(
            f"Expected {FILE_LIMIT} of each; got {len(files_277)} .277 and {len(files_999)} .999"
        )

    saved_277, saved_999 = ingest_mongo(files_277, files_999)
    log.info(
        "Mongo saved: 277 docs=%d from %d files; 999 docs=%d from %d files",
        saved_277,
        len(files_277),
        saved_999,
        len(files_999),
    )

    # Re-bind after wipe/create — collection handles stay valid on db object
    sql_text = build_sql(db_277_999)
    log.info("Inserting into SQL Server %s / %s ...", SQL_SERVER, SQL_DATABASE)
    sql_out = run_sql(sql_text)
    log.info("SQL insert result:\n%s", sql_out[-2000:])

    summary = verify(db_277_999)
    report_path = repo_root / "tmp" / "process_20_summary.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    ok_files = (
        summary["mongo_277_files"] == FILE_LIMIT
        and summary["mongo_999_files"] == FILE_LIMIT
    )
    log.info(
        "VERIFY Mongo files: 277=%d 999=%d docs: 277=%d 999=%d",
        summary["mongo_277_files"],
        summary["mongo_999_files"],
        summary["mongo_277_docs"],
        summary["mongo_999_docs"],
    )
    log.info("SQL verify output:\n%s", summary["sql_check_output"][-2000:])
    if not ok_files:
        raise SystemExit("Mongo file count mismatch — expected 20 of each")
    log.info("SUCCESS: 20 .277 and 20 .999 processed into Mongo, then SQL.")
    client.close()


if __name__ == "__main__":
    main()
