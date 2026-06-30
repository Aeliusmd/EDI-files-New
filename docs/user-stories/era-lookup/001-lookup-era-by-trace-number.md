# Story 001 — Look Up ERA Payment by Trace Number

**Epic:** ERA Lookup API
**Status:** Ready for development
**Priority:** Must-have (MVP v1)

---

## User Story

As a billing reconciliation analyst on the outside team,
I want to query the ERA Lookup API with a trace number (ERA cheque number),
so that I can retrieve the full payment and claim details for that remittance
without manually accessing the internal EDI pipeline or MongoDB.

---

## Background

The outside team receives trace numbers from their bank or payment processor. They need to reconcile
those numbers against the parsed ERA data that the internal pipeline stores in MongoDB. Currently
this requires requesting a manual data extract, which creates delays and human error. A lookup API
removes that dependency.

A `trace_number` maps to the TRN02 segment in an X12 835 file. It is stored at the transaction
level in MongoDB, one value per ERA document. In the parsed data it lives at
`payment.trace_number` on each transaction object.

---

## Acceptance Criteria

### AC-1 — Happy path: single match

Given the caller provides a valid `X-API-Key` header and a `trace_number` that exists in exactly
one MongoDB ERA document,
When they send `GET /api/v1/era/{trace_number}`,
Then the response is HTTP 200 with a JSON body containing:
- `trace_number` (string)
- `payment_date` (ISO 8601 date string, e.g. "2024-03-15")
- `payment_amount` (number, two decimal places)
- `payment_method` (string: "CHK" or "EFT")
- `payer` object with `name` and `id`
- `payee` object with `name` and `id`
- `claim_count` (integer, count of claims in this ERA)
- `claims` array — each claim contains:
  - `claim_id`
  - `status` (human-readable, e.g. "Processed as Primary")
  - `billed_amount`
  - `paid_amount`
  - `patient_responsibility_amount`
  - `adjustments` array (group_code, reason_code, amount)
  - `service_lines` array (procedure_code, service_date, billed_amount, paid_amount, units, adjustments)
- `source` object with `name` ("Matrix" or "DMS") and `filename` (original .835 filename)

### AC-2 — Not found

Given the caller provides a valid `X-API-Key` and a `trace_number` that does not exist in MongoDB,
When they send `GET /api/v1/era/{trace_number}`,
Then the response is HTTP 404 with body:
```json
{
  "error": "not_found",
  "message": "No ERA document found for trace number '<value>'."
}
```

### AC-3 — Multiple matches

Given the caller provides a valid `X-API-Key` and a `trace_number` that matches more than one
MongoDB document,
When they send `GET /api/v1/era/{trace_number}`,
Then the response is HTTP 300 with body:
```json
{
  "error": "multiple_matches",
  "message": "2 ERA documents share this trace number. Use the document_id parameter to select one.",
  "matches": [
    {
      "document_id": "<mongo_object_id>",
      "payment_date": "2024-03-15",
      "payment_amount": 1234.56,
      "source": { "name": "Matrix", "filename": "ERA_20240315.835" }
    }
  ]
}
```
The caller can then re-request with `GET /api/v1/era/{trace_number}?document_id=<id>` to retrieve
the specific document.

### AC-4 — Missing or invalid API key

Given the caller omits the `X-API-Key` header or provides a key that is not recognized,
When they send any request to the API,
Then the response is HTTP 401 with body:
```json
{
  "error": "unauthorized",
  "message": "A valid X-API-Key header is required."
}
```

### AC-5 — Rate limit exceeded

Given a caller sends more than 60 requests within any 60-second window using the same API key,
When they send the next request,
Then the response is HTTP 429 with a `Retry-After` header indicating when they may retry, and body:
```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit of 60 requests per minute exceeded."
}
```

### AC-6 — Fields excluded from response

Given any valid request,
When the server builds the response,
Then the following fields are NOT present anywhere in the response body:
- Internal MongoDB `_id` (except when explicitly disambiguating multi-match via `document_id`)
- `payer.address_1`, `payer.address_2`, `payer.city`, `payer.state`, `payer.zip`
- `payee.address_1`, `payee.address_2`, `payee.city`, `payee.state`, `payee.zip`
- `payer.contact` (phone/fax details)
- `patient.id` (patient member ID — see QUESTIONS.md Q3 regarding patient name)
- Raw EDI text or any `flat_rows` / `separators` / `envelope` internals
- `originating_company_id` and `reference_id` from the TRN segment

### AC-7 — Audit log entry written

Given any request to the endpoint (authenticated or not),
When the request completes,
Then a log entry is written containing: timestamp, caller IP, API key identifier (not the key value),
trace number queried, HTTP status returned, and response latency in milliseconds.

---

## Request Specification

```
GET /api/v1/era/{trace_number}
```

**Path parameter:**
- `trace_number` (required) — the ERA cheque or EFT number, URL-encoded if it contains special
  characters. Exact match. Case-sensitive (pending Q1 resolution).

**Query parameter (optional):**
- `document_id` — MongoDB ObjectId string. Only used to resolve a multi-match 300 response.

**Required header:**
- `X-API-Key: <key>` — opaque string issued by the ops team.

**No request body.**

---

## Response Specification (HTTP 200)

All monetary amounts are numbers (not strings), rounded to two decimal places.
All dates are ISO 8601 strings ("YYYY-MM-DD"). Absent optional fields are omitted (not null).

```
{
  "trace_number": string,
  "payment_date": string (YYYY-MM-DD),
  "payment_amount": number,
  "payment_method": string ("CHK" | "EFT"),
  "payer": {
    "name": string,
    "id":   string
  },
  "payee": {
    "name": string,
    "id":   string
  },
  "claim_count": integer,
  "claims": [
    {
      "claim_id":                    string,
      "status":                      string,
      "billed_amount":               number,
      "paid_amount":                 number,
      "patient_responsibility_amount": number,
      "patient_name":                string (see Q3),
      "adjustments": [
        {
          "group_code":   string,
          "group":        string,
          "reason_code":  string,
          "amount":       number
        }
      ],
      "service_lines": [
        {
          "procedure_code": string,
          "service_date":   string (YYYY-MM-DD) or absent,
          "billed_amount":  number,
          "paid_amount":    number,
          "units":          string or absent,
          "adjustments": [
            {
              "group_code":  string,
              "group":       string,
              "reason_code": string,
              "amount":      number
            }
          ]
        }
      ]
    }
  ],
  "source": {
    "name":     string ("Matrix" | "DMS"),
    "filename": string
  }
}
```

---

## Definition of Done

- Endpoint is deployed and reachable over HTTPS.
- All 7 acceptance criteria pass in a staging environment against real MongoDB data.
- At least one trace number known to the outside team is tested end-to-end by them.
- A MongoDB index on `trace_number` is confirmed in place (query must not perform a full collection scan).
- API key for the outside team has been issued and confirmed working.
- Audit log output has been reviewed by at least one engineer.
- QUESTIONS.md items Q1 and Q3 have been resolved before marking AC-1 and AC-6 complete.

---

## Out-of-Scope for This Story

- Authentication mechanism changes (OAuth, OIDC)
- Bulk lookup
- Any write operations
