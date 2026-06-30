# Story 011 — AI-Assisted Denial Pattern Analyzer (Moonshot)

**Epic:** Analytics / Intelligence
**Priority:** P3 (Moonshot)
**Effort:** L (1–2 weeks, requires LLM API integration)

---

## User Story

As a revenue cycle manager, I want the application to automatically analyze denial patterns across one or more parsed 835 files and provide plain-English explanations of why claims are being denied and what corrective actions to take, so that I can proactively fix billing errors and recover denied revenue without requiring a dedicated denial management specialist.

---

## Background

The parser already captures all the data needed for denial analysis:
- CAS adjustments with group codes (CO, PR) and reason codes (4, 45, 96, 97, etc.) per claim and per service line
- CLP02 claim status code (4 = Denied)
- Procedure codes (SVC segment) and payer identity (N1 PR segment)

Today, this data is shown as raw codes with descriptions (after Story 001). The next-level insight — "these 12 denials of CPT 93000 by Payer X are all CO-97, suggesting you need modifier 59" — requires pattern detection and domain reasoning that goes beyond a lookup table. An LLM with healthcare billing context can perform this reasoning against the structured JSON output the parser already produces.

This is a differentiating feature. Most standalone ERA converters are passive file translators. A denial intelligence layer would make this tool a revenue recovery asset.

---

## Acceptance Criteria

**AC-1: Denial summary is extracted from parsed data**

Given a parsed 835 result with one or more claims having status "Denied" or CAS adjustments with CO or PR group codes,
When the user clicks "Analyze Denials",
Then the backend extracts the denial subset from the parsed JSON (denied claims, adjustment codes, procedure codes, payer names) and sends it to the LLM analysis endpoint.

**AC-2: LLM returns a structured denial pattern report**

Given the denial data is sent to the LLM,
When the analysis completes,
Then the response includes: a list of identified denial patterns (each with: pattern name, frequency count, affected procedure codes, payer name, root cause explanation in plain English), and for each pattern a list of recommended corrective actions.

**AC-3: Report is displayed in a readable, actionable format**

Given the LLM denial analysis has returned results,
When the user views the "Denial Analysis" panel,
Then patterns are shown in descending frequency order. Each pattern card shows: denial reason in plain English, affected claim count and dollar amount at risk, and a numbered list of recommended actions (e.g., "1. Verify modifier 25 is appended when billing 99213 with a procedure on the same date").

**AC-4: Analysis is scoped to avoid sending PHI to external APIs**

Given HIPAA considerations apply to patient data,
When the denial data is assembled for LLM analysis,
Then patient names, patient IDs, and subscriber IDs are stripped or replaced with anonymized tokens before the payload is sent to any external LLM API. Payer names, procedure codes, adjustment codes, and dollar amounts are included as they are not PHI.

**AC-5: Report is downloadable**

Given the denial analysis report is displayed,
When the user clicks "Download Denial Report",
Then a formatted Excel or PDF document is generated containing the pattern table and recommendations, suitable for sharing with a practice manager or billing team.

---

## Implementation Notes

- New backend endpoint: `POST /api/edi/analyze/denials`. Accepts the parsed JSON (or a subset) as the request body.
- Pre-processing step: aggregate denial patterns from `flat_rows` — group by (`payer_name`, `procedure_code`, `claim_adjustment_codes`) and count. This structured summary (not raw EDI) is what gets sent to the LLM.
- LLM integration: use the Anthropic Claude API (claude-sonnet-4-x or similar). Send the aggregated pattern summary as a structured prompt with a system prompt defining the healthcare billing expert persona and output format (JSON schema for structured response parsing).
- PHI stripping: remove `patient_name`, `patient_id` fields before sending. Confirm with legal/compliance that payer names and procedure codes alone are not PHI in this context.
- Cost control: implement a token budget check before sending. Cap input at 100K tokens. If the denial dataset is larger, sample the top N patterns by frequency.
- The feature should be clearly labeled as "AI-assisted suggestions — verify before acting" to avoid over-reliance.
- Requires `ANTHROPIC_API_KEY` environment variable (backend `.env`).
- Frontend: add an "Analyze Denials" button that is enabled only when the parsed data contains at least one denied claim.

---

## Out of Scope

- Real-time denial prevention (requires 837 claim integration).
- Automatic claim resubmission.
- Training a custom model (use general-purpose LLM with domain-specific prompting).
- Guaranteed correctness of recommendations — this is a decision support tool, not a billing compliance authority.
