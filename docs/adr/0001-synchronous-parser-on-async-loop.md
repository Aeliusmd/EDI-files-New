# ADR 0001 — Synchronous X12 Parser Executed on the Async Event Loop

Date: 2026-06-23
Status: Identified — remediation recommended

## Context

The FastAPI application uses Uvicorn's ASGI event loop. All five endpoints
are declared `async def`. The shared helper `read_and_parse` awaits the
file read correctly (`await file.read()`), but immediately calls
`parse_835_text(text)`, which is a synchronous Python function containing
a linear scan of every segment in the EDI file. A typical production 835
file can contain thousands of segments. For large files the parse step may
run for hundreds of milliseconds to several seconds, blocking the event
loop entirely and preventing Uvicorn from processing any other request
during that window.

The same issue applies to `save_parsed_result` in `db.py`, which opens a
SQLAlchemy session and issues synchronous database I/O.

## Decision (as-built)

`parse_835_text` is called directly from async endpoint handlers without
offloading to a thread pool. No `asyncio.run_in_executor` or
`anyio.to_thread.run_sync` call is present. The synchronous SQLAlchemy
engine is also called directly.

## Consequences

Positive:
- Code is simple to read and trace.
- For single-user local use with small files the latency is acceptable.

Negative:
- Any file large enough to take more than ~50 ms to parse will stall all
  concurrent requests. This is a correctness issue under concurrent load,
  not just a performance issue.
- Uvicorn workers cannot serve a second request while parsing is in progress.
- The pattern will need to be changed before the system can handle more than
  one concurrent user.

## Alternatives Considered

1. `asyncio.run_in_executor(None, parse_835_text, text)` — offloads to the
   default ThreadPoolExecutor with zero library changes. Rejected (in original
   design) for simplicity; should be adopted immediately.

2. Replace synchronous SQLAlchemy with `sqlalchemy[asyncio]` + `aiomysql` —
   provides fully non-blocking DB I/O. Higher complexity; appropriate for a
   production system but out of scope for a local tool.

## Recommended Remediation

Wrap both the parse call and the database call with
`await asyncio.get_event_loop().run_in_executor(None, ...)` in the interim.
For production, migrate to the async SQLAlchemy driver.
