# ADR-0007 — Authentication: Static API Key via X-API-Key Header

Date: 2026-06-23
Status: Accepted

---

## Context

The ERA lookup endpoint exposes PHI to an outside team over the network.
The caller is a machine (automated system), not a human browser session.
The team is a known, single counterparty. The existing FastAPI backend has
no authentication infrastructure whatsoever (no middleware, no identity
library, no token store).

The authentication mechanism must:
1. Be implementable with no new infrastructure (no OAuth server, no identity
   provider, no database table for tokens).
2. Prevent unauthorised callers from reading ERA/PHI data.
3. Be simple enough for the outside team to implement in any language in
   under an hour.
4. Support key rotation without restarting the service, or at worst with
   a config-only restart (no code change, no redeploy).

---

## Decision

Use a static pre-shared API key transmitted in the `X-API-Key` HTTP request
header.

**Storage:** One or more valid keys are stored in the `API_KEYS` environment
variable as a comma-separated list of raw key strings (e.g.,
`API_KEYS=key_abc123,key_def456`). The environment variable is set in a
`.env` file on the server (never committed to source control). The `.env.example`
documents the variable name with a placeholder value.

**Validation:** The FastAPI dependency function computes
`hmac.compare_digest(hashlib.sha256(provided.encode()).digest(),
hashlib.sha256(stored.encode()).digest())` for each key in `API_KEYS`. If
any key matches, the request is allowed. Using `hmac.compare_digest` with
SHA-256 digests prevents timing-oracle attacks (an attacker cannot infer
key length or partial correctness from response time).

**Key format recommendation:** Keys should be generated as
`secrets.token_urlsafe(32)` (43 characters of URL-safe base64, 256 bits of
entropy). This format is easy to generate in Python, Go, Node, or any shell.

**Key rotation:** Add the new key to `API_KEYS` (comma-separated) before
revoking the old one. Both keys are valid during the transition window.
Remove the old key from the env var and restart the process to complete
rotation. No database migration required.

---

## Consequences

**Positive:**
- Zero new infrastructure. Implementable in approximately 20 lines of Python.
- The outside team only needs to add one HTTP header — no OAuth handshake,
  no token refresh, no JWT library.
- Key rotation is a config-file edit, not a schema migration or deployment
  pipeline change.
- The comma-separated multi-key list supports overlap-window rotation.

**Negative / accepted trade-offs:**
- Static keys do not expire automatically. The organisation must establish
  an operational key rotation schedule (recommended: every 90 days, or
  immediately on suspected compromise).
- If the server's `.env` file is read by an attacker, all keys are
  compromised. Mitigation: restrict filesystem access to the `.env` file
  (owner read-only, no world read), and consider moving to a secrets manager
  (see "Alternatives" below) as a future improvement.
- There is no per-caller identity — all holders of a valid key are
  indistinguishable at the application layer. If multiple outside teams
  need access in the future, assign each team a different key value from the
  same `API_KEYS` list, but note that the current design cannot attribute a
  request to a specific key without additional logging.
- API keys in HTTP headers are visible in server access logs. Ensure access
  log files are restricted appropriately and that log shipping destinations
  (if any) are treated as sensitive.

---

## Alternatives Rejected

**OAuth 2.0 Client Credentials grant**
Rejected for this phase. Requires an OAuth authorisation server (e.g., Keycloak,
Auth0, or AWS Cognito). The outside team must register a client, implement token
acquisition, handle token expiry, and refresh. This is appropriate for a
multi-tenant production API with many callers, but the overhead is unjustified
for a single external counterparty with a machine-to-machine pattern. Can be
adopted later if the number of external callers grows.

**Mutual TLS (mTLS)**
Rejected. Requires the outside team to generate a client certificate, and
requires TLS termination infrastructure that can perform client certificate
validation. The current deployment has no TLS termination layer at all.
Even after TLS is added (ADR-0006), mTLS adds significant operational
complexity for a single outside team. An API key provides equivalent access
control with far less overhead at this scale.
