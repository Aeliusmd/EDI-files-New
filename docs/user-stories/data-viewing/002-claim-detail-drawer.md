# Story 002 — Claim Detail Drawer

**Epic:** Data Viewing
**Priority:** P1
**Effort:** M (1–2 days)

---

## User Story

As a revenue cycle manager, I want to click on any claim row in the table and see a full detail panel with all associated service lines, adjustments, dates, references, patient, subscriber, and rendering provider, so that I can review a complete claim picture without exporting and opening a separate file.

---

## Background

The parser already captures rich per-claim data: `patient`, `subscriber`, `rendering_provider`, `references` (REF segments), `dates` (DTM segments), `adjustments` (CAS), `service_lines` (SVC), and `remarks` (LQ). None of this data except procedure code, service date, and flat adjustment summary appears in the current UI table. The `parsed` state object held in React memory contains the full `transactions[].claims[]` tree — it simply has no UI surface.

The flat table rows include `claim_id` and `transaction_no` which are sufficient keys to look up the matching claim object in `parsed.transactions`.

---

## Acceptance Criteria

**AC-1: Row click opens the detail panel**

Given the parsed results table is visible with at least one claim row,
When the user clicks anywhere on a table row,
Then a side drawer or modal panel opens showing the full claim detail for that claim, including: patient name and ID, subscriber name and ID, rendering provider name and NPI, payer claim control number, claim filing indicator, facility type, all service lines with their individual adjustments and remark codes, all claim-level dates, and all claim-level references.

**AC-2: Panel is dismissible and does not lose table state**

Given the claim detail panel is open,
When the user presses Escape or clicks a close button,
Then the panel closes and the table remains in its current scroll position, filter state, and page position.

**AC-3: Service line adjustments in the panel decode reason codes**

Given Story 001 (reason code descriptions) is implemented,
When the claim detail panel displays a service line's adjustments,
Then each adjustment row shows group code label, reason code, reason description, and dollar amount — not raw code strings alone.

---

## Implementation Notes

- Frontend-only change. The detail data is already available in the `parsed` state object.
- Use a lookup: given a row's `transaction_no` (1-indexed) and `claim_id`, find `parsed.transactions[transaction_no - 1].claims.find(c => c.claim_id === claim_id)`.
- Recommend a right-side slide-over drawer (CSS `position: fixed; right: 0`) over a modal to keep the table visible for context.
- No backend endpoint change required.
- Consider adding a `rendering_provider` column or tooltip to the main table as a related enhancement.

---

## Out of Scope

- Editing claim data in the panel.
- Navigating between claims from within the panel (previous/next buttons). That can be a follow-on story.
