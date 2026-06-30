# Story 007 — Column-Level Filter Controls

**Epic:** Data Viewing
**Priority:** P2
**Effort:** M (1–2 days)

---

## User Story

As a revenue cycle manager, I want to filter the claims table by payer name, claim status, and service date range so that I can quickly isolate denied claims or payments from a specific payer without scrolling through unrelated rows.

---

## Background

The current search input in `page.jsx` performs a case-insensitive substring match across all fields of every flat row (`Object.values(row).some(...)`). This means searching "denied" returns matches but so does any row where the word appears in an adjustment detail string. There is no way to show only rows where `claim_status === "Denied"`, or to filter to a date range, or to isolate one payer. These are the three most common filtering operations for ERA review in revenue cycle workflows.

The `filteredRows` `useMemo` already provides the correct extension point — additional filter predicates compose naturally.

---

## Acceptance Criteria

**AC-1: Payer dropdown filter**

Given the parsed table is visible,
When the user opens a "Payer" filter dropdown,
Then it shows a list of all distinct `payer_name` values present in the current result set, and selecting one limits the table to rows with that payer name. Selecting "All Payers" removes the filter.

**AC-2: Claim status filter**

Given the parsed table is visible,
When the user opens a "Status" filter dropdown,
Then it shows all distinct `claim_status` values in the data (e.g., "Processed as Primary", "Denied", "Reversal of Previous Payment"), and selecting one limits the table to rows with that status.

**AC-3: Service date range filter**

Given the parsed table is visible,
When the user sets a "From" and "To" date in the date range filter inputs,
Then only rows where `service_date` falls within the inclusive date range are displayed. Rows with a null service_date are excluded when a date filter is active.

**AC-4: Active filters are visually indicated and clearable**

Given one or more filters are active,
When the user views the filter controls,
Then each active filter is highlighted (e.g., a badge or bold label) and a "Clear All Filters" button is visible. Clicking it resets all column filters to their default (show all) state while preserving the text search input.

**AC-5: Filters compose with text search**

Given the user has selected "Denied" as the status filter and typed a patient name in the search box,
When both are active,
Then only rows matching BOTH the status filter AND the text search are displayed.

---

## Implementation Notes

- No backend change required.
- Add state: `filterPayer: string | null`, `filterStatus: string | null`, `filterDateFrom: string | null`, `filterDateTo: string | null`.
- Derive distinct payer and status values from `rows` (not `filteredRows`) to always show the full option list regardless of current filter state.
- Date comparison: parse ISO date strings (`YYYY-MM-DD`) to `Date` objects for range comparison.
- Integrate filter predicates into the existing `filteredRows` `useMemo` by chaining additional `.filter()` calls after the text search filter.
- UI placement: filter controls in a collapsible "Filters" bar between the search input and the table.

---

## Out of Scope

- Server-side filtering (not needed; data is in memory).
- Filtering on adjustment code values (useful but deferred; can be a follow-on story).
- Saving filter presets across sessions.
