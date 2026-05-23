import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS enti (
    id_runts          TEXT PRIMARY KEY,
    codice_fiscale    TEXT UNIQUE,
    denominazione     TEXT,
    forma_giuridica   TEXT,
    natura_giuridica  TEXT,
    sede_stato        TEXT,
    sede_indirizzo    TEXT,
    sede_civico       TEXT,
    sede_comune       TEXT,
    sede_provincia    TEXT,
    sede_regione      TEXT,
    sede_cap          TEXT,
    data_iscrizione   TEXT,
    sezione_registro  TEXT,
    settori_attivita  TEXT,
    rappresentante_legale TEXT,
    sito_web          TEXT,
    pec               TEXT,
    url_dettaglio     TEXT,
    raw_json          TEXT,
    updated_at        TEXT NOT NULL
);
"""

_MIGRATIONS = [
    "ALTER TABLE enti ADD COLUMN sede_stato TEXT",
    "ALTER TABLE enti ADD COLUMN sede_civico TEXT",
]


def init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    for migration in _MIGRATIONS:
        try:
            conn.execute(migration)
        except sqlite3.OperationalError:
            pass  # column already exists
    conn.commit()
    return conn


def upsert_ente(conn: sqlite3.Connection, data: dict) -> str:
    """Insert or replace an entity. Returns 'inserted' or 'updated'."""
    data = {k: v for k, v in data.items()}
    data["updated_at"] = datetime.now(timezone.utc).isoformat()

    if "raw_json" not in data:
        data["raw_json"] = json.dumps(data, ensure_ascii=False)

    id_runts = data.get("id_runts") or data.get("codice_fiscale")
    if not id_runts:
        raise ValueError("Record senza id_runts né codice_fiscale, impossibile fare upsert")

    existing = conn.execute(
        "SELECT 1 FROM enti WHERE id_runts = ?", (id_runts,)
    ).fetchone()
    action = "updated" if existing else "inserted"

    columns = [
        "id_runts", "codice_fiscale", "denominazione", "forma_giuridica",
        "natura_giuridica", "sede_stato", "sede_indirizzo", "sede_civico",
        "sede_comune", "sede_provincia", "sede_regione", "sede_cap",
        "data_iscrizione", "sezione_registro", "settori_attivita",
        "rappresentante_legale", "sito_web", "pec",
        "url_dettaglio", "raw_json", "updated_at",
    ]
    row = {col: data.get(col) for col in columns}
    if not row["id_runts"]:
        row["id_runts"] = id_runts

    conn.execute(
        f"INSERT OR REPLACE INTO enti ({', '.join(columns)}) "
        f"VALUES ({', '.join(':' + c for c in columns)})",
        row,
    )
    conn.commit()
    return action


def get_stats(conn: sqlite3.Connection) -> dict:
    total = conn.execute("SELECT COUNT(*) FROM enti").fetchone()[0]
    return {"total": total}
