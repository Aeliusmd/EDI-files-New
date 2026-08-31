from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Add backend to sys.path so parser is importable without installing the package.
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
from app.parser import parse_835_text  # noqa: E402
from app.parser_277_999 import (  # noqa: E402
    parse_277_text,
    parse_999_text,
)

from .sftp_client import (
    download_file,
    list_835_files,
    list_files_by_extension,
    sftp_connection,
)
from .tracker import init_tracker, is_seen, mark_seen
from .mongo_save import save_era_file, save_277_file, save_999_file
from .sql_sync import is_sql_sync_enabled, sync_277_file_to_sql, sync_999_file_to_sql

SFTP_HOST = os.getenv("SFTP_HOST", "Secure.edidrop.com")
SFTP_PORT = int(os.getenv("SFTP_PORT", "522"))
SFTP_REMOTE_PATH = os.getenv("SFTP_REMOTE_PATH", "/837P/OUT/")
POLL_INTERVAL = int(os.getenv("SFTP_POLL_INTERVAL_SECONDS", "60"))
DOWNLOADS_ROOT = Path(os.getenv("DOWNLOADS_DIR", str(Path(__file__).parent.parent / "downloads")))

SOURCES = [
    {
        "name": "Matrix",
        "user": os.getenv("SFTP_MATRIX_USER", ""),
        "pass": os.getenv("SFTP_MATRIX_PASS", ""),
    },
    {
        "name": "DMS",
        "user": os.getenv("SFTP_DMS_USER", ""),
        "pass": os.getenv("SFTP_DMS_PASS", ""),
    },
]

logger = logging.getLogger("pipeline.poller")


def _poll_source(src: dict) -> int:
    """Sync: connect, find new files, download+parse+save. Returns count saved."""
    saved = 0
    with sftp_connection(SFTP_HOST, SFTP_PORT, src["user"], src["pass"]) as sftp:
        save_dir = DOWNLOADS_ROOT / src["name"]
        save_dir.mkdir(parents=True, exist_ok=True)

        files_835 = list_835_files(sftp, SFTP_REMOTE_PATH)
        files_277 = list_files_by_extension(sftp, SFTP_REMOTE_PATH, {".277"})
        files_999 = list_files_by_extension(sftp, SFTP_REMOTE_PATH, {".999"})

        for filename in files_835:
            if is_seen(src["name"], filename):
                continue
            local_path = download_file(sftp, SFTP_REMOTE_PATH, filename, save_dir)
            text = local_path.read_text(encoding="utf-8", errors="ignore")
            parsed = parse_835_text(text)
            count = save_era_file(src["name"], filename, parsed)
            mark_seen(src["name"], filename)
            saved += count
            logger.info("Saved %d ERA docs from %s/%s", count, src["name"], filename)

        for filename in files_277:
            if is_seen(src["name"], filename):
                continue
            local_path = download_file(sftp, SFTP_REMOTE_PATH, filename, save_dir)
            text = local_path.read_text(encoding="utf-8", errors="ignore")
            parsed = parse_277_text(text)
            count = save_277_file(src["name"], filename, parsed)
            if count and is_sql_sync_enabled():
                try:
                    sync_277_file_to_sql(src["name"], filename, parsed)
                except Exception as exc:
                    logger.error(
                        "SQL sync failed for 277 %s/%s: %s",
                        src["name"],
                        filename,
                        exc,
                        exc_info=True,
                    )
            mark_seen(src["name"], filename)
            saved += count
            logger.info("Saved %d 277 claim-status records from %s/%s", count, src["name"], filename)

        for filename in files_999:
            if is_seen(src["name"], filename):
                continue
            local_path = download_file(sftp, SFTP_REMOTE_PATH, filename, save_dir)
            text = local_path.read_text(encoding="utf-8", errors="ignore")
            parsed = parse_999_text(text)
            count = save_999_file(src["name"], filename, parsed)
            if count and is_sql_sync_enabled():
                try:
                    sync_999_file_to_sql(src["name"], filename, parsed)
                except Exception as exc:
                    logger.error(
                        "SQL sync failed for 999 %s/%s: %s",
                        src["name"],
                        filename,
                        exc,
                        exc_info=True,
                    )
            mark_seen(src["name"], filename)
            saved += count
            logger.info("Saved %d 999 acknowledgment records from %s/%s", count, src["name"], filename)
    return saved


async def run() -> None:
    """Async loop — called from FastAPI lifespan."""
    loop = asyncio.get_event_loop()
    init_tracker()
    logger.info("Pipeline poller started. Interval=%ds", POLL_INTERVAL)
    while True:
        for src in SOURCES:
            try:
                saved = await loop.run_in_executor(None, _poll_source, src)
                if saved:
                    logger.info(
                        "Poll cycle: %s -> %d new docs", src["name"], saved
                    )
            except Exception as exc:
                logger.error("Poll error [%s]: %s", src["name"], exc)
        await asyncio.sleep(POLL_INTERVAL)
