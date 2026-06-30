from __future__ import annotations

import json
import os

from dotenv import load_dotenv
from typing import Any, Dict

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func

load_dotenv()

MYSQL_URL = os.getenv("MYSQL_URL", "").strip()

Base = declarative_base()
engine = None
SessionLocal = None

if MYSQL_URL:
    engine = create_engine(MYSQL_URL, pool_pre_ping=True, future=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class EdiImport(Base):
    __tablename__ = "edi_835_imports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(100), nullable=False)
    transaction_count = Column(Integer, default=0)
    claim_count = Column(Integer, default=0)
    service_line_count = Column(Integer, default=0)
    total_payment_amount = Column(Float, default=0)
    raw_json = Column(JSON().with_variant(Text, "mysql"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EdiClaimRow(Base):
    __tablename__ = "edi_835_claim_rows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    import_id = Column(Integer, nullable=False, index=True)
    claim_id = Column(String(100), nullable=True, index=True)
    patient_name = Column(String(255), nullable=True)
    payer_name = Column(String(255), nullable=True)
    payee_name = Column(String(255), nullable=True)
    payment_date = Column(String(20), nullable=True)
    payment_amount = Column(Float, default=0)
    claim_billed_amount = Column(Float, default=0)
    claim_paid_amount = Column(Float, default=0)
    procedure_code = Column(String(80), nullable=True)
    service_date = Column(String(20), nullable=True)
    service_paid_amount = Column(Float, default=0)
    adjustment_details = Column(Text, nullable=True)
    row_json = Column(JSON().with_variant(Text, "mysql"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


def is_enabled() -> bool:
    return bool(MYSQL_URL and engine and SessionLocal)


def init_db() -> None:
    if not is_enabled():
        return
    Base.metadata.create_all(bind=engine)


def save_parsed_result(filename: str, parsed: Dict[str, Any]) -> Dict[str, Any]:
    if not is_enabled():
        return {
            "enabled": False,
            "message": "MYSQL_URL is not configured. Add it to backend/.env to enable MySQL saving.",
        }

    init_db()
    session = SessionLocal()
    try:
        summary = parsed.get("summary", {})
        import_row = EdiImport(
            filename=filename,
            file_type=parsed.get("file_type", "X12 835"),
            transaction_count=summary.get("transaction_count", 0),
            claim_count=summary.get("claim_count", 0),
            service_line_count=summary.get("service_line_count", 0),
            total_payment_amount=summary.get("total_payment_amount", 0),
            raw_json=json.dumps(parsed),
        )
        session.add(import_row)
        session.flush()

        for row in parsed.get("flat_rows", []):
            claim_row = EdiClaimRow(
                import_id=import_row.id,
                claim_id=row.get("claim_id"),
                patient_name=row.get("patient_name"),
                payer_name=row.get("payer_name"),
                payee_name=row.get("payee_name"),
                payment_date=row.get("payment_date"),
                payment_amount=row.get("payment_amount") or 0,
                claim_billed_amount=row.get("claim_billed_amount") or 0,
                claim_paid_amount=row.get("claim_paid_amount") or 0,
                procedure_code=row.get("procedure_code"),
                service_date=row.get("service_date"),
                service_paid_amount=row.get("service_paid_amount") or 0,
                adjustment_details=row.get("service_adjustment_details") or row.get("claim_adjustment_details"),
                row_json=json.dumps(row),
            )
            session.add(claim_row)

        session.commit()
        return {"enabled": True, "import_id": import_row.id, "saved_rows": len(parsed.get("flat_rows", []))}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
