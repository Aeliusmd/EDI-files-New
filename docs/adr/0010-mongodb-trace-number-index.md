# ADR-0010 — MongoDB Index Strategy for trace_number Lookups

Date: 2026-06-23
Status: Accepted

---

## Context

The `era_payments` collection currently has 7,351 documents. The ERA lookup
endpoint will execute `db.era_payments.find({"trace_number": trace_number})`
on every external call. Without an index, MongoDB performs a full collection
scan (COLLSCAN) — every document is read and tested. At 7,351 documents this
is fast today (sub-millisecond for an in-memory collection), but the
collection will grow as new ERA files are ingested.

The `trace_number` field lives in two places in each document:
1. As a top-level field (`document.trace_number`) — this is the denormalised
   fast-path field intended for queries.
2. Nested inside the `transaction` sub-document
   (`document.transaction.payment.trace_number`) — the canonical position
   within the parsed ERA structure.

The index must target the correct field path.

---

## Decision

Create a single-field ascending index on `trace_number` (the top-level field).

```
db.era_payments.createIndex({ "trace_number": 1 }, { "name": "idx_trace_number" })
```

This index is created once, manually, against the live MongoDB instance at
`10.103.0.201:27017`. It is documented here and in the database runbook. No
automated migration is required because the existing pipeline that populates
the collection already writes the top-level `trace_number` field.

The index should also be marked `background: true` (or use the equivalent
`createIndex` default in MongoDB 4.2+, which builds indexes without a
global write lock) so that the collection remains available during index
construction.

A unique constraint is intentionally NOT applied. A `trace_number` may
legitimately appear in more than one document (same cheque number in different
source files, or the same ERA ingested twice from different source systems).
A unique index would block valid inserts and corrupt the lookup semantics
(the endpoint is designed to return all matches).

---

## Consequences

**Positive:**
- COLLSCAN is replaced by IXSCAN. MongoDB's B-tree index on `trace_number`
  reduces lookup cost from O(n) to O(log n + k) where k is the number of
  matching documents. For point lookups (one or two matches), this is
  effectively O(log n).
- The index is small: `trace_number` values are short strings (~10-20
  characters). The index for 7,351 documents will occupy under 1 MB.
- No schema change is required to the collection documents.
- The `find()` query does not change; MongoDB's query planner selects the
  index automatically.

**Negative / accepted trade-offs:**
- Slightly increased write latency for new ingests (index must be updated on
  every insert). At the current ingestion volume (batch file uploads) this is
  negligible.
- The index must be created manually. If the MongoDB instance is rebuilt or
  the collection is dropped and repopulated, the index creation step must be
  re-executed. Document this in the operations runbook.

---

## Index creation command (for operations runbook)

Connect to the MongoDB instance and run in the `edi_835` database:

```javascript
db.era_payments.createIndex(
    { "trace_number": 1 },
    { "name": "idx_trace_number", "background": true }
)
```

Verify the index exists:

```javascript
db.era_payments.getIndexes()
```

Verify the query planner uses the index:

```javascript
db.era_payments.find({ "trace_number": "1234567890" }).explain("executionStats")
```

The `winningPlan.stage` field in the output should show `IXSCAN`, not `COLLSCAN`.

---

## Alternatives Rejected

**Compound index on `{ trace_number: 1, source: 1 }`**
Rejected. The lookup endpoint queries by `trace_number` alone. A compound
index with `source` as the second field would satisfy `trace_number`-only
queries (MongoDB can use a compound index as a prefix index), but the added
complexity is unnecessary. If a future endpoint needs to query by `source`
together with `trace_number`, a compound index can be added at that time.

**Text index on `trace_number`**
Rejected. Text indexes are designed for full-text search with stemming and
stop-word removal. `trace_number` is an exact-match identifier, not a text
field. A text index on it would be wasteful, would not support equality
queries without the `$text` operator (which has different syntax), and would
be case-folded in ways that could produce incorrect matches.
