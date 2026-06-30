# Architecture Assessment — EDI 835 Converter

Date: 2026-06-23
Reviewer: Architect (automated assessment)

---

## 1. C4-Style Component Diagram (text)

See `01-context.md`, `02-containers.md`, and `03-components.md` for full
layered diagrams. Inline summary below.

```
[Operator Browser]
      |
      | HTTP multipart/form-data  (file re-sent on every action)
      |
      v
[FastAPI — port 7007]
  |                   \
  | parse_835_text()   \ save_parsed_result()
  | (sync, blocking)    \ (sync, blocking)
  |                      \
  v                       v
[parser.py]            [db.py]
  linear X12 scan        SQLAlchemy session
  ~530 lines             ORM: EdiImport + EdiClaimRow
  pure function          |
                         v
                      [MySQL — optional]
                         edi_835_imports
                         edi_835_claim_rows
```

---

## 2. Architecture Assessment

### What Is Well Done

**Parser design is clean.**
`parse_835_text` in `parser.py` is a pure function with no side effects and
no I/O dependencies. Separator detection reads the ISA envelope rather than
assuming defaults. The linear segment scan uses a state-machine pattern
(tx, current_claim, current_service, current_party) that mirrors the X12
hierarchy faithfully. Lookup tables for CLAIM_STATUS_CODES, ADJUSTMENT_GROUP_CODES,
ENTITY_CODES, DATE_QUALIFIERS, and REF_QUALIFIERS are correct and readable.
The `money()` helper uses `Decimal` for parsing and converts to `float` only
for the output dict — this is the right approach for input parsing, though
float in the output dict is still imprecise for downstream aggregation.

**Database optionality is handled gracefully.**
`is_enabled()` and the conditional engine creation mean the app starts
cleanly without a MySQL URL. The save endpoint returns a clear diagnostic
message when MySQL is not configured rather than crashing. This is good
defensive design for a tool that is often run without a database.

**Separation of concerns at the module level is reasonable.**
`parser.py`, `db.py`, and `main.py` have clearly bounded responsibilities.
The parser knows nothing about HTTP or databases. The API layer is thin.
This will make future refactoring tractable.

**Export format coverage is appropriate.**
JSON, CSV, and Excel with a multi-sheet layout (Summary, Envelope,
Claim Service Lines) covers the practical needs of billing staff. The
auto-column-width Excel formatting is a usability touch that shows awareness
of end-user needs.

**`.env.example` pattern for secrets is correct.**
`MYSQL_URL` and `CORS_ORIGINS` are externalised through environment
variables with documented defaults. The `.gitignore` correctly excludes `.env`.

---

### Concerns

**C1 — Synchronous blocking on the async event loop (HIGH)**
`parse_835_text` and all SQLAlchemy calls run synchronously inside async
endpoint handlers. Any file that takes more than ~20 ms to parse will stall
Uvicorn's event loop, blocking all concurrent requests. For a single-user
local tool this is survivable; for any shared or multi-tab use it is a
correctness problem. See ADR 0001.

**C2 — File re-parsed on every request (MEDIUM)**
Every user action (parse, export CSV, export Excel, save) re-uploads and
re-parses the file from scratch. For a five-action workflow the parser runs
five times on the same bytes. See ADR 0002.

**C3 — CORS origins mismatch (HIGH — IMMEDIATE BUG)**
The default value of `CORS_ORIGINS` in `main.py` is
`http://localhost:3000,http://127.0.0.1:3000`. The frontend now runs on
port 7008. Any browser request from the frontend to the backend will be
rejected by the CORS preflight unless the operator has manually set the
environment variable. This will cause silent failures in the browser.
The `.env.example` also still references port 3000 and an old backend port
of 8000. All three values are stale.

**C4 — No authentication, no file size limit (HIGH for networked use)**
The backend accepts uploads from any HTTP client with no size cap. On a
localhost-only deployment this is acceptable. Any exposure beyond loopback
is a security and availability risk, compounded by the PHI content of 835
files. See ADR 0004.

**C5 — ORM and DDL are inconsistent (MEDIUM)**
`Float` columns in the ORM vs `DECIMAL(12,2)` in the DDL. Missing FK in
the ORM. If `create_all` runs, the database will have incorrect types and
no referential integrity. See ADR 0005.

**C6 — raw_json blob doubles storage (MEDIUM)**
The entire parsed result (including all flat_rows) is stored as a JSON
string in `edi_835_imports.raw_json`. For large remittances this can be
tens of megabytes per import record. `row_json` on `EdiClaimRow` adds a
third copy of each service-line's data. See ADR 0003.

**C7 — No server-side pagination (MEDIUM for large files)**
The frontend renders all flat_rows into the DOM without virtualisation.
A 2,500-row result set will produce a 2,500-row `<table>` with 35,000
`<td>` nodes. Browsers begin to lag noticeably at this scale. No
pagination, no windowing library, no server-side cursor.

**C8 — Client-side search scans all values of all rows (LOW-MEDIUM)**
The `useMemo` filter in `page.jsx` converts every value of every flat_row
to a string and performs a substring match. For large result sets this is
an O(n * columns) scan on every keystroke. Acceptable for hundreds of rows;
degrades visibly at thousands.

**C9 — Filename used unsanitised in Content-Disposition header (LOW)**
`os.path.basename(file.filename)` is used in export response headers.
`os.path.basename` does strip path separators but does not sanitise
characters that are invalid in HTTP headers (semicolons, quotes, newlines).
A specially crafted filename could inject into the `Content-Disposition`
header value. Low risk in a local tool; worth fixing before any networked
exposure.

---

## 3. Top 5 Structural Improvements Ranked by Impact

### Rank 1 — Fix the CORS origins mismatch (effort: minutes)

**Why it is highest:** This is a live bug. Any developer who runs both
services at their default ports and has not set `CORS_ORIGINS` manually
will find that parse, export, and save all fail silently in the browser.

**What to change:**
- `backend/app/main.py` line 19: change the default string from
  `http://localhost:3000,http://127.0.0.1:3000` to
  `http://localhost:7008,http://127.0.0.1:7008`.
- `backend/.env.example`: update `CORS_ORIGINS` to port 7008 and the
  comment to reflect the correct backend port (7007, not 8000).

No architecture change required. One line of code.

---

### Rank 2 — Offload the parser to a thread pool (effort: small)

**Why:** Blocking the async event loop is a structural defect that prevents
correct concurrent behaviour. Even for single-user use, a large file will
cause the browser to time out if the default Uvicorn request timeout is hit.

**What to change:**
In `main.py`, replace the direct call to `parse_835_text(text)` with
`await asyncio.get_event_loop().run_in_executor(None, parse_835_text, text)`.
Apply the same pattern to the `save_parsed_result` call in `/save`.

No changes to `parser.py` or `db.py` are required. Parser is already a
pure function, which makes this safe.

---

### Rank 3 — Add a file size guard before parsing (effort: small)

**Why:** Without a size limit, any caller can send an arbitrarily large file.
The parser will allocate memory proportional to the file size with no cap.
This is a denial-of-service vector and a memory safety concern.

**What to change:**
In `read_and_parse`, after `content = await file.read()`, add:
```
MAX_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", 10 * 1024 * 1024))  # 10 MB
if len(content) > MAX_BYTES:
    raise HTTPException(status_code=413, detail=f"File exceeds maximum size of {MAX_BYTES} bytes.")
```
Expose `MAX_UPLOAD_BYTES` in `.env.example`.

---

### Rank 4 — Fix the ORM monetary column types and add the FK (effort: small)

**Why:** Financial data stored as IEEE 754 FLOAT loses precision. The missing
FK means referential integrity depends entirely on application code. Both are
correctness bugs for a healthcare remittance tool.

**What to change:**
In `db.py`:
- Add `from sqlalchemy import ForeignKey, Numeric` to imports.
- Change all `Float` monetary columns to `Numeric(precision=12, scale=2,
  asdecimal=True)`.
- Change `import_id = Column(Integer, ...)` to
  `import_id = Column(Integer, ForeignKey('edi_835_imports.id', ondelete='CASCADE'), ...)`.
- Change `Integer` PK columns to `BigInteger` to match the DDL's BIGINT.

This also closes the ORM/DDL divergence described in ADR 0005.

---

### Rank 5 — Eliminate raw_json from edi_835_imports (effort: medium)

**Why:** The blob duplicates all data already stored in `edi_835_claim_rows`.
For large files it will be the dominant storage cost and will slow down
any query that touches the imports table due to the large row size.

**What to change:**
Remove `raw_json` from `EdiImport`. If full-fidelity replay is needed,
store the original file bytes separately (local filesystem path or object
storage) and re-parse on demand. Also remove `row_json` from `EdiClaimRow`;
the normalised scalar columns are sufficient for querying.

This requires a schema migration if any existing data exists.

---

## 4. Suggested Next-Phase Architecture for Production Healthcare Use

A healthcare production deployment of this tool must address: multi-tenancy,
HIPAA technical safeguards, auditability, scale, and operational resilience.
The following is a recommended target architecture. Each boundary below
represents a new container or service; none of this exists today.

```
                         ┌──────────────────────────────┐
                         │  Identity Provider           │
                         │  (Okta / Azure AD / Auth0)   │
                         │  SAML 2.0 or OIDC            │
                         └──────────────────────────────┘
                                        |
                                        | JWT / session
                                        v
┌───────────────────────────────────────────────────────────────────────┐
│  API Gateway / Reverse Proxy (nginx / AWS API Gateway)                │
│  - TLS termination                                                    │
│  - Rate limiting per tenant                                           │
│  - JWT validation                                                     │
│  - Request logging (PHI-aware: log metadata, not content)            │
└───────────────────────────────────────────────────────────────────────┘
         |                       |                       |
         v                       v                       v
┌─────────────────┐   ┌──────────────────┐   ┌─────────────────────┐
│  Upload Service │   │  Parse Worker    │   │  Export Service     │
│                 │   │  (async task)    │   │                     │
│  Accepts file   │   │                  │   │  Reads from DB;     │
│  Validates type │   │  Consumed from   │   │  generates CSV /    │
│  Enforces size  │   │  message queue   │   │  Excel / JSON from  │
│  Stores raw     │   │  (RabbitMQ /     │   │  stored rows only.  │
│  file in object │   │  SQS)            │   │  No re-parsing.     │
│  storage        │   │                  │   │                     │
│  (S3 / Azure    │   │  Calls           │   │  Streams response   │
│   Blob)         │   │  parse_835_text  │   │  to caller.         │
│                 │   │  in subprocess   │   └─────────────────────┘
│  Returns job ID │   │  or thread pool  │
└─────────────────┘   │                  │
         |            │  Writes result   │
         | enqueue    │  to database     │
         v            └──────────────────┘
┌─────────────────┐              |
│  Message Queue  │              v
│  (RabbitMQ /    │   ┌──────────────────────────────────────┐
│   SQS)          │   │  Database (PostgreSQL preferred)     │
└─────────────────┘   │                                      │
                       │  edi_835_imports (no raw_json blob) │
                       │  edi_835_claim_rows (FK enforced)   │
                       │  edi_audit_log (every access event) │
                       │  edi_users / edi_tenants            │
                       │                                     │
                       │  Alembic migrations                 │
                       │  DECIMAL for all monetary fields    │
                       └──────────────────────────────────────┘
                                        |
                                        v
                       ┌──────────────────────────────────────┐
                       │  Object Storage (S3 / Azure Blob)   │
                       │  Original .835 files (encrypted)    │
                       │  Retention policy (HIPAA: 6 years)  │
                       └──────────────────────────────────────┘
```

### Key production decisions

**Database:** Switch from MySQL to PostgreSQL. PostgreSQL's JSONB is more
efficient if any JSON is retained. The `Numeric` type is better supported.
The ecosystem (Alembic, asyncpg, pgBouncer) is more mature for Python
services. MySQL remains viable but requires careful DECIMAL/BIGINT discipline
already missing from the current ORM.

**Async task queue:** Move parsing off the HTTP request path entirely.
POST /api/edi/upload accepts the file, stores it in object storage, enqueues
a job, and returns a job ID. The frontend polls or uses a WebSocket for
completion notification. This decouples upload latency from parse latency
and allows horizontal scaling of parse workers.

**Audit log:** Every read, parse, export, and save of PHI must be logged with
user identity, timestamp, resource identifier, and action. The current system
has no audit trail. This is a HIPAA technical safeguard requirement.

**PHI encryption at rest:** Object storage and database must use encryption
at rest. Encryption keys must be managed separately from application credentials
(AWS KMS / Azure Key Vault). The current system stores PHI in plaintext in
MySQL and in memory.

**No FLOAT for money — ever:** All financial columns must be DECIMAL or use
an integer-cents representation. IEEE 754 is not acceptable for remittance
amounts subject to payer reconciliation.

**Multi-tenancy:** Add a `tenant_id` foreign key to all data tables. All
queries must include tenant isolation. Row-level security in PostgreSQL is the
recommended mechanism.

**Frontend pagination:** Replace the all-rows DOM render with a server-side
paginated API (`GET /api/edi/imports/{id}/rows?page=1&size=50`). The current
approach will not scale beyond a few hundred rows without noticeable browser
lag.

---

## ADR Cross-Reference

| Issue | ADR |
|---|---|
| Synchronous parser on async loop | 0001 |
| Re-parse on every request | 0002 |
| raw_json blob storage | 0003 |
| No auth, no size limit, CORS mismatch | 0004 |
| ORM/DDL schema divergence | 0005 |
