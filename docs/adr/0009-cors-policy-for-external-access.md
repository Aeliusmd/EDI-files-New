# ADR-0009 — CORS Policy for External Access

Date: 2026-06-23
Status: Accepted

---

## Context

The current CORS policy allows only `localhost:7008` and `127.0.0.1:7008`.
This is correct for the browser-based internal frontend.

The new external caller is a machine-to-machine system (not a browser). It
will send requests from a server process, not from a browser's JavaScript
fetch/XMLHttpRequest context. CORS is a browser security mechanism — it is
enforced by browsers, not by server-to-server callers. A Python script, a Go
service, or a curl command does not send CORS preflight (`OPTIONS`) requests
and is not restricted by the `Access-Control-Allow-Origin` response header.

The design question is therefore: should the CORS policy be widened at all,
and if so, to what value?

---

## Decision

Do not widen the existing CORS policy. The `CORS_ORIGINS` environment variable
remains set to `http://localhost:7008,http://127.0.0.1:7008` (correcting the
existing bug where the default was `localhost:3000`).

The external caller (a server-side system) is not subject to CORS restrictions
and will not be blocked by the current policy. No CORS change is needed to
support machine-to-machine access.

If in the future a browser-based external caller is required, the specific
origin of that caller should be added to `CORS_ORIGINS` explicitly (e.g.,
`https://partner.example.com`). The value `*` (wildcard) must never be used
for an endpoint that accepts an authentication header and returns PHI.

---

## Consequences

**Positive:**
- The CORS surface area stays minimal. Only the internal frontend origin is
  permitted for cross-origin browser requests.
- The wildcard `*` is never introduced, which would allow any browser-based
  script on any domain to attempt authenticated calls using a stolen API key.
- No CORS change is required to ship the external lookup endpoint — the only
  change is the API key dependency injection.

**Negative / accepted trade-offs:**
- If the outside team's system is ever called from a browser (e.g., a web
  app embedded in their UI), this CORS policy will block those calls. The
  resolution at that point is to add the specific origin, not to open the
  policy to all origins.

---

## Important clarification on CORS vs. authentication

CORS and API key authentication are independent security controls:
- CORS prevents unauthorised browser-origin reads (same-origin policy enforcement).
- API key prevents unauthorised server-origin reads (authentication).

Both controls must be in place for their respective threats. The absence of a
broad CORS policy does not reduce the need for API key authentication, and the
presence of API key authentication does not reduce the value of a narrow CORS
policy.

---

## Alternatives Rejected

**Open CORS to all origins (`allow_origins=["*"]`)**
Rejected. When `allow_origins=["*"]` is combined with
`allow_credentials=True`, CORS specifications forbid the browser from honouring
the response (browsers enforce this at the protocol level). More importantly,
a wildcard CORS origin means any web page on any domain can trigger a
cross-origin GET to the lookup endpoint — the API key in the `X-API-Key`
header would still protect the data, but the attack surface is unnecessarily
expanded. Minimal origin lists are the correct posture for healthcare APIs.

**Add a separate CORS policy for the lookup endpoint with `allow_origins=["*"]`
and `allow_credentials=False`**
Rejected. The lookup endpoint returns PHI. Even without credentials, allowing
any browser origin to initiate authenticated API key requests increases the
risk that a stolen key can be exploited from a browser context. Tight CORS
is a defence-in-depth layer, not a primary control, but it has value.
