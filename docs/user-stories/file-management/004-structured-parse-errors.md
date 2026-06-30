# Story 004 — Structured Parse Error Detail

**Epic:** File Management / Data Quality
**Priority:** P1
**Effort:** S (< 4 hours)

---

## User Story

As a healthcare IT team member, I want the application to show me a specific, actionable error message when an EDI file fails to parse, so that I can diagnose whether the file is malformed, the wrong transaction type, or an encoding issue without reading Python stack traces.

---

## Background

The backend `read_and_parse()` function in `main.py` catches two exception types:
- `ValueError` — raised intentionally by `parse_835_text()` when structural problems are detected (empty file, missing ISA segment).
- `Exception` — a catch-all that returns `f"Failed to parse EDI file: {exc}"`, which surfaces as the raw Python exception string in the frontend message banner.

The frontend renders the `detail` field from the JSON error body as an unformatted string with no categorization or recovery instructions. Users cannot tell whether they uploaded the wrong file type (an 837, for example), a truncated file, or a file with an unusual separator character.

The parser's `detect_separators()` already handles non-standard separators gracefully but does not report back which separators it detected. Adding a `parse_warnings` list to the result would make partial-success cases transparent.

---

## Acceptance Criteria

**AC-1: Wrong transaction type produces a clear error**

Given a user uploads an X12 file that starts with ISA but whose ST segment is type 837 (claim) or 277 (status) rather than 835,
When the backend attempts to parse the file,
Then the API response has HTTP 400 and a `detail` object (not string) with fields: `error_code: "WRONG_TRANSACTION_TYPE"`, `message: "This file is an X12 [837/277] transaction, not an 835 ERA."`, and `hint: "Please upload an Electronic Remittance Advice (835) file."`.

**AC-2: Empty or corrupted file produces a clear error**

Given a user uploads an empty file or a file whose content cannot be decoded as X12 (e.g., a PDF accidentally named .835),
When the backend processes the upload,
Then the API response has HTTP 400 with `error_code: "INVALID_FILE"` and a human-readable `message` indicating the file cannot be parsed as an X12 EDI document.

**AC-3: Frontend displays structured errors with guidance**

Given the backend returns a structured error object with `error_code`, `message`, and `hint`,
When the frontend receives the error response,
Then the message banner displays the `message` text prominently and the `hint` text in a secondary style, not a raw exception string or JSON blob.

**AC-4: Partial parse produces a warnings list**

Given a 835 file that is structurally valid but contains segments the parser does not recognize (non-standard extensions),
When parsing completes successfully,
Then the JSON response includes a `parse_warnings` array listing each unrecognized segment tag and its occurrence count, so the user is aware of data that was skipped.

---

## Implementation Notes

- Backend: Replace the generic `Exception` catch in `read_and_parse()` with specific exception subclasses or error codes. Add a `parse_warnings` collector list to `parse_835_text()`.
- Detect ST01 segment value; if not `"835"`, raise a `ValueError` with `WRONG_TRANSACTION_TYPE` context.
- Frontend: Check if `data.detail` is a string or object; branch rendering accordingly.
- Do not expose internal Python tracebacks in any error response.

---

## Out of Scope

- Full EDI validation report (that is Story 009).
- Recovering and partially displaying data from a corrupted file.
