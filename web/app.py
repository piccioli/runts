import csv
import io
import json
import os
import sqlite3
from typing import Optional

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

DB_PATH = os.environ.get("DB_PATH", "/app/runts.db")
PAGE_SIZE = 20

app = FastAPI()
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")
app.mount("/attachments", StaticFiles(directory=os.environ.get("ATTACHMENTS_DIR", "/app/attachments"), check_dir=False), name="attachments")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))


def _mask_cf(cf: str | None) -> str:
    if not cf or len(cf) < 8:
        return cf or "—"
    return cf[:3] + "•••••" + cf[-5:]


def _human_size(size: int | None) -> str:
    if size is None:
        return "—"
    if size >= 1_048_576:
        return f"{size / 1_048_576:.1f} MB"
    return f"{size // 1024} KB"


def _format_euro(value) -> str:
    if value is None:
        return "—"
    try:
        formatted = f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{formatted} €"
    except (TypeError, ValueError):
        return "—"


templates.env.filters["mask_cf"] = _mask_cf
templates.env.filters["human_size"] = _human_size
templates.env.filters["format_euro"] = _format_euro


def get_db():
    uri = f"file:{DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _db_exists() -> bool:
    return os.path.exists(DB_PATH)


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _tr(request: Request, name: str, context: dict = {}, **kwargs):
    return templates.TemplateResponse(request=request, name=name, context=context, **kwargs)


def _build_filter_clauses(
    q: Optional[str],
    regione: Optional[str],
    sezione_registro: Optional[str],
) -> tuple[list[str], list]:
    """Return (where_clauses, params). Supports comma-separated multi-values for regione/sezione."""
    clauses: list[str] = []
    params: list = []

    if q:
        clauses.append("denominazione LIKE ?")
        params.append(f"%{q}%")

    if regione:
        values = [v.strip() for v in regione.split(",") if v.strip()]
        if len(values) == 1:
            clauses.append("sede_regione = ?")
            params.append(values[0])
        elif values:
            placeholders = ",".join("?" * len(values))
            clauses.append(f"sede_regione IN ({placeholders})")
            params.extend(values)

    if sezione_registro:
        values = [v.strip() for v in sezione_registro.split(",") if v.strip()]
        if len(values) == 1:
            clauses.append("sezione_registro = ?")
            params.append(values[0])
        elif values:
            placeholders = ",".join("?" * len(values))
            clauses.append(f"sezione_registro IN ({placeholders})")
            params.extend(values)

    return clauses, params


@app.get("/", response_class=HTMLResponse)
async def enti_list(
    request: Request,
    q: Optional[str] = None,
    regione: Optional[str] = None,
    sezione_registro: Optional[str] = None,
    page: int = 1,
):
    if not _db_exists():
        return _tr(request, "list.html", {
            "enti": [], "total": 0, "page": 1, "total_pages": 0,
            "q": "", "regione": "", "sezione_registro": "",
            "regioni": [], "sezioni": [],
        })

    conn = get_db()
    try:
        clauses, params = _build_filter_clauses(q, regione, sezione_registro)
        where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""

        total = conn.execute(f"SELECT COUNT(*) FROM enti {where_sql}", params).fetchone()[0]
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = max(1, min(page, total_pages))
        offset = (page - 1) * PAGE_SIZE

        enti = conn.execute(
            f"SELECT id_runts, denominazione, sede_comune, sede_regione, sezione_registro, lat, lon "
            f"FROM enti {where_sql} ORDER BY denominazione LIMIT ? OFFSET ?",
            params + [PAGE_SIZE, offset],
        ).fetchall()

        regioni = [
            r[0] for r in conn.execute(
                "SELECT DISTINCT sede_regione FROM enti WHERE sede_regione IS NOT NULL ORDER BY sede_regione"
            ).fetchall()
        ]
        sezioni = [
            r[0] for r in conn.execute(
                "SELECT DISTINCT sezione_registro FROM enti WHERE sezione_registro IS NOT NULL ORDER BY sezione_registro"
            ).fetchall()
        ]
    finally:
        conn.close()

    return _tr(request, "list.html", {
        "enti": enti,
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "q": q or "",
        "regione": regione or "",
        "sezione_registro": sezione_registro or "",
        "regioni": regioni,
        "sezioni": sezioni,
    })


@app.get("/ente/{id_runts}", response_class=HTMLResponse)
async def ente_detail(request: Request, id_runts: str, back: Optional[str] = None):
    if not _db_exists():
        return _tr(request, "404.html", status_code=404)

    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM enti WHERE id_runts = ?", (id_runts,)).fetchone()
        if row is None:
            return _tr(request, "404.html", status_code=404)

        allegati = conn.execute(
            "SELECT * FROM allegati WHERE id_runts = ? ORDER BY codice_pratica, anno",
            (id_runts,),
        ).fetchall() if _table_exists(conn, "allegati") else []

        bilanci = conn.execute(
            "SELECT * FROM bilanci WHERE id_runts = ? ORDER BY anno DESC",
            (id_runts,),
        ).fetchall() if _table_exists(conn, "bilanci") else []

        cariche = conn.execute(
            "SELECT * FROM cariche_sociali WHERE id_runts = ? "
            "ORDER BY (valid_to IS NULL) DESC, ruolo, cognome",
            (id_runts,),
        ).fetchall() if _table_exists(conn, "cariche_sociali") else []
    finally:
        conn.close()

    fields = {k: row[k] for k in row.keys() if row[k] is not None and k not in ("id_runts", "raw_json", "updated_at")}
    return _tr(request, "detail.html", {
        "ente": row,
        "fields": fields,
        "back": back or "/",
        "lat": row["lat"] if "lat" in row.keys() else None,
        "lon": row["lon"] if "lon" in row.keys() else None,
        "allegati": allegati,
        "bilanci": bilanci,
        "cariche": cariche,
    })


@app.get("/ente/{id_runts}/pdf")
async def ente_pdf(id_runts: str):
    if not _db_exists():
        return Response(status_code=404)

    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM enti WHERE id_runts = ?", (id_runts,)).fetchone()
        if row is None:
            return Response(status_code=404)

        allegati = conn.execute(
            "SELECT * FROM allegati WHERE id_runts = ? ORDER BY codice_pratica, anno",
            (id_runts,),
        ).fetchall() if _table_exists(conn, "allegati") else []

        bilanci = conn.execute(
            "SELECT * FROM bilanci WHERE id_runts = ? ORDER BY anno DESC",
            (id_runts,),
        ).fetchall() if _table_exists(conn, "bilanci") else []

        cariche = conn.execute(
            "SELECT * FROM cariche_sociali WHERE id_runts = ? "
            "ORDER BY (valid_to IS NULL) DESC, ruolo, cognome",
            (id_runts,),
        ).fetchall() if _table_exists(conn, "cariche_sociali") else []
    finally:
        conn.close()

    from .pdf_utils import build_ente_pdf
    pdf_bytes = build_ente_pdf(row, allegati=allegati, bilanci=bilanci, cariche=cariche)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="ente_{id_runts}.pdf"'},
    )


# ---------- API endpoints ----------

_EXPORT_COLUMNS = [
    "id_runts", "denominazione", "codice_fiscale",
    "sede_indirizzo", "sede_civico", "sede_comune", "sede_provincia",
    "sede_regione", "sede_cap", "sezione_registro", "forma_giuridica",
    "natura_giuridica", "data_iscrizione", "pec", "sito_web",
    "url_dettaglio", "lat", "lon",
]


def _fetch_filtered(
    q: Optional[str],
    regione: Optional[str],
    sezione_registro: Optional[str],
    columns: list[str],
):
    """Return rows matching the filters. Raises RuntimeError if DB missing."""
    if not _db_exists():
        return []
    conn = get_db()
    try:
        clauses, params = _build_filter_clauses(q, regione, sezione_registro)
        where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        col_sql = ", ".join(columns)
        return conn.execute(
            f"SELECT {col_sql} FROM enti {where_sql} ORDER BY denominazione", params
        ).fetchall()
    finally:
        conn.close()


@app.get("/api/enti.geojson")
async def enti_geojson(
    q: Optional[str] = None,
    regione: Optional[str] = None,
    sezione_registro: Optional[str] = None,
):
    if not _db_exists():
        return Response(
            content='{"type":"FeatureCollection","features":[]}',
            media_type="application/geo+json",
        )

    conn = get_db()
    try:
        clauses, params = _build_filter_clauses(q, regione, sezione_registro)
        clauses.append("lat IS NOT NULL AND lon IS NOT NULL")
        where_sql = "WHERE " + " AND ".join(clauses)

        rows = conn.execute(
            f"SELECT id_runts, denominazione, sede_comune, sede_regione, sezione_registro, lat, lon "
            f"FROM enti {where_sql} ORDER BY denominazione",
            params,
        ).fetchall()
    finally:
        conn.close()

    features = [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [row["lon"], row["lat"]]},
            "properties": {
                "id_runts":         row["id_runts"],
                "denominazione":    row["denominazione"],
                "sede_comune":      row["sede_comune"],
                "sede_regione":     row["sede_regione"],
                "sezione_registro": row["sezione_registro"],
            },
        }
        for row in rows
    ]

    body = json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False)
    return Response(content=body, media_type="application/geo+json")


@app.get("/api/enti.csv")
async def enti_csv(
    q: Optional[str] = None,
    regione: Optional[str] = None,
    sezione_registro: Optional[str] = None,
):
    rows = _fetch_filtered(q, regione, sezione_registro, _EXPORT_COLUMNS)

    def generate():
        buf = io.StringIO()
        writer = csv.writer(buf, delimiter=";")
        writer.writerow(_EXPORT_COLUMNS)
        yield "﻿"  # UTF-8 BOM
        yield buf.getvalue()
        for row in rows:
            buf = io.StringIO()
            writer = csv.writer(buf, delimiter=";")
            writer.writerow([row[c] for c in _EXPORT_COLUMNS])
            yield buf.getvalue()

    return StreamingResponse(
        generate(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="enti.csv"'},
    )


@app.get("/api/enti.xlsx")
async def enti_xlsx(
    q: Optional[str] = None,
    regione: Optional[str] = None,
    sezione_registro: Optional[str] = None,
):
    import openpyxl
    from openpyxl.styles import Font

    rows = _fetch_filtered(q, regione, sezione_registro, _EXPORT_COLUMNS)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Enti"

    # Header row
    ws.append(_EXPORT_COLUMNS)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    ws.freeze_panes = "A2"

    for row in rows:
        ws.append([row[c] for c in _EXPORT_COLUMNS])

    # Auto-width (approximate)
    for col in ws.columns:
        max_len = max((len(str(cell.value or "")) for cell in col), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 50)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    return Response(
        content=buf.read(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="enti.xlsx"'},
    )
