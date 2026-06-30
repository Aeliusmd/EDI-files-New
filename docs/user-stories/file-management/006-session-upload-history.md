# Story 006 — Session Upload History

**Epic:** File Management
**Priority:** P2
**Effort:** M (1–2 days)

---

## User Story

As a billing coordinator, I want to see a list of all 835 files I have parsed during my current browser session and switch between their results without re-uploading, so that I can compare payment information across multiple ERAs without losing my work.

---

## Background

The React state currently holds a single `parsed` object and a single `file` reference. Navigating away or selecting a new file overwrites the previous result permanently. Users who need to process multiple files in a working session must keep them all open and upload each one fresh when they want to reference it again.

Session history does not require backend persistence — browser `sessionStorage` or an in-memory React state array is sufficient. The parsed JSON for a typical 835 file is 50–500 KB, easily held in browser memory for a session.

---

## Acceptance Criteria

**AC-1: Each parsed file is added to a session history list**

Given the user has successfully parsed a file,
When the parse completes,
Then a "Recent Files" sidebar or collapsible panel shows an entry for that file with: filename, parse timestamp, claim count, and total payment amount from the summary.

**AC-2: Clicking a history entry restores that file's results**

Given the session history panel shows two previously parsed files,
When the user clicks the entry for the first file,
Then the main table, summary cards, and raw JSON view update to show that file's results without re-uploading or re-parsing.

**AC-3: History is bounded to prevent memory exhaustion**

Given the user parses more than 20 files in a single session,
When the 21st file is parsed,
Then the oldest entry is automatically removed from the session history list and its parsed data is released from memory, keeping the history at a maximum of 20 entries.

**AC-4: Session history does not persist across browser tab closure**

Given the user closes the browser tab and reopens the application,
When the page loads,
Then the session history is empty (not restored from localStorage or any persistent store).

---

## Implementation Notes

- Replace `const [parsed, setParsed] = useState(null)` with a history array: `const [history, setHistory] = useState([])` and `const [activeIndex, setActiveIndex] = useState(null)`.
- Each history entry: `{ id: uuid, filename, parsedAt: Date, summary, parsed }`.
- Use `sessionStorage` only if tab-refresh persistence within the session is desired (optional).
- History panel: collapsible left sidebar or a horizontal file-tab strip above the table.
- Cap at 20 entries; FIFO eviction.
- Do not persist to localStorage (AC-4).

---

## Out of Scope

- Cross-session persistence (that requires the MySQL save feature + a history UI, which is P3).
- Sharing history entries between browser tabs.
