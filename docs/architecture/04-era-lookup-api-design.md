# ERA Lookup API — Complete Design Plan

Date: 2026-06-23

This document captures all design decisions for the new external ERA lookup
endpoint. It is the single reference for the implementing developer.

---

## 1. Endpoint Design

| Attribute | Value |
|---|---|
| HTTP Method | GET |
| Path | /api/era/lookup |
| Base URL | http://\<host\>:7007 (plain HTTP internally); https://\<host\> via nginx in production |
| Auth header | X-API-Key: \<key\> |
| Query parameter | trace_number (string, required) |
| Response content type | application/json |

### Request format

```
GET /api/era/lookup?trace_number=1234567890 HTTP/1.1
Host: api.example.internal
X-API-Key: your_api_key_here
Accept: application/json
```

No request body. No other headers required beyond `X-API-Key` and standard
HTTP/1.1 headers.

### Path rationale

`/api/era/lookup` uses:
- `/api/` — consistent with all existing endpoints in this service.
- `/era/` — identifies the resource domain (Electronic Remittance Advice).
  This separates ERA lookup from the existing `/api/edi/` endpoints (which
  are file-processing operations, not stored-record queries).
- `/lookup` — communicates a search operation, consistent with the
  query-parameter approach.

---

## 2. Authentication Approach

### Mechanism

Pre-shared API key in the `X-API-Key` HTTP request header.

See ADR-0007 for the full rationale. Summary:
- The key is stored in the `API_KEYS` environment variable on the server,
  never in source code.
- Multiple keys can be stored as a comma-separated list to support
  overlap-window rotation.
- Validation uses `hmac.compare_digest` on SHA-256 digests to prevent
  timing attacks.

### Key provisioning

1. Generate the key using a cryptographically secure random generator:
   `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
   This produces a 43-character URL-safe string with 256 bits of entropy.
2. Store it in the server's `.env` file: `API_KEYS=your_generated_key`.
3. Communicate the key to the outside team via a secure out-of-band channel
   (encrypted email, 1Password share link, or equivalent). Never transmit
   the key in plain-text email or a chat message.

### Key rotation procedure

1. Generate a new key.
2. Add the new key to `API_KEYS` alongside the old key:
   `API_KEYS=old_key,new_key`.
3. Restart the FastAPI process to pick up the updated env var.
4. Share the new key with the outside team.
5. Once the outside team confirms they have updated their system, remove the
   old key from `API_KEYS` and restart again.

---

## 3. Edge Cases and Error Handling

| Scenario | HTTP Status | Response body |
|---|---|---|
| `trace_number` query param missing or blank | 400 Bad Request | `{"detail": "trace_number query parameter is required and must not be blank."}` |
| `X-API-Key` header absent | 401 Unauthorized | `{"detail": "API key required."}` + `WWW-Authenticate: ApiKey` response header |
| `X-API-Key` header present but incorrect | 401 Unauthorized | `{"detail": "Invalid API key."}` |
| `trace_number` provided, no matching documents | 404 Not Found | `{"detail": "No ERA documents found for trace_number '1234567890'."}` |
| `trace_number` provided, one or more matches | 200 OK | See response schema in section 6 |
| MongoDB unreachable or query fails | 503 Service Unavailable | `{"detail": "Database unavailable. Please try again later."}` |

### Edge case notes

**Multiple matches:** This is an expected condition, not an error. The same
`trace_number` can appear in multiple ERA documents (e.g., the same cheque
processed through both Matrix and DMS source systems, or an ERA file ingested
more than once). The response always returns an array, even for a single match,
so the caller's parsing logic does not need to branch on count.

**Empty trace_number string:** A request like `?trace_number=` or
`?trace_number=%20` (URL-encoded space) must be treated as a bad request
(HTTP 400), not as a database query. Running `find({"trace_number": ""})` or
`find({"trace_number": " "})` would scan for documents with a blank trace
number, which is semantically meaningless and could return unexpected results.
The endpoint handler must strip and validate the value before querying.

**trace_number with special characters:** `trace_number` values in X12 835
files are alphanumeric strings (typically 10-20 digits). The endpoint should
treat the value as an opaque string match — no parsing, no numeric conversion.
Do not cast to int (leading zeros may be significant). Do not apply regex
interpretation. Exact string equality in MongoDB is the correct query.

**Authentication failure — no information leakage:** Both "key absent" and
"key invalid" conditions return HTTP 401. The error message may distinguish
them (as shown in the table above) for developer usability. Do not include
any diagnostic information about why the key was rejected (e.g., "key is too
short", "key not found in list") as this aids key-guessing attacks.

**Oversized response:** A `trace_number` that matches a very large number of
documents (in pathological cases, if the same cheque number appears in hundreds
of ERA files due to a data quality issue) could produce a very large response.
Recommended: apply a server-side limit of 100 results with a `truncated: true`
flag and a `total_match_count` field in the response if the query returns more
than 100 matches. The outside team's use case is point lookups; a limit of 100
is generous and prevents memory exhaustion.

---

## 4. CORS Changes

None required. See ADR-0009 for the full analysis.

The existing `CORS_ORIGINS` environment variable default must be corrected from
`localhost:3000` to `localhost:7008` (this is an existing bug documented in
ADR-0004 and the 00-assessment.md, unrelated to the new endpoint).

The external caller is a server-side system that does not initiate browser
cross-origin requests. The CORS middleware does not need to list external IP
addresses or domains.

If the outside team ever builds a browser-based consumer of this endpoint, the
specific `https://partner.example.com` origin must be added explicitly.
A wildcard `*` origin must never be used for an endpoint that returns PHI.

---

## 5. MongoDB Index Recommendation

See ADR-0010 for full rationale.

**Required index:**

```javascript
db.era_payments.createIndex(
    { "trace_number": 1 },
    { "name": "idx_trace_number", "background": true }
)
```

- Single-field ascending index on the top-level `trace_number` field.
- No unique constraint (duplicate trace numbers are valid).
- Must be created manually on the MongoDB instance before the endpoint is
  put into service. Queries without this index will COLLSCAN the entire
  collection on every request.

**Verify the index is used:**

```javascript
db.era_payments.find({ "trace_number": "1234567890" }).explain("executionStats")
// winningPlan.stage must be "IXSCAN", not "COLLSCAN"
```

---

## 6. Response Schema

### Success response (HTTP 200)

```json
{
  "trace_number": "1234567890",
  "match_count": 2,
  "truncated": false,
  "results": [
    {
      "id": "6676a1b2c3d4e5f6a7b8c9d0",
      "source": "Matrix",
      "source_filename": "MATRIX_ERA_20240315.835",
      "era_index": 1,
      "trace_number": "1234567890",
      "payment_date": "2024-03-15",
      "payment_amount": 4821.50,
      "payment_method": "ACH",
      "payer_name": "BLUE CROSS BLUE SHIELD",
      "payer_id": "00431",
      "payee_name": "AELIUS MEDICAL GROUP",
      "payee_id": "1234567890",
      "claim_count": 3,
      "envelope": {
        "sender_id": "00431",
        "receiver_id": "1234567890",
        "date": "2024-03-15",
        "time": "1200",
        "version": "00501",
        "control_number": "000000001",
        "usage_indicator": "P",
        "functional_group": "HP",
        "application_sender": "00431",
        "application_receiver": "1234567890",
        "group_date": "2024-03-15",
        "group_time": "1200",
        "group_control_number": "1",
        "implementation_version": "005010X221A1"
      },
      "transaction": {
        "transaction_control_number": "0001",
        "payment": {
          "handling_code": "I",
          "amount": 4821.50,
          "credit_debit_flag": "C",
          "method": "ACH",
          "payment_format_code": "CCP",
          "date": "2024-03-15",
          "trace_type_code": "1",
          "trace_number": "1234567890",
          "originating_company_id": "1428654321",
          "reference_id": ""
        },
        "payer": {
          "entity_code": "PR",
          "entity": "Payer",
          "name": "BLUE CROSS BLUE SHIELD",
          "id_qualifier": "XV",
          "id": "00431"
        },
        "payee": {
          "entity_code": "PE",
          "entity": "Payee",
          "name": "AELIUS MEDICAL GROUP",
          "id_qualifier": "XX",
          "id": "1234567890"
        },
        "references": [],
        "dates": [],
        "claims": [
          {
            "claim_id": "CLM12345",
            "status_code": "1",
            "status": "Processed as Primary",
            "billed_amount": 1200.00,
            "paid_amount": 980.00,
            "patient_responsibility_amount": 220.00,
            "claim_filing_indicator_code": "MB",
            "payer_claim_control_number": "PCCN001",
            "patient": {
              "entity_code": "QC",
              "entity": "Patient",
              "name": "SMITH JOHN",
              "id": "INS12345"
            },
            "service_lines": [
              {
                "procedure_code": "99213",
                "billed_amount": 250.00,
                "paid_amount": 185.00,
                "service_date": "2024-03-10",
                "adjustments": [
                  {
                    "group_code": "CO",
                    "group": "Contractual Obligation",
                    "reason_code": "45",
                    "amount": 65.00,
                    "quantity": null
                  }
                ],
                "remarks": []
              }
            ],
            "adjustments": [],
            "references": [],
            "dates": []
          }
        ]
      },
      "flat_rows": [
        {
          "transaction_no": 1,
          "transaction_control_number": "0001",
          "payment_amount": 4821.50,
          "payment_method": "ACH",
          "payment_date": "2024-03-15",
          "trace_number": "1234567890",
          "payer_name": "BLUE CROSS BLUE SHIELD",
          "payer_id": "00431",
          "payee_name": "AELIUS MEDICAL GROUP",
          "payee_id": "1234567890",
          "claim_no": 1,
          "claim_id": "CLM12345",
          "claim_status": "Processed as Primary",
          "patient_name": "SMITH JOHN",
          "procedure_code": "99213",
          "service_date": "2024-03-10",
          "service_billed_amount": 250.00,
          "service_paid_amount": 185.00
        }
      ]
    }
  ]
}
```

### Schema field definitions (top level)

| Field | Type | Description |
|---|---|---|
| `trace_number` | string | The trace_number value that was queried. Echoed back for caller confirmation. |
| `match_count` | integer | Number of ERA documents returned in `results`. |
| `truncated` | boolean | True if more than 100 documents matched and results are capped. |
| `results` | array | Array of ERA document objects. May be empty (but 404 is returned instead of 200 when empty). |

### Schema field definitions (per result object)

| Field | Type | Description |
|---|---|---|
| `id` | string | MongoDB ObjectId serialised as a hex string. |
| `source` | string | "Matrix" or "DMS" — the originating system. |
| `source_filename` | string | Original .835 filename. |
| `era_index` | integer | Position of this ERA transaction within its source file. |
| `trace_number` | string | ERA check/EFT number (same as query parameter). |
| `payment_date` | string | ISO 8601 date (YYYY-MM-DD). |
| `payment_amount` | number | Total ERA payment amount. |
| `payment_method` | string | Payment method code (e.g., "ACH", "CHK"). |
| `payer_name` | string | Payer organisation name. |
| `payer_id` | string | Payer identification number. |
| `payee_name` | string | Payee (provider) organisation name. |
| `payee_id` | string | Payee NPI or identification number. |
| `claim_count` | integer | Number of claims in this ERA transaction. |
| `envelope` | object | ISA/GS file envelope metadata. |
| `transaction` | object | Full parsed ERA transaction: payment, payer, payee, references, dates, claims (with service lines, adjustments, remarks). |
| `flat_rows` | array | Denormalised rows — one entry per service line. Repeats parent payment/claim fields on every row. |

### Not-found response (HTTP 404)

```json
{
  "detail": "No ERA documents found for trace_number '1234567890'."
}
```

### Authentication failure (HTTP 401)

```json
{
  "detail": "API key required."
}
```

or

```json
{
  "detail": "Invalid API key."
}
```

### Bad request (HTTP 400)

```json
{
  "detail": "trace_number query parameter is required and must not be blank."
}
```

### Service unavailable (HTTP 503)

```json
{
  "detail": "Database unavailable. Please try again later."
}
```

---

## 7. Security Concerns for a Healthcare Data API

This section is a condensed checklist. Full analysis is in ADR-0011.

### Blocking concerns (must be resolved before external use)

**TLS required.** The API currently runs on plain HTTP. The `X-API-Key`
header and the PHI response body both travel in cleartext over an unencrypted
channel. An nginx reverse proxy with a valid TLS certificate must be deployed
before the endpoint is reachable by the outside team. Without TLS, the API
key can be captured by any network observer between the caller and the server.

**API key entropy.** Keys must be generated using `secrets.token_urlsafe(32)`
or equivalent (256 bits minimum). Do not use guessable values (UUIDs have
only 122 bits of effective entropy, but are acceptable as a minimum; short
passwords or readable strings are not acceptable).

**Key transmission.** The API key must be shared with the outside team via an
encrypted channel. Never transmit it in plain-text email, Slack, or an
unencrypted chat application.

### Required before production use

**Audit logging.** Every successful and failed lookup must be logged with
timestamp, queried `trace_number`, client IP, HTTP status code, and
`match_count`. Logs must be retained for the HIPAA minimum of 6 years and
restricted to authorised system accounts.

**Rate limiting.** Without rate limiting, a valid API key holder can iterate
over all known trace numbers and harvest the entire `era_payments` collection.
Recommend 60 requests per minute per key, enforced via `slowapi` or nginx
`limit_req_zone`.

### Recommended controls

**IP allowlisting.** If the outside team's egress IP range is stable, restrict
access to the API port at the network or nginx level. This prevents use of a
compromised key from arbitrary IP addresses.

**Response size cap.** Limit results to 100 documents per query with a
`truncated: true` flag to prevent unbounded memory use and accidental bulk
export.

**Periodic key rotation.** Establish a key rotation schedule. Recommended:
every 90 days, or immediately upon any suspected compromise. The multi-key
`API_KEYS` env var supports overlap-window rotation with no downtime.

### PHI handling reminders

- ERA documents contain patient names, claim identifiers, provider identifiers,
  and payment amounts. These are PHI under HIPAA.
- The outside team must be a Covered Entity or a Business Associate under a
  signed BAA before PHI can be shared with them.
- Do not log the response body. The `trace_number` value in the request
  (which is not PHI) may be logged; the claims, patient names, and amounts
  in the response body must not be written to any log file.
- Ensure the MongoDB instance at `10.103.0.201:27017` is not directly
  accessible from outside the internal network. All external access must be
  mediated by the FastAPI API layer, never by direct MongoDB client connections.

---

## ADR Cross-Reference

| Decision | ADR |
|---|---|
| GET with query parameter vs POST with body | ADR-0006 |
| API key authentication mechanism and storage | ADR-0007 |
| MongoDB connection module design | ADR-0008 |
| CORS policy for external access | ADR-0009 |
| MongoDB trace_number index strategy | ADR-0010 |
| Healthcare PHI security control set | ADR-0011 |
