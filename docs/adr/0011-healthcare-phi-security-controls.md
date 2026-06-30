# ADR-0011 — Security Controls for External PHI Exposure via REST API

Date: 2026-06-23
Status: Accepted

---

## Context

The ERA lookup endpoint returns full ERA documents from MongoDB. These documents
contain Protected Health Information (PHI): patient names, claim identifiers,
provider identifiers, and payment amounts. Exposing PHI over a network API
triggers obligations under HIPAA's Technical Safeguard rules (45 CFR §164.312)
regardless of whether the outside team is also a Covered Entity.

The current system has no TLS, no audit logging, no rate limiting, and no IP
allowlisting. Shipping the lookup endpoint without addressing these gaps would
constitute a HIPAA technical safeguard deficiency.

This ADR documents the minimum viable security control set for the initial
release of the external endpoint, and identifies controls deferred to a future
phase.

---

## Decision

The following controls are required before the endpoint is put into external use.

### Control 1 — TLS in transit (required, blocking)

All external HTTP traffic to the FastAPI service must travel over TLS (HTTPS).
The current deployment exposes plain HTTP on port 7007. A TLS-terminating
reverse proxy (nginx recommended) must be placed in front of port 7007 for
any external access. The FastAPI process itself does not need to terminate TLS.

Implementation: nginx `ssl_certificate` + `ssl_certificate_key` directives
pointing to a valid certificate (Let's Encrypt or an internal CA certificate
for a private network deployment). Port 443 on the host faces externally;
nginx proxies to `127.0.0.1:7007` over plain HTTP on the loopback interface.

Without TLS, the `X-API-Key` header travels in plaintext and can be
intercepted by a network observer. This is not acceptable for a PHI endpoint.

### Control 2 — API key authentication (required, blocking)

Documented in ADR-0007. A pre-shared key in the `X-API-Key` header with
`hmac.compare_digest` validation. Minimum 256 bits of entropy. Required on
every request to the lookup endpoint.

### Control 3 — Access logging with audit trail (required before production use)

Every request to `GET /api/era/lookup` must be logged with:
- Timestamp (UTC)
- `trace_number` value queried (not PHI itself, but the access event)
- HTTP status code returned
- Client IP address
- `match_count` (how many documents were returned)

The FastAPI middleware or a uvicorn access log handler can provide client IP
and status code. The `trace_number` and `match_count` fields require explicit
logging in the endpoint handler (e.g., using Python's `logging` module at
INFO level).

Log files must be restricted to read access by the service account only.
Log retention must meet the HIPAA minimum of 6 years for access records.

### Control 4 — Rate limiting (required before production use)

The endpoint must enforce a request rate limit per API key to prevent:
- Bulk harvesting of ERA documents by iterating over known trace numbers.
- Denial-of-service against the MongoDB instance.

Recommended initial limit: 60 requests per minute per API key.

Implementation options in order of preference:
1. `slowapi` library (wraps `limits`, integrates with FastAPI as middleware).
2. nginx `limit_req_zone` directive (before the request reaches FastAPI).

The rate limit values should be configurable via environment variables
(`RATE_LIMIT_PER_MINUTE`, default 60).

### Control 5 — Response field filtering (deferred, recommended)

The current design returns the full MongoDB document including `flat_rows`
(denormalised service lines) and `envelope` (ISA/GS metadata). The outside
team's stated need is "full ERA details." However, `flat_rows` is a
redundant denormalisation that repeats every service-line field once per row.
Returning it doubles the response payload size without providing new information.

This control is deferred: for the initial release, return the full document
as specified in the requirements. Revisit once the outside team's actual
consumption pattern is understood. If they only use `transaction` and `payment`
fields, a `fields` query parameter can be added to allow callers to request
a projection.

### Control 6 — IP allowlisting (optional, recommended for private deployments)

If the outside team's systems egress from a stable IP range, configure
nginx or a network firewall to allowlist those CIDRs on the API port.
This is a defence-in-depth layer: even if the API key is compromised,
requests from unexpected IP ranges are dropped at the network layer before
reaching the application.

Not required if the outside team's egress IPs are dynamic or unknown.

---

## Consequences

**Positive:**
- TLS + API key + audit log covers the three HIPAA Technical Safeguard
  requirements most directly implicated: transmission security (TLS),
  access control (API key), and audit controls (access log).
- Rate limiting prevents a single compromised key from harvesting the
  entire collection.
- The controls are additive — they do not require changes to the existing
  internal endpoints.

**Negative / accepted trade-offs:**
- TLS requires a certificate and a reverse proxy. This is operational work
  that must be completed before the endpoint is reachable externally.
- Audit logs containing `trace_number` and client IP must themselves be
  secured (restricted file permissions, encrypted log shipping if sent
  off-host). Failure to secure the log is a secondary PHI exposure risk.
- Rate limiting adds a dependency on a new Python library (`slowapi`) or
  nginx configuration. This must be tested to confirm it does not interfere
  with the internal endpoints.

---

## Alternatives Rejected

**No TLS, rely on VPN**
Rejected. If the outside team accesses the endpoint over a shared VPN, TLS
is less critical. However, VPN configurations can change, traffic can be
misrouted, and the HIPAA transmission security standard requires encryption
of PHI in transit regardless of the network path. TLS is the correct solution.

**Application-level encryption of response body (instead of TLS)**
Rejected. Encrypting the JSON response body at the application layer while
transmitting over plain HTTP is a non-standard approach that burdens the
outside team with implementing decryption. TLS provides transport encryption
transparently to both sides and is the industry standard. There is no scenario
where application-level encryption of the body is preferable to TLS.
