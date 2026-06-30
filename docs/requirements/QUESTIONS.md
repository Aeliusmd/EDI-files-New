# Open Questions — ERA Lookup API

**Date opened:** 2026-06-23
**Owner:** Product / BA

Answer these before implementation starts. Each unanswered item is a blocker or a risk.

---

## Q1 — trace_number case sensitivity and format

**Question:** Are trace numbers always uppercase alphanumeric, or can they contain lowercase letters,
leading zeros, or special characters? Should the lookup be case-insensitive?

**Why it matters:** The MongoDB index strategy and the match logic differ depending on the answer.
A case-insensitive collation index is more forgiving for the outside team but slightly slower.

**Default assumed in MVP:** Exact case-sensitive match.

**Needed from:** Outside team + whoever populates `trace_number` in the pipeline.

---

## Q2 — Duplicate trace numbers: expected or data error?

**Question:** In the 7,351 existing documents, do any share the same `trace_number`? If yes, is that
a legitimate scenario (e.g. the same EFT split across two 835 files from different sources) or a
data quality problem to be fixed before the API ships?

**Why it matters:** The 300 multi-match response path only needs to be built if duplicates are a
legitimate business scenario. If they are always a data error, a 409 Conflict or 500 with an alert
is more appropriate.

**Needed from:** Internal pipeline team + data audit of the MongoDB collection.

---

## Q3 — Patient name in response: PHI exposure acceptable?

**Question:** The outside team is billing reconciliation. Do they need patient names in the response,
or is the claim ID sufficient for their matching workflow?

**Why it matters:** Patient name is PHI under HIPAA. Returning it over an API key-authenticated
endpoint (rather than OAuth with user-level scoping) raises the minimum required security controls.
If they do not need it, omit it entirely from v1 to reduce compliance surface.

**Needed from:** Outside team lead + compliance/privacy officer.

---

## Q4 — payee address fields in response

**Question:** The parser stores payer and payee street addresses (address_1, address_2, city, state,
zip). Does the outside team need these, or is name plus NPI/ID sufficient?

**Why it matters:** Addresses are not needed for payment reconciliation in most workflows and
unnecessarily expand the PHI / sensitive data surface.

**Needed from:** Outside team.

---

## Q5 — Rate limit threshold

**Question:** Is 60 requests per minute per API key the right ceiling? What is the outside team's
expected call volume (daily total, peak burst)?

**Why it matters:** Too low a limit causes 429 errors during their batch reconciliation runs.
Too high a limit provides no real protection.

**Needed from:** Outside team (usage estimate).

---

## Q6 — Source field naming

**Question:** The pipeline downloads files from two SFTP sources named "Matrix" and "DMS". Are these
the correct canonical names to expose in the API response `source` field, or should they be mapped
to different names the outside team recognizes?

**Needed from:** Outside team + pipeline team.

---

## Q7 — SLA and support ownership

**Question:** Who owns the API after delivery — the internal pipeline team or a platform team?
What is the agreed response time for incidents (e.g., 4-hour SLA during business hours)?

**Needed from:** Engineering management.
