from __future__ import annotations

from time import time

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .api_auth import check_rate_limit
from .audit_log import write as audit_write
from .jwt_auth import validate_bearer_token
from .mongo_lookup import find_by_trace_number

router = APIRouter(prefix="/api/era", tags=["ERA Lookup"])


@router.get("/lookup")
async def lookup_era(
    request: Request,
    trace_number: str = Query(..., description="ERA cheque / EFT trace number"),
    client_id: str = Depends(validate_bearer_token),
):
    start = time()
    client_ip = request.client.host if request.client else "unknown"

    check_rate_limit(client_id)

    trace_number = trace_number.strip()
    if not trace_number:
        audit_write(
            client_ip=client_ip,
            client_id=client_id,
            trace_number="",
            status_code=400,
            match_count=0,
            latency_ms=(time() - start) * 1000,
        )
        raise HTTPException(status_code=400, detail="trace_number cannot be blank.")

    if len(trace_number) > 100:
        audit_write(
            client_ip=client_ip,
            client_id=client_id,
            trace_number=trace_number[:20] + "...",
            status_code=400,
            match_count=0,
            latency_ms=(time() - start) * 1000,
        )
        raise HTTPException(status_code=400, detail="trace_number too long (max 100 chars).")

    try:
        results = find_by_trace_number(trace_number)
    except Exception as exc:
        audit_write(
            client_ip=client_ip,
            client_id=client_id,
            trace_number=trace_number,
            status_code=503,
            match_count=0,
            latency_ms=(time() - start) * 1000,
        )
        raise HTTPException(status_code=503, detail="Database temporarily unavailable.") from exc

    latency = (time() - start) * 1000

    if not results:
        audit_write(
            client_ip=client_ip,
            client_id=client_id,
            trace_number=trace_number,
            status_code=404,
            match_count=0,
            latency_ms=latency,
        )
        raise HTTPException(
            status_code=404,
            detail=f"No ERA found for trace number '{trace_number}'.",
        )

    audit_write(
        client_ip=client_ip,
        client_id=client_id,
        trace_number=trace_number,
        status_code=200,
        match_count=len(results),
        latency_ms=latency,
    )

    return {
        "trace_number": trace_number,
        "match_count": len(results),
        "results": results,
    }
