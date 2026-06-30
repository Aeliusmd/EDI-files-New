from __future__ import annotations

import os
from typing import Any

from bson import ObjectId
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING

load_dotenv()

MONGO_URI       = os.getenv("MONGO_URI",       "mongodb://10.103.0.201:27017")
MONGO_DB        = os.getenv("MONGO_DB",        "edi_835")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "era_payments")

_client: MongoClient | None = None


def _get_collection():
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    col = _client[MONGO_DB][MONGO_COLLECTION]
    col.create_index([("trace_number", ASCENDING)], name="idx_trace_number", background=True)
    return col


def _serialize(doc: Any) -> Any:
    """Recursively convert ObjectId → str, exclude _id."""
    if isinstance(doc, dict):
        return {k: _serialize(v) for k, v in doc.items() if k != "_id"}
    if isinstance(doc, list):
        return [_serialize(i) for i in doc]
    if isinstance(doc, ObjectId):
        return str(doc)
    return doc


def find_by_trace_number(trace_number: str) -> list[dict]:
    col = _get_collection()
    docs = list(col.find({"trace_number": trace_number}))
    return [_serialize(doc) for doc in docs]
