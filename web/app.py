import csv
import io
import json
import os
import sqlite3
from typing import Optional

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

DB_PATH = os.environ.get("DB_PATH", "/app/runts.db")
PAGE_SIZE = 50


def _read_version() -> str:
    for candidate in (
        "VERSION",
        os.path.join(os.path.dirname(__file__), "..", "VERSION"),
    ):
        try:
            return open(candidate).read().strip()
        except OSError:
            pass
    return ""


APP_VERSION = _read_version()

app = FastAPI()
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")),
    name="static",
)
app.mount(
    "/attachments",
    StaticFiles(
        directory=os.environ.get("ATTACHMENTS_DIR", "/app/attachments"), check_dir=False
    ),
    name="attachments",
)
templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "templates")
)


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
        formatted = (
            f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
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
    return (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        is not None
    )


def _tr(request: Request, name: str, context: dict = {}, **kwargs):
    return templates.TemplateResponse(
        request=request,
        name=name,
        context={"app_version": APP_VERSION, **context},
        **kwargs,
    )


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


def _build_cai_filter_clauses(
    q: Optional[str],
    regione: Optional[str],
) -> tuple[list[str], list]:
    """Return (where_clauses, params) for sezioni_cai queries (alias prefix 's.')."""
    clauses: list[str] = []
    params: list = []

    if q:
        clauses.append("s.cai_denominazione LIKE ?")
        params.append(f"%{q}%")

    if regione:
        values = [v.strip() for v in regione.split(",") if v.strip()]
        if len(values) == 1:
            clauses.append("s.cai_regione = ?")
            params.append(values[0])
        elif values:
            placeholders = ",".join("?" * len(values))
            clauses.append(f"s.cai_regione IN ({placeholders})")
            params.extend(values)

    return clauses, params


@app.get("/", response_class=HTMLResponse)
async def enti_list(
    request: Request,
    q: Optional[str] = None,
    regione: Optional[str] = None,
    sezione_registro: Optional[str] = None,
    ets: Optional[int] = None,
    issues: Optional[int] = None,
    page: int = 1,
):
    if not _db_exists():
        return _tr(
            request,
            "list.html",
            {
                "enti": [],
                "total": 0,
                "page": 1,
                "total_pages": 0,
                "q": "",
                "regione": "",
                "regioni": [],
                "ets": 0,
                "issues": 0,
                "active_page": "sezioni",
            },
        )

    conn = get_db()
    try:
        if not _table_exists(conn, "sezioni_cai"):
            return _tr(
                request,
                "list.html",
                {
                    "enti": [],
                    "total": 0,
                    "page": 1,
                    "total_pages": 0,
                    "q": q or "",
                    "regione": regione or "",
                    "regioni": [],
                    "ets": 0,
                    "issues": 0,
                    "active_page": "sezioni",
                },
            )

        clauses, params = _build_cai_filter_clauses(q, regione)
        if ets:
            clauses.append(
                "s.cai_codice_fiscale IS NOT NULL AND e.id_runts IS NOT NULL"
            )
        if issues:
            clauses.append(
                "(s.cai_match_note = 'fuzzy_nome'"
                " OR s.cai_match_note LIKE 'cf_mismatch%'"
                " OR e.lat IS NULL OR e.lon IS NULL"
                " OR (e.id_runts IS NOT NULL AND NOT EXISTS (SELECT 1 FROM bilanci b WHERE b.id_runts = e.id_runts))"
                " OR (e.id_runts IS NOT NULL AND NOT EXISTS (SELECT 1 FROM allegati a WHERE a.id_runts = e.id_runts)))"
            )
        where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""

        total = conn.execute(
            f"SELECT COUNT(*) FROM sezioni_cai s "
            f"LEFT JOIN enti e ON s.cai_codice_fiscale = e.codice_fiscale {where_sql}",
            params,
        ).fetchone()[0]
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = max(1, min(page, total_pages))
        offset = (page - 1) * PAGE_SIZE

        enti = conn.execute(
            f"SELECT s.codice_cai, s.cai_denominazione, s.cai_regione, "
            f"json_extract(s.cai_indirizzo_sede, '$.city') AS comune, e.id_runts, s.cai_match_note "
            f"FROM sezioni_cai s "
            f"LEFT JOIN enti e ON s.cai_codice_fiscale = e.codice_fiscale "
            f"{where_sql} ORDER BY s.cai_denominazione LIMIT ? OFFSET ?",
            params + [PAGE_SIZE, offset],
        ).fetchall()

        regioni = [
            r[0]
            for r in conn.execute(
                "SELECT DISTINCT cai_regione FROM sezioni_cai WHERE cai_regione IS NOT NULL ORDER BY cai_regione"
            ).fetchall()
        ]
    finally:
        conn.close()

    return _tr(
        request,
        "list.html",
        {
            "enti": enti,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "q": q or "",
            "regione": regione or "",
            "regioni": regioni,
            "ets": 1 if ets else 0,
            "issues": 1 if issues else 0,
            "active_page": "sezioni",
        },
    )


_VALID_TABS = {"principale", "bilanci", "allegati", "mappa", "sottosezioni"}


@app.get("/ets", response_class=HTMLResponse)
async def ets_list(request: Request):
    if not _db_exists():
        return _tr(
            request,
            "ets.html",
            {
                "enti": [],
                "total": 0,
                "agganciati": 0,
                "non_agganciati": 0,
                "active_page": "ets",
            },
        )

    conn = get_db()
    try:
        if not _table_exists(conn, "enti") or not _table_exists(conn, "sezioni_cai"):
            return _tr(
                request,
                "ets.html",
                {
                    "enti": [],
                    "total": 0,
                    "agganciati": 0,
                    "non_agganciati": 0,
                    "active_page": "ets",
                },
            )

        enti = conn.execute(
            "SELECT e.id_runts, e.denominazione, e.sede_comune, e.sede_regione, "
            "e.codice_fiscale, s.codice_cai, s.cai_match_note "
            "FROM enti e "
            "LEFT JOIN sezioni_cai s ON e.codice_fiscale = s.cai_codice_fiscale "
            "ORDER BY (CASE WHEN s.codice_cai IS NULL THEN 0 ELSE 1 END), e.denominazione"
        ).fetchall()

        total = len(enti)
        agganciati = sum(1 for r in enti if r["codice_cai"] is not None)
        non_agganciati = total - agganciati
    finally:
        conn.close()

    return _tr(
        request,
        "ets.html",
        {
            "enti": enti,
            "total": total,
            "agganciati": agganciati,
            "non_agganciati": non_agganciati,
            "active_page": "ets",
        },
    )


@app.get("/gruppi-regionali", response_class=HTMLResponse)
async def gruppi_regionali(request: Request):
    empty_ctx = {
        "gruppi": [],
        "total": 0,
        "agganciati": 0,
        "non_agganciati": 0,
        "active_page": "gruppi-regionali",
    }
    if not _db_exists():
        return _tr(request, "gruppi_regionali.html", empty_ctx)

    conn = get_db()
    try:
        if not _table_exists(conn, "gruppi_regionali_cai"):
            return _tr(request, "gruppi_regionali.html", empty_ctx)

        gruppi = conn.execute(
            "SELECT g.gr_codice, g.gr_nome, "
            "json_extract(g.gr_indirizzo_sede, '$.province') AS provincia, "
            "g.gr_email, g.gr_telefono, g.gr_sito_web, g.gr_id_runts, "
            "e.denominazione AS ente_denominazione "
            "FROM gruppi_regionali_cai g "
            "LEFT JOIN enti e ON g.gr_id_runts = e.id_runts "
            "ORDER BY g.gr_nome"
        ).fetchall()

        total = len(gruppi)
        agganciati = sum(1 for r in gruppi if r["gr_id_runts"] is not None)
        non_agganciati = total - agganciati
    finally:
        conn.close()

    return _tr(
        request,
        "gruppi_regionali.html",
        {
            "gruppi": gruppi,
            "total": total,
            "agganciati": agganciati,
            "non_agganciati": non_agganciati,
            "active_page": "gruppi-regionali",
        },
    )


@app.get("/gr/{gr_codice}", response_class=HTMLResponse)
async def gr_detail(request: Request, gr_codice: str, back: Optional[str] = None):
    import json as _json

    if not _db_exists():
        return _tr(request, "404.html", status_code=404)

    conn = get_db()
    try:
        gr_row = (
            conn.execute(
                "SELECT * FROM gruppi_regionali_cai WHERE gr_codice = ?", (gr_codice,)
            ).fetchone()
            if _table_exists(conn, "gruppi_regionali_cai")
            else None
        )
        if gr_row is None:
            return _tr(request, "404.html", status_code=404)

        ente_row = (
            conn.execute(
                "SELECT * FROM enti WHERE id_runts = ?", (gr_row["gr_id_runts"],)
            ).fetchone()
            if gr_row["gr_id_runts"] and _table_exists(conn, "enti")
            else None
        )

        allegati = (
            conn.execute(
                "SELECT * FROM allegati WHERE id_runts = ? ORDER BY codice_pratica, anno",
                (gr_row["gr_id_runts"],),
            ).fetchall()
            if gr_row["gr_id_runts"] and _table_exists(conn, "allegati")
            else []
        )

        bilanci = (
            conn.execute(
                "SELECT * FROM bilanci WHERE id_runts = ? ORDER BY anno DESC",
                (gr_row["gr_id_runts"],),
            ).fetchall()
            if gr_row["gr_id_runts"] and _table_exists(conn, "bilanci")
            else []
        )

        cariche = (
            conn.execute(
                "SELECT * FROM cariche_sociali WHERE id_runts = ? "
                "ORDER BY (valid_to IS NULL) DESC, ruolo, cognome",
                (gr_row["gr_id_runts"],),
            ).fetchall()
            if gr_row["gr_id_runts"] and _table_exists(conn, "cariche_sociali")
            else []
        )
    finally:
        conn.close()

    gr = dict(gr_row)
    raw_addr = gr.get("gr_indirizzo_sede")
    gr["gr_indirizzo_sede_parsed"] = _json.loads(raw_addr) if raw_addr else None

    tab = request.query_params.get("tab", "gr")
    valid = {"gr", "ets", "bilanci", "allegati", "mappa"}
    active_tab = tab if tab in valid else "gr"
    if active_tab == "ets" and not ente_row:
        active_tab = "gr"

    lat = ente_row["lat"] if ente_row and ente_row["lat"] else None
    lon = ente_row["lon"] if ente_row and ente_row["lon"] else None

    fields = {}
    if ente_row:
        fields = {
            k: ente_row[k]
            for k in ente_row.keys()
            if ente_row[k] is not None
            and k not in ("id_runts", "raw_json", "updated_at")
        }

    return _tr(
        request,
        "gr_detail.html",
        {
            "gr": gr,
            "ente": ente_row,
            "fields": fields,
            "back": back or "/gruppi-regionali",
            "allegati": allegati,
            "bilanci": bilanci,
            "cariche": cariche,
            "lat": lat,
            "lon": lon,
            "active_tab": active_tab,
            "active_page": "gruppi-regionali",
        },
    )


@app.get("/stats", response_class=HTMLResponse)
async def stats(request: Request):
    kpi: dict = {
        "sezioni_totali": 0,
        "soci_totali": 0,
        "enti_ets": 0,
        "ets_agganciati": 0,
        "gr_totali": 21,
        "gr_agganciati": 0,
        "bilanci_analizzati": 0,
        "copertura_bilanci_pct": 0.0,
    }
    soci_per_regione: list = []
    proventi_2024_per_regione: list = []
    top10_soci: list = []
    top10_sottosezioni: list = []
    allegati_per_tipo: list = []
    bilanci_per_ente: list = []
    copertura_ets: dict = {
        "totale": 226,
        "agganciati": 0,
        "con_bilanci": 0,
        "con_allegati": 0,
        "con_coordinate": 0,
    }
    qualita_dati: list = []

    if _db_exists():
        conn = get_db()
        try:
            has_sezioni = _table_exists(conn, "sezioni_cai")
            has_enti = _table_exists(conn, "enti")
            has_bilanci = _table_exists(conn, "bilanci")
            has_allegati = _table_exists(conn, "allegati")
            has_gr = _table_exists(conn, "gruppi_regionali_cai")
            has_sottosezioni = _table_exists(conn, "sottosezioni_cai")

            if has_sezioni:
                kpi["sezioni_totali"] = conn.execute(
                    "SELECT COUNT(*) FROM sezioni_cai"
                ).fetchone()[0]
                kpi["soci_totali"] = conn.execute(
                    "SELECT COALESCE(SUM(cai_soci_ultimo_anno), 0) FROM sezioni_cai"
                ).fetchone()[0]
                rows = conn.execute(
                    "SELECT cai_regione, COUNT(*) n_sezioni, SUM(cai_soci_ultimo_anno) soci "
                    "FROM sezioni_cai WHERE cai_regione != '' "
                    "GROUP BY cai_regione ORDER BY soci DESC"
                ).fetchall()
                soci_per_regione = [
                    {"cai_regione": r[0], "n_sezioni": r[1], "soci": r[2] or 0}
                    for r in rows
                ]
                rows = conn.execute(
                    "SELECT codice_cai, cai_denominazione, cai_soci_ultimo_anno "
                    "FROM sezioni_cai WHERE cai_soci_ultimo_anno IS NOT NULL "
                    "ORDER BY cai_soci_ultimo_anno DESC LIMIT 10"
                ).fetchall()
                top10_soci = [
                    {
                        "codice_cai": r[0],
                        "cai_denominazione": r[1],
                        "cai_soci_ultimo_anno": r[2],
                    }
                    for r in rows
                ]

            if has_enti:
                kpi["enti_ets"] = conn.execute("SELECT COUNT(*) FROM enti").fetchone()[
                    0
                ]
                copertura_ets["totale"] = kpi["enti_ets"] or 226
                copertura_ets["con_coordinate"] = conn.execute(
                    "SELECT COUNT(*) FROM enti WHERE lat IS NOT NULL"
                ).fetchone()[0]

            if has_enti and has_sezioni:
                kpi["ets_agganciati"] = conn.execute(
                    "SELECT COUNT(*) FROM enti e "
                    "JOIN sezioni_cai s ON e.codice_fiscale = s.cai_codice_fiscale"
                ).fetchone()[0]
                copertura_ets["agganciati"] = kpi["ets_agganciati"]

            if has_gr:
                kpi["gr_totali"] = conn.execute(
                    "SELECT COUNT(*) FROM gruppi_regionali_cai"
                ).fetchone()[0]
                kpi["gr_agganciati"] = conn.execute(
                    "SELECT COUNT(*) FROM gruppi_regionali_cai WHERE gr_id_runts IS NOT NULL"
                ).fetchone()[0]

            if has_bilanci:
                kpi["bilanci_analizzati"] = conn.execute(
                    "SELECT COUNT(*) FROM bilanci"
                ).fetchone()[0]
                enti_con_bilanci_cnt = conn.execute(
                    "SELECT COUNT(DISTINCT id_runts) FROM bilanci"
                ).fetchone()[0]
                if kpi["enti_ets"] > 0:
                    kpi["copertura_bilanci_pct"] = round(
                        enti_con_bilanci_cnt / kpi["enti_ets"] * 100, 1
                    )
                copertura_ets["con_bilanci"] = enti_con_bilanci_cnt

            if has_allegati:
                copertura_ets["con_allegati"] = conn.execute(
                    "SELECT COUNT(DISTINCT id_runts) FROM allegati"
                ).fetchone()[0]
                rows = conn.execute(
                    "SELECT tipo, COUNT(*) n FROM allegati GROUP BY tipo ORDER BY n DESC"
                ).fetchall()
                allegati_per_tipo = [{"tipo": r[0], "n": r[1]} for r in rows]

            if has_bilanci and has_enti:
                rows = conn.execute(
                    "SELECT e.sede_regione, SUM(b.totale_proventi) totale "
                    "FROM bilanci b JOIN enti e ON b.id_runts = e.id_runts "
                    "WHERE b.anno = 2024 AND b.totale_proventi IS NOT NULL "
                    "GROUP BY e.sede_regione ORDER BY totale DESC"
                ).fetchall()
                proventi_2024_per_regione = [
                    {"sede_regione": r[0], "totale_proventi": r[1]} for r in rows
                ]
                rows = conn.execute(
                    "SELECT b.id_runts, e.denominazione, b.anno, b.totale_proventi "
                    "FROM bilanci b JOIN enti e ON b.id_runts = e.id_runts "
                    "WHERE b.totale_proventi IS NOT NULL ORDER BY b.id_runts, b.anno"
                ).fetchall()
                _ente_map: dict = {}
                for r in rows:
                    if r[0] not in _ente_map:
                        _ente_map[r[0]] = {
                            "id_runts": r[0],
                            "denominazione": r[1],
                            "punti": [],
                        }
                    _ente_map[r[0]]["punti"].append(
                        {"anno": r[2], "totale_proventi": r[3]}
                    )
                bilanci_per_ente = [
                    v for v in _ente_map.values() if len(v["punti"]) >= 2
                ]

            if has_sottosezioni and has_sezioni:
                rows = conn.execute(
                    "SELECT sc.codice_cai, sc.cai_denominazione, COUNT(*) n "
                    "FROM sottosezioni_cai ss "
                    "JOIN sezioni_cai sc ON ss.cai_sezione_codice = sc.codice_cai "
                    "GROUP BY ss.cai_sezione_codice ORDER BY n DESC LIMIT 10"
                ).fetchall()
                top10_sottosezioni = [
                    {"codice_cai": r[0], "cai_denominazione": r[1], "n": r[2]}
                    for r in rows
                ]

            # qualita_dati: fixed order of 4 items
            n_no_cf = (
                conn.execute(
                    "SELECT COUNT(*) FROM sezioni_cai WHERE cai_codice_fiscale IS NULL"
                ).fetchone()[0]
                if has_sezioni
                else 0
            )
            n_ets_non_agg = (
                conn.execute(
                    "SELECT COUNT(*) FROM enti e "
                    "LEFT JOIN sezioni_cai s ON e.codice_fiscale = s.cai_codice_fiscale "
                    "WHERE s.codice_cai IS NULL"
                ).fetchone()[0]
                if (has_enti and has_sezioni)
                else 0
            )
            n_no_soci = (
                conn.execute(
                    "SELECT COUNT(*) FROM sezioni_cai "
                    "WHERE cai_soci_ultimo_anno IS NULL OR cai_soci_ultimo_anno = 0"
                ).fetchone()[0]
                if has_sezioni
                else 0
            )
            n_gr_non_agg = (
                conn.execute(
                    "SELECT COUNT(*) FROM gruppi_regionali_cai WHERE gr_id_runts IS NULL"
                ).fetchone()[0]
                if has_gr
                else kpi["gr_totali"]
            )
            qualita_dati = [
                {
                    "label": "Sezioni senza CF nel registro CAI",
                    "n": n_no_cf,
                    "url": "/?issues=1",
                },
                {
                    "label": "Enti ETS non agganciati a sezione CAI",
                    "n": n_ets_non_agg,
                    "url": "/ets",
                },
                {
                    "label": "Sezioni CAI senza dati soci",
                    "n": n_no_soci,
                    "url": "/?issues=1",
                },
                {
                    "label": "Gruppi Regionali non agganciati RUNTS",
                    "n": n_gr_non_agg,
                    "url": "/gruppi-regionali",
                },
            ]
        finally:
            conn.close()

    return _tr(
        request,
        "stats.html",
        {
            "kpi": kpi,
            "soci_per_regione": soci_per_regione,
            "proventi_2024_per_regione": proventi_2024_per_regione,
            "top10_soci": top10_soci,
            "top10_sottosezioni": top10_sottosezioni,
            "allegati_per_tipo": allegati_per_tipo,
            "bilanci_per_ente": bilanci_per_ente,
            "copertura_ets": copertura_ets,
            "qualita_dati": qualita_dati,
            "active_page": "stats",
        },
    )


@app.get("/ente/{id_runts}", response_class=HTMLResponse)
async def ente_redirect(request: Request, id_runts: str):
    """Redirect legacy /ente/<id_runts> to unified /sezione/<id>."""
    from fastapi.responses import RedirectResponse

    if not _db_exists():
        return _tr(request, "404.html", status_code=404)
    conn = get_db()
    try:
        sc = (
            conn.execute(
                "SELECT codice_cai FROM sezioni_cai s "
                "JOIN enti e ON e.codice_fiscale = s.cai_codice_fiscale "
                "WHERE e.id_runts = ?",
                (id_runts,),
            ).fetchone()
            if _table_exists(conn, "sezioni_cai")
            else None
        )
    finally:
        conn.close()
    target_id = sc["codice_cai"] if sc else id_runts
    qs = str(request.url.query)
    dest = f"/sezione/{target_id}" + (f"?{qs}" if qs else "")
    return RedirectResponse(dest, status_code=301)


@app.get("/sezione/{sezione_id}", response_class=HTMLResponse)
async def sezione_detail(request: Request, sezione_id: str, back: Optional[str] = None):
    """Unified section detail: accepts either codice_cai or id_runts."""
    import json as _json

    if not _db_exists():
        return _tr(request, "404.html", status_code=404)

    tab = request.query_params.get("tab", "cai")
    conn = get_db()
    try:
        # 1. Try sezioni_cai by codice_cai
        sc_row = (
            conn.execute(
                "SELECT * FROM sezioni_cai WHERE codice_cai = ?", (sezione_id,)
            ).fetchone()
            if _table_exists(conn, "sezioni_cai")
            else None
        )

        # 2. Fallback: try enti by id_runts, then join sezioni_cai
        ente_row = None
        if sc_row is None:
            ente_row = (
                conn.execute(
                    "SELECT * FROM enti WHERE id_runts = ?", (sezione_id,)
                ).fetchone()
                if _table_exists(conn, "enti")
                else None
            )
            if ente_row is None:
                return _tr(request, "404.html", status_code=404)
            sc_row = (
                conn.execute(
                    "SELECT * FROM sezioni_cai WHERE cai_codice_fiscale = ?",
                    (ente_row["codice_fiscale"],),
                ).fetchone()
                if _table_exists(conn, "sezioni_cai") and ente_row["codice_fiscale"]
                else None
            )
        else:
            # Found by codice_cai — also try to load the RUNTS ente
            ente_row = (
                conn.execute(
                    "SELECT * FROM enti WHERE codice_fiscale = ?",
                    (sc_row["cai_codice_fiscale"],),
                ).fetchone()
                if sc_row["cai_codice_fiscale"] and _table_exists(conn, "enti")
                else None
            )

        id_runts = ente_row["id_runts"] if ente_row else None
        codice_cai = sc_row["codice_cai"] if sc_row else None

        allegati = (
            conn.execute(
                "SELECT * FROM allegati WHERE id_runts = ? ORDER BY codice_pratica, anno",
                (id_runts,),
            ).fetchall()
            if id_runts and _table_exists(conn, "allegati")
            else []
        )

        bilanci = (
            conn.execute(
                "SELECT * FROM bilanci WHERE id_runts = ? ORDER BY anno DESC",
                (id_runts,),
            ).fetchall()
            if id_runts and _table_exists(conn, "bilanci")
            else []
        )

        cariche = (
            conn.execute(
                "SELECT * FROM cariche_sociali WHERE id_runts = ? "
                "ORDER BY (valid_to IS NULL) DESC, ruolo, cognome",
                (id_runts,),
            ).fetchall()
            if id_runts and _table_exists(conn, "cariche_sociali")
            else []
        )

        sottosezioni = (
            conn.execute(
                "SELECT ss.*, json_extract(ss.cai_indirizzo_sede, '$.city') AS cai_comune "
                "FROM sottosezioni_cai ss WHERE ss.cai_sezione_codice = ? ORDER BY ss.cai_nome",
                (codice_cai,),
            ).fetchall()
            if codice_cai and _table_exists(conn, "sottosezioni_cai")
            else []
        )
    finally:
        conn.close()

    sezione_cai = None
    if sc_row:
        sezione_cai = dict(sc_row)
        raw_addr = sezione_cai.get("cai_indirizzo_sede")
        sezione_cai["cai_indirizzo_sede_parsed"] = (
            _json.loads(raw_addr) if raw_addr else None
        )

    valid_tabs = {"cai", "principale", "bilanci", "allegati", "mappa", "sottosezioni"}
    active_tab = tab if tab in valid_tabs else ("cai" if sezione_cai else "principale")
    if active_tab == "cai" and not sezione_cai:
        active_tab = "principale"
    if active_tab == "principale" and not ente_row:
        active_tab = "cai"

    fields = {}
    if ente_row:
        fields = {
            k: ente_row[k]
            for k in ente_row.keys()
            if ente_row[k] is not None
            and k not in ("id_runts", "raw_json", "updated_at")
        }

    return _tr(
        request,
        "sezione.html",
        {
            "ente": ente_row,
            "fields": fields,
            "sezione_cai": sezione_cai,
            "sezione_id": sezione_id,
            "back": back or "/",
            "lat": ente_row["lat"]
            if ente_row and "lat" in ente_row.keys()
            else (sezione_cai.get("cai_lat") if sezione_cai else None),
            "lon": ente_row["lon"]
            if ente_row and "lon" in ente_row.keys()
            else (sezione_cai.get("cai_lon") if sezione_cai else None),
            "allegati": allegati,
            "bilanci": bilanci,
            "cariche": cariche,
            "sottosezioni": sottosezioni,
            "active_tab": active_tab,
            "active_page": "sezioni",
        },
    )


@app.get("/ente/{id_runts}/pdf")
async def ente_pdf(id_runts: str):
    if not _db_exists():
        return Response(status_code=404)

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM enti WHERE id_runts = ?", (id_runts,)
        ).fetchone()
        if row is None:
            return Response(status_code=404)

        allegati = (
            conn.execute(
                "SELECT * FROM allegati WHERE id_runts = ? ORDER BY codice_pratica, anno",
                (id_runts,),
            ).fetchall()
            if _table_exists(conn, "allegati")
            else []
        )

        bilanci = (
            conn.execute(
                "SELECT * FROM bilanci WHERE id_runts = ? ORDER BY anno DESC",
                (id_runts,),
            ).fetchall()
            if _table_exists(conn, "bilanci")
            else []
        )

        cariche = (
            conn.execute(
                "SELECT * FROM cariche_sociali WHERE id_runts = ? "
                "ORDER BY (valid_to IS NULL) DESC, ruolo, cognome",
                (id_runts,),
            ).fetchall()
            if _table_exists(conn, "cariche_sociali")
            else []
        )
    finally:
        conn.close()

    from .pdf_utils import build_ente_pdf

    pdf_bytes = build_ente_pdf(row, allegati=allegati, bilanci=bilanci, cariche=cariche)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="ente_{id_runts}.pdf"'},
    )


# ---------- Health endpoint ----------


@app.get("/health")
async def health():
    if not _db_exists():
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": "DB file not found"},
        )
    try:
        conn = get_db()
        try:
            n = conn.execute("SELECT COUNT(*) FROM enti").fetchone()[0]
        finally:
            conn.close()
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": str(exc)},
        )
    if n == 0:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": "enti table is empty"},
        )
    return JSONResponse(status_code=200, content={"status": "ok", "enti": n})


# ---------- API endpoints ----------

_EXPORT_COLUMNS = [
    "id_runts",
    "denominazione",
    "codice_fiscale",
    "sede_indirizzo",
    "sede_civico",
    "sede_comune",
    "sede_provincia",
    "sede_regione",
    "sede_cap",
    "sezione_registro",
    "forma_giuridica",
    "natura_giuridica",
    "data_iscrizione",
    "pec",
    "sito_web",
    "url_dettaglio",
    "lat",
    "lon",
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
                "id_runts": row["id_runts"],
                "denominazione": row["denominazione"],
                "sede_comune": row["sede_comune"],
                "sede_regione": row["sede_regione"],
                "sezione_registro": row["sezione_registro"],
            },
        }
        for row in rows
    ]

    body = json.dumps(
        {"type": "FeatureCollection", "features": features}, ensure_ascii=False
    )
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
