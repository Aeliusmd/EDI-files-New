# C4 Level 1 — System Context

## Purpose

The EDI 835 Converter accepts X12 835 Electronic Remittance Advice (ERA) files
from a human operator, transforms them into human-readable and machine-readable
forms, persists the results to MongoDB, and exposes a REST API for both internal
and external consumers.

A new external access channel is being added: an outside team may query full ERA
details by `trace_number` (cheque / EFT number) using a pre-shared API key.

## Diagram

```mermaid
C4Context
    title System Context — EDI 835 Converter + ERA Lookup API

    Person(internalUser, "Medical Billing Operator",
        "Practice staff. Uploads .835 files, views parsed results, downloads exports.")

    Person_Ext(externalCaller, "External Team (machine-to-machine)",
        "Outside organisation. Queries ERA payment details by trace_number using a pre-shared API key.")

    System_Boundary(sys, "EDI 835 System") {
        System(api, "EDI 835 Converter API",
            "FastAPI service on port 7007. Parses X12 835 files, serves internal UI, and exposes the authenticated ERA Lookup endpoint for external callers.")
    }

    SystemDb(mongo, "MongoDB — edi_835 / era_payments",
        "Stores all ingested ERA transactions. 7,351+ documents. Hosted at 10.103.0.201:27017.")

    System_Ext(sourceEdi, "Source EDI Systems (Matrix / DMS)",
        "Upstream payer systems. Produce .835 remittance files consumed by billing staff.")

    Rel(internalUser, api, "Uploads .835 files, views results, downloads exports", "HTTPS / browser — localhost:7008 frontend")
    Rel(externalCaller, api, "GET /api/era/lookup?trace_number=... with X-API-Key header", "HTTPS / REST")
    Rel(api, mongo, "Reads and writes ERA transactions", "TCP / pymongo driver — 10.103.0.201:27017")
    Rel(sourceEdi, internalUser, "Provides .835 files", "SFTP / manual download")
```

## Actors and External Systems

| Actor / System | Type | Role |
|---|---|---|
| Medical Billing Operator | Internal person | Uploads ERA files, views table / JSON output, downloads exports. Uses browser on localhost:7008. |
| External Team Caller | External system (machine) | Automated consumer. Sends `trace_number`, expects full ERA document(s) in return. Authenticates via `X-API-Key` header. |
| MongoDB `era_payments` | Internal data store | Persistent store of all ingested ERA transactions. The source of truth for the lookup endpoint. |
| Source EDI Systems (Matrix / DMS) | External system | Originate the .835 files. Not directly connected to this API. |

## Key Context Constraints

- The external caller is machine-to-machine — no browser, no OAuth flow. A pre-shared static API key (`X-API-Key` header) is the authentication mechanism.
- MongoDB is on an internal network address (`10.103.0.201`). It must not be exposed publicly; all access is mediated by the FastAPI backend.
- ERA documents contain PHI (patient names, claim details, provider identifiers). Any external exposure requires authentication and transport encryption.
- The existing CORS policy restricts cross-origin browser access to `localhost:7008`. The new external endpoint must not widen the CORS policy for browser callers beyond what is required.
- A single `trace_number` may match more than one ERA document (same cheque number appearing in different source files or different `era_index` positions). The response must return all matches.
