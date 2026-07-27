from __future__ import annotations

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from pymongo import ASCENDING, MongoClient

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://10.103.0.201:27017")
MONGO_DB = os.getenv("MONGO_DB", "edi_835")
REFRESH_COLLECTION = os.getenv("MONGO_REFRESH_COLLECTION", "auth_refresh_tokens")

_client: MongoClient | None = None


def _get_collection():
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    col = _client[MONGO_DB][REFRESH_COLLECTION]
    ensure_indexes(col)
    return col


def ensure_indexes(col) -> None:
    col.create_index([("jti", ASCENDING)], name="idx_refresh_jti", unique=True, background=True)
    col.create_index([("client_id", ASCENDING)], name="idx_refresh_client_id", background=True)
    col.create_index(
        [("expires_at", ASCENDING)],
        name="idx_refresh_ttl",
        expireAfterSeconds=0,
        background=True,
    )


def save_refresh_jti(jti: str, client_id: str, expires_at: datetime) -> None:
    col = _get_collection()
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    col.insert_one(
        {
            "jti": jti,
            "client_id": client_id,
            "expires_at": expires_at,
            "revoked": False,
            "created_at": datetime.now(timezone.utc),
        }
    )


def is_refresh_jti_valid(jti: str) -> bool:
    col = _get_collection()
    doc = col.find_one({"jti": jti, "revoked": False})
    return doc is not None


def revoke_refresh_jti(jti: str) -> None:
    col = _get_collection()
    col.update_one({"jti": jti}, {"$set": {"revoked": True}})


def revoke_all_for_client(client_id: str) -> None:
    col = _get_collection()
    col.update_many({"client_id": client_id, "revoked": False}, {"$set": {"revoked": True}})


def init_refresh_store() -> None:
    """Create indexes on startup."""
    _get_collection()
