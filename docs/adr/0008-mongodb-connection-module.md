# ADR-0008 — MongoDB Access: New Module with Singleton Client

Date: 2026-06-23
Status: Accepted

---

## Context

The existing backend has no MongoDB connectivity. All persistence uses the
optional MySQL pathway in `db.py`. The ERA lookup endpoint requires reading
from the `edi_835.era_payments` MongoDB collection at `10.103.0.201:27017`.

The design must decide:
1. Where MongoDB connection logic lives (inline in the endpoint vs. separate
   module).
2. How the connection is managed (new client per request vs. singleton).
3. How the connection string and credentials are supplied.

The existing `db.py` pattern (optional activation via env var, init at startup,
module-level singleton) is the established convention in this codebase.

---

## Decision

Create a new module `backend/app/mongo_db.py` containing:

- A module-level `_client: MongoClient | None = None` variable.
- A `get_mongo_client() -> MongoClient` function that initialises the client
  once on first call (lazy singleton) and returns it on subsequent calls.
  `MongoClient` is thread-safe and designed to be shared across threads.
- A `find_by_trace_number(trace_number: str) -> list[dict]` function that
  uses `get_mongo_client()`, queries `era_payments`, converts BSON ObjectId
  values to strings, and returns a plain Python list of dicts.
- The connection string is read from the `MONGO_URI` environment variable
  (e.g., `mongodb://10.103.0.201:27017/`). If `MONGO_URI` is absent, the
  endpoint returns HTTP 503.

The `MONGO_URI` variable is added to `.env.example` with a placeholder.
If MongoDB requires authentication, credentials are embedded in the URI
(`mongodb://user:pass@host:port/`) and the URI is treated as a secret.

The `mongo_db.py` module follows the same optional-activation pattern as
`db.py`: the startup hook calls a lightweight ping/init; failure is logged
but does not crash the process (the internal endpoints do not need MongoDB).

---

## Consequences

**Positive:**
- A shared `MongoClient` singleton uses a connection pool efficiently.
  `pymongo` recommends one client per process, not one per request.
- Separation from `db.py` keeps MySQL and MongoDB concerns isolated.
  Future changes to either database do not affect the other module.
- The `MONGO_URI` env var pattern is already understood by the team (mirrors
  `MYSQL_URL`).
- The module is easy to mock in unit tests (replace `get_mongo_client` with
  a fixture that returns a mock).

**Negative / accepted trade-offs:**
- The lazy singleton initialisation is not thread-safe if two requests
  arrive simultaneously before the client is created. In practice uvicorn
  uses a single process by default, so this race is absent. If multiple
  workers are added in the future, the startup hook must eagerly initialise
  the client.
- Credentials embedded in the URI appear in process environment variables,
  which are readable by any process running as the same OS user. This is
  the same risk as `MYSQL_URL` today. A secrets manager is the right
  long-term solution; see ADR-0007 "Alternatives Rejected" discussion.

---

## Alternatives Rejected

**Motor (async MongoDB driver) instead of pymongo**
Rejected for this phase. Motor is the asyncio-native MongoDB driver and
would prevent blocking the event loop during database I/O. However, the
existing codebase already blocks the event loop in `parse_835_text` and all
SQLAlchemy calls (ADR-0001). Adding Motor would create an inconsistency
where one I/O path is async and others are not. The lookup query is a
single-document point lookup on an index; expected latency is under 5 ms,
making event-loop blocking acceptable at the current scale. Motor should be
adopted together with the ADR-0001 thread-pool fix in a future pass.

**Inline connection logic in main.py**
Rejected. Placing pymongo calls directly in the endpoint function mixes
database concerns into the API layer. Testing would require patching
`main.py` internals. A dedicated module with a clear interface is testable
in isolation and consistent with the existing `db.py` pattern.
