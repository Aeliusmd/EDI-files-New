"""PDF: 277/999 purpose, custom parser, IK5, and why one file can make many Mongo docs."""
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

OUT = Path(__file__).resolve().parents[1] / "docs" / "EDI_277_999_Explanation.pdf"


def make_styles():
    s = getSampleStyleSheet()
    s.add(
        ParagraphStyle(
            "CoverTitle",
            parent=s["Title"],
            fontSize=20,
            leading=24,
            spaceAfter=8,
            textColor=colors.HexColor("#0f3d5e"),
        )
    )
    s.add(
        ParagraphStyle(
            "Section",
            parent=s["Heading1"],
            fontSize=14,
            textColor=colors.HexColor("#0f3d5e"),
            spaceBefore=12,
            spaceAfter=6,
        )
    )
    s.add(
        ParagraphStyle(
            "Sub",
            parent=s["Heading2"],
            fontSize=11,
            textColor=colors.HexColor("#1a5f8a"),
            spaceBefore=8,
            spaceAfter=4,
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
    s = make_styles()
    story = []

    story.append(Paragraph("277 and 999 Files: Purpose, Parser, MongoDB, and SQL Tables", s["CoverTitle"]))
    story.append(
        Paragraph(
            "Simple explanation of why these files exist, how the custom parser reads them, "
            "what IK5 means, why one file can create many Mongo documents, and what the "
            "277/999 SQL tables are for.",
            s["Body2"],
        )
    )
    story.append(Paragraph("EDI 835 Converter project &mdash; 277/999 extension", s["FooterNote"]))
    story.append(Spacer(1, 8))

    story.append(Paragraph("What to say (process and libraries)", s["Section"]))
    story.append(
        Paragraph(
            "If someone asks <b>what process or library we used to parse 277 and 999 files</b>, say this:",
            s["Body2"],
        )
    )
    story.append(
        Paragraph(
            "<b>Short answer:</b> We did <b>not</b> use a third-party 277/999 library (not pyx12, not botocore EDI, not a paid HIPAA mapper). "
            "We use the <b>same custom X12 segment-walking process as 835</b>, in our own Python parser. "
            "SFTP download uses <b>paramiko</b>. MongoDB save uses <b>pymongo</b>. Settings use <b>python-dotenv</b>.",
            s["Body2"],
        )
    )
    story.append(
        table(
            s,
            [
                ["Question", "What to say"],
                [
                    "What library parses 277/999?",
                    "No dedicated 277/999 package. Custom parser: backend/app/parser_277_999.py (parse_277_text and parse_999_text).",
                ],
                [
                    "How does it parse?",
                    "Read ISA, detect * and ~ separators, split segments, walk tags in order (same method as the 835 parser). 277 creates a row on STC. 999 creates a row on IK5.",
                ],
                [
                    "What libraries are used?",
                    "Python standard library (split/walk text). Helpers from the existing 835 parser (detect_separators, get, edi_date, money, parse_nm1). paramiko (SFTP). pymongo (MongoDB). python-dotenv (.env).",
                ],
                [
                    "What is the process?",
                    "SFTP folder /837P/OUT/ → poller lists .277 and .999 → download → parse by extension → save to Mongo collections claim_status_277 and functional_ack_999. 835 path is unchanged.",
                ],
                [
                    "Is it a full HIPAA validator?",
                    "No. It is a best-effort extractor of business fields, same idea as 835, not a full X12 implementation-guide validator.",
                ],
                [
                    "What about SQL tables?",
                    "277/999 only. Script SQL/Create_Edi277_Edi999_Tables.sql. No 835 tables. Mongo stays the live save; SQL tables are the relational design for the same parsed fields.",
                ],
            ],
            [2.0 * inch, 5.0 * inch],
        )
    )
    story.append(Spacer(1, 8))

    story.append(Paragraph("1. Why these files exist", s["Section"]))
    story.append(
        Paragraph(
            "When a clinic bills insurance, the claim is sent as an <b>837</b>. After that, three kinds of "
            "replies can come back. They are <b>not the same thing</b>.",
            s["Body2"],
        )
    )
    story.append(
        table(
            s,
            [
                ["File", "Purpose", "Simple meaning"],
                [".999", "Did the computer accept the 837 file?", "Your file arrived. Syntax OK / not OK."],
                [".277", "What is the status of the claim?", "We received it / pending / rejected."],
                [".835", "Did they pay, and how much?", "Here is the payment / denial with money."],
            ],
            [1.1 * inch, 2.5 * inch, 3.4 * inch],
        )
    )
    story.append(Spacer(1, 6))
    story.append(Paragraph("Timeline", s["Sub"]))
    story.append(
        bullets(
            [
                "You send <b>837</b> (the bill).",
                "You get <b>999</b> &mdash; the 837 batch was readable / accepted as valid EDI.",
                "You get <b>277</b> &mdash; claim status for that patient (in process, rejected, etc.).",
                "You get <b>835</b> &mdash; payment details (ERA).",
            ],
            s,
        )
    )
    story.append(
        Paragraph(
            "<b>999</b> = file-level technical ack. <b>277</b> = claim-level status. <b>835</b> = payment.",
            s["Body2"],
        )
    )

    story.append(Paragraph("2. Custom parser — what that means", s["Section"]))
    story.append(
        Paragraph(
            "We did <b>not</b> use a ready-made 277/999 library. We wrote our own reader, the same style as the 835 parser.",
            s["Body2"],
        )
    )
    story.append(
        bullets(
            [
                "Open the text file (starts with ISA*...~).",
                "Split it into segments (pieces ending with ~).",
                "Look at the first code of each piece (ST, STC, IK5, AK2, ...).",
                "Copy useful fields into JSON.",
                "Save to MongoDB.",
            ],
            s,
        )
    )
    story.append(
        Paragraph("Code file: <b>backend/app/parser_277_999.py</b>", s["Body2"])
    )
    story.append(
        Paragraph(
            "277 function: <b>parse_277_text()</b>. 999 function: <b>parse_999_text()</b>. "
            "Libraries used around this: Python built-in text reading, <b>paramiko</b> (SFTP download), "
            "<b>pymongo</b> (Mongo save), <b>python-dotenv</b> (.env settings).",
            s["Body2"],
        )
    )

    story.append(Paragraph("3. 999 parser — purpose and how it reads", s["Section"]))
    story.append(
        Paragraph(
            "<b>Purpose of .999:</b> the clearinghouse/payer saying the 837 file you sent was accepted or "
            "rejected at the <b>technical / syntax</b> level. It usually has <b>no patient name</b> and "
            "<b>no payment</b>.",
            s["Body2"],
        )
    )
    story.append(
        Paragraph(
            "<b>How it works:</b> the parser walks the file and creates <b>one Mongo row each time it sees IK5</b>.",
            s["Body2"],
        )
    )
    story.append(
        table(
            s,
            [
                ["Segment", "What we take"],
                ["AK1", "Which 837 batch is being acknowledged"],
                ["AK2*837*0001", "Which 837 transaction inside that batch"],
                ["IK5*A", "Result for that transaction (see IK5 below)"],
                ["AK9", "Overall result for the whole batch"],
            ],
            [2.0 * inch, 5.0 * inch],
        )
    )
    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            "Example: one .999 with 49 IK5 lines &rarr; <b>49 Mongo documents</b> in collection "
            "<b>functional_ack_999</b>.",
            s["Body2"],
        )
    )

    story.append(Paragraph("4. What is IK5?", s["Section"]))
    story.append(
        Paragraph(
            "<b>IK5</b> is an X12 999 segment. Its name is <b>Transaction Set Response Trailer</b>. "
            "In plain language: it is the <b>yes/no/error result for one 837 transaction</b> inside the file you sent.",
            s["Body2"],
        )
    )
    story.append(
        Paragraph(
            "A 999 file can acknowledge many 837 claims packed in one batch. Each claim (or each ST*837 block) "
            "gets its own IK5. That is why IK5 appears many times in one .999 file.",
            s["Body2"],
        )
    )
    story.append(
        table(
            s,
            [
                ["IK5 code", "Meaning"],
                ["A", "Accepted — that 837 transaction passed syntax checks"],
                ["E", "Accepted with errors — usable, but some issues were reported"],
                ["R", "Rejected — that 837 transaction failed; it will not be processed as a claim"],
                ["M / W / X", "Less common: rejected, wait for correction, or rejected but may be resubmitted (depends on payer)"],
            ],
            [1.5 * inch, 5.5 * inch],
        )
    )
    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            "Example from a real file: <b>AK2*837*0001~IK5*A~</b> means 837 control number 0001 was accepted. "
            "Then <b>AK2*837*0002~IK5*A~</b> means the next 837 in the same batch was also accepted. "
            "<b>AK9*A</b> at the end means the whole batch was accepted.",
            s["Body2"],
        )
    )
    story.append(
        Paragraph(
            "IK5 is <b>not</b> a payment and <b>not</b> claim medical status. It only answers: "
            "did this piece of the 837 file pass the computer check?",
            s["Body2"],
        )
    )

    story.append(Paragraph("5. 277 parser — purpose and how it reads", s["Section"]))
    story.append(
        Paragraph(
            "<b>Purpose of .277:</b> the payer saying here is the <b>status of the claim</b> — received, "
            "pending, forwarded, rejected, etc. Still <b>not a payment</b>. Payment comes later in 835.",
            s["Body2"],
        )
    )
    story.append(
        Paragraph(
            "<b>How it works:</b> it remembers who the patient/payer is, then creates "
            "<b>one Mongo row each time it sees STC</b> (status).",
            s["Body2"],
        )
    )
    story.append(
        table(
            s,
            [
                ["Segment", "What we take"],
                ["NM1*PR", "Payer"],
                ["NM1*QC", "Patient"],
                ["TRN / REF*D9", "Patient account / claim number"],
                ["STC", "The actual status — this creates a Mongo document"],
            ],
            [2.0 * inch, 5.0 * inch],
        )
    )
    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            "Example: <b>STC*A1:20:AY*20260326*WQ*230</b> becomes category A1, code 20, remark AY, date, amount. "
            "The parser does <b>not</b> stop at the first <b>SE</b>. If one .277 file has two <b>ST*277</b> blocks "
            "(two claims), both are saved. Sample ....108.277 has 2 ST blocks x 2 STC lines = "
            "<b>4 Mongo documents</b> in <b>claim_status_277</b>.",
            s["Body2"],
        )
    )

    story.append(Paragraph("6. Why can the same file create multiple Mongo documents?", s["Section"]))
    story.append(
        Paragraph(
            "This matches the existing <b>835 design</b>: one Mongo document per inner business record, "
            "not one document for the whole file. A single EDI file is a container. Inside it there can be "
            "many claims or many acknowledgments.",
            s["Body2"],
        )
    )
    story.append(
        table(
            s,
            [
                ["File type", "One Mongo doc is created for each...", "Why"],
                [
                    ".835",
                    "Payment transaction (ST*835 block)",
                    "One file can contain several checks / ERA transactions.",
                ],
                [
                    ".277",
                    "STC status line",
                    "One file can report status for several patients or several levels (submitter + patient).",
                ],
                [
                    ".999",
                    "IK5 acknowledgment",
                    "One 999 can ack dozens of 837 claims that were in the same batch.",
                ],
            ],
            [1.1 * inch, 2.4 * inch, 3.5 * inch],
        )
    )
    story.append(Spacer(1, 6))
    story.append(Paragraph("Real examples from SFTP testing", s["Sub"]))
    story.append(
        bullets(
            [
                "One 277 file (....108.277) has 2 ST*277 blocks and 4 STC lines &rarr; 4 Mongo docs (after SE fix).",
                "One 999 file (....133530.999) had 49 IK5 lines &rarr; 49 Mongo docs.",
                "Another 999 file (....134228.999) had 200 IK5 lines &rarr; 200 Mongo docs.",
            ],
            s,
        )
    )
    story.append(
        Paragraph(
            "If we saved only one Mongo document per filename, you would lose the detail of each claim/ack "
            "inside the file. Multiple docs from one file is <b>correct</b>, not a duplicate bug. "
            "Duplicates are still blocked by unique index: source + filename + record_index (277) or ack_index (999).",
            s["Body2"],
        )
    )

    story.append(Paragraph("7. Simple picture", s["Section"]))
    story.append(
        Paragraph(
            "837 = you send the claim.<br/>"
            "999 = file is valid EDI &rarr; custom parser looks for <b>IK5</b>.<br/>"
            "277 = claim status &rarr; custom parser looks for <b>STC</b>.<br/>"
            "835 = here is the money &rarr; old parser (unchanged).",
            s["Body2"],
        )
    )

    story.append(Paragraph("8. Where it is saved", s["Section"]))
    story.append(
        table(
            s,
            [
                ["Item", "Value"],
                ["Mongo host", "10.103.0.201:27017"],
                ["Database", "edi_835"],
                ["999 collection", "functional_ack_999"],
                ["277 collection", "claim_status_277"],
                ["835 collection (unchanged)", "era_payments"],
                ["SQL script (277/999 only)", "SQL/Create_Edi277_Edi999_Tables.sql"],
                ["SQL schema", "edi (database edi_835)"],
                ["SQL 277 tables", "edi.Edi277File + edi.Edi277Status"],
                ["SQL 999 tables", "edi.Edi999File + edi.Edi999Ack + error/context children"],
            ],
            [2.3 * inch, 4.7 * inch],
        )
    )

    story.append(PageBreak())
    story.append(Paragraph("9. MongoDB structure after processing (current parser)", s["Section"]))
    story.append(
        Paragraph(
            "Host <b>10.103.0.201:27017</b>, database <b>edi_835</b>. "
            "277 and 999 collections are filled only by <b>parse_277_text</b> / <b>parse_999_text</b> "
            "in <b>backend/app/parser_277_999.py</b>. The 835 collection is not changed. "
            "Existing 277/999 Mongo documents were deleted and re-inserted with this parser so Compass matches the fields below.",
            s["Body2"],
        )
    )

    story.append(Paragraph("277 collection: claim_status_277 (one doc per STC)", s["Sub"]))
    story.append(
        table(
            s,
            [
                ["Mongo path", "Meaning"],
                ["source", "SFTP account (Matrix / DMS)"],
                ["source_filename", "Original .277 filename"],
                ["record_index", "1, 2, 3... inside that file"],
                ["imported_at", "UTC time saved"],
                ["file_type", "X12 277 Claim Status"],
                ["envelope.sender_id / receiver_id", "ISA sender and receiver"],
                ["envelope.date / time / version / control_number / usage_indicator", "ISA header"],
                ["envelope.functional_group", "GS01, usually HN"],
                ["envelope.application_sender / application_receiver", "GS sender/receiver"],
                ["envelope.group_date / group_time / group_control_number", "GS dates and control"],
                ["envelope.implementation_version", "e.g. 005010X214"],
                ["record.transaction_control_number", "ST02 of this 277 block"],
                ["record.group_control_number", "GS06"],
                ["record.tran_date", "BHT date"],
                ["record.patient_acc_no", "TRN*2 or REF*D9"],
                ["record.patient_name", "NM1*QC patient name"],
                ["record.payer_name", "NM1*PR payer name"],
                ["record.submitter_name / submitter_entity_id", "NM1*41 submitter/receiver"],
                ["record.provider_name / provider_id", "NM1*85 billing provider"],
                ["record.payer_trace", "TRN*1 payer trace number"],
                ["record.service_date", "DTP*472"],
                ["record.received_date", "DTP*050"],
                ["record.process_date", "DTP*009"],
                ["record.hl_id / hl_parent_id / hl_level_code / hl_level_name", "HL hierarchy for this STC row"],
                ["record.claim_status_cat_code", "STC first token, e.g. A1"],
                ["record.claim_status_code", "STC second token, e.g. 20"],
                ["record.claim_status_code_full", "Full STC01, e.g. A1:20:AY"],
                ["record.remark_token / record.remarks", "STC third token, e.g. AY"],
                ["record.status_date", "STC date"],
                ["record.status_qualifier", "e.g. WQ"],
                ["record.status_amount", "STC amount"],
                ["record.status", "Same as claim_status_code_full"],
                ["record.submitter_id", "NM1*PR ID"],
                ["record.insured_id", "NM1*QC member ID"],
            ],
            [3.2 * inch, 3.8 * inch],
        )
    )
    story.append(Spacer(1, 6))
    story.append(Paragraph("277 — saved vs NOT saved", s["Sub"]))
    story.append(
        Paragraph(
            "Status <b>SAVED</b> means it is written to MongoDB. Status <b>NOT SAVED</b> means it is in the .277 file but the current parser does not write it.",
            s["Body2"],
        )
    )
    story.append(
        table(
            s,
            [
                ["EDI detail", "Status", "Where it is in the file"],
                ["Patient name (last / first)", "SAVED", "record.patient_name from NM1*QC"],
                ["Payer name", "SAVED", "record.payer_name from NM1*PR"],
                ["Service date / period", "SAVED", "record.service_date from DTP*472"],
                ["Billing provider name / NPI", "SAVED", "record.provider_name / provider_id from NM1*85"],
                ["Submitter / receiver name", "SAVED", "record.submitter_name from NM1*41"],
                ["HL hierarchy (source / receiver / provider / patient)", "SAVED", "record.hl_* on each STC row"],
                ["Received date", "SAVED", "record.received_date from DTP*050"],
                ["Process date", "SAVED", "record.process_date from DTP*009"],
                ["Payer trace number", "SAVED", "record.payer_trace from TRN*1"],
                ["BHT time / hierarchical structure code", "NOT SAVED", "BHT05, BHT06 (low value)"],
                ["Raw EDI file text", "NOT SAVED", "File already kept under downloads/"],
            ],
            [2.6 * inch, 1.3 * inch, 3.1 * inch],
        )
    )

    story.append(Paragraph("999 collection: functional_ack_999 (one doc per IK5)", s["Sub"]))
    story.append(
        table(
            s,
            [
                ["Mongo path", "Meaning"],
                ["source", "SFTP account (Matrix / DMS)"],
                ["source_filename", "Original .999 filename"],
                ["ack_index", "1, 2, 3... inside that file"],
                ["imported_at", "UTC time saved"],
                ["file_type", "X12 999 Functional Acknowledgment"],
                ["envelope.*", "Same ISA/GS envelope fields as 277 (GS01 is FA)"],
                ["ack.transaction_control_number", "ST02 of this 999"],
                ["ack.group_control_number", "GS06 of the 999 file"],
                ["ack.group_control_id", "AK102 — original 837 group control"],
                ["ack.ak1_functional_id", "AK101, e.g. HC"],
                ["ack.ak1_implementation_version", "AK103, e.g. 005010X222"],
                ["ack.file_type", "AK201, usually 837"],
                ["ack.file_837_control_number", "AK202 — that 837 ST control"],
                ["ack.status999", "IK5: A / E / R"],
                ["ack.status999_error_codes", "Extra IK5 codes after A/E/R (empty if accepted)"],
                ["ack.errors", "IK3/IK4 list: which segment/field failed, plus CTX on that error"],
                ["ack.context", "CTX not tied to an IK3 (if any)"],
                ["ack.overall_status999", "AK9 overall: A / E / P / R"],
                ["ack.ak9_included_count / received / accepted", "AK9 counts, e.g. 49 / 49 / 49"],
                ["ack.ak9_error_codes", "Extra AK9 reason codes if present"],
                ["ack.patient_no", "Stored but usually empty (999 has no patient)"],
            ],
            [3.2 * inch, 3.8 * inch],
        )
    )
    story.append(Spacer(1, 6))
    story.append(Paragraph("999 — saved vs NOT saved", s["Sub"]))
    story.append(
        Paragraph(
            "Status <b>SAVED</b> means it is written to MongoDB. Status <b>NOT SAVED</b> means it can exist in the .999 file but is not written.",
            s["Body2"],
        )
    )
    story.append(
        table(
            s,
            [
                ["EDI detail", "Status", "Where it is in the file"],
                ["AK9 counts (received / accepted / etc.)", "SAVED", "ack.ak9_included_count / received / accepted"],
                ["AK1 functional identifier", "SAVED", "ack.ak1_functional_id"],
                ["AK1 implementation version", "SAVED", "ack.ak1_implementation_version"],
                ["IK3 error segment location", "SAVED", "ack.errors[].segment_id / position / loop / error_code"],
                ["IK4 data-element error details", "SAVED", "ack.errors[].element_errors[]"],
                ["IK5 extra error codes after A/E/R", "SAVED", "ack.status999_error_codes"],
                ["CTX context / CTX02 details", "SAVED", "ack.errors[].context or ack.context"],
                ["Patient name / account", "NOT SAVED as real data", "999 usually has none; patient_no is stored empty"],
                ["Raw EDI file text", "NOT SAVED", "Full ISA...IEA string is not stored"],
            ],
            [2.6 * inch, 1.3 * inch, 3.1 * inch],
        )
    )
    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            "<b>Important:</b> NOT SAVED means it is in the EDI file but it is <b>not</b> in MongoDB. "
            "Only the saved-field tables above are written to <b>claim_status_277</b> and <b>functional_ack_999</b>.",
            s["Body2"],
        )
    )
    story.append(
        Paragraph(
            "Unique indexes: 277 = (source, source_filename, record_index). "
            "999 = (source, source_filename, ack_index). 835 stays in <b>era_payments</b> unchanged.",
            s["Body2"],
        )
    )

    story.append(PageBreak())
    story.append(Paragraph("10. SQL tables (277 and 999 only — not 835)", s["Section"]))
    story.append(
        Paragraph(
            "MongoDB is what the poller writes today. The SQL tables are a <b>relational copy of the same 277/999 "
            "parsed fields</b> so the data can also live in SQL Server (same idea as MySQL tables: one file row, "
            "many status/ack child rows). They are <b>not</b> 835 / ERA tables. Do not run the old 835 drop-and-create script.",
            s["Body2"],
        )
    )
    story.append(
        Paragraph(
            "Create script: <b>SQL/Create_Edi277_Edi999_Tables.sql</b> (SSMS / SQL Server syntax). "
            "Database <b>edi_835</b>, schema <b>edi</b>. The script does not drop existing rows and does not change Mongo.",
            s["Body2"],
        )
    )
    story.append(
        table(
            s,
            [
                ["Item", "Value"],
                ["What they store", "Parsed 277 claim status and 999 acknowledgments — same fields as Mongo"],
                ["What they do not store", "835 payments, ERA, ClearingHouse835, raw EDI text"],
                ["How to create", "Open the script in SSMS and run (F5)"],
                ["Live ingest today", "Still Mongo collections claim_status_277 and functional_ack_999"],
            ],
            [2.3 * inch, 4.7 * inch],
        )
    )

    story.append(Paragraph("What each SQL table is about", s["Sub"]))
    story.append(
        table(
            s,
            [
                ["SQL table", "About", "Matches"],
                [
                    "edi.Edi277File",
                    "One row per .277 filename. Envelope (ISA/GS), source, imported time.",
                    "Shared header of claim_status_277 docs for that file",
                ],
                [
                    "edi.Edi277Status",
                    "One row per STC status (patient/claim status line). Child of Edi277File.",
                    "One Mongo document in claim_status_277",
                ],
                [
                    "edi.Edi999File",
                    "One row per .999 filename. Envelope (ISA/GS), source, imported time.",
                    "Shared header of functional_ack_999 docs for that file",
                ],
                [
                    "edi.Edi999Ack",
                    "One row per IK5 (accepted / error / rejected for one 837 transaction).",
                    "One Mongo document in functional_ack_999",
                ],
                [
                    "edi.Edi999Ik5ErrorCode",
                    "Extra IK5 reason codes after A/E/R.",
                    "ack.status999_error_codes[]",
                ],
                [
                    "edi.Edi999Ak9ErrorCode",
                    "Extra AK9 batch-level reason codes.",
                    "ack.ak9_error_codes[]",
                ],
                [
                    "edi.Edi999Error",
                    "IK3 segment error (which segment/loop failed).",
                    "ack.errors[]",
                ],
                [
                    "edi.Edi999ElementError",
                    "IK4 field error inside an IK3.",
                    "ack.errors[].element_errors[]",
                ],
                [
                    "edi.Edi999ErrorContext",
                    "CTX tied to an IK3 error.",
                    "ack.errors[].context",
                ],
                [
                    "edi.Edi999AckContext",
                    "CTX tied to the IK5 ack, not to a specific IK3.",
                    "ack.context",
                ],
            ],
            [1.7 * inch, 2.6 * inch, 2.7 * inch],
        )
    )

    story.append(Paragraph("How the SQL tables relate", s["Sub"]))
    story.append(
        bullets(
            [
                "<b>277:</b> Edi277File (1 file) &rarr; many Edi277Status rows (one per STC).",
                "<b>999:</b> Edi999File (1 file) &rarr; many Edi999Ack rows (one per IK5).",
                "Each Edi999Ack can have IK5 codes, AK9 codes, IK3 errors, IK4 element errors, and CTX rows.",
                "Foreign keys use ON DELETE CASCADE: deleting a file row removes its status/ack children.",
                "Unique keys: file = (Source, SourceFilename). 277 status = (FileId, RecordIndex). 999 ack = (FileId, AckIndex).",
            ],
            s,
        )
    )

    story.append(Paragraph("277 SQL columns (edi.Edi277Status) — what they are about", s["Sub"]))
    story.append(
        table(
            s,
            [
                ["SQL column", "About"],
                ["RecordIndex", "1, 2, 3... STC order inside the file"],
                ["TransactionControlNumber / GroupControlNumber", "ST02 and GS06"],
                ["TranDate", "BHT date"],
                ["PatientAccNo / PatientName / InsuredId", "Account, NM1*QC name, member ID"],
                ["PayerName / PayerTrace / SubmitterId", "NM1*PR name, TRN*1, payer ID"],
                ["SubmitterName / SubmitterEntityId", "NM1*41"],
                ["ProviderName / ProviderId", "NM1*85 billing provider"],
                ["ServiceDate / ReceivedDate / ProcessDate", "DTP*472 / DTP*050 / DTP*009"],
                ["HlId / HlParentId / HlLevelCode / HlLevelName", "HL hierarchy for this STC"],
                ["ClaimStatusCatCode / ClaimStatusCode / ClaimStatusCodeFull", "STC codes, e.g. A1, 20, A1:20:AY"],
                ["RemarkToken / Remarks", "STC remark, e.g. AY"],
                ["StatusDate / StatusQualifier / StatusAmount / Status", "STC date, WQ, amount, full status"],
            ],
            [3.2 * inch, 3.8 * inch],
        )
    )

    story.append(Paragraph("999 SQL columns (edi.Edi999Ack) — what they are about", s["Sub"]))
    story.append(
        table(
            s,
            [
                ["SQL column", "About"],
                ["AckIndex", "1, 2, 3... IK5 order inside the file"],
                ["GroupControlId", "AK102 — original 837 group control"],
                ["Ak1FunctionalId / Ak1ImplementationVersion", "AK1 (e.g. HC, 005010X222)"],
                ["AckedFileType / File837ControlNumber", "AK2 — usually 837 and that ST control"],
                ["Status999", "IK5: A accepted, E accepted with errors, R rejected"],
                ["OverallStatus999", "AK9 overall for the batch"],
                ["Ak9IncludedCount / ReceivedCount / AcceptedCount", "AK9 counts"],
                ["PatientNo", "Usually empty — 999 has no patient"],
            ],
            [3.2 * inch, 3.8 * inch],
        )
    )
    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            "<b>Important:</b> these SQL tables are 277 and 999 only. They do not replace Mongo. "
            "They do not create or change 835 tables. One .277 file = one Edi277File + many Edi277Status rows. "
            "One .999 file = one Edi999File + many Edi999Ack rows.",
            s["Body2"],
        )
    )

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawString(0.75 * inch, 0.45 * inch, "277 / 999 explanation — purpose, IK5, Mongo, SQL tables")
        canvas.drawRightString(letter[0] - 0.75 * inch, 0.45 * inch, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=letter,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.7 * inch,
        title="277 and 999 Explanation (Mongo and SQL tables)",
        author="EDI 835 Converter",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(OUT)


if __name__ == "__main__":
    build()
