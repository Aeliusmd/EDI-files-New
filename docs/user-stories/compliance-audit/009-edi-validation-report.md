# Story 009 — EDI Validation Report

**Epic:** Compliance and Audit
**Priority:** P2
**Effort:** L (3+ days)

---

## User Story

As a healthcare IT team member, I want to see a validation report after parsing an 835 file that lists any structural errors, missing required segments, or data quality issues found in the file, so that I can identify upstream problems in the EDI generation process before the data is used for payment reconciliation.

---

## Background

The current parser operates in a best-effort mode: unrecognized segments are silently skipped (the `for raw in segments` loop has no default case or warning collector), malformed amounts fall back to `0.0` via the `money()` function without noting the failure, and the SE segment count is never validated against the actual segment count parsed. A user uploading a truncated or partially corrupted 835 has no way to know data is missing from their output.

A separate validation pass (distinct from parsing) would identify structural rule violations without preventing the parse from succeeding for valid portions of the file.

---

## Acceptance Criteria

**AC-1: Validation runs automatically after parse and returns a report**

Given a user uploads a 835 file and clicks "View / Parse",
When the backend returns the parsed result,
Then the JSON response also includes a `validation_report` object containing: `is_valid` (boolean), `error_count` (integer), `warning_count` (integer), and `findings` (array of finding objects).

**AC-2: Each finding describes the issue, location, and severity**

Given the validation report contains one or more findings,
When the user views the report,
Then each finding includes: `severity` (ERROR or WARNING), `segment` (the segment tag involved, e.g., "SE"), `description` (plain-English description of the issue), and `recommendation` (suggested corrective action).

**AC-3: SE segment count mismatch is reported as an ERROR**

Given a 835 file where the SE02 element (included segment count) does not match the actual number of segments between ST and SE,
When the file is parsed and validated,
Then the validation report includes a finding with `severity: "ERROR"`, `segment: "SE"`, and a description stating the expected vs. actual segment count.

**AC-4: Unrecognized segments are reported as WARNINGs**

Given a 835 file containing segments with non-standard tags (e.g., vendor extensions),
When the file is parsed and validated,
Then the validation report includes one WARNING per distinct unrecognized segment tag, listing the tag and the count of occurrences skipped.

**AC-5: Validation findings are visible in the UI**

Given the parse result includes a validation report with one or more findings,
When the user views the parsed results,
Then a "Validation" tab or panel is available alongside the table view and JSON view, displaying the findings in a readable list grouped by severity (errors first, then warnings).

**AC-6: Clean files show a passing validation status**

Given a well-formed 835 file with no structural issues,
When the file is parsed and validated,
Then `is_valid` is `true`, `error_count` and `warning_count` are both 0, and the UI displays a green "Passed" indicator on the validation tab.

---

## Implementation Notes

- Add a `validate_835(parsed_result, raw_segments)` function to `parser.py` or a new `validator.py` module.
- Validation rules to implement (minimum viable set):
  1. SE02 segment count matches actual segment count between ST and SE.
  2. Each ST segment has a matching SE segment.
  3. Each GS segment has a matching GE segment.
  4. BPR02 (payment amount) is a valid positive decimal.
  5. CLP04 (billed amount) >= CLP05 (paid amount) — warn if paid > billed.
  6. Unrecognized segment tags not in the known tag list.
  7. ISA usage indicator is "P" (production) or "T" (test) — warn if "T" (test file).
- Return `validation_report` as an additional top-level key in the parse result dict.
- Frontend: add a third tab toggle ("Validation") next to "Readable Table" and "Normalized JSON".

---

## Out of Scope

- Full X12 TR3 implementation guide compliance checking (would require the full ASC X12 835 5010 TR3 spec).
- HIPAA transaction set compliance audit (WEDI/ASC X12 level compliance).
- Automated correction or repair of invalid segments.
