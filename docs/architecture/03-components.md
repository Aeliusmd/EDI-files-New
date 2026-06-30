# C4 Level 3 — Components

## Backend Components (existing + new)

```mermaid
C4Component
    title Component Diagram — FastAPI Backend

    Container_Boundary(backend, "EDI 835 Converter API — FastAPI / Uvicorn port 7007") {

        Component(corsMiddleware, "CORS Middleware",
            "FastAPI CORSMiddleware",
            "Reads CORS_ORIGINS env var. Currently permits localhost:7008. Does not need to list external API callers (non-browser clients skip CORS).")

        Component(apiKeyMiddleware, "API Key Auth Dependency",
            "FastAPI Depends() function — new",
            "Reads X-API-Key header. Compares HMAC-safe digest against hashed value in API_KEYS env var. Raises HTTP 401 on mismatch. Injected only into the lookup endpoint.")

        Component(internalEndpoints, "Internal Endpoints",
            "main.py — existing",
            "POST /api/edi/parse, /export/json, /export/csv, /export/excel, /save. No auth. Accept multipart file uploads. Call parser and db modules.")

        Component(eraLookupEndpoint, "ERA Lookup Endpoint",
            "main.py — new",
            "GET /api/era/lookup. Depends on apiKeyMiddleware. Validates trace_number query param. Delegates to MongoEraRepository. Returns EraLookupResponse.")

        Component(parser, "X12 835 Parser",
            "parser.py — existing",
            "parse_835_text(str) -> dict. Pure function. Detects separators, scans segments linearly, builds nested transaction/claim/service-line structure plus flat_rows and summary.")

        Component(mysqlDb, "MySQL Persistence",
            "db.py — existing",
            "save_parsed_result(). ORM models EdiImport + EdiClaimRow. SQLAlchemy 2.0 + PyMySQL. Activated only when MYSQL_URL env var is set.")

        Component(mongoRepo, "MongoDB ERA Repository",
            "mongo_db.py — new module",
            "get_mongo_client() singleton using MONGO_URI env var. find_by_trace_number(trace_number) -> list[dict]. Serialises ObjectId to string. Raises on connection failure.")
    }

    ComponentDb(mongo, "MongoDB era_payments", "10.103.0.201:27017", "Single-field index on trace_number")
    ComponentDb(mysql, "MySQL (optional)", "local", "edi_835_imports + edi_835_claim_rows")

    Rel(eraLookupEndpoint, apiKeyMiddleware, "Depends on", "FastAPI DI")
    Rel(eraLookupEndpoint, mongoRepo, "Calls find_by_trace_number()", "in-process")
    Rel(mongoRepo, mongo, "find({ trace_number })", "pymongo TCP")
    Rel(internalEndpoints, parser, "Calls parse_835_text()", "in-process")
    Rel(internalEndpoints, mysqlDb, "Calls save_parsed_result()", "in-process")
    Rel(mysqlDb, mysql, "SQLAlchemy session", "TCP / PyMySQL")
```

## Component Descriptions — New Components

### API Key Auth Dependency (`apiKeyMiddleware`)

A FastAPI `Depends()` callable injected only into the ERA lookup endpoint. The
existing internal endpoints remain unauthenticated (internal-only, localhost).

Behaviour:
1. Read the `X-API-Key` request header.
2. If the header is absent → `HTTP 401` with `WWW-Authenticate: ApiKey`.
3. Compute `hmac.compare_digest(sha256(provided_key), sha256(stored_key))` using
   the value(s) from the `API_KEYS` environment variable (comma-separated list
   to support key rotation).
4. If digest comparison fails → `HTTP 401`.
5. If comparison passes → return; endpoint handler proceeds.

The `hmac.compare_digest` call is mandatory to prevent timing-oracle attacks.
Keys are never logged. The comparison uses SHA-256 digests so the raw key is
never held in a comparable form in memory during the check.

### MongoDB ERA Repository (`mongo_db.py`)

New module. Keeps a module-level `MongoClient` singleton (thread-safe) created
at startup using the `MONGO_URI` environment variable. Connection string format:
`mongodb://host:port/` (no credentials shown here — see ADR-0008 for credential
management).

`find_by_trace_number(trace_number: str) -> list[dict]`:
- Executes `db.era_payments.find({"trace_number": trace_number})`.
- Converts every `ObjectId` field to `str` before returning (recursive walk or
  `bson.json_util.dumps` / `loads` round-trip).
- Returns an empty list if no documents match (the endpoint handler converts this
  to HTTP 404).
- Raises `pymongo.errors.PyMongoError` on connection failure; the endpoint handler
  catches this and returns HTTP 503.

### ERA Lookup Endpoint (`GET /api/era/lookup`)

New endpoint in `main.py`.

| Attribute | Value |
|---|---|
| Method | GET |
| Path | /api/era/lookup |
| Auth | X-API-Key header (required) |
| Query param | trace_number (string, required, non-blank) |
| Success | 200 with EraLookupResponse |
| Not found | 404 |
| Bad input | 400 |
| Auth failure | 401 |
| DB unavailable | 503 |

The endpoint is intentionally read-only (GET). It does not accept a request body.
The `trace_number` travels as a query parameter so the caller can construct the
URL directly and the value appears in server access logs for audit purposes.

## Existing Components (unchanged in function, listed for completeness)

### Internal Endpoints (`main.py` — existing)

Five endpoints unchanged. No auth added. CORS middleware continues to serve
them as before. The only change is that `main.py` gains one new endpoint
function and one new import of `mongo_db`.

### X12 835 Parser (`parser.py` — existing)

Zero changes. The lookup endpoint does not call the parser; it reads pre-stored
documents from MongoDB. The parser is only used during the upload/save workflow.

### MySQL Persistence (`db.py` — existing)

Zero changes. The lookup endpoint does not use MySQL.

## Component Interaction Summary

| Caller | Callee | Protocol | Notes |
|---|---|---|---|
| External caller | eraLookupEndpoint | HTTPS GET + X-API-Key | New. Requires TLS in production. |
| eraLookupEndpoint | apiKeyMiddleware | FastAPI Depends() | New. In-process. |
| eraLookupEndpoint | mongoRepo | In-process function call | New. |
| mongoRepo | MongoDB era_payments | TCP / pymongo | New. |
| Internal browser (page.jsx) | internalEndpoints | HTTP multipart | Existing. Unchanged. |
| internalEndpoints | parser | In-process | Existing. Synchronous. Blocks event loop (see ADR-0001). |
| internalEndpoints | mysqlDb | In-process | Existing. Optional. |
| mysqlDb | MySQL | TCP / PyMySQL | Existing. Optional. |
