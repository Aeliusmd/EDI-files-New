from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .parser import detect_separators, edi_date, get, money, parse_nm1

HL_LEVEL_NAMES = {
    "20": "Information source (payer)",
    "21": "Information receiver (submitter)",
    "19": "Provider of service",
    "22": "Subscriber",
    "23": "Dependent",
    "PT": "Patient",
}


def _edi_date_value(value: str) -> Optional[str]:
    """Format CCYYMMDD, or an RD8 range CCYYMMDD-CCYYMMDD."""
    raw = str(value or "").strip()
    if not raw:
        return None
    if "-" in raw:
        left, _, right = raw.partition("-")
        start = edi_date(left)
        end = edi_date(right)
        if start and end and start != end:
            return f"{start}/{end}"
        return start or end or raw
    return edi_date(raw)


def _split_segments(edi_text: str) -> Tuple[List[str], str, str, str]:
    text = str(edi_text or "").replace("\ufeff", "").strip()
    if not text:
        raise ValueError("File is empty.")
    if not text.startswith("ISA"):
        raise ValueError("Invalid X12 EDI file. ISA segment not found.")

    element_sep, segment_term, composite_sep = detect_separators(text)
    segments = [
        seg.strip()
        for seg in text.replace("\r", "").replace("\n", "").split(segment_term)
        if seg.strip()
    ]
    return segments, element_sep, segment_term, composite_sep


def _parse_envelope_from_isa_gs(segments: List[str], element_sep: str) -> Dict[str, Any]:
    envelope: Dict[str, Any] = {}
    for raw in segments:
        e = raw.split(element_sep)
        tag = get(e, 0)
        if tag == "ISA":
            # ISA layout positions match X12 fixed positions, but we're still
            # using the same indices as the existing 835 parser.
            envelope.update(
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
            envelope.update(
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
        if envelope.get("group_control_number") and envelope.get("implementation_version"):
            break
    return envelope


def parse_277_text(edi_text: str) -> Dict[str, Any]:
    """
    Parse HIPAA X12 277 (claim status) into extractable records.

    This is a best-effort extractor focused on fields that match the
    project's older ClearingHouse277 schema:
      - GroupControlNumber, TranDate, PatientAccNo
      - ClaimStatusCatCode, ClaimStatusCode
      - Remarks, Status, Submitter, InsuredId
    """
    segments, element_sep, _segment_term, _composite_sep = _split_segments(edi_text)

    envelope = _parse_envelope_from_isa_gs(segments, element_sep)

    result: Dict[str, Any] = {
        "file_type": "X12 277 Claim Status",
        "envelope": envelope,
        "transactions": [],
        "flat_rows": [],
        "summary": {},
    }

    # Best-effort “current context” extracted from segments.
    # Reset on each ST so a later ST*277 in the same file does not inherit
    # patient/payer IDs from the previous transaction set.
    tran_date: Optional[str] = None  # BHT04 in sample
    submitter_id: str = ""
    payer_name: str = ""
    submitter_name: str = ""
    submitter_entity_id: str = ""
    provider_name: str = ""
    provider_id: str = ""
    insured_member_id: str = ""
    patient_name: str = ""
    patient_acc_no: str = ""
    payer_trace: str = ""
    service_date: Optional[str] = None
    received_date: Optional[str] = None
    process_date: Optional[str] = None
    hl_id: str = ""
    hl_parent_id: str = ""
    hl_level_code: str = ""
    transaction_control_number: str = ""

    records: List[Dict[str, Any]] = []

    for raw in segments:
        e = raw.split(element_sep)
        tag = get(e, 0)

        if tag == "ST":
            # ST*277*<control>*<impl_version>
            transaction_control_number = get(e, 2)
            tran_date = None
            submitter_id = ""
            payer_name = ""
            submitter_name = ""
            submitter_entity_id = ""
            provider_name = ""
            provider_id = ""
            insured_member_id = ""
            patient_name = ""
            patient_acc_no = ""
            payer_trace = ""
            service_date = None
            received_date = None
            process_date = None
            hl_id = ""
            hl_parent_id = ""
            hl_level_code = ""

        elif tag == "BHT":
            # BHT*0085*08*<ref>*<date>*<time>*TH
            tran_date = edi_date(get(e, 4))

        elif tag == "HL":
            hl_id = get(e, 1)
            hl_parent_id = get(e, 2)
            hl_level_code = get(e, 3)

        elif tag == "NM1":
            person = parse_nm1(e)
            code = person["entity_code"]
            if code == "PR":
                payer_name = person.get("name") or ""
                submitter_id = person.get("id") or get(e, -1)
            elif code == "41":
                submitter_name = person.get("name") or ""
                submitter_entity_id = person.get("id") or get(e, -1)
            elif code == "85":
                provider_name = person.get("name") or ""
                provider_id = person.get("id") or get(e, -1)
            elif code == "QC":
                patient_name = person.get("name") or ""
                insured_member_id = person.get("id") or get(e, -1)

        elif tag == "REF":
            # Sample: REF*D9*<patient account number>
            if get(e, 1) == "D9":
                patient_acc_no = get(e, 2)

        elif tag == "TRN":
            if get(e, 1) == "1":
                payer_trace = get(e, 2)
            elif get(e, 1) == "2":
                patient_acc_no = get(e, 2)

        elif tag == "DTP":
            qualifier = get(e, 1)
            date_val = _edi_date_value(get(e, 3) or get(e, 2))
            last = (
                records[-1]
                if records and records[-1].get("transaction_control_number") == transaction_control_number
                else None
            )
            if qualifier == "472":
                service_date = date_val
                if last is not None:
                    last["service_date"] = service_date
            elif qualifier == "050":
                received_date = date_val
                if last is not None:
                    last["received_date"] = received_date
            elif qualifier == "009":
                process_date = date_val
                if last is not None:
                    last["process_date"] = process_date

        elif tag == "STC":
            # Sample: STC*A1:20:AY*20260326*WQ*230
            stc01 = get(e, 1)
            stc_date = edi_date(get(e, 2))
            stc_qual = get(e, 3)  # WQ
            stc_amount_raw = get(e, 4)

            tokens = [t for t in (stc01 or "").split(":") if t]
            claim_status_cat_code = tokens[0] if len(tokens) > 0 else ""
            claim_status_code = tokens[1] if len(tokens) > 1 else ""
            remark_token = tokens[2] if len(tokens) > 2 else ""

            record = {
                "transaction_control_number": transaction_control_number,
                "group_control_number": envelope.get("group_control_number", ""),
                "tran_date": tran_date,
                "patient_acc_no": patient_acc_no,
                "patient_name": patient_name,
                "payer_name": payer_name,
                "submitter_name": submitter_name,
                "submitter_entity_id": submitter_entity_id,
                "provider_name": provider_name,
                "provider_id": provider_id,
                "payer_trace": payer_trace,
                "service_date": service_date,
                "received_date": received_date,
                "process_date": process_date,
                "hl_id": hl_id,
                "hl_parent_id": hl_parent_id,
                "hl_level_code": hl_level_code,
                "hl_level_name": HL_LEVEL_NAMES.get(hl_level_code, hl_level_code),
                "claim_status_cat_code": claim_status_cat_code,
                "claim_status_code": claim_status_code,
                "claim_status_code_full": stc01,
                "remark_token": remark_token,
                "status_date": stc_date,
                "status_qualifier": stc_qual,
                "status_amount": money(stc_amount_raw),
                "status": stc01,
                "remarks": remark_token,
                "submitter_id": submitter_id,
                "insured_id": insured_member_id,
            }
            records.append(record)

        elif tag == "SE":
            # End of this ST*277 transaction set. Continue so later ST*277
            # blocks in the same interchange are still parsed.
            continue

    result["transactions"] = records
    result["flat_rows"] = [
        {
            **r,
            # Convenience columns used when exporting tables:
            "patient_account": r.get("patient_acc_no", ""),
        }
        for r in records
    ]
    result["summary"] = {"record_count": len(records)}
    return result


def parse_999_text(edi_text: str) -> Dict[str, Any]:
    """
    Parse HIPAA X12 999 functional acknowledgment.

    Focus fields (best-effort):
      - group_control_number, group_control_id
      - 837 control numbers acknowledged (AK2)
      - overall + per-item status codes (AK9, IK5)
    """
    segments, element_sep, _segment_term, _composite_sep = _split_segments(edi_text)
    envelope = _parse_envelope_from_isa_gs(segments, element_sep)

    result: Dict[str, Any] = {
        "file_type": "X12 999 Functional Acknowledgment",
        "envelope": envelope,
        "acknowledgments": [],
        "flat_rows": [],
        "summary": {},
    }

    transaction_control_number: str = ""
    ak1_control_id: str = ""
    ak1_functional_id: str = ""
    ak1_implementation_version: str = ""
    overall_status: str = ""
    current_837_control: str = ""
    current_837_function: str = ""
    current_errors: List[Dict[str, Any]] = []
    current_ctx: List[Dict[str, Any]] = []

    ack_entries: List[Dict[str, Any]] = []

    for raw in segments:
        e = raw.split(element_sep)
        tag = get(e, 0)

        if tag == "ST":
            transaction_control_number = get(e, 2)
            ak1_control_id = ""
            ak1_functional_id = ""
            ak1_implementation_version = ""
            overall_status = ""
            current_837_control = ""
            current_837_function = ""
            current_errors = []
            current_ctx = []

        elif tag == "AK1":
            ak1_functional_id = get(e, 1)
            ak1_control_id = get(e, 2)
            ak1_implementation_version = get(e, 3)

        elif tag == "AK2":
            current_837_function = get(e, 1)
            current_837_control = get(e, 2)
            current_errors = []
            current_ctx = []

        elif tag == "IK3":
            current_errors.append(
                {
                    "segment_id": get(e, 1),
                    "segment_position": get(e, 2),
                    "loop_id": get(e, 3),
                    "error_code": get(e, 4),
                    "element_errors": [],
                    "context": [],
                }
            )

        elif tag == "IK4":
            element_error = {
                "element_position": get(e, 1),
                "element_ref": get(e, 2),
                "error_code": get(e, 3),
                "bad_data": get(e, 4),
            }
            if current_errors:
                current_errors[-1]["element_errors"].append(element_error)
            else:
                current_errors.append(
                    {
                        "segment_id": "",
                        "segment_position": "",
                        "loop_id": "",
                        "error_code": "",
                        "element_errors": [element_error],
                        "context": [],
                    }
                )

        elif tag == "CTX":
            ctx = {
                "context_name": get(e, 1),
                "segment_id": get(e, 2),
                "segment_position": get(e, 3),
                "loop_id": get(e, 4),
                "elements": [get(e, i) for i in range(1, len(e)) if get(e, i)],
            }
            if current_errors:
                current_errors[-1].setdefault("context", []).append(ctx)
            else:
                current_ctx.append(ctx)

        elif tag == "IK5":
            status_code = get(e, 1)
            extra_codes = [get(e, i) for i in range(2, 7) if get(e, i)]
            ack_entries.append(
                {
                    "transaction_control_number": transaction_control_number,
                    "group_control_number": envelope.get("group_control_number", ""),
                    "group_control_id": ak1_control_id,
                    "ak1_functional_id": ak1_functional_id,
                    "ak1_implementation_version": ak1_implementation_version,
                    "file_type": current_837_function,
                    "file_837_control_number": current_837_control,
                    "status999": status_code,
                    "status999_error_codes": extra_codes,
                    "errors": list(current_errors),
                    "context": list(current_ctx),
                    "overall_status999": overall_status,
                    "ak9_included_count": "",
                    "ak9_received_count": "",
                    "ak9_accepted_count": "",
                    "ak9_error_codes": [],
                    "patient_no": "",
                }
            )
            current_errors = []
            current_ctx = []

        elif tag == "AK9":
            overall_status = get(e, 1)
            included = get(e, 2)
            received = get(e, 3)
            accepted = get(e, 4)
            ak9_error_codes = [get(e, i) for i in range(5, 10) if get(e, i)]
            for ent in ack_entries:
                if ent.get("transaction_control_number") == transaction_control_number:
                    ent["overall_status999"] = overall_status
                    ent["ak9_included_count"] = included
                    ent["ak9_received_count"] = received
                    ent["ak9_accepted_count"] = accepted
                    ent["ak9_error_codes"] = ak9_error_codes

        elif tag == "SE":
            # End of this ST*999. Continue so later 999 transaction sets
            # in the same file are still parsed.
            continue

    result["acknowledgments"] = ack_entries
    result["flat_rows"] = ack_entries
    result["summary"] = {"ack_count": len(ack_entries)}
    return result

