# ADR-0006 — ERA Lookup Endpoint: GET with Query Parameter vs POST with Body

Date: 2026-06-23
Status: Accepted

---

## Context

The outside team needs to query ERA documents by `trace_number`. The design
must choose an HTTP method and how the lookup key is conveyed (URL query
parameter vs. request body). The `trace_number` is a check or EFT number
(e.g., `1234567890`) — a non-sensitive identifier, not PHI itself, though
the response it unlocks is PHI.

The caller is machine-to-machine. No HTML form, no browser caching concern.
The primary consumer will likely construct the URL in code and read the
JSON response programmatically.

---

## Decision

Use `GET /api/era/lookup?trace_number={value}`.

- Method: `GET`
- Path: `/api/era/lookup`
- Lookup key: `trace_number` as a URL query parameter (not in the request body)
- Auth: `X-API-Key` request header

---

## Consequences

**Positive:**
- GET semantics are correct: this is a read-only, idempotent operation.
  Caches (if any are ever added) can cache GET responses; POST responses
  are not cacheable by default.
- The `trace_number` value appears in server access logs automatically,
  creating an audit trail of every lookup at no extra implementation cost.
  This is directly useful for HIPAA access audit requirements.
- Callers can test the endpoint directly from a browser address bar or
  `curl` without constructing a body.
- Standard REST convention: looking up a resource by identifier maps to
  GET with a query parameter when the identifier does not form a clean
  resource hierarchy path (trace numbers are not hierarchical).

**Negative / accepted trade-off:**
- The `trace_number` appears in URLs and therefore in access logs, browser
  history (if ever called from a browser), and HTTP Referer headers.
  Assessment: `trace_number` is a payment reference number, not a patient
  identifier. Its appearance in logs is acceptable and is actually desirable
  for audit purposes. The PHI lives only in the response body, which is not
  logged.
- URL length is not a concern: trace numbers are short strings (typically
  10-20 characters).

---

## Alternatives Rejected

**POST /api/era/lookup with JSON body `{"trace_number": "..."}`**
Rejected. POST implies resource creation or a non-idempotent side effect.
Using POST for a read operation is semantically wrong and violates REST
conventions. It would also prevent HTTP-level caching of responses. The only
advantage of POST (hiding the parameter from logs) is actually a disadvantage
here because log visibility serves the audit trail.

**GET /api/era/{trace_number} as a path parameter**
Rejected. Path parameters imply the parameter uniquely identifies a resource
at a stable URL (e.g., `/users/{id}`). A `trace_number` is a query key that
may return multiple results and is more naturally a filter parameter than a
resource identity. A query parameter (`?trace_number=`) communicates "search
by this value" more clearly.
