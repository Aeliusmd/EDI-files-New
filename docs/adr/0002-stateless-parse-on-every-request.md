# ADR 0002 — Stateless Re-parse on Every Request (No Server-Side Cache)

Date: 2026-06-23
Status: Identified — remediation recommended

## Context

The frontend holds the user's `File` object in React state. Every action
(parse, export JSON, export CSV, export Excel, save to MySQL) sends a fresh
`multipart/form-data` POST that re-uploads the file bytes and causes the
backend to re-parse the entire EDI document from scratch. For a 1 MB 835
file this means the same 530-line parser runs five separate times for a
single user session.

This design emerged from a deliberate choice to keep the backend stateless
(no server-side session, no temporary file storage), which is reasonable for
a local tool. However it creates unnecessary CPU and network overhead.

## Decision (as-built)

No result cache exists on the backend. Each endpoint independently calls
`read_and_parse`, which calls `parse_835_text`. The frontend cannot pass
a previously parsed result back to the export endpoints because those
endpoints accept only a raw file upload.

## Consequences

Positive:
- Backend remains truly stateless. No temp files, no memory leaks, no
  cache eviction logic needed.
- Consistent: every response reflects the actual current file bytes.

Negative:
- Parse cost (CPU + memory) multiplied by number of user actions.
- Network cost: the file is uploaded N times per session, once per action.
- For large 835 files with thousands of claims the redundant work compounds.
- Export endpoints cannot derive data from the already-parsed result that
  the frontend received from /parse; they must rebuild it entirely.

## Alternatives Considered

1. Server-side parse cache keyed by file hash (SHA-256 of file content) with
   a short TTL (e.g., 10 minutes). Client sends hash as a header; if the
   server has the cached result it skips parsing. Rejected in original design
   for simplicity; this is the recommended next step for multi-action sessions.

2. Frontend-driven exports: the frontend already holds the parsed JSON; export
   endpoints could accept a structured JSON body instead of a raw file, removing
   re-parsing entirely for CSV/Excel. This shifts export logic closer to the
   client but keeps the backend simpler. The JSON view already shows the full
   structure; the data is present.

3. Parse once on /parse; return a short-lived token; other endpoints accept
   the token. Introduces server state and a cleanup problem. Over-engineered
   for a local tool.

## Recommended Remediation

Implement option 2 for local use: add `/api/edi/export/csv` and `/excel`
variants that accept the already-parsed JSON body rather than a file upload.
The frontend sends the data it already holds. Reserve option 1 (hash cache)
for multi-user scenarios.
