# C4 Level 2 — Containers

## Diagram

```mermaid
C4Container
    title Container Diagram — EDI 835 Converter + ERA Lookup API

    Person(internalUser, "Medical Billing Operator", "Uploads .835 files via browser")
    Person_Ext(externalCaller, "External Team Caller", "Queries ERA by trace_number")

    System_Boundary(sys, "EDI 835 System") {

        Container(frontend, "Web Frontend",
            "Next.js 14 / React — port 7008",
            "Single-page application. File selection, parse trigger, table/JSON viewer, export downloads, MySQL save. All parsed data held in browser React state.")

        Container(backend, "EDI 835 Converter API",
            "Python / FastAPI / Uvicorn — port 7007",
            "HTTP API. Handles file upload + parse, export streaming, MongoDB ERA lookup. Enforces API key auth on the lookup endpoint. CORS managed via env var.")

        ContainerDb(mongo, "MongoDB",
            "MongoDB 10.103.0.201:27017 — database: edi_835 / collection: era_payments",
            "Stores ingested ERA transactions as documents. Key query field: trace_number (top-level, indexed). Each document contains full transaction, flat_rows, and envelope sub-objects.")
    }

    ContainerDb_Ext(mysql, "MySQL Database",
        "Optional — local",
        "Stores edi_835_imports and edi_835_claim_rows. Used by internal save workflow only. Not consulted by the ERA lookup endpoint.")

    Rel(internalUser, frontend, "Uses", "HTTPS / browser")
    Rel(frontend, backend, "Uploads files, fetches exports", "HTTP multipart/form-data — localhost:7007")
    Rel(externalCaller, backend, "GET /api/era/lookup with X-API-Key", "HTTPS / REST / JSON")
    Rel(backend, mongo, "find({ trace_number: ... })", "TCP — pymongo")
    Rel(backend, mysql, "save_parsed_result() — optional", "TCP — SQLAlchemy / PyMySQL")
```

## Container Descriptions

### Web Frontend — Next.js 14 (port 7008)

Single-page React application for internal billing operators. Communicates with
the backend exclusively at `localhost:7007`. Re-sends the uploaded file on every
action because parsed data lives only in browser memory (`useState`). This
container is not involved in the new external lookup workflow.

### EDI 835 Converter API — FastAPI / Uvicorn (port 7007)

The central container. Handles all HTTP traffic from both internal and external
callers. Responsibilities after the new endpoint is added:

| Endpoint group | Auth | Consumer |
|---|---|---|
| POST /api/edi/parse | None | Internal frontend |
| POST /api/edi/export/{format} | None | Internal frontend |
| POST /api/edi/save | None | Internal frontend |
| GET /api/era/lookup | X-API-Key header (new) | External team |

CORS is configured via the `CORS_ORIGINS` environment variable. The existing
value covers `localhost:7008`. External callers are not browsers and do not send
CORS preflight requests, so the CORS middleware does not need to list external
IP addresses — but see the CORS design note in section 5 of the design plan.

### MongoDB — edi_835 / era_payments (10.103.0.201:27017)

Stores one document per ingested ERA transaction. The lookup endpoint queries
this collection exclusively. The `trace_number` field must carry a single-field
ascending index to support sub-millisecond point lookups and list queries.

The `_id` field (BSON ObjectId) is serialised as a string in the API response
using a custom JSON encoder, since ObjectId is not natively JSON-serialisable.

### MySQL Database (optional, local)

Unchanged from the existing design. Used only by the internal save workflow.
Not consulted by the new ERA lookup endpoint.

## Runtime Data Flow — ERA Lookup (new)

```
External Caller
  |
  |-- GET /api/era/lookup?trace_number=1234567890
  |   Header: X-API-Key: <key>
  |
  v
FastAPI — /api/era/lookup handler
  |
  |-- 1. Extract X-API-Key header
  |-- 2. Compare against hashed key stored in API_KEY env var
  |-- 3a. If mismatch → 401 Unauthorized
  |-- 3b. If trace_number absent or blank → 400 Bad Request
  |
  |-- 4. db.era_payments.find({ "trace_number": trace_number })
  |        (uses index on trace_number)
  |
  |-- 5a. No documents found → 404 Not Found
  |-- 5b. One or more documents found → serialise (ObjectId → str)
  |
  v
External Caller
  |<-- 200 OK
       Content-Type: application/json
       {
         "trace_number": "1234567890",
         "match_count": 2,
         "results": [ { ...era doc... }, { ...era doc... } ]
       }
```

## Deployment Topology

Both the frontend and backend run on the same host machine. MongoDB is on a
separate internal server (`10.103.0.201`). There is currently no reverse proxy,
TLS termination, or API gateway between the external caller and the FastAPI
process. For production external exposure, a TLS-terminating reverse proxy
(nginx or equivalent) must sit in front of the FastAPI port. See ADR-0006.
