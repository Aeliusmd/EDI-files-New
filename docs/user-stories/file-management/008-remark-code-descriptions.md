# Story 008 — Remark Code Descriptions

**Epic:** File Management / Data Quality
**Priority:** P2
**Effort:** S (< 4 hours)

---

## User Story

As a billing coordinator, I want remark codes in the ERA to display their plain-English description, so that I can understand the reason for a payment decision without consulting an external ANSI X12 Remark Code reference sheet.

---

## Background

The parser captures LQ segments as `{"qualifier": "HE", "code": "M51"}` (or similar). Remark codes are Claim Adjustment Remark Codes (CARCs) and Remittance Advice Remark Codes (RARCs), both published by CMS/ASC X12. The `LQ02` element is the code value; `LQ01` is the qualifier indicating whether it is a RARC ("HE") or a code from another source. Neither the qualifier nor the code is decoded to a description. The `remarks` list per claim and per service line is already populated but unexplained.

This story mirrors Story 001 (CAS reason codes) but for the LQ remark codes. Both are dictionary lookups with the same pattern.

---

## Acceptance Criteria

**AC-1: RARC codes are decoded in parser output**

Given a valid 835 file containing an LQ segment with qualifier `HE` and code `M51`,
When the `/api/edi/parse` endpoint processes the file,
Then the remark object in the response includes a `description` field with the plain-English RARC description for M51 (`"Missing/incomplete/invalid onset of current illness or injury date."`).

**AC-2: Unknown remark codes fall back gracefully**

Given a 835 file containing an LQ remark code not present in the RARC dictionary,
When the file is parsed,
Then the `description` field equals the raw code value (fallback), and parsing completes without error.

**AC-3: Remark descriptions appear in the claim detail drawer**

Given Story 002 (claim detail drawer) is implemented,
When the user opens the detail panel for a claim that has remark codes,
Then each remark entry shows: qualifier label, code, and plain-English description.

---

## Implementation Notes

- Add `REMITTANCE_ADVICE_REMARK_CODES: Dict[str, str]` to `parser.py`. The CMS publishes the RARC list as a downloadable spreadsheet; as of 2025, there are approximately 900 active codes.
- Modify the `LQ` parsing block in `parse_835_text()` to add `"description": REMITTANCE_ADVICE_REMARK_CODES.get(code, code)` to each remark dict.
- The qualifier `HE` indicates a RARC; other qualifiers may reference different code sets. Log or note non-HE qualifiers for future handling.
- This change is fully additive — no existing fields change, no API contract breaks.

---

## Out of Scope

- CAS reason code descriptions (Story 001).
- Qualifier code descriptions other than HE (RARC) — defer to a follow-on story if other qualifiers appear in practice.
