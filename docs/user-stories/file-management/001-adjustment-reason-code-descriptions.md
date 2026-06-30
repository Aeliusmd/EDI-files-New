# Story 001 — Adjustment Reason Code Descriptions

**Epic:** File Management / Data Quality
**Priority:** P1
**Effort:** S (< 4 hours)

---

## User Story

As a billing coordinator, I want each CAS adjustment reason code to display its plain-English description alongside the code, so that I can immediately understand why a claim was adjusted without cross-referencing the ANSI X12 CARC lookup table manually.

---

## Background

The parser (`parser.py`) already decodes the CAS adjustment group code (CO, CR, OA, PI, PR) via `ADJUSTMENT_GROUP_CODES` but does not decode the numeric reason code (e.g., 45, 97, 4, 96, 50). The `reason_code` field in each adjustment dict is a bare string. The frontend's "Service Adjustments" column therefore shows values like `CO:45 $150.00` with no description.

The fix is adding a CARC dictionary to `parser.py` and populating a `reason_description` field in `parse_cas()`. No API contract changes are needed — the field is additive to the existing adjustment object.

---

## Acceptance Criteria

**AC-1: Reason codes are decoded in parser output**

Given a valid 835 file containing a CAS segment with reason code `45`,
When the `/api/edi/parse` endpoint processes the file,
Then the adjustment object in the response must include a `reason_description` field with the value `"Charges exceed your contracted/legislated fee arrangement"` (or the approved ANSI description for that code).

**AC-2: Unknown codes do not break parsing**

Given a 835 file containing a CAS reason code not present in the CARC dictionary (e.g., a future or payer-proprietary code),
When the file is parsed,
Then the `reason_description` field must be populated with the raw code value (fallback equals the code itself), and parsing must complete without error.

**AC-3: Descriptions appear in all export formats**

Given a file has been parsed and reason code descriptions are present in the JSON,
When the user downloads the CSV or Excel export,
Then the exported file must include a `reason_description` column in the flat rows, populated with the plain-English description for each adjustment row that has a reason code.

---

## Implementation Notes

- Source: ASC X12 Claim Adjustment Reason Code (CARC) list, published at wpc-edi.com / ASC X12 website. As of X12 v5010, there are approximately 250 active codes.
- Add `CLAIM_ADJUSTMENT_REASON_CODES: Dict[str, str]` constant to `parser.py`.
- Modify `parse_cas()` to set `"reason_description": CLAIM_ADJUSTMENT_REASON_CODES.get(reason_code, reason_code)`.
- The `build_flat_rows()` function flattens adjustment details via `adjustment_summary()` — consider also appending the description to the `details` string for readability in CSV/Excel.

---

## Out of Scope

- Remark codes (LQ segment) are handled in Story 008.
- Group code descriptions already exist; no change needed there.
