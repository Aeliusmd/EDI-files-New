# Story 010 — Upload Audit Log

**Epic:** Compliance and Audit
**Priority:** P2
**Effort:** M (1–2 days)

---

## User Story

As a practice manager, I want the system to record a log entry every time an ERA file is uploaded and parsed, including the filename, timestamp, summary totals, and outcome, so that I have a traceable record of remittance processing activity for compliance and reconciliation purposes.

---

## Background

The existing `EdiImport` table in `db.py` already captures `filename`, `file_type`, `transaction_count`, `claim_count`, `service_line_count`, `total_payment_amount`, and `created_at`. However, this record is only written when the user explicitly clicks "Save to MySQL" — the parse endpoint (`POST /api/edi/parse`) writes nothing. An audit log should be automatic and separate from the user-initiated save action.

Additionally, there is no UI to view past imports. The database accumulates data only if MySQL is configured, and there is no read endpoint to retrieve the history.

---

## Acceptance Criteria

**AC-1: Parse events are automatically logged when MySQL is configured**

Given the backend has MYSQL_URL configured,
When a user uploads and parses any 835 file via `POST /api/edi/parse`,
Then a row is automatically inserted into a new `edi_parse_log` table with: `filename`, `parse_timestamp`, `client_ip` (or "unknown"), `outcome` ("success" or "error"), `error_message` (null on success), `transaction_count`, `claim_count`, `total_payment_amount`.

**AC-2: Failed parse attempts are also logged**

Given the backend has MySQL configured and a user uploads an invalid file,
When the parse fails,
Then a log entry is recorded with `outcome: "error"` and `error_message` containing the error detail. The log entry must not itself fail (the logging operation must not propagate exceptions that hide the original parse error from the user).

**AC-3: A read endpoint returns the audit log**

Given MySQL is configured and at least one parse event has occurred,
When an authorized client calls `GET /api/edi/audit-log?limit=50&offset=0`,
Then the response returns a paginated list of log entries ordered by `parse_timestamp` descending, each entry containing all logged fields.

**AC-4: The UI displays the audit log**

Given the audit log endpoint is available,
When the user opens an "Upload History" page or panel in the frontend,
Then they see a table of past upload events with columns: filename, timestamp, outcome, claim count, and total payment. Failed events are visually distinguished (e.g., red badge).

**AC-5: Log entries are read-only**

Given the audit log is visible in the UI,
When the user views log entries,
Then there is no delete, edit, or modify action available on individual log entries. The log is append-only.

---

## Implementation Notes

- Add a new `EdiParseLog` SQLAlchemy model to `db.py`. Do not reuse `EdiImport` — they serve different purposes (EdiImport stores full parsed data for query; EdiParseLog is a lightweight event log).
- Log insertion must be wrapped in a separate try/except so a DB failure during logging does not surface as a parse failure to the user.
- `client_ip`: extract from `Request.client.host` (FastAPI `Request` dependency injection). Do not store full request headers.
- The `GET /api/edi/audit-log` endpoint should require MySQL to be enabled and return a 503 with a clear message if it is not.
- When MySQL is not configured, skip logging silently (not an error).

---

## Out of Scope

- Authentication of log viewers (deferred to P3-1 auth story).
- Log retention policy / automatic purging (deferred).
- Exporting the audit log (useful; can be a follow-on story).
- Logging export and save events (useful extension; currently only parse events are in scope).
