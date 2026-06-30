from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

CLAIM_STATUS_CODES = {
    "1": "Processed as Primary",
    "2": "Processed as Secondary",
    "3": "Processed as Tertiary",
    "4": "Denied",
    "19": "Processed as Primary, Forwarded",
    "20": "Processed as Secondary, Forwarded",
    "21": "Processed as Tertiary, Forwarded",
    "22": "Reversal of Previous Payment",
    "23": "Not Our Claim, Forwarded",
    "25": "Predetermination Pricing Only",
}

ADJUSTMENT_GROUP_CODES = {
    "CO": "Contractual Obligation",
    "CR": "Correction/Reversal",
    "OA": "Other Adjustment",
    "PI": "Payer Initiated Reduction",
    "PR": "Patient Responsibility",
}

ENTITY_CODES = {
    "PR": "Payer",
    "PE": "Payee",
    "QC": "Patient",
    "IL": "Subscriber",
    "82": "Rendering Provider",
    "TT": "Transfer To",
    "GB": "Other Insured",
}

DATE_QUALIFIERS = {
    "405": "Production Date",
    "472": "Service Date",
    "050": "Received Date",
    "232": "Claim Statement Period Start",
    "233": "Claim Statement Period End",
    "036": "Expiration Date",
}

REF_QUALIFIERS = {
    "EV": "Receiver Identification",
    "2U": "Payer Identification Number",
    "EO": "Submitter Identification Number",
    "6R": "Provider Control Number",
    "F8": "Original Reference Number",
    "1L": "Group or Policy Number",
    "TJ": "Federal Taxpayer ID",
    "PQ": "Payee ID",
}


def clean(value: Any) -> str:
    return str(value or "").strip()


def money(value: Any) -> float:
    value = clean(value)
    if not value:
        return 0.0
    try:
        return float(Decimal(value))
    except (InvalidOperation, ValueError):
        return 0.0


def edi_date(value: Any) -> Optional[str]:
    value = clean(value)
    if not value:
        return None
    if len(value) == 8 and value.isdigit():
        return f"{value[0:4]}-{value[4:6]}-{value[6:8]}"
    if len(value) == 6 and value.isdigit():
        return f"20{value[0:2]}-{value[2:4]}-{value[4:6]}"
    return value


def get(e: List[str], index: int, default: str = "") -> str:
    return clean(e[index]) if index < len(e) else default


def split_composite(value: str, composite_sep: str) -> List[str]:
    value = clean(value)
    if not value:
        return []
    return value.split(composite_sep)


def detect_separators(text: str) -> Tuple[str, str, str]:
    """Return element separator, segment terminator, composite separator."""
    if len(text) < 4 or not text.startswith("ISA"):
        return "*", "~", ":"

    element_sep = text[3]
    # ISA is fixed length. Character at position 105 is segment terminator if present.
    segment_terminator = "~"
    if len(text) > 105 and text.startswith("ISA"):
        maybe_term = text[105]
        if maybe_term and maybe_term not in "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz":
            segment_terminator = maybe_term
    elif "~" in text:
        segment_terminator = "~"
    elif "\n" in text:
        segment_terminator = "\n"

    isa_segment = text.split(segment_terminator, 1)[0]
    parts = isa_segment.split(element_sep)
    composite_sep = parts[-1][-1] if parts and parts[-1] else ":"
    return element_sep, segment_terminator, composite_sep


def parse_nm1(e: List[str]) -> Dict[str, Any]:
    entity_code = get(e, 1)
    entity_type = get(e, 2)
    last_or_org = get(e, 3)
    first = get(e, 4)
    middle = get(e, 5)
    suffix = get(e, 7)

    if entity_type == "2":
        name = last_or_org
    else:
        name = " ".join([part for part in [first, middle, last_or_org, suffix] if part])

    return {
        "entity_code": entity_code,
        "entity": ENTITY_CODES.get(entity_code, entity_code),
        "entity_type": entity_type,
        "name": name,
        "last_or_organization_name": last_or_org,
        "first_name": first,
        "middle_name": middle,
        "id_qualifier": get(e, 8),
        "id": get(e, 9),
    }


def parse_cas(e: List[str]) -> List[Dict[str, Any]]:
    group_code = get(e, 1)
    adjustments: List[Dict[str, Any]] = []
    i = 2
    while i < len(e):
        reason_code = get(e, i)
        if reason_code:
            adjustments.append(
                {
                    "group_code": group_code,
                    "group": ADJUSTMENT_GROUP_CODES.get(group_code, group_code),
                    "reason_code": reason_code,
                    "amount": money(get(e, i + 1)),
                    "quantity": get(e, i + 2) or None,
                }
            )
        i += 3
    return adjustments


def adjustment_summary(adjustments: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not adjustments:
        return {"codes": "", "amount": 0.0, "details": ""}
    codes = []
    amount = 0.0
    details = []
    for adj in adjustments:
        code = f"{adj.get('group_code','')}:{adj.get('reason_code','')}"
        codes.append(code)
        amount += float(adj.get("amount") or 0)
        details.append(f"{code} ${float(adj.get('amount') or 0):.2f}")
    return {"codes": ", ".join(codes), "amount": round(amount, 2), "details": "; ".join(details)}


def new_transaction(control_number: str) -> Dict[str, Any]:
    return {
        "transaction_control_number": control_number,
        "payment": {},
        "payer": {},
        "payee": {},
        "references": [],
        "dates": [],
        "claims": [],
    }


def new_claim(e: List[str]) -> Dict[str, Any]:
    status_code = get(e, 2)
    return {
        "claim_id": get(e, 1),
        "status_code": status_code,
        "status": CLAIM_STATUS_CODES.get(status_code, status_code),
        "billed_amount": money(get(e, 3)),
        "paid_amount": money(get(e, 4)),
        "patient_responsibility_amount": money(get(e, 5)),
        "claim_filing_indicator_code": get(e, 6),
        "payer_claim_control_number": get(e, 7),
        "facility_type_code": get(e, 8),
        "claim_frequency_code": get(e, 9),
        "patient": {},
        "subscriber": {},
        "rendering_provider": {},
        "references": [],
        "dates": [],
        "adjustments": [],
        "service_lines": [],
        "remarks": [],
    }


def new_service_line(e: List[str], composite_sep: str) -> Dict[str, Any]:
    svc_code = get(e, 1)
    parts = split_composite(svc_code, composite_sep)
    return {
        "service_code_raw": svc_code,
        "product_service_qualifier": parts[0] if len(parts) > 0 else None,
        "procedure_code": parts[1] if len(parts) > 1 else svc_code,
        "modifiers": parts[2:] if len(parts) > 2 else [],
        "billed_amount": money(get(e, 2)),
        "paid_amount": money(get(e, 3)),
        "revenue_code": get(e, 4) or None,
        "units": get(e, 5) or None,
        "service_date": None,
        "references": [],
        "adjustments": [],
        "remarks": [],
    }


def parse_835_text(edi_text: str) -> Dict[str, Any]:
    text = str(edi_text or "").replace("\ufeff", "").strip()
    if not text:
        raise ValueError("File is empty.")
    if not text.startswith("ISA"):
        raise ValueError("Invalid X12 EDI file. ISA segment not found.")

    element_sep, segment_term, composite_sep = detect_separators(text)
    segments = [seg.strip() for seg in text.replace("\r", "").replace("\n", "").split(segment_term) if seg.strip()]

    result: Dict[str, Any] = {
        "file_type": "X12 835 Electronic Remittance Advice (ERA)",
        "separators": {
            "element": element_sep,
            "segment": segment_term,
            "composite": composite_sep,
        },
        "envelope": {},
        "summary": {},
        "transactions": [],
        "flat_rows": [],
    }

    tx: Optional[Dict[str, Any]] = None
    current_claim: Optional[Dict[str, Any]] = None
    current_service: Optional[Dict[str, Any]] = None
    current_party: Optional[str] = None

    for raw in segments:
        e = raw.split(element_sep)
        tag = get(e, 0)

        if tag == "ISA":
            result["envelope"].update(
                {
                    "sender_id": get(e, 6),
                    "receiver_id": get(e, 8),
                    "date": edi_date(get(e, 9)),
                    "time": get(e, 10),
                    "version": get(e, 12),
                    "control_number": get(e, 13),
                    "usage_indicator": get(e, 15),
                }
            )
        elif tag == "GS":
            result["envelope"].update(
                {
                    "functional_group": get(e, 1),
                    "application_sender": get(e, 2),
                    "application_receiver": get(e, 3),
                    "group_date": edi_date(get(e, 4)),
                    "group_time": get(e, 5),
                    "group_control_number": get(e, 6),
                    "implementation_version": get(e, 8),
                }
            )
        elif tag == "ST":
            tx = new_transaction(get(e, 2))
            result["transactions"].append(tx)
            current_claim = None
            current_service = None
            current_party = None
        elif tag == "SE":
            tx = None
            current_claim = None
            current_service = None
            current_party = None
        elif not tx:
            continue
        elif tag == "BPR":
            tx["payment"] = {
                "handling_code": get(e, 1),
                "amount": money(get(e, 2)),
                "credit_debit_flag": get(e, 3),
                "method": get(e, 4),
                "payment_format_code": get(e, 5),
                "date": edi_date(get(e, 16)),
            }
        elif tag == "TRN":
            tx["payment"].update(
                {
                    "trace_type_code": get(e, 1),
                    "trace_number": get(e, 2),
                    "originating_company_id": get(e, 3),
                    "reference_id": get(e, 4),
                }
            )
        elif tag == "N1":
            current_party = get(e, 1)
            party = {
                "entity_code": current_party,
                "entity": ENTITY_CODES.get(current_party, current_party),
                "name": get(e, 2),
                "id_qualifier": get(e, 3),
                "id": get(e, 4),
            }
            if current_party == "PR":
                tx["payer"] = party
            elif current_party == "PE":
                tx["payee"] = party
        elif tag == "N3":
            target = tx["payer"] if current_party == "PR" else tx["payee"] if current_party == "PE" else None
            if target is not None:
                target["address_1"] = get(e, 1)
                target["address_2"] = get(e, 2)
        elif tag == "N4":
            target = tx["payer"] if current_party == "PR" else tx["payee"] if current_party == "PE" else None
            if target is not None:
                target.update({"city": get(e, 1), "state": get(e, 2), "zip": get(e, 3)})
        elif tag == "PER":
            target = tx["payer"] if current_party == "PR" else tx["payee"] if current_party == "PE" else None
            if target is not None:
                target["contact"] = {
                    "function_code": get(e, 1),
                    "name": get(e, 2),
                    "communication_qualifier": get(e, 3),
                    "communication_number": get(e, 4),
                }
        elif tag == "REF":
            ref = {
                "qualifier": get(e, 1),
                "qualifier_name": REF_QUALIFIERS.get(get(e, 1), get(e, 1)),
                "value": get(e, 2),
            }
            if current_service is not None:
                current_service["references"].append(ref)
            elif current_claim is not None:
                current_claim["references"].append(ref)
            else:
                tx["references"].append(ref)
        elif tag == "DTM":
            date_item = {
                "qualifier": get(e, 1),
                "qualifier_name": DATE_QUALIFIERS.get(get(e, 1), get(e, 1)),
                "date": edi_date(get(e, 2)),
            }
            if current_service is not None and get(e, 1) == "472":
                current_service["service_date"] = date_item["date"]
            elif current_claim is not None:
                current_claim["dates"].append(date_item)
            else:
                tx["dates"].append(date_item)
        elif tag == "CLP":
            current_claim = new_claim(e)
            tx["claims"].append(current_claim)
            current_service = None
        elif tag == "NM1" and current_claim is not None:
            person = parse_nm1(e)
            code = person["entity_code"]
            if code == "QC":
                current_claim["patient"] = person
            elif code == "IL":
                current_claim["subscriber"] = person
            elif code == "82":
                current_claim["rendering_provider"] = person
            else:
                current_claim.setdefault("other_entities", []).append(person)
        elif tag == "SVC" and current_claim is not None:
            current_service = new_service_line(e, composite_sep)
            current_claim["service_lines"].append(current_service)
        elif tag == "CAS":
            cas_items = parse_cas(e)
            if current_service is not None:
                current_service["adjustments"].extend(cas_items)
            elif current_claim is not None:
                current_claim["adjustments"].extend(cas_items)
        elif tag == "AMT":
            amount_item = {"qualifier": get(e, 1), "amount": money(get(e, 2))}
            if current_service is not None:
                current_service.setdefault("amounts", []).append(amount_item)
            elif current_claim is not None:
                current_claim.setdefault("amounts", []).append(amount_item)
            else:
                tx.setdefault("amounts", []).append(amount_item)
        elif tag == "QTY":
            qty_item = {"qualifier": get(e, 1), "quantity": get(e, 2)}
            if current_service is not None:
                current_service.setdefault("quantities", []).append(qty_item)
            elif current_claim is not None:
                current_claim.setdefault("quantities", []).append(qty_item)
        elif tag == "LQ":
            remark = {"qualifier": get(e, 1), "code": get(e, 2)}
            if current_service is not None:
                current_service["remarks"].append(remark)
            elif current_claim is not None:
                current_claim["remarks"].append(remark)

    result["flat_rows"] = build_flat_rows(result)
    result["summary"] = build_summary(result)
    return result


def build_summary(result: Dict[str, Any]) -> Dict[str, Any]:
    transactions = result.get("transactions", [])
    claims = [claim for tx in transactions for claim in tx.get("claims", [])]
    service_lines = [svc for claim in claims for svc in claim.get("service_lines", [])]
    total_payment = round(sum(float(tx.get("payment", {}).get("amount") or 0) for tx in transactions), 2)
    total_billed = round(sum(float(claim.get("billed_amount") or 0) for claim in claims), 2)
    total_paid = round(sum(float(claim.get("paid_amount") or 0) for claim in claims), 2)
    total_patient_resp = round(sum(float(claim.get("patient_responsibility_amount") or 0) for claim in claims), 2)
    total_adjustments = 0.0
    for claim in claims:
        total_adjustments += sum(float(adj.get("amount") or 0) for adj in claim.get("adjustments", []))
        for svc in claim.get("service_lines", []):
            total_adjustments += sum(float(adj.get("amount") or 0) for adj in svc.get("adjustments", []))

    return {
        "transaction_count": len(transactions),
        "claim_count": len(claims),
        "service_line_count": len(service_lines),
        "total_payment_amount": total_payment,
        "total_claim_billed_amount": total_billed,
        "total_claim_paid_amount": total_paid,
        "total_patient_responsibility_amount": total_patient_resp,
        "total_adjustment_amount": round(total_adjustments, 2),
    }


def build_flat_rows(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for tx_index, tx in enumerate(result.get("transactions", []), start=1):
        payment = tx.get("payment", {})
        payer = tx.get("payer", {})
        payee = tx.get("payee", {})
        claims = tx.get("claims", [])
        for claim_index, claim in enumerate(claims, start=1):
            patient = claim.get("patient", {}) or claim.get("subscriber", {}) or {}
            claim_adj = adjustment_summary(claim.get("adjustments", []))
            base = {
                "transaction_no": tx_index,
                "transaction_control_number": tx.get("transaction_control_number"),
                "payment_amount": payment.get("amount"),
                "payment_method": payment.get("method"),
                "payment_date": payment.get("date"),
                "trace_number": payment.get("trace_number"),
                "payer_name": payer.get("name"),
                "payer_id": payer.get("id"),
                "payee_name": payee.get("name"),
                "payee_id": payee.get("id"),
                "claim_no": claim_index,
                "claim_id": claim.get("claim_id"),
                "claim_status_code": claim.get("status_code"),
                "claim_status": claim.get("status"),
                "payer_claim_control_number": claim.get("payer_claim_control_number"),
                "patient_name": patient.get("name"),
                "patient_id": patient.get("id"),
                "claim_billed_amount": claim.get("billed_amount"),
                "claim_paid_amount": claim.get("paid_amount"),
                "patient_responsibility_amount": claim.get("patient_responsibility_amount"),
                "claim_adjustment_codes": claim_adj["codes"],
                "claim_adjustment_amount": claim_adj["amount"],
                "claim_adjustment_details": claim_adj["details"],
            }

            service_lines = claim.get("service_lines", [])
            if not service_lines:
                row = dict(base)
                row.update(
                    {
                        "service_line_no": None,
                        "service_date": None,
                        "procedure_code": None,
                        "service_billed_amount": None,
                        "service_paid_amount": None,
                        "service_units": None,
                        "service_adjustment_codes": "",
                        "service_adjustment_amount": 0.0,
                        "service_adjustment_details": "",
                    }
                )
                rows.append(row)
                continue

            for svc_index, svc in enumerate(service_lines, start=1):
                svc_adj = adjustment_summary(svc.get("adjustments", []))
                row = dict(base)
                row.update(
                    {
                        "service_line_no": svc_index,
                        "service_date": svc.get("service_date"),
                        "procedure_code": svc.get("procedure_code"),
                        "service_code_raw": svc.get("service_code_raw"),
                        "service_billed_amount": svc.get("billed_amount"),
                        "service_paid_amount": svc.get("paid_amount"),
                        "service_units": svc.get("units"),
                        "service_adjustment_codes": svc_adj["codes"],
                        "service_adjustment_amount": svc_adj["amount"],
                        "service_adjustment_details": svc_adj["details"],
                    }
                )
                rows.append(row)
    return rows


def parse_835_file(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return parse_835_text(f.read())
