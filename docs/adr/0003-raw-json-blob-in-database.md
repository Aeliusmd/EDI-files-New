# ADR 0003 — Full Parsed JSON Stored as Blob in edi_835_imports

Date: 2026-06-23
Status: Identified — remediation recommended

## Context

`db.py` serialises the entire result dict returned by `parse_835_text` as
a JSON string and stores it in `edi_835_imports.raw_json`. This dict contains
the `flat_rows` list (one entry per service line), the `transactions` tree,
the `summary`, and the `envelope`. For a large 835 file with 500 claims and
five service lines each, this is 2,500 flat rows plus the full transaction
tree — easily 5–20 MB of JSON per import row.

Additionally, `edi_835_claim_rows.row_json` stores the full flat_row dict as
a second JSON blob on every claim row record.

## Decision (as-built)

Both tables store redundant JSON blobs alongside the normalised columns.
The `raw_json` column on the import row duplicates all data that also exists
as individual `EdiClaimRow` records. `row_json` on each claim row duplicates
the normalised scalar columns on the same row.

## Consequences

Positive:
- Full fidelity: a re-export can be produced from the stored blob without
  re-parsing the original file.
- Simple recovery: one blob contains everything.

Negative:
- Storage bloat: for large remittances, `raw_json` will be tens of megabytes
  per row. MySQL's JSON column has a 1 GB limit per cell but performance
  degrades well before that.
- Double storage: every scalar value (claim_id, amounts, dates) is stored
  twice: once in the normalised columns, once inside the blob.
- `row_json` on `EdiClaimRow` adds a third copy of every service-line field.
- The blobs are not queryable in a meaningful way without JSON path
  expressions, which are slow on large documents.
- Float columns (`payment_amount`, `claim_billed_amount`) use the IEEE 754
  `FLOAT` type in the ORM, which introduces rounding errors for financial
  amounts. The DDL correctly uses `DECIMAL(12,2)`. The ORM and the DDL are
  inconsistent in this regard.

## Alternatives Considered

1. Store raw_json as a separate archive (e.g., gzip-compressed file on disk or
   object storage) and reference it by path. Keeps the database lean; retrieval
   requires a second I/O. Preferred for production.

2. Remove raw_json entirely; rely on the normalised rows plus the original file.
   Loses full-fidelity replay but eliminates bloat. Acceptable if the original
   files are retained.

3. Store raw_json only for files below a configurable size threshold. Hybrid
   approach; adds conditional logic.

## Recommended Remediation

For production: remove raw_json from the ORM model. If full-fidelity replay
is required, store the original file bytes in blob/object storage and
re-parse on demand. Fix ORM Float columns for monetary fields to use
SQLAlchemy's `Numeric(precision=12, scale=2)` to match the DDL. Remove
row_json from EdiClaimRow; the normalised columns are sufficient.
