# ERA Lookup API — MVP Requirements

**Version:** 1.0
**Date:** 2026-06-23
**Status:** Draft

---

## Problem Statement

An outside team (billing reconciliation) needs to query ERA (Electronic Remittance Advice) payment details
by providing a trace number — the cheque or EFT reference printed on their remittance. The existing EDI 835
pipeline already stores 7,351 parsed ERA documents in MongoDB, each identified by a `trace_number`. No
programmatic lookup endpoint currently exists.

---

## In-Scope (MVP v1)

| # | Feature |
|---|---------|
| 1 | GET endpoint: look up a single ERA document by exact `trace_number` |
| 2 | Return ERA payment header (amounts, dates, method, payer, payee) |
| 3 | Return claim list with service lines and adjustment details |
| 4 | Return data source metadata (Matrix or DMS, original filename) |
| 5 | 404 response when trace number not found |
| 6 | 300 multi-match response (list of summaries) when trace number is duplicated |
| 7 | API key authentication via `X-API-Key` header |
| 8 | API key issuance and rotation process (manual, ops-managed) |
| 9 | Rate limiting: 60 requests per minute per key |
| 10 | HTTPS only — no plaintext HTTP |
| 11 | Request/response logging for audit trail |

---

## Out-of-Scope (MVP v1)

| Feature | Reason deferred |
|---------|-----------------|
| Search by payer name, date range, or claim ID | Requires query parameters beyond point lookup; v2 candidate |
| Bulk / batch trace number lookup | Scope reduction; v2 candidate |
| Webhook / push notifications | Requires event infrastructure |
| Self-service key provisioning portal | Ops-managed process sufficient for single outside team |
| OAuth 2.0 / OIDC | Over-engineered for a single known consumer at MVP |
| Pagination of claims within a single ERA | ERA claim counts are bounded; not an unbounded list |
| Write / mutation operations | Read-only is all the outside team requires |
| Raw EDI text in response | Sensitive source data; not needed by caller |
| SFTP pipeline control via API | Unrelated to lookup |

---

## Success Metrics

| Metric | Target |
|--------|--------|
| P99 response latency (single lookup) | Less than 200 ms |
| Availability | 99.5% monthly uptime |
| Correct match rate on valid trace numbers | 100% (no silent mismatches) |
| Zero unauthorized access incidents | Enforced by key gate plus HTTPS |
| Outside team integration complete | Within 5 business days of API delivery |

---

## Constraints

- MongoDB is the system of record; no additional data store may be introduced for v1.
- `trace_number` values are treated as case-sensitive exact strings until confirmed otherwise
  (see QUESTIONS.md item Q1).
- PHI handling: patient names and claim IDs are present in ERA data. The API is internal B2B only.
  TLS in transit is mandatory. Key holders must be on an approved access list.
- The existing FastAPI backend (backend/) is the target service for the new endpoint.
