"""Generate a field/process guide PDF for 277 and 999 ingestion."""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT = Path(__file__).resolve().parents[1] / "docs" / "EDI_277_and_999_Field_Guide.pdf"


def styles():
    s = getSampleStyleSheet()
    s.add(
        ParagraphStyle(
            "CoverTitle",
            parent=s["Title"],
            fontSize=22,
            leading=26,
            spaceAfter=8,
            textColor=colors.HexColor("#0f3d5e"),
        )
    )
    s.add(
        ParagraphStyle(
            "Section",
            parent=s["Heading1"],
            fontSize=16,
            textColor=colors.HexColor("#0f3d5e"),
            spaceBefore=14,
            spaceAfter=8,
        )
    )
    s.add(
        ParagraphStyle(
            "Sub",
            parent=s["Heading2"],
            fontSize=12,
            textColor=colors.HexColor("#1a5f8a"),
            spaceBefore=10,
            spaceAfter=6,
        )
    )
    s.add(
        ParagraphStyle(
            "Body2",
            parent=s["BodyText"],
            fontSize=10,
            leading=14,
            spaceAfter=6,
        )
    )
    s.add(
        ParagraphStyle(
            "Cell",
            parent=s["BodyText"],
            fontSize=8.5,
            leading=11,
        )
    )
    s.add(
        ParagraphStyle(
            "FooterNote",
            parent=s["BodyText"],
            fontSize=8,
            textColor=colors.HexColor("#555555"),
        )
    )
    return s


def table(s, rows, col_widths):
    data = []
    for i, row in enumerate(rows):
        if i == 0:
            data.append([Paragraph(f"<b>{c}</b>", s["Cell"]) for c in row])
        else:
            data.append([Paragraph(str(c), s["Cell"]) for c in row])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3d5e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f4f8fb")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f4f8fb"), colors.white]),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c5d4df")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def bullets(items, s):
    return ListFlowable(
        [ListItem(Paragraph(i, s["Body2"]), leftIndent=8) for i in items],
        bulletType="bullet",
        start="circle",
        leftIndent=16,
    )


def build():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    s = styles()
    story = []

    story.append(Paragraph("EDI 277 and 999 Extraction Guide", s["CoverTitle"]))
    story.append(Paragraph("Field list, parser, libraries, process, and MongoDB save location", s["Body2"]))
    story.append(Paragraph("Project: EDI 835 Converter &mdash; 277/999 extension (existing 835 flow unchanged)", s["FooterNote"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("1. Overview", s["Section"]))
    story.append(
        Paragraph(
            "This project already processed HIPAA X12 <b>835</b> Electronic Remittance Advice (ERA) files. "
            "277 and 999 support was added as a <b>separate path</b>: same SFTP folder, different parsers, "
            "and <b>new MongoDB collections</b>. The 835 parser, 835 Mongo collection, billing lookup, "
            "and 835 UI/API were not changed.",
            s["Body2"],
        )
    )

    story.append(Paragraph("2. Parser used", s["Section"]))
    story.append(
        Paragraph(
            "A <b>custom in-project Python parser</b> is used, not a third-party 277/999 transaction mapper.",
            s["Body2"],
        )
    )
    story.append(
        table(s, 
            [
                ["Item", "Value"],
                ["Parser module", "backend/app/parser_277_999.py"],
                ["277 function", "parse_277_text()"],
                ["999 function", "parse_999_text()"],
                ["Shared helpers", "backend/app/parser.py (separator detection, element get, date, money)"],
                ["Approach", "Segment-walking X12 extractor (same style as the existing 835 parser)"],
                ["Why not a full IG library", "pyx12 is the best public HIPAA X12 library, but 277/999 maps vary by version and it is heavier for this extract-and-store use case. A custom parser matches the current 835 design and avoids changing 835 behavior."],
            ],
            [1.6 * inch, 5.4 * inch],
        )
    )

    story.append(Paragraph("3. Libraries used", s["Section"]))
    story.append(Paragraph("Runtime libraries involved in 277/999 processing:", s["Body2"]))
    story.append(
        table(s, 
            [
                ["Library", "Role"],
                ["Python standard library", "Split ISA/GS/ST segments, walk tags, build dictionaries"],
                ["python-dotenv", "Load backend/.env (SFTP + Mongo settings)"],
                ["paramiko", "SFTP connect, list, and download .277 / .999 files"],
                ["pymongo", "Insert parsed records into MongoDB collections"],
                ["Existing app.parser helpers", "detect_separators, get, edi_date, money, clean"],
            ],
            [2.1 * inch, 4.9 * inch],
        )
    )
    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            "Libraries <b>not</b> used for extraction: pyx12, py835, pandas (pandas is only used by the 835 export API).",
            s["Body2"],
        )
    )

    story.append(Paragraph("4. Process (end to end)", s["Section"]))
    story.append(Paragraph("Source of files (not local by default)", s["Sub"]))
    story.append(
        Paragraph(
            "Automatic ingestion reads from SFTP: host <b>Secure.edidrop.com</b>, remote folder "
            "<b>/837P/OUT/</b>, accounts Matrix and DMS. Files are downloaded to "
            "<b>downloads/Matrix</b> or <b>downloads/DMS</b>, then parsed.",
            s["Body2"],
        )
    )
    story.append(Paragraph("Steps", s["Sub"]))
    story.append(
        bullets(
            [
                "Poller starts with the FastAPI backend (pipeline/poller.py).",
                "SFTP lists files. .835 still uses the original 835-only listing. .277 and .999 are listed separately.",
                "Already-processed filenames are skipped via pipeline_tracker (same tracker as 835).",
                "Each new file is downloaded, then routed by extension.",
                ".835: parse_835_text() -> save_era_file() -> collection era_payments (unchanged).",
                ".277: parse_277_text() -> save_277_file() -> collection claim_status_277.",
                ".999: parse_999_text() -> save_999_file() -> collection functional_ack_999.",
                "Granularity matches 835: one Mongo document per inner record (one 277 STC status line; one 999 IK5 acknowledgment), not one document per whole file.",
            ],
            s,
        )
    )

    story.append(Paragraph("5. Where data is saved (MongoDB)", s["Section"]))
    story.append(
        table(s, 
            [
                ["Setting", "Value"],
                ["Connection (from backend/.env)", "mongodb://10.103.0.201:27017"],
                ["Database", "edi_835"],
                ["277 collection", "claim_status_277"],
                ["999 collection", "functional_ack_999"],
                ["835 collection (unchanged)", "era_payments"],
                ["Tracker collection", "pipeline_tracker"],
            ],
            [2.3 * inch, 4.7 * inch],
        )
    )
    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            "In MongoDB Compass: connect to <b>10.103.0.201:27017</b> (not 10.103.0.22), then open database "
            "<b>edi_835</b>. Unique indexes: 277 = (source, source_filename, record_index); "
            "999 = (source, source_filename, ack_index).",
            s["Body2"],
        )
    )

    story.append(PageBreak())
    story.append(Paragraph("6. 277 files — what they are", s["Section"]))
    story.append(
        Paragraph(
            "A <b>.277</b> file is a HIPAA X12 <b>277 Claim Status Response / Claim Acknowledgment</b> "
            "(implementation seen in samples: <b>005010X214</b>, GS functional ID <b>HN</b>, ST*277). "
            "It tells the provider what happened to a submitted claim (accepted, rejected, pending, etc.). "
            "It is <b>not a payment file</b> (that is 835).",
            s["Body2"],
        )
    )
    story.append(Paragraph("Main 277 segments used", s["Sub"]))
    story.append(
        table(s, 
            [
                ["Segment", "Meaning"],
                ["ISA / IEA", "Interchange envelope (sender, receiver, date, control number)"],
                ["GS / GE", "Functional group (HN = claim status notification)"],
                ["ST / SE", "Transaction set 277"],
                ["BHT", "Beginning of hierarchical transaction; date of the status response"],
                ["HL", "Hierarchy: information source, receiver, provider, patient/claim"],
                ["NM1 PR", "Payer / information source"],
                ["NM1 41", "Submitter / receiver"],
                ["NM1 85", "Billing provider"],
                ["NM1 QC", "Patient"],
                ["TRN", "Trace / patient control number (used as patient account when TRN01=2)"],
                ["STC", "Status information: category:code:remark, date, qualifier, amount"],
                ["REF D9", "Claim / patient account reference (when present)"],
                ["DTP", "Dates (received, process, service period)"],
            ],
            [1.5 * inch, 5.5 * inch],
        )
    )
    story.append(Paragraph("277 extracted record fields (inside document.record)", s["Sub"]))
    story.append(
        table(s, 
            [
                ["Field", "Source", "Meaning"],
                ["transaction_control_number", "ST02", "277 transaction control number"],
                ["group_control_number", "GS06", "Functional group control number"],
                ["tran_date", "BHT04", "Transaction / response date"],
                ["patient_acc_no", "TRN02 (TRN01=2) or REF*D9", "Patient / claim account number"],
                ["claim_status_cat_code", "STC01 token 1", "Claim status category (e.g. A1, A0)"],
                ["claim_status_code", "STC01 token 2", "Claim status code (e.g. 20, 16)"],
                ["claim_status_code_full", "STC01", "Full composite, e.g. A1:20:AY"],
                ["remark_token", "STC01 token 3", "Optional remark (e.g. AY, PR)"],
                ["status_date", "STC02", "Status date"],
                ["status_qualifier", "STC03", "Status qualifier (e.g. WQ)"],
                ["status_amount", "STC04", "Related amount"],
                ["status", "STC01", "Same as full status composite (legacy-compatible)"],
                ["remarks", "STC01 token 3", "Same as remark_token"],
                ["submitter_id", "NM1*PR last ID", "Payer / submitter identifier"],
                ["insured_id", "NM1*QC last ID", "Patient / member ID"],
            ],
            [2.0 * inch, 2.2 * inch, 2.8 * inch],
        )
    )
    story.append(Paragraph("277 Mongo document wrapper fields", s["Sub"]))
    story.append(
        table(s, 
            [
                ["Field", "Meaning"],
                ["source", "SFTP account name (Matrix, DMS, or test source)"],
                ["source_filename", "Original filename, e.g. DD_AeliusMD_BILLS_....277"],
                ["record_index", "1-based index of this STC record inside the file"],
                ["imported_at", "UTC ISO timestamp when saved"],
                ["file_type", "X12 277 Claim Status"],
                ["envelope", "ISA/GS header fields (see envelope table)"],
                ["record", "The extracted 277 fields listed above"],
            ],
            [2.0 * inch, 5.0 * inch],
        )
    )

    story.append(PageBreak())
    story.append(Paragraph("7. 999 files — what they are", s["Section"]))
    story.append(
        Paragraph(
            "A <b>.999</b> file is a HIPAA X12 <b>999 Implementation Acknowledgment</b> "
            "(samples: <b>005010X231A1</b>, GS functional ID <b>FA</b>, ST*999). "
            "It reports whether a previously submitted X12 file (usually an <b>837 claim</b>) "
            "was accepted or rejected at the <b>syntax / implementation-guide</b> level. "
            "It is not claim payment (835) and not claim status (277).",
            s["Body2"],
        )
    )
    story.append(Paragraph("Main 999 segments used", s["Sub"]))
    story.append(
        table(s, 
            [
                ["Segment", "Meaning"],
                ["ISA / IEA", "Interchange envelope"],
                ["GS / GE", "Functional group (FA = functional acknowledgment)"],
                ["ST / SE", "Transaction set 999"],
                ["AK1", "Acknowledged functional group: ID + group control number"],
                ["AK2", "Acknowledged transaction set: usually 837 + control number"],
                ["IK3 / IK4", "Error location / data element error (not stored yet; extend if needed)"],
                ["IK5", "Transaction-set acknowledgment code (A=accepted, R=rejected, E=accepted with errors)"],
                ["AK9", "Functional-group acknowledgment: overall accept/reject and counts"],
            ],
            [1.5 * inch, 5.5 * inch],
        )
    )
    story.append(Paragraph("999 extracted acknowledgment fields (inside document.ack)", s["Sub"]))
    story.append(
        table(s, 
            [
                ["Field", "Source", "Meaning"],
                ["transaction_control_number", "ST02", "999 transaction control number"],
                ["group_control_number", "GS06", "999 file group control number"],
                ["group_control_id", "AK102", "Control number of the acknowledged 837 group"],
                ["file_type", "AK201", "Acknowledged transaction type (typically 837)"],
                ["file_837_control_number", "AK202", "ST control number of that 837"],
                ["status999", "IK501", "Per-transaction ack: A / E / R"],
                ["overall_status999", "AK901", "Overall group ack: A / E / P / R"],
                ["patient_no", "(not in sample 999)", "Left empty; 999 usually has no patient name"],
            ],
            [2.1 * inch, 1.6 * inch, 3.3 * inch],
        )
    )
    story.append(Paragraph("999 Mongo document wrapper fields", s["Sub"]))
    story.append(
        table(s, 
            [
                ["Field", "Meaning"],
                ["source", "SFTP account name"],
                ["source_filename", "Original filename, e.g. DD_AeliusMD_BILLS_....999"],
                ["ack_index", "1-based index of this IK5 acknowledgment inside the file"],
                ["imported_at", "UTC ISO timestamp when saved"],
                ["file_type", "X12 999 Functional Acknowledgment"],
                ["envelope", "ISA/GS header fields"],
                ["ack", "The extracted 999 fields listed above"],
            ],
            [2.0 * inch, 5.0 * inch],
        )
    )

    story.append(Paragraph("8. Shared envelope fields (both 277 and 999)", s["Section"]))
    story.append(
        table(s, 
            [
                ["Field", "Source", "Meaning"],
                ["sender_id", "ISA06", "Interchange sender"],
                ["receiver_id", "ISA08", "Interchange receiver"],
                ["date", "ISA09", "Interchange date"],
                ["time", "ISA10", "Interchange time"],
                ["version", "ISA12", "Interchange version (00501)"],
                ["control_number", "ISA13", "Interchange control number"],
                ["usage_indicator", "ISA15", "P=production, T=test"],
                ["functional_group", "GS01", "HN for 277, FA for 999, HP for 835"],
                ["application_sender", "GS02", "Application sender"],
                ["application_receiver", "GS03", "Application receiver"],
                ["group_date", "GS04", "Group date"],
                ["group_time", "GS05", "Group time"],
                ["group_control_number", "GS06", "Group control number"],
                ["implementation_version", "GS08", "e.g. 005010X214 or 005010X231A1"],
            ],
            [2.1 * inch, 1.4 * inch, 3.5 * inch],
        )
    )

    story.append(Paragraph("9. 835 vs 277 vs 999 (do not mix)", s["Section"]))
    story.append(
        table(s, 
            [
                ["File", "Business meaning", "Parser", "Mongo collection"],
                [".835", "Payment / remittance (ERA)", "parse_835_text (unchanged)", "era_payments"],
                [".277", "Claim status / claim ack", "parse_277_text", "claim_status_277"],
                [".999", "Syntax ack of a submitted 837", "parse_999_text", "functional_ack_999"],
            ],
            [1.1 * inch, 2.3 * inch, 2.0 * inch, 1.6 * inch],
        )
    )

    story.append(Paragraph("10. Code files involved", s["Section"]))
    story.append(
        bullets(
            [
                "backend/app/parser_277_999.py — 277 and 999 extraction",
                "pipeline/sftp_client.py — list_files_by_extension for .277/.999",
                "pipeline/poller.py — download, parse, save by file type",
                "pipeline/mongo_save.py — save_277_file / save_999_file and indexes",
                "backend/app/main.py — creates 277/999 unique indexes on startup",
                "backend/.env — SFTP_REMOTE_PATH=/837P/OUT/, MONGO_URI, MONGO_DB=edi_835",
            ],
            s,
        )
    )
    story.append(
        Paragraph(
            "Verification: 10 SFTP files were parsed and inserted. claim_status_277 received 10 documents "
            "(5 files x 2 STC records). functional_ack_999 received 293 documents across 5 files.",
            s["Body2"],
        )
    )

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawString(0.75 * inch, 0.45 * inch, "EDI 277 / 999 Field Guide — internal")
        canvas.drawRightString(letter[0] - 0.75 * inch, 0.45 * inch, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=letter,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.7 * inch,
        title="EDI 277 and 999 Field Guide",
        author="EDI 835 Converter",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(OUT)


if __name__ == "__main__":
    build()
