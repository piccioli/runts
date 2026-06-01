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
    lat               REAL,
    lon               REAL,
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

CREATE INDEX IF NOT EXISTS idx_enti_sede_regione ON enti(sede_regione);
CREATE INDEX IF NOT EXISTS idx_enti_sezione_registro ON enti(sezione_registro);

CREATE TABLE IF NOT EXISTS geocoding_cache (
    cache_key TEXT PRIMARY KEY,
    lat       REAL NOT NULL,
    lon       REAL NOT NULL,
    source    TEXT NOT NULL,
    ts        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS allegati (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    id_runts        TEXT NOT NULL REFERENCES enti(id_runts),
    documento       TEXT NOT NULL,
    codice_pratica  TEXT NOT NULL,
    tipo            TEXT NOT NULL,
    anno            INTEGER,
    filename        TEXT,
    path            TEXT,
    mime            TEXT,
    size            INTEGER,
    hash_sha256     TEXT,
    url_originale   TEXT,
    skip_reason     TEXT,
    downloaded_at   TEXT NOT NULL,
    UNIQUE (id_runts, hash_sha256)
);

CREATE TABLE IF NOT EXISTS bilanci (
    id                                  INTEGER PRIMARY KEY AUTOINCREMENT,
    id_runts                            TEXT NOT NULL REFERENCES enti(id_runts),
    anno                                INTEGER NOT NULL,
    oneri_a_interesse_generale          REAL,
    oneri_b_attivita_diverse            REAL,
    oneri_c_raccolta_fondi              REAL,
    oneri_d_finanziarie_patrimoniali    REAL,
    oneri_e_supporto_generale           REAL,
    totale_oneri                        REAL,
    proventi_a_interesse_generale       REAL,
    proventi_b_attivita_diverse         REAL,
    proventi_c_raccolta_fondi           REAL,
    proventi_d_finanziarie_patrimoniali REAL,
    proventi_e_supporto_generale        REAL,
    totale_proventi                     REAL,
    risultato_ante_imposte              REAL,
    imposte                             REAL,
    risultato_esercizio                 REAL,
    raw_text                            TEXT,
    allegato_id                         INTEGER REFERENCES allegati(id),
    analyzed_at                         TEXT NOT NULL,
    UNIQUE (id_runts, anno)
);

CREATE TABLE IF NOT EXISTS cariche_sociali (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    id_runts        TEXT NOT NULL REFERENCES enti(id_runts),
    ruolo           TEXT NOT NULL,
    nome            TEXT,
    cognome         TEXT,
    codice_fiscale  TEXT,
    valid_from      TEXT,
    valid_to        TEXT,
    updated_at      TEXT NOT NULL,
    UNIQUE (id_runts, codice_fiscale, ruolo, valid_from)
);

CREATE INDEX IF NOT EXISTS idx_allegati_id_runts ON allegati(id_runts);
CREATE INDEX IF NOT EXISTS idx_allegati_tipo ON allegati(tipo);
CREATE INDEX IF NOT EXISTS idx_allegati_codice_pratica ON allegati(codice_pratica);
CREATE INDEX IF NOT EXISTS idx_bilanci_id_runts ON bilanci(id_runts);
CREATE INDEX IF NOT EXISTS idx_cariche_id_runts ON cariche_sociali(id_runts);
CREATE INDEX IF NOT EXISTS idx_cariche_attive ON cariche_sociali(id_runts, valid_to);

CREATE TABLE IF NOT EXISTS sezioni_cai (
    codice_cai            TEXT PRIMARY KEY,
    cai_denominazione     TEXT NOT NULL,
    cai_codice_fiscale    TEXT,
    cai_partita_iva       TEXT,
    cai_email             TEXT,
    cai_pec               TEXT,
    cai_telefono_sede     TEXT,
    cai_telefono          TEXT,
    cai_fax               TEXT,
    cai_indirizzo_sede    TEXT,
    cai_indirizzo_postale TEXT,
    cai_sito_web          TEXT,
    cai_orari             TEXT,
    cai_avvisi            TEXT,
    cai_anno_fondazione   INTEGER,
    cai_soci_ultimo_anno  INTEGER,
    cai_lat               REAL,
    cai_lon               REAL,
    cai_regione           TEXT NOT NULL,
    cai_scraped_at        TEXT
);

CREATE INDEX IF NOT EXISTS idx_sezioni_cai_cf ON sezioni_cai(cai_codice_fiscale);
CREATE INDEX IF NOT EXISTS idx_sezioni_cai_regione ON sezioni_cai(cai_regione);

CREATE TABLE IF NOT EXISTS sottosezioni_cai (
    cai_codice          TEXT PRIMARY KEY,
    cai_sezione_codice  TEXT NOT NULL REFERENCES sezioni_cai(codice_cai),
    cai_nome            TEXT NOT NULL,
    cai_email           TEXT,
    cai_telefono_sede   TEXT,
    cai_telefono        TEXT,
    cai_indirizzo_sede  TEXT,
    cai_sito_web        TEXT,
    cai_orari           TEXT,
    cai_avvisi          TEXT,
    cai_anno_fondazione INTEGER,
    cai_soci            INTEGER,
    cai_lat             REAL,
    cai_lon             REAL,
    cai_scraped_at      TEXT
);

CREATE INDEX IF NOT EXISTS idx_sottosezioni_cai_sezione ON sottosezioni_cai(cai_sezione_codice);
"""

_MIGRATIONS = [
    "ALTER TABLE enti ADD COLUMN sede_stato TEXT",
    "ALTER TABLE enti ADD COLUMN sede_civico TEXT",
    "ALTER TABLE enti ADD COLUMN lat REAL",
    "ALTER TABLE enti ADD COLUMN lon REAL",
    "CREATE INDEX IF NOT EXISTS idx_enti_sede_regione ON enti(sede_regione)",
    "CREATE INDEX IF NOT EXISTS idx_enti_sezione_registro ON enti(sezione_registro)",
    """CREATE TABLE IF NOT EXISTS geocoding_cache (
        cache_key TEXT PRIMARY KEY,
        lat       REAL NOT NULL,
        lon       REAL NOT NULL,
        source    TEXT NOT NULL,
        ts        TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS allegati (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        id_runts        TEXT NOT NULL REFERENCES enti(id_runts),
        documento       TEXT NOT NULL,
        codice_pratica  TEXT NOT NULL,
        tipo            TEXT NOT NULL,
        anno            INTEGER,
        filename        TEXT,
        path            TEXT,
        mime            TEXT,
        size            INTEGER,
        hash_sha256     TEXT,
        url_originale   TEXT,
        skip_reason     TEXT,
        downloaded_at   TEXT NOT NULL,
        UNIQUE (id_runts, hash_sha256)
    )""",
    """CREATE TABLE IF NOT EXISTS bilanci (
        id                                  INTEGER PRIMARY KEY AUTOINCREMENT,
        id_runts                            TEXT NOT NULL REFERENCES enti(id_runts),
        anno                                INTEGER NOT NULL,
        oneri_a_interesse_generale          REAL,
        oneri_b_attivita_diverse            REAL,
        oneri_c_raccolta_fondi              REAL,
        oneri_d_finanziarie_patrimoniali    REAL,
        oneri_e_supporto_generale           REAL,
        totale_oneri                        REAL,
        proventi_a_interesse_generale       REAL,
        proventi_b_attivita_diverse         REAL,
        proventi_c_raccolta_fondi           REAL,
        proventi_d_finanziarie_patrimoniali REAL,
        proventi_e_supporto_generale        REAL,
        totale_proventi                     REAL,
        risultato_ante_imposte              REAL,
        imposte                             REAL,
        risultato_esercizio                 REAL,
        raw_text                            TEXT,
        allegato_id                         INTEGER REFERENCES allegati(id),
        analyzed_at                         TEXT NOT NULL,
        UNIQUE (id_runts, anno)
    )""",
    """CREATE TABLE IF NOT EXISTS cariche_sociali (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        id_runts        TEXT NOT NULL REFERENCES enti(id_runts),
        ruolo           TEXT NOT NULL,
        nome            TEXT,
        cognome         TEXT,
        codice_fiscale  TEXT,
        valid_from      TEXT,
        valid_to        TEXT,
        updated_at      TEXT NOT NULL,
        UNIQUE (id_runts, codice_fiscale, ruolo, valid_from)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_allegati_id_runts ON allegati(id_runts)",
    "CREATE INDEX IF NOT EXISTS idx_allegati_tipo ON allegati(tipo)",
    "CREATE INDEX IF NOT EXISTS idx_allegati_codice_pratica ON allegati(codice_pratica)",
    "CREATE INDEX IF NOT EXISTS idx_bilanci_id_runts ON bilanci(id_runts)",
    "CREATE INDEX IF NOT EXISTS idx_cariche_id_runts ON cariche_sociali(id_runts)",
    "CREATE INDEX IF NOT EXISTS idx_cariche_attive ON cariche_sociali(id_runts, valid_to)",
    """CREATE TABLE IF NOT EXISTS sezioni_cai (
        codice_cai            TEXT PRIMARY KEY,
        cai_denominazione     TEXT NOT NULL,
        cai_codice_fiscale    TEXT,
        cai_partita_iva       TEXT,
        cai_email             TEXT,
        cai_pec               TEXT,
        cai_telefono_sede     TEXT,
        cai_telefono          TEXT,
        cai_fax               TEXT,
        cai_indirizzo_sede    TEXT,
        cai_indirizzo_postale TEXT,
        cai_sito_web          TEXT,
        cai_orari             TEXT,
        cai_avvisi            TEXT,
        cai_anno_fondazione   INTEGER,
        cai_soci_ultimo_anno  INTEGER,
        cai_lat               REAL,
        cai_lon               REAL,
        cai_regione           TEXT NOT NULL,
        cai_scraped_at        TEXT
    )""",
    "CREATE INDEX IF NOT EXISTS idx_sezioni_cai_cf ON sezioni_cai(cai_codice_fiscale)",
    "CREATE INDEX IF NOT EXISTS idx_sezioni_cai_regione ON sezioni_cai(cai_regione)",
    """CREATE TABLE IF NOT EXISTS sottosezioni_cai (
        cai_codice          TEXT PRIMARY KEY,
        cai_sezione_codice  TEXT NOT NULL REFERENCES sezioni_cai(codice_cai),
        cai_nome            TEXT NOT NULL,
        cai_email           TEXT,
        cai_telefono_sede   TEXT,
        cai_telefono        TEXT,
        cai_indirizzo_sede  TEXT,
        cai_sito_web        TEXT,
        cai_orari           TEXT,
        cai_avvisi          TEXT,
        cai_anno_fondazione INTEGER,
        cai_soci            INTEGER,
        cai_lat             REAL,
        cai_lon             REAL,
        cai_scraped_at      TEXT
    )""",
    "CREATE INDEX IF NOT EXISTS idx_sottosezioni_cai_sezione ON sottosezioni_cai(cai_sezione_codice)",
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
            pass  # column/index/table already exists
    conn.commit()
    return conn


def upsert_ente(conn: sqlite3.Connection, data: dict) -> str:
    """Insert or replace an entity. Returns 'inserted' or 'updated'.
    Preserves existing lat/lon if not present in the input dict."""
    data = {k: v for k, v in data.items()}
    data["updated_at"] = datetime.now(timezone.utc).isoformat()

    if "raw_json" not in data:
        data["raw_json"] = json.dumps(data, ensure_ascii=False)

    id_runts = data.get("id_runts") or data.get("codice_fiscale")
    if not id_runts:
        raise ValueError("Record senza id_runts né codice_fiscale, impossibile fare upsert")

    existing_row = conn.execute(
        "SELECT lat, lon FROM enti WHERE id_runts = ?", (id_runts,)
    ).fetchone()
    action = "updated" if existing_row else "inserted"

    # Preserve coordinates already in DB if the incoming dict doesn't supply them
    if existing_row:
        if data.get("lat") is None and existing_row["lat"] is not None:
            data["lat"] = existing_row["lat"]
        if data.get("lon") is None and existing_row["lon"] is not None:
            data["lon"] = existing_row["lon"]

    columns = [
        "id_runts", "codice_fiscale", "denominazione", "forma_giuridica",
        "natura_giuridica", "sede_stato", "sede_indirizzo", "sede_civico",
        "sede_comune", "sede_provincia", "sede_regione", "sede_cap",
        "lat", "lon", "data_iscrizione", "sezione_registro", "settori_attivita",
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


def upsert_allegato(conn: sqlite3.Connection, data: dict) -> str:
    """Upsert an allegato by (id_runts, hash_sha256). Returns 'inserted' or 'cache_hit'."""
    now = datetime.now(timezone.utc).isoformat()
    existing = None
    if data.get("hash_sha256"):
        existing = conn.execute(
            "SELECT id FROM allegati WHERE id_runts = ? AND hash_sha256 = ?",
            (data["id_runts"], data["hash_sha256"]),
        ).fetchone()

    if existing:
        conn.execute(
            "UPDATE allegati SET downloaded_at = ? WHERE id = ?",
            (now, existing["id"]),
        )
        conn.commit()
        return "cache_hit"

    cols = [
        "id_runts", "documento", "codice_pratica", "tipo", "anno",
        "filename", "path", "mime", "size", "hash_sha256",
        "url_originale", "skip_reason", "downloaded_at",
    ]
    row = {c: data.get(c) for c in cols}
    row["downloaded_at"] = now
    conn.execute(
        f"INSERT INTO allegati ({', '.join(cols)}) VALUES ({', '.join(':' + c for c in cols)})",
        row,
    )
    conn.commit()
    return "inserted"


_NUMERIC_BILANCIO_COLS = [
    "oneri_a_interesse_generale", "oneri_b_attivita_diverse",
    "oneri_c_raccolta_fondi", "oneri_d_finanziarie_patrimoniali",
    "oneri_e_supporto_generale", "totale_oneri",
    "proventi_a_interesse_generale", "proventi_b_attivita_diverse",
    "proventi_c_raccolta_fondi", "proventi_d_finanziarie_patrimoniali",
    "proventi_e_supporto_generale", "totale_proventi",
    "risultato_ante_imposte", "imposte", "risultato_esercizio",
]


def upsert_bilancio(conn: sqlite3.Connection, data: dict) -> None:
    """Upsert a bilancio record by (id_runts, anno).

    Merges with any existing record: each numeric field is updated only if the
    incoming value is not None (best-of-all-files wins per field).
    """
    now = datetime.now(timezone.utc).isoformat()
    cols = ["id_runts", "anno"] + _NUMERIC_BILANCIO_COLS + ["raw_text", "allegato_id", "analyzed_at"]
    row = {c: data.get(c) for c in cols}
    row["analyzed_at"] = now

    existing = conn.execute(
        f"SELECT {', '.join(cols)} FROM bilanci WHERE id_runts = ? AND anno = ?",
        (row["id_runts"], row["anno"]),
    ).fetchone()

    if existing:
        existing_row = dict(zip(cols, existing))
        # Merge: keep existing value when new is None; prefer new when new is not None
        for c in _NUMERIC_BILANCIO_COLS:
            if row[c] is None:
                row[c] = existing_row[c]
        # Keep raw_text if new is empty
        if not (row.get("raw_text") or "").strip():
            row["raw_text"] = existing_row.get("raw_text")

    conn.execute(
        f"INSERT OR REPLACE INTO bilanci ({', '.join(cols)}) "
        f"VALUES ({', '.join(':' + c for c in cols)})",
        row,
    )
    conn.commit()


def sync_cariche(conn: sqlite3.Connection, id_runts: str, cariche_new: list[dict]) -> None:
    """Sync active charges: close removed ones, insert new ones, leave unchanged ones."""
    today = datetime.now(timezone.utc).date().isoformat()
    now = datetime.now(timezone.utc).isoformat()

    active = conn.execute(
        "SELECT id, codice_fiscale, nome, cognome, ruolo, valid_from FROM cariche_sociali "
        "WHERE id_runts = ? AND valid_to IS NULL",
        (id_runts,),
    ).fetchall()

    def _key(row_or_dict, is_dict=False):
        if is_dict:
            cf = row_or_dict.get("codice_fiscale")
            if cf:
                return (cf, row_or_dict.get("ruolo"), row_or_dict.get("valid_from"))
            return (row_or_dict.get("nome"), row_or_dict.get("cognome"), row_or_dict.get("ruolo"), row_or_dict.get("valid_from"))
        else:
            cf = row_or_dict["codice_fiscale"]
            if cf:
                return (cf, row_or_dict["ruolo"], row_or_dict["valid_from"])
            return (row_or_dict["nome"], row_or_dict["cognome"], row_or_dict["ruolo"], row_or_dict["valid_from"])

    new_keys = {_key(c, is_dict=True) for c in cariche_new}

    for active_row in active:
        if _key(active_row) not in new_keys:
            conn.execute(
                "UPDATE cariche_sociali SET valid_to = ?, updated_at = ? WHERE id = ?",
                (today, now, active_row["id"]),
            )

    existing_keys = {_key(r) for r in active}
    for carica in cariche_new:
        if _key(carica, is_dict=True) not in existing_keys:
            conn.execute(
                "INSERT INTO cariche_sociali "
                "(id_runts, ruolo, nome, cognome, codice_fiscale, valid_from, valid_to, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    id_runts,
                    carica.get("ruolo"),
                    carica.get("nome"),
                    carica.get("cognome"),
                    carica.get("codice_fiscale"),
                    carica.get("valid_from"),
                    carica.get("valid_to"),
                    now,
                ),
            )

    conn.commit()


def get_stats(conn: sqlite3.Connection) -> dict:
    total = conn.execute("SELECT COUNT(*) FROM enti").fetchone()[0]
    return {"total": total}


def upsert_sezione_cai(conn: sqlite3.Connection, data: dict) -> str:
    """Insert or replace a CAI section. Returns 'inserted' or 'updated'."""
    now = datetime.now(timezone.utc).isoformat()
    cols = [
        "codice_cai", "cai_denominazione", "cai_codice_fiscale", "cai_partita_iva",
        "cai_email", "cai_pec", "cai_telefono_sede", "cai_telefono", "cai_fax",
        "cai_indirizzo_sede", "cai_indirizzo_postale", "cai_sito_web", "cai_orari",
        "cai_avvisi", "cai_anno_fondazione", "cai_soci_ultimo_anno",
        "cai_lat", "cai_lon", "cai_regione", "cai_scraped_at",
    ]
    existing = conn.execute(
        "SELECT codice_cai FROM sezioni_cai WHERE codice_cai = ?", (data.get("codice_cai"),)
    ).fetchone()
    action = "updated" if existing else "inserted"
    row = {c: data.get(c) for c in cols}
    row["cai_scraped_at"] = row.get("cai_scraped_at") or now
    conn.execute(
        f"INSERT OR REPLACE INTO sezioni_cai ({', '.join(cols)}) "
        f"VALUES ({', '.join(':' + c for c in cols)})",
        row,
    )
    conn.commit()
    return action


def upsert_sottosezione_cai(conn: sqlite3.Connection, data: dict) -> str:
    """Insert or replace a CAI sub-section. Returns 'inserted' or 'updated'."""
    now = datetime.now(timezone.utc).isoformat()
    cols = [
        "cai_codice", "cai_sezione_codice", "cai_nome", "cai_email",
        "cai_telefono_sede", "cai_telefono", "cai_indirizzo_sede", "cai_sito_web",
        "cai_orari", "cai_avvisi", "cai_anno_fondazione", "cai_soci",
        "cai_lat", "cai_lon", "cai_scraped_at",
    ]
    existing = conn.execute(
        "SELECT cai_codice FROM sottosezioni_cai WHERE cai_codice = ?", (data.get("cai_codice"),)
    ).fetchone()
    action = "updated" if existing else "inserted"
    row = {c: data.get(c) for c in cols}
    row["cai_scraped_at"] = row.get("cai_scraped_at") or now
    conn.execute(
        f"INSERT OR REPLACE INTO sottosezioni_cai ({', '.join(cols)}) "
        f"VALUES ({', '.join(':' + c for c in cols)})",
        row,
    )
    conn.commit()
    return action
