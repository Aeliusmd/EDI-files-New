# Story 003 — Table Pagination

**Epic:** Data Viewing
**Priority:** P1
**Effort:** S (< 4 hours)

---

## User Story

As a billing coordinator working with high-volume payer remittances, I want the claim table to paginate results in manageable pages rather than rendering all rows at once, so that the browser remains responsive even when an ERA file contains hundreds of service lines.

---

## Background

The current `page.jsx` renders `filteredRows` in a single unbounded `<table>` with no row limit. An 835 file covering a large provider group or multi-physician practice can produce 500–2000 flat rows (many claims x multiple service lines each). Rendering this many `<tr>` elements causes measurable browser frame-rate drops. The `filteredRows` array is computed via `useMemo` and is already available — pagination is a pure slice operation on top of it.

---

## Acceptance Criteria

**AC-1: Default page size limits visible rows**

Given a parsed 835 file with more than 50 flat rows,
When the table first renders,
Then only the first 50 rows are visible, a row count indicator reads "(showing 1–50 of N rows)", and pagination controls are present below the table.

**AC-2: User can navigate pages**

Given the table is paginated and the user is on page 1,
When the user clicks "Next" or a specific page number button,
Then the table advances to the next page of rows, the row count indicator updates, and the page scrolls to the top of the table section.

**AC-3: Filtering resets to page 1**

Given the user is on page 3 of results,
When the user types a new search term in the filter input,
Then the filtered result set is displayed starting from page 1, preventing the empty-page scenario where the current page index exceeds the filtered page count.

**AC-4: User can change page size**

Given the table is visible,
When the user selects a different page size (25 / 50 / 100) from a dropdown,
Then the table re-renders with the selected number of rows per page, starting from page 1.

---

## Implementation Notes

- No backend change required.
- State needed: `currentPage` (default 1), `pageSize` (default 50).
- Derived value: `pagedRows = filteredRows.slice((currentPage - 1) * pageSize, currentPage * pageSize)`.
- Reset `currentPage` to 1 in the `useEffect` or `useMemo` that watches `search` and `file`.
- Page control component: show first, previous, page numbers (max 5 visible), next, last. Disable previous on page 1, next on last page.
- Page size selector options: 25, 50, 100, 250.

---

## Out of Scope

- Server-side pagination (not needed; data is already fully in memory).
- Virtual scrolling (heavier to implement; pagination achieves the same UX goal with simpler code).
