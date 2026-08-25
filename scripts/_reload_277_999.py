"""Wipe 277/999 Mongo docs, then ingest 10 .277 and 10 .999 files via existing parsers."""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

repo_root = Path(__file__).resolve().parents[1]
load_dotenv(repo_root / "backend" / ".env")

# backend/.env uses MONGO_URI / SFTP_HOST; pipeline code also accepts those names.
# Copy backend .env names onto the names pipeline code reads, if those differ.
for dst, src in [
    ("SFTP_HOST", "SFTP_HOST"),
    ("SFTP_PORT", "SFTP_PORT"),
    ("SFTP_REMOTE_PATH", "SFTP_REMOTE_PATH"),
]:
    if not os.getenv(dst) and os.getenv(src):
        os.environ[dst] = os.environ[src]

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
log = logging.getLogger("reload_277_999")

FILE_LIMIT = 10
SOURCE = "Local-reload"
SAMPLE_DIR = repo_root / "sample-files" / "_tmp_sftp_samples"
DOWNLOAD_DIR = repo_root / "downloads" / "Local-reload"

PROTECTED = {"era_payments"}


def _mongo():
    uri = os.environ["MONGO_URI"]
    client = MongoClient(uri, serverSelectionTimeoutMS=8000)
    client.admin.command("ping")
    return client, client[MONGO_277_999_DB], client[MONGO_DB]


def wipe_277_999(db_277_999, db_835) -> None:
    existing = set(db_277_999.list_collection_names())
    log.info("Mongo collections in %s before wipe: %s", MONGO_277_999_DB, sorted(existing))
    to_drop = {
        CLAIM_STATUS_277_COLLECTION,
        FUNCTIONAL_ACK_999_COLLECTION,
        "claim_status_277",
        "functional_ack_999",
    }
    to_drop.update(
        name
        for name in existing
        if name not in PROTECTED and ("277" in name or "999" in name)
    )
    for name in sorted(to_drop):
        if name in PROTECTED:
            continue
        if name in existing:
            db_277_999.drop_collection(name)
            log.info("Dropped collection %s.%s", MONGO_277_999_DB, name)

    # Also remove any leftover 277/999 collections from the old 835 DB
    old_existing = set(db_835.list_collection_names())
    for name in sorted(old_existing):
        if name in PROTECTED:
            continue
        if name in to_drop or "277" in name or "999" in name:
            db_835.drop_collection(name)
            log.info("Dropped leftover %s.%s", MONGO_DB, name)

    tracker_names = {
        os.getenv("MONGO_TRACKER_COLLECTION", "pipeline_tracker"),
        "pipeline_tracker",
    }
    for tracker_name in tracker_names:
        if tracker_name in db_835.list_collection_names():
            result = db_835[tracker_name].delete_many(
                {"filename": {"$regex": r"\.(277|999)$", "$options": "i"}}
            )
            log.info(
                "Removed %d tracker row(s) from %s.%s for .277/.999 files",
                result.deleted_count,
                MONGO_DB,
                tracker_name,
            )
    init_277_collection()
    init_999_collection()


def gather_files() -> tuple[list[Path], list[Path]]:
    files_277: list[Path] = []
    files_999: list[Path] = []

    host = os.getenv("SFTP_HOST", "Secure.edidrop.com")
    port = int(os.getenv("SFTP_PORT", "522"))
    user = os.getenv("SFTP_MATRIX_USER", "")
    password = os.getenv("SFTP_MATRIX_PASS", "")
    remote = os.getenv("SFTP_REMOTE_PATH", "/837P/OUT/")

    try:
        with sftp_connection(host, port, user, password) as sftp:
            remote_277 = list_files_by_extension(sftp, remote, {".277"})[:FILE_LIMIT]
            remote_999 = list_files_by_extension(sftp, remote, {".999"})[:FILE_LIMIT]
            log.info("SFTP listed %d .277 and %d .999 (using first %d each)", len(remote_277), len(remote_999), FILE_LIMIT)
            for name in remote_277:
                files_277.append(download_file(sftp, remote, name, DOWNLOAD_DIR))
            for name in remote_999:
                files_999.append(download_file(sftp, remote, name, DOWNLOAD_DIR))
    except Exception:
        log.exception("SFTP download failed; falling back to local samples")

    if SAMPLE_DIR.exists():
        local_277 = sorted(SAMPLE_DIR.glob("*.277"))
        local_999 = sorted(SAMPLE_DIR.glob("*.999"))
        have_277 = {p.name for p in files_277}
        have_999 = {p.name for p in files_999}
        for path in local_277:
            if len(files_277) >= FILE_LIMIT:
                break
            if path.name not in have_277:
                files_277.append(path)
        for path in local_999:
            if len(files_999) >= FILE_LIMIT:
                break
            if path.name not in have_999:
                files_999.append(path)

    return files_277[:FILE_LIMIT], files_999[:FILE_LIMIT]


def ingest(files_277: list[Path], files_999: list[Path]) -> None:
    saved_277 = 0
    saved_999 = 0

    log.info("Processing %d .277 file(s)", len(files_277))
    for path in files_277:
        text = path.read_text(encoding="utf-8", errors="ignore")
        parsed = parse_277_text(text)
        count = save_277_file(SOURCE, path.name, parsed)
        saved_277 += count
        log.info("277 %s -> %d doc(s)", path.name, count)

    log.info("Processing %d .999 file(s)", len(files_999))
    for path in files_999:
        text = path.read_text(encoding="utf-8", errors="ignore")
        parsed = parse_999_text(text)
        count = save_999_file(SOURCE, path.name, parsed)
        saved_999 += count
        log.info("999 %s -> %d doc(s)", path.name, count)

    log.info("Done. 277 docs=%d from %d files; 999 docs=%d from %d files", saved_277, len(files_277), saved_999, len(files_999))


def main() -> None:
    client, db_277_999, db_835 = _mongo()
    log.info("Connected to Mongo; 277/999 db=%s; 835 db=%s", db_277_999.name, db_835.name)
    wipe_277_999(db_277_999, db_835)
    files_277, files_999 = gather_files()
    if len(files_277) < FILE_LIMIT or len(files_999) < FILE_LIMIT:
        log.warning(
            "Wanted %d of each; got %d .277 and %d .999",
            FILE_LIMIT,
            len(files_277),
            len(files_999),
        )
    ingest(files_277, files_999)
    log.info(
        "Counts now: %s.%s=%d %s.%s=%d %s.era_payments=%d",
        MONGO_277_999_DB,
        CLAIM_STATUS_277_COLLECTION,
        db_277_999[CLAIM_STATUS_277_COLLECTION].count_documents({}),
        MONGO_277_999_DB,
        FUNCTIONAL_ACK_999_COLLECTION,
        db_277_999[FUNCTIONAL_ACK_999_COLLECTION].count_documents({}),
        MONGO_DB,
        db_835["era_payments"].count_documents({})
        if "era_payments" in db_835.list_collection_names()
        else -1,
    )
    client.close()


if __name__ == "__main__":
    main()
