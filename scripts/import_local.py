"""
Import local .835 files into MongoDB — same pipeline logic as the SFTP poller.

Usage:
    python scripts/import_local.py <folder>
    python scripts/import_local.py sample-files
    python scripts/import_local.py "C:\\Users\\VisalC\\Downloads\\era_files"
"""
from __future__ import annotations

import sys
import os
import logging
from pathlib import Path

# ── resolve repo root and add backend to sys.path ──
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "backend"))
sys.path.insert(0, str(repo_root))

from dotenv import load_dotenv
load_dotenv(repo_root / "backend" / ".env")

from app.parser import parse_835_text          # noqa: E402
from pipeline.mongo_save import save_era_file  # noqa: E402
from pipeline.tracker import init_tracker, is_seen, mark_seen  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)
log = logging.getLogger("import_local")

EXTENSIONS = {".835", ".edi", ".txt"}


def import_folder(folder: Path, source: str = "Local") -> None:
    init_tracker()

    files = [
        f for f in sorted(folder.iterdir())
        if f.is_file() and f.suffix.lower() in EXTENSIONS
    ]

    if not files:
        log.warning("No .835 / .edi / .txt files found in: %s", folder)
        return

    log.info("Found %d file(s) in %s", len(files), folder)
    total_saved = 0

    for f in files:
        if is_seen(source, f.name):
            log.info("SKIP (already imported): %s", f.name)
            continue

        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
            parsed = parse_835_text(text)
            count = save_era_file(source, f.name, parsed)
            mark_seen(source, f.name)
            total_saved += count
            log.info("OK  %s → %d ERA doc(s) saved", f.name, count)
        except Exception as exc:
            log.error("FAIL %s — %s", f.name, exc)

    log.info("Done. Total new docs saved: %d", total_saved)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/import_local.py <folder_path>")
        print("Example: python scripts/import_local.py sample-files")
        sys.exit(1)

    target = Path(sys.argv[1])
    if not target.is_absolute():
        target = repo_root / target

    if not target.exists():
        print(f"ERROR: Folder not found: {target}")
        sys.exit(1)

    import_folder(target)
