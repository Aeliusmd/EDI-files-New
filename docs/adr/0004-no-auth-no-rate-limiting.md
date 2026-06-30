# ADR 0004 — No Authentication, No File-Size Limit, No Rate Limiting

Date: 2026-06-23
Status: Identified — critical gap before any multi-user or networked deployment

## Context

All five FastAPI endpoints are publicly accessible to any HTTP client that
can reach port 7007. There is no API key check, no session token, no IP
allow-list, and no rate limiter. The upload size limit is not configured in
FastAPI or Uvicorn; the only guard is file extension validation
(`ensure_835_file`), which can be bypassed by renaming any file to `.txt`.

The CORS middleware allows credentials from the configured origin list, but
CORS is a browser-only mechanism — it provides no server-side enforcement.
Any non-browser client (curl, Python requests, Postman) ignores CORS entirely.

835 files contain Protected Health Information (PHI): patient names, member
IDs, payer claim control numbers, diagnoses in some extended loops, and
financial amounts. Under HIPAA, handling PHI requires administrative,
physical, and technical safeguards.

## Decision (as-built)

No authentication or authorisation layer exists. No file size limit is
enforced. The design assumes single-user local execution where the network
port is not externally reachable.

## Consequences

Positive:
- Zero friction for a local developer tool.
- No credential management overhead.

Negative:
- If the backend port is exposed on a network interface reachable by other
  hosts, any actor can upload files, trigger parsing (CPU cost), and read
  returned PHI.
- An attacker can send arbitrarily large files to exhaust memory or disk
  (no multipart size limit in python-multipart defaults except the
  `max_field_size` which applies to form fields, not file parts).
- Re-parsing on every export request means a large file can be sent
  repeatedly to cause sustained CPU load (denial of service).
- No audit log of what was parsed or exported.

## Alternatives Considered

1. Static API key in environment variable, checked by FastAPI dependency.
   Minimal friction, adequate for a single-operator tool accessed over a
   LAN. Rejected in original design for simplicity.

2. mTLS at the reverse proxy layer (nginx/caddy). Strong but high operational
   overhead for a local tool.

3. OS-level firewall rule binding the port to 127.0.0.1 only. Not a code
   change; must be documented as a deployment requirement.

## Recommended Remediation

For any deployment beyond a developer's own laptop:
1. Bind Uvicorn to `127.0.0.1` only (not `0.0.0.0`).
2. Add a FastAPI dependency that checks a bearer token from an environment
   variable on all non-health endpoints.
3. Add a `max_upload_bytes` guard in `read_and_parse` that rejects files
   over a configurable threshold (e.g., 10 MB) before calling the parser.
4. Correct CORS_ORIGINS default from port 3000 to port 7008 in `.env.example`
   and in `main.py`'s fallback string.
