import os
import sqlite3
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

DB_PATH = os.environ.get("DB_PATH", "/app/runts.db")
PAGE_SIZE = 20

app = FastAPI()
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))


def get_db():
    uri = f"file:{DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _db_exists() -> bool:
    return os.path.exists(DB_PATH)


def _tr(request: Request, name: str, context: dict = {}, **kwargs):
    return templates.TemplateResponse(request=request, name=name, context=context, **kwargs)


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
        where_clauses = []
        params: list = []

        if q:
            where_clauses.append("denominazione LIKE ?")
            params.append(f"%{q}%")
        if regione:
            where_clauses.append("sede_regione = ?")
            params.append(regione)
        if sezione_registro:
            where_clauses.append("sezione_registro = ?")
            params.append(sezione_registro)

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

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
    finally:
        conn.close()

    if row is None:
        return _tr(request, "404.html", status_code=404)

    fields = {k: row[k] for k in row.keys() if row[k] is not None and k not in ("id_runts", "raw_json", "updated_at")}
    return _tr(request, "detail.html", {
        "ente": row,
        "fields": fields,
        "back": back or "/",
        "lat": row["lat"] if "lat" in row.keys() else None,
        "lon": row["lon"] if "lon" in row.keys() else None,
    })
