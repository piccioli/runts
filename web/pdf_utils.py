"""PDF generation for ente detail sheets using reportlab + pypdf overlay."""
import io
import os
import sqlite3
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    Paragraph, Spacer, Table, TableStyle, KeepInFrame, SimpleDocTemplate
)
from reportlab.pdfgen import canvas

_CARTA_INTESTATA = Path(__file__).parent / "static" / "MS_Carta_Intestata.pdf"

_FIELD_LABELS = [
    ("codice_fiscale",      "Codice fiscale"),
    ("forma_giuridica",     "Forma giuridica"),
    ("natura_giuridica",    "Natura giuridica"),
    ("sezione_registro",    "Sezione del registro"),
    ("data_iscrizione",     "Data iscrizione"),
    ("sede_stato",          "Stato"),
    ("sede_indirizzo",      "Indirizzo"),
    ("sede_civico",         "Civico"),
    ("sede_comune",         "Comune"),
    ("sede_provincia",      "Provincia"),
    ("sede_regione",        "Regione"),
    ("sede_cap",            "CAP"),
    ("rappresentante_legale", "Rappresentante legale"),
    ("pec",                 "PEC"),
    ("sito_web",            "Sito web"),
    ("lat",                 "Latitudine"),
    ("lon",                 "Longitudine"),
]


def _row_value(row, key: str):
    try:
        v = row[key]
        return str(v) if v is not None else None
    except (IndexError, KeyError):
        return None


def build_ente_pdf(ente_row: sqlite3.Row) -> bytes:
    """Generate a PDF sheet for an ente, overlaid with MS carta intestata."""
    buf = io.BytesIO()

    # A4: 596 x 842 pt — leave top 140 pt for header, bottom 60 pt for footer
    PAGE_W, PAGE_H = A4  # (595.27, 841.89)
    TOP_MARGIN = 140
    BOTTOM_MARGIN = 60
    LEFT_MARGIN = 60
    RIGHT_MARGIN = 60
    content_w = PAGE_W - LEFT_MARGIN - RIGHT_MARGIN

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=LEFT_MARGIN,
        rightMargin=RIGHT_MARGIN,
        topMargin=TOP_MARGIN,
        bottomMargin=BOTTOM_MARGIN,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "title",
        parent=styles["Heading1"],
        fontSize=13,
        spaceAfter=4,
        textColor=colors.HexColor("#1a1a2e"),
    )
    sub_style = ParagraphStyle(
        "sub",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.grey,
        spaceAfter=12,
    )
    label_style = ParagraphStyle("label", parent=styles["Normal"], fontSize=9, textColor=colors.grey)
    value_style = ParagraphStyle("value", parent=styles["Normal"], fontSize=9)

    denominazione = _row_value(ente_row, "denominazione") or "Ente sconosciuto"
    codice_fiscale = _row_value(ente_row, "codice_fiscale") or ""

    story = [
        Paragraph(denominazione, title_style),
        Paragraph(f"Codice fiscale: {codice_fiscale}" if codice_fiscale else "", sub_style),
    ]

    # Build field table
    table_data = []
    for key, label in _FIELD_LABELS:
        value = _row_value(ente_row, key)
        if value:
            table_data.append([
                Paragraph(label, label_style),
                Paragraph(value, value_style),
            ])

    if table_data:
        col_w = [content_w * 0.35, content_w * 0.65]
        tbl = Table(table_data, colWidths=col_w, repeatRows=0)
        tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#e0e0e0")),
        ]))
        story.append(tbl)

    # Wrap story in KeepInFrame to prevent overflow beyond available height
    available_h = PAGE_H - TOP_MARGIN - BOTTOM_MARGIN
    framed = KeepInFrame(content_w, available_h, story, mode="shrink")
    doc.build([framed])

    content_bytes = buf.getvalue()

    # Overlay carta intestata as background on every page
    try:
        from pypdf import PdfWriter, PdfReader

        content_reader = PdfReader(io.BytesIO(content_bytes))
        carta_reader = PdfReader(str(_CARTA_INTESTATA))
        carta_page = carta_reader.pages[0]

        writer = PdfWriter()
        for page in content_reader.pages:
            carta_copy = carta_page.clone(writer)
            carta_copy.merge_page(page)
            writer.add_page(carta_copy)

        out = io.BytesIO()
        writer.write(out)
        return out.getvalue()
    except Exception:
        # Fallback: return content without overlay if pypdf merge fails
        return content_bytes
