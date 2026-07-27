"""Generate backend/app/carc_codes.py from the remark-code workbook.

Reads two tabs of "Remark code updated.xlsx":
  - "Claim Adjustment Reason Code"      -> CLAIM_ADJUSTMENT_REASON_CODES  (297 codes)
  - "Remittance Advice Remark Codes"    -> REMITTANCE_ADVICE_REMARK_CODES (~1140 codes)

Run this ONCE, and again only if "Remark code updated.xlsx" changes. The mapping
is otherwise static, so the pipeline reads the generated Python module at runtime
instead of parsing the spreadsheet on every startup.

Some RARC codes (M26, N125, N355, N887) span multiple spreadsheet rows — the
description is split into paragraphs, one row per paragraph, all carrying the
same code. Those rows are joined into a single description string.

Usage:
    python scripts/generate_carc_codes.py
"""

from __future__ import annotations

from pathlib import Path

import openpyxl

REPO_ROOT = Path(__file__).resolve().parent.parent
XLSX_PATH = REPO_ROOT / "Remark code updated.xlsx"
CARC_SHEET = "Claim Adjustment Reason Code"
RARC_SHEET = "Remittance Advice Remark Codes"
OUTPUT_PATH = REPO_ROOT / "backend" / "app" / "carc_codes.py"


def normalize_code(raw: object) -> str:
    """Codes are a mix of ints (1, 2, 3) and strings (P1, A0, N202). ERA data
    always uses strings, so coerce every code to a stripped string for lookup
    parity."""
    return str(raw).strip()


def read_mapping(wb: openpyxl.Workbook, sheet_name: str) -> dict[str, str]:
    """Read a Code/Description sheet into a dict.

    Rows sharing the same code are treated as one description split across
    multiple rows; their texts are joined with a single space, in row order.
    """
    ws = wb[sheet_name]
    mapping: dict[str, str] = {}
    for code, description in ws.iter_rows(min_row=2, values_only=True):
        if code is None:
            continue
        key = normalize_code(code)
        if not key or key.lower() == "code":
            continue
        text = str(description).strip() if description is not None else ""
        if key in mapping and text:
            mapping[key] = f"{mapping[key]} {text}" if mapping[key] else text
        else:
            mapping[key] = text
    return mapping


def write_module(carc: dict[str, str], rarc: dict[str, str]) -> None:
    lines = [
        '"""AUTO-GENERATED from "Remark code updated.xlsx" by',
        'scripts/generate_carc_codes.py. Do not edit by hand — re-run the generator',
        'if the workbook changes.',
        "",
        "Tabs:",
        '  "Claim Adjustment Reason Code"   -> CLAIM_ADJUSTMENT_REASON_CODES',
        '  "Remittance Advice Remark Codes" -> REMITTANCE_ADVICE_REMARK_CODES',
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "CLAIM_ADJUSTMENT_REASON_CODES: dict[str, str] = {",
    ]
    for code, description in carc.items():
        lines.append(f"    {code!r}: {description!r},")
    lines.append("}")
    lines.append("")
    lines.append("REMITTANCE_ADVICE_REMARK_CODES: dict[str, str] = {")
    for code, description in rarc.items():
        lines.append(f"    {code!r}: {description!r},")
    lines.append("}")
    lines.append("")

    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    wb = openpyxl.load_workbook(XLSX_PATH, read_only=True, data_only=True)
    carc = read_mapping(wb, CARC_SHEET)
    rarc = read_mapping(wb, RARC_SHEET)
    wb.close()
    write_module(carc, rarc)
    print(
        f"Wrote {len(carc)} CARC codes and {len(rarc)} RARC codes "
        f"to {OUTPUT_PATH.relative_to(REPO_ROOT)}"
    )


if __name__ == "__main__":
    main()
