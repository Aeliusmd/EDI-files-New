"""Project-wide file logging for the EDI pipeline / backend."""
from __future__ import annotations

import logging
import os
from pathlib import Path

_CONFIGURED = False


def setup_project_logging(
    log_name: str = "edi_pipeline.log",
    level: int | None = None,
) -> Path:
    """Attach a rotating-style file handler under repo logs/.

    Safe to call multiple times — configures only once.
    Returns the log file path.
    """
    global _CONFIGURED

    repo_root = Path(__file__).resolve().parents[1]
    logs_dir = Path(os.getenv("EDI_LOG_DIR", str(repo_root / "logs")))
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / log_name

    if _CONFIGURED:
        return log_path

    log_level = level
    if log_level is None:
        name = os.getenv("EDI_LOG_LEVEL", "INFO").upper()
        log_level = getattr(logging, name, logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(log_level)

    # Avoid duplicate file handlers if uvicorn already configured logging.
    for h in root.handlers:
        if isinstance(h, logging.FileHandler) and Path(getattr(h, "baseFilename", "")) == log_path:
            _CONFIGURED = True
            return log_path

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    # Keep console output if nothing else is attached yet.
    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) for h in root.handlers):
        console = logging.StreamHandler()
        console.setLevel(log_level)
        console.setFormatter(fmt)
        root.addHandler(console)

    _CONFIGURED = True
    logging.getLogger("pipeline.logging_setup").info("Project log file: %s", log_path)
    return log_path
