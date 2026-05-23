"""
Integration test: verifica che lo scraper estragga correttamente i campi sede legale.

Se runts.db non esiste o non contiene un ente di test, lo scraper viene eseguito
automaticamente per quella sola denominazione.
"""
import asyncio
import sqlite3
from pathlib import Path

import pytest

DB_PATH = Path(__file__).parent.parent / "runts.db"

_CASES = [
    {
        "id_runts": "83894",
        "search_denominazione": "CLUB ALPINO ITALIANO SEZIONE DI PISA- APS-ETS",
        "expected": {
            "sede_stato":     "I",
            "sede_provincia": "PI",
            "sede_comune":    "PISA",
            "sede_indirizzo": "VIA DEL CHIASSATELLO",
            "sede_civico":    "38-39-40",
            "sede_cap":       "56122",
            "sede_regione":   "Toscana",
        },
    },
    {
        "id_runts": "61826",
        "search_denominazione": "CLUB ALPINO ITALIANO - SEZIONE DI PARMA - APS - ETS",
        "expected": {
            "sede_stato":     "I",
            "sede_provincia": "PR",
            "sede_comune":    "PARMA",
            "sede_indirizzo": "VIALE PIACENZA",
            "sede_civico":    "40",
            "sede_cap":       "43126",
            "sede_regione":   "Emilia-Romagna",
        },
    },
    {
        "id_runts": "46877",
        "search_denominazione": "CLUB ALPINO ITALIANO - SEZIONE DI BOLOGNA MARIO FANTIN APS",
        "expected": {
            "sede_stato":     "I",
            "sede_provincia": "BO",
            "sede_comune":    "BOLOGNA",
            "sede_indirizzo": "VIA DEI FORNACIAI",
            "sede_civico":    "25/A",
            "sede_cap":       "40129",
            "sede_regione":   "Emilia-Romagna",
        },
    },
]


def _fetch_row(conn: sqlite3.Connection, id_runts: str) -> dict | None:
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM enti WHERE id_runts = ?", (id_runts,)
    ).fetchone()
    return dict(row) if row else None


def _ensure_ente(conn: sqlite3.Connection, id_runts: str, search_denominazione: str) -> None:
    if _fetch_row(conn, id_runts) is not None:
        return
    from scraper.db import upsert_ente
    from scraper.scraper import run_scraper

    entities = asyncio.run(
        run_scraper(denominazione=search_denominazione, headless=True, delay_ms=0)
    )
    for e in entities:
        upsert_ente(conn, e)


@pytest.fixture(scope="session")
def db_conn():
    from scraper.db import init_db
    conn = init_db(str(DB_PATH))
    yield conn
    conn.close()


@pytest.mark.parametrize("case", _CASES, ids=[c["id_runts"] for c in _CASES])
def test_sede_legale(db_conn, case):
    _ensure_ente(db_conn, case["id_runts"], case["search_denominazione"])
    row = _fetch_row(db_conn, case["id_runts"])

    assert row is not None, f"Ente id_runts={case['id_runts']!r} non trovato nel DB"

    for field, expected in case["expected"].items():
        assert row.get(field) == expected, (
            f"[{case['id_runts']}] {field}: atteso {expected!r}, trovato {row.get(field)!r}"
        )
