"""PDF generation for ente detail sheets using reportlab + pypdf overlay."""
import io
import os
import sqlite3
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    Paragraph, Spacer, Table, TableStyle, SimpleDocTemplate
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


def _fmt(value, decimals: int = 2) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return str(value)


def _section_heading(title: str, styles) -> Paragraph:
    st = ParagraphStyle(
        "section_head",
        parent=styles["Heading2"],
        fontSize=10,
        spaceBefore=14,
        spaceAfter=4,
        textColor=colors.HexColor("#1a1a2e"),
    )
    return Paragraph(title, st)


def _build_allegati_section(allegati, styles) -> list:
    if not allegati:
        return []
    cell_style = ParagraphStyle("cell", parent=styles["Normal"], fontSize=8)
    header_style = ParagraphStyle("hdr", parent=styles["Normal"], fontSize=8, textColor=colors.grey)

    rows = [[
        Paragraph("Tipo", header_style),
        Paragraph("Cod. pratica", header_style),
        Paragraph("Anno", header_style),
        Paragraph("Dimensione", header_style),
        Paragraph("Link RUNTS", header_style),
    ]]
    for att in allegati:
        try:
            tipo = att["tipo"] or "—"
            codice = att["codice_pratica"] or "—"
            anno = str(att["anno"]) if att["anno"] else "—"
            size = att["size"]
            size_str = (f"{size // 1024} KB" if size and size < 1_048_576 else f"{size / 1_048_576:.1f} MB") if size else "—"
            url = att["url_originale"] or ""
            link_cell = Paragraph(f'<link href="{url}">↗</link>' if url else "—", cell_style)
        except (KeyError, TypeError):
            continue
        rows.append([
            Paragraph(tipo, cell_style),
            Paragraph(codice, cell_style),
            Paragraph(anno, cell_style),
            Paragraph(size_str, cell_style),
            link_cell,
        ])

    tbl = Table(rows, colWidths=[110, 70, 40, 60, 40])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f5f5f5")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#e0e0e0")),
    ]))
    return [_section_heading("Atti e documenti", styles), tbl]


def _build_bilanci_section(bilanci, styles) -> list:
    if not bilanci:
        return []
    cell_style = ParagraphStyle("cell", parent=styles["Normal"], fontSize=8)
    header_style = ParagraphStyle("hdr", parent=styles["Normal"], fontSize=8, textColor=colors.grey)
    num_style = ParagraphStyle("num", parent=styles["Normal"], fontSize=8, alignment=2)

    rows = [[
        Paragraph("Anno", header_style),
        Paragraph("Totale proventi", header_style),
        Paragraph("Totale oneri", header_style),
        Paragraph("Risultato", header_style),
    ]]
    for b in bilanci:
        try:
            anno = str(b["anno"]) if b["anno"] else "—"
            proventi = _fmt(b["totale_proventi"])
            oneri = _fmt(b["totale_oneri"])
            risultato = b["risultato_esercizio"]
            risultato_str = _fmt(risultato)
            ris_color = colors.red if risultato is not None and float(risultato) < 0 else colors.black
            ris_style = ParagraphStyle("ris", parent=styles["Normal"], fontSize=8, alignment=2, textColor=ris_color)
        except (KeyError, TypeError):
            continue
        rows.append([
            Paragraph(anno, cell_style),
            Paragraph(proventi, num_style),
            Paragraph(oneri, num_style),
            Paragraph(risultato_str, ris_style),
        ])

    tbl = Table(rows, colWidths=[40, 110, 110, 110])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f5f5f5")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#e0e0e0")),
    ]))
    return [_section_heading("Indicatori di bilancio", styles), tbl]


def _build_cariche_section(cariche, styles) -> list:
    if not cariche:
        return []
    cell_style = ParagraphStyle("cell", parent=styles["Normal"], fontSize=8)
    hist_style = ParagraphStyle("hist", parent=styles["Normal"], fontSize=8, textColor=colors.grey)
    header_style = ParagraphStyle("hdr", parent=styles["Normal"], fontSize=8, textColor=colors.grey)

    rows = [[
        Paragraph("Ruolo", header_style),
        Paragraph("Nome", header_style),
        Paragraph("Cognome", header_style),
        Paragraph("Periodo", header_style),
    ]]
    for c in cariche:
        try:
            ruolo = c["ruolo"] or "—"
            nome = c["nome"] or "—"
            cognome = c["cognome"] or "—"
            valid_from = c["valid_from"] or ""
            valid_to = c["valid_to"]
            periodo = f"{valid_from} – {valid_to}" if valid_to else f"dal {valid_from}"
            st = cell_style if valid_to is None else hist_style
        except (KeyError, TypeError):
            continue
        rows.append([
            Paragraph(ruolo, st),
            Paragraph(nome, st),
            Paragraph(cognome, st),
            Paragraph(periodo, st),
        ])

    tbl = Table(rows, colWidths=[90, 90, 90, 100])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f5f5f5")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#e0e0e0")),
    ]))
    return [_section_heading("Persone e cariche", styles), tbl]


def build_ente_pdf(ente_row: sqlite3.Row, *, allegati=None, bilanci=None, cariche=None) -> bytes:
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

    story.extend(_build_allegati_section(allegati or [], styles))
    story.extend(_build_bilanci_section(bilanci or [], styles))
    story.extend(_build_cariche_section(cariche or [], styles))

    doc.build(story)

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
