from __future__ import annotations

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING
from pymongo.collection import Collection

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "edi_835")
MONGO_TRACKER_COLLECTION = os.getenv("MONGO_TRACKER_COLLECTION", "pipeline_tracker")

_client: MongoClient | None = None


def _collection() -> Collection:
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    return _client[MONGO_DB][MONGO_TRACKER_COLLECTION]


def init_tracker() -> None:
    """Ensure the unique compound index on (source, filename) exists."""
    col = _collection()
    col.create_index(
        [("source", ASCENDING), ("filename", ASCENDING)],
        unique=True,
        name="source_filename_unique",
    )


def is_seen(source: str, filename: str) -> bool:
    """Return True if this (source, filename) has already been processed."""
    col = _collection()
    return col.find_one({"source": source, "filename": filename}) is not None


def mark_seen(source: str, filename: str) -> None:
    """Upsert a tracker record with status='done' and the current UTC timestamp."""
    col = _collection()
    col.update_one(
        {"source": source, "filename": filename},
        {
            "$set": {
                "downloaded_at": datetime.now(timezone.utc).isoformat(),
                "status": "done",
            }
        },
        upsert=True,
    )
