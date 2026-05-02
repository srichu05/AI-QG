"""
exporter.py
===========
Export generated questions to PDF and CSV formats.
"""

import logging
import csv
import json
from pathlib import Path
from typing import Any

from config import EXPORT_DIR
from modules.utils import timed, generate_uuid

logger = logging.getLogger(__name__)


def export_questions(
    questions: list[dict[str, Any]],
    document_info: dict | None,
    export_type: str,
    doc_id: str,
) -> str:
    """
    Export questions to the specified format.

    Parameters
    ----------
    questions : list[dict]
        Questions to export.
    document_info : dict or None
        Document metadata.
    export_type : str
        'pdf' or 'csv'.
    doc_id : str
        Document ID.

    Returns
    -------
    str
        Path to the generated export file.
    """
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    if export_type == "pdf":
        return _export_pdf(questions, document_info, doc_id)
    elif export_type == "csv":
        return _export_csv(questions, document_info, doc_id)
    else:
        raise ValueError(f"Unsupported export type: {export_type}")


@timed
def _export_pdf(
    questions: list[dict[str, Any]],
    document_info: dict | None,
    doc_id: str,
) -> str:
    """Generate a professional PDF question bank."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, HRFlowable,
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    filename = f"question_bank_{doc_id[:8]}.pdf"
    filepath = EXPORT_DIR / filename

    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=A4,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=20,
        textColor=HexColor("#1e293b"),
        spaceAfter=12,
        alignment=TA_CENTER,
    )
    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=HexColor("#3b82f6"),
        spaceBefore=18,
        spaceAfter=8,
    )
    q_style = ParagraphStyle(
        "QuestionStyle",
        parent=styles["Normal"],
        fontSize=11,
        leading=15,
        spaceBefore=8,
        spaceAfter=4,
    )
    answer_style = ParagraphStyle(
        "AnswerStyle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=HexColor("#16a34a"),
        leftIndent=20,
    )
    badge_style = ParagraphStyle(
        "BadgeStyle",
        parent=styles["Normal"],
        fontSize=9,
        textColor=HexColor("#6b7280"),
        leftIndent=20,
    )

    elements = []

    # Title
    doc_name = (document_info or {}).get("filename", "Document")
    elements.append(Paragraph("AI Question Bank", title_style))
    elements.append(Paragraph(f"Source: {doc_name}", styles["Normal"]))
    elements.append(Spacer(1, 8))
    elements.append(HRFlowable(width="100%", thickness=1, color=HexColor("#e2e8f0")))
    elements.append(Spacer(1, 12))

    # Summary
    total = len(questions)
    elements.append(Paragraph(f"Total Questions: {total}", styles["Normal"]))
    elements.append(Spacer(1, 16))

    # Group by type
    type_groups = {}
    for q in questions:
        qtype = q.get("question_type", "other")
        type_groups.setdefault(qtype, []).append(q)

    type_labels = {
        "fill_blank": "Fill in the Blank",
        "wh": "WH Questions",
        "short_answer": "Short Answer Questions",
        "mcq": "Multiple Choice Questions",
    }

    q_num = 1
    for qtype, label in type_labels.items():
        group = type_groups.get(qtype, [])
        if not group:
            continue

        elements.append(Paragraph(f"{label} ({len(group)})", heading_style))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#e2e8f0")))

        for q in group:
            q_text = q.get("question_text", q.get("question", ""))
            answer = q.get("answer", "")
            difficulty = q.get("difficulty", "medium")
            bloom = q.get("bloom_taxonomy", "remember")

            elements.append(Paragraph(f"<b>Q{q_num}.</b> {q_text}", q_style))

            # MCQ options
            if qtype == "mcq":
                options = q.get("options", [])
                if isinstance(options, str):
                    try:
                        options = json.loads(options)
                    except (json.JSONDecodeError, TypeError):
                        options = []
                for i, opt in enumerate(options):
                    letter = chr(65 + i)  # A, B, C, D
                    elements.append(Paragraph(f"    {letter}) {opt}", q_style))

            elements.append(Paragraph(f"<b>Answer:</b> {answer}", answer_style))
            elements.append(Paragraph(
                f"Difficulty: {difficulty.capitalize()} | Bloom's: {bloom.capitalize()}",
                badge_style,
            ))
            elements.append(Spacer(1, 6))
            q_num += 1

    # Answer key section
    elements.append(PageBreak())
    elements.append(Paragraph("Answer Key", title_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=HexColor("#e2e8f0")))
    elements.append(Spacer(1, 12))

    q_num = 1
    for qtype, label in type_labels.items():
        group = type_groups.get(qtype, [])
        for q in group:
            answer = q.get("answer", "")
            elements.append(Paragraph(f"Q{q_num}: {answer}", q_style))
            q_num += 1

    doc.build(elements)
    logger.info("PDF exported: %s (%d questions)", filepath, total)
    return str(filepath)


@timed
def _export_csv(
    questions: list[dict[str, Any]],
    document_info: dict | None,
    doc_id: str,
) -> str:
    """Generate a CSV export of all questions."""
    filename = f"question_bank_{doc_id[:8]}.csv"
    filepath = EXPORT_DIR / filename

    fieldnames = [
        "number", "question", "answer", "type", "difficulty",
        "bloom_taxonomy", "source_sentence", "options", "distractors",
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for i, q in enumerate(questions, 1):
            options = q.get("options", [])
            if isinstance(options, str):
                try:
                    options = json.loads(options)
                except (json.JSONDecodeError, TypeError):
                    options = []

            distractors = q.get("distractors", [])
            if isinstance(distractors, str):
                try:
                    distractors = json.loads(distractors)
                except (json.JSONDecodeError, TypeError):
                    distractors = []

            writer.writerow({
                "number": i,
                "question": q.get("question_text", q.get("question", "")),
                "answer": q.get("answer", ""),
                "type": q.get("question_type", ""),
                "difficulty": q.get("difficulty", ""),
                "bloom_taxonomy": q.get("bloom_taxonomy", ""),
                "source_sentence": q.get("source_sentence", ""),
                "options": " | ".join(options) if options else "",
                "distractors": " | ".join(distractors) if distractors else "",
            })

    logger.info("CSV exported: %s (%d questions)", filepath, len(questions))
    return str(filepath)
