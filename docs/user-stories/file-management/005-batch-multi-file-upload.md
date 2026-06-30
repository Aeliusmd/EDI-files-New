# Story 005 — Batch / Multi-File Upload

**Epic:** File Management
**Priority:** P1
**Effort:** M (1–2 days)

---

## User Story

As a billing coordinator, I want to upload multiple 835 files in a single drag-and-drop action and see their combined claims in one unified table, so that I can review an entire payer remittance run without repeating the upload cycle for each file.

---

## Background

The current frontend accepts `event.dataTransfer.files` but only uses `files[0]`. The backend parses one file per request. A payer remittance run (especially for a clearinghouse-delivered ERA) often arrives as a batch of separate 835 files segmented by payer or date. Users currently must upload, review, download, then upload the next file — losing the previous result each time.

The backend's `parse_835_text()` is stateless and side-effect-free; merging multiple parse results is purely additive work on `flat_rows`, `summary` aggregation, and `transactions` concatenation.

---

## Acceptance Criteria

**AC-1: Drop zone accepts multiple files**

Given the user drags and drops multiple .835 files onto the upload zone simultaneously,
When the files are received by the frontend,
Then all selected filenames are listed below the drop zone (e.g., "3 files selected: file1.835, file2.835, file3.835") and a single "Parse All" button is enabled.

**AC-2: Backend processes all files and merges results**

Given the user clicks "Parse All" with three valid 835 files selected,
When the backend receives the request,
Then it parses each file independently, merges all `transactions` into one list, concatenates all `flat_rows`, recalculates the `summary` totals across all files, and returns a single combined JSON response with a `source_files` array indicating which filename each transaction originated from.

**AC-3: Table identifies source file per row**

Given the combined parse result is displayed in the table,
When the user views the "Converted Output" table,
Then each row includes a "Source File" column showing the originating filename, so claims from different files are distinguishable.

**AC-4: Per-file parse errors do not abort the batch**

Given a batch of three files where the second file is invalid (wrong type or malformed),
When the batch is processed,
Then the response includes successful results from files 1 and 3, a `errors` array entry for file 2 with a descriptive message, and the summary reflects only the successfully parsed files. The frontend displays a banner noting the partial failure.

**AC-5: Exports cover the entire merged result**

Given a batch has been parsed and merged,
When the user downloads CSV or Excel,
Then the export contains all rows from all successfully parsed files, including the "Source File" column.

---

## Implementation Notes

- Frontend: Change `<input type="file">` to `multiple`. Update state from `file: File | null` to `files: File[]`. Update the drop handler to store all dropped files.
- Backend: Add a new endpoint `POST /api/edi/parse/batch` that accepts `files: List[UploadFile]`. Loop, collect results, merge, return. Alternatively, keep the single-file endpoint and merge on the frontend side; the backend merge is preferred for atomicity of the combined summary.
- Add `source_filename` to `flat_rows` items in `build_flat_rows()` — accept it as a parameter.
- The existing `/api/edi/export/{format}` endpoint will need to accept either a pre-parsed JSON body or a list of files for batch export. Simplest approach: accept the merged JSON structure and generate export from it.
- File size guard: reject batch if total size exceeds a configurable limit (e.g., 50 MB combined).

---

## Out of Scope

- Asynchronous / background processing for very large batches (that is a P3 feature).
- Progress indicator per file during upload (nice to have; defer to follow-on).
