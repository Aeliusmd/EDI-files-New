from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from .auth_router import router as auth_router
from .db import init_db, is_enabled, save_parsed_result
from .era_router import router as era_router
from .mongo_refresh import init_refresh_store
from .parser import parse_835_text

# Make the pipeline package importable regardless of working directory.
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from pipeline import poller  # noqa: E402
from pipeline.mongo_save import (  # noqa: E402
    init_era_collection,
    init_277_collection,
    init_999_collection,
)


_log = logging.getLogger("app.main")


async def _run_poller() -> None:
    try:
        await poller.run()
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        _log.error("Pipeline poller crashed: %s", exc, exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    try:
        init_refresh_store()
    except Exception:
        pass
    try:
        init_era_collection()
    except Exception:
        _log.error("Failed to create era_payments unique index", exc_info=True)
    try:
        init_277_collection()
    except Exception:
        _log.error("Failed to create claim_status_277 unique index", exc_info=True)
    try:
        init_999_collection()
    except Exception:
        _log.error("Failed to create functional_ack_999 unique index", exc_info=True)
    task = asyncio.create_task(_run_poller())
    _log.info("Pipeline poller task created — polling every %ss",
              os.getenv("SFTP_POLL_INTERVAL_SECONDS", "60"))
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    _log.info("Pipeline poller stopped.")


app = FastAPI(title="EDI 835 Converter API", version="1.0.0", lifespan=lifespan)

allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost:7008,http://127.0.0.1:7008").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in allowed_origins if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(era_router)


@app.get("/")
def root():
    return {
        "name": "EDI 835 Converter API",
        "status": "running",
        "mysql_enabled": is_enabled(),
        "endpoints": [
            "POST /api/auth/token",
            "POST /api/auth/refresh",
            "POST /api/edi/parse",
            "POST /api/edi/export/json",
            "POST /api/edi/export/csv",
            "POST /api/edi/export/excel",
            "POST /api/edi/save",
            "GET  /api/era/lookup?trace_number=...  (Bearer access token)",
        ],
    }


def ensure_835_file(file: UploadFile) -> None:
    name = (file.filename or "").lower()
    if not (name.endswith(".835") or name.endswith(".edi") or name.endswith(".txt")):
        raise HTTPException(status_code=400, detail="Please upload a .835, .edi, or .txt EDI file.")


async def read_and_parse(file: UploadFile) -> dict:
    ensure_835_file(file)
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    text = content.decode("utf-8", errors="ignore")
    try:
        return parse_835_text(text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to parse EDI file: {exc}") from exc


@app.post("/api/edi/parse")
async def parse_edi(file: UploadFile = File(...)):
    parsed = await read_and_parse(file)
    return JSONResponse(parsed)


@app.post("/api/edi/save")
async def save_edi(file: UploadFile = File(...)):
    parsed = await read_and_parse(file)
    result = save_parsed_result(file.filename or "uploaded.835", parsed)
    return {"success": bool(result.get("enabled")), "database": result}


@app.post("/api/edi/export/{format_name}")
async def export_edi(format_name: Literal["json", "csv", "excel"], file: UploadFile = File(...)):
    parsed = await read_and_parse(file)
    safe_base = os.path.splitext(os.path.basename(file.filename or "edi_835_output"))[0]

    if format_name == "json":
        payload = json.dumps(parsed, indent=2, ensure_ascii=False).encode("utf-8")
        return StreamingResponse(
            io.BytesIO(payload),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{safe_base}.json"'},
        )

    rows = parsed.get("flat_rows", [])
    df = pd.DataFrame(rows)

    if format_name == "csv":
        csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
        return StreamingResponse(
            io.BytesIO(csv_bytes),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{safe_base}.csv"'},
        )

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary_df = pd.DataFrame([parsed.get("summary", {})])
        envelope_df = pd.DataFrame([parsed.get("envelope", {})])
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
        envelope_df.to_excel(writer, sheet_name="Envelope", index=False)
        df.to_excel(writer, sheet_name="Claim Service Lines", index=False)

        # Auto-size columns for readability.
        for worksheet in writer.book.worksheets:
            for column_cells in worksheet.columns:
                length = max(len(str(cell.value or "")) for cell in column_cells)
                worksheet.column_dimensions[column_cells[0].column_letter].width = min(max(length + 2, 12), 45)

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{safe_base}.xlsx"'},
    )
