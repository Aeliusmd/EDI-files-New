# ADR 0005 — ORM Model and DDL Schema Are Divergent

Date: 2026-06-23
Status: Identified — remediation recommended

## Context

The project ships two independent schema definitions:

1. `backend/mysql_schema.sql` — hand-authored DDL with `BIGINT UNSIGNED`
   primary keys, `DECIMAL(12,2)` monetary columns, and a declared
   `FOREIGN KEY` constraint from `edi_835_claim_rows.import_id` to
   `edi_835_imports.id` with `ON DELETE CASCADE`.

2. `backend/app/db.py` — SQLAlchemy ORM models with `Integer` primary keys,
   `Float` monetary columns, and `import_id` declared only as
   `Column(Integer, nullable=False, index=True)` — no `ForeignKey()`
   constructor argument.

At runtime, `init_db()` calls `Base.metadata.create_all(bind=engine)`, which
uses the ORM definition to create tables. If the database is created via the
ORM rather than the DDL script, the resulting schema will:
- Use `INT` (signed 32-bit) instead of `BIGINT UNSIGNED` for all PKs.
- Use `FLOAT` instead of `DECIMAL(12,2)` for all monetary amounts.
- Omit the foreign key constraint entirely.

There is no migration tooling (Alembic or equivalent). Schema changes require
dropping and recreating tables or hand-editing the database.

## Decision (as-built)

The DDL file is provided for reference and manual execution. The ORM model
is used at runtime for table creation. No mechanism enforces consistency
between them. No migration history exists.

## Consequences

Positive:
- DDL file provides clear documentation of intended schema.
- ORM model allows the app to start without a pre-existing database.

Negative:
- A developer who creates the database using the DDL file and then runs the
  app will have a schema mismatch if the ORM ever tries to alter tables.
- Financial amounts stored as IEEE 754 FLOAT lose precision for values with
  more than seven significant digits. A claim paid amount of $1,234,567.89
  will be rounded. Healthcare remittances regularly contain amounts in this
  range.
- The missing FK in the ORM means `ON DELETE CASCADE` will not be enforced
  when the ORM manages the schema, leaving orphaned `edi_835_claim_rows`
  if an import row is deleted.
- No migration path exists for future schema changes.

## Alternatives Considered

1. Adopt Alembic for migration management. ORM models become the single source
   of truth; DDL is generated and versioned. Rejected in original design for
   simplicity. Strongly recommended for any non-throwaway deployment.

2. Remove ORM-based table creation (`create_all`); require operators to run
   `mysql_schema.sql` manually before first use. Keeps ORM models lean;
   removes the divergence risk. Simpler than Alembic for a local tool.

3. Annotate the ORM model with explicit `server_default` and type overrides
   to match the DDL. Partial fix; does not address the FK gap without
   adding `ForeignKey('edi_835_imports.id')` to the `import_id` column
   definition.

## Recommended Remediation

Short term: add `ForeignKey('edi_835_imports.id')` to `EdiClaimRow.import_id`
and change all monetary `Float` columns to
`Numeric(precision=12, scale=2, asdecimal=True)` in the ORM model. This
closes the schema gap without introducing migration tooling.

Longer term: introduce Alembic with an initial migration generated from the
corrected ORM models. Delete `mysql_schema.sql` to eliminate the dual-source
problem.
