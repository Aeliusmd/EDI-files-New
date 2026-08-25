"""
Create Mongo database edi_277_999 with 277/999 collections on the same server,
and remove old 277/999 collections from edi_835. Does not touch era_payments.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

repo_root = Path(__file__).resolve().parents[1]
load_dotenv(repo_root / "backend" / ".env")

sys.path.insert(0, str(repo_root))

from pymongo import MongoClient  # noqa: E402

from pipeline.mongo_save import (  # noqa: E402
    CLAIM_STATUS_277_COLLECTION,
    FUNCTIONAL_ACK_999_COLLECTION,
    MONGO_277_999_DB,
    MONGO_DB,
    MONGO_URI,
    init_277_collection,
    init_999_collection,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger("setup_mongo_277_999")

OLD_277_999_NAMES = {
    CLAIM_STATUS_277_COLLECTION,
    FUNCTIONAL_ACK_999_COLLECTION,
    "claim_status_277",
    "functional_ack_999",
}
PROTECTED = {"era_payments", "pipeline_tracker", "auth_refresh_tokens"}


def main() -> None:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)
    client.admin.command("ping")
    log.info("Connected to %s", MONGO_URI)

    # 1) Remove old 277/999 collections from the 835 database
    old_db = client[MONGO_DB]
    old_names = set(old_db.list_collection_names())
    log.info("Collections in %s before cleanup: %s", MONGO_DB, sorted(old_names))

    to_drop = {
        name
        for name in old_names
        if name not in PROTECTED
        and (name in OLD_277_999_NAMES or "277" in name or "999" in name)
    }
    for name in sorted(to_drop):
        old_db.drop_collection(name)
        log.info("Dropped %s.%s", MONGO_DB, name)

    tracker = os.getenv("MONGO_TRACKER_COLLECTION", "pipeline_tracker")
    if tracker in old_db.list_collection_names():
        result = old_db[tracker].delete_many(
            {"filename": {"$regex": r"\.(277|999)$", "$options": "i"}}
        )
        log.info("Removed %d .277/.999 tracker row(s) from %s.%s", result.deleted_count, MONGO_DB, tracker)

    remaining_old = set(old_db.list_collection_names())
    leftover_277_999 = {
        n for n in remaining_old if ("277" in n or "999" in n) and n not in PROTECTED
    }
    if leftover_277_999:
        raise SystemExit(f"Still found 277/999 collections in {MONGO_DB}: {sorted(leftover_277_999)}")
    log.info("%s after cleanup: %s", MONGO_DB, sorted(remaining_old))

    # 2) Create new database + collections (indexes force collection creation)
    new_db = client[MONGO_277_999_DB]
    init_277_collection()
    init_999_collection()

    # Touch collections so they exist even if empty
    new_db[CLAIM_STATUS_277_COLLECTION]
    new_db[FUNCTIONAL_ACK_999_COLLECTION]

    new_names = set(new_db.list_collection_names())
    log.info(
        "Created database %s with collections: %s",
        MONGO_277_999_DB,
        sorted(new_names),
    )
    log.info(
        "Counts: %s=%d %s=%d",
        CLAIM_STATUS_277_COLLECTION,
        new_db[CLAIM_STATUS_277_COLLECTION].count_documents({}),
        FUNCTIONAL_ACK_999_COLLECTION,
        new_db[FUNCTIONAL_ACK_999_COLLECTION].count_documents({}),
    )
    log.info("%s.era_payments untouched (%d docs)", MONGO_DB, old_db["era_payments"].count_documents({}))
    client.close()


if __name__ == "__main__":
    main()
