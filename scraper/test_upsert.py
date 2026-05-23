import sqlite3
import pytest
from scraper.db import init_db, upsert_ente


@pytest.fixture
def mem_db():
    conn = init_db(":memory:")
    yield conn
    conn.close()


def test_upsert_preserves_lat_lon_on_rerun(mem_db):
    """A rerun without lat/lon in the dict must not erase existing coordinates."""
    first = {
        "id_runts": "TEST001",
        "denominazione": "Test Ente",
        "lat": 43.7,
        "lon": 10.4,
    }
    upsert_ente(mem_db, first)

    # Verify stored
    row = mem_db.execute("SELECT lat, lon FROM enti WHERE id_runts='TEST001'").fetchone()
    assert row["lat"] == pytest.approx(43.7)
    assert row["lon"] == pytest.approx(10.4)

    # Second upsert without coordinates
    second = {
        "id_runts": "TEST001",
        "denominazione": "Test Ente aggiornato",
    }
    upsert_ente(mem_db, second)

    row = mem_db.execute("SELECT lat, lon, denominazione FROM enti WHERE id_runts='TEST001'").fetchone()
    assert row["lat"] == pytest.approx(43.7), "lat deve essere preservato"
    assert row["lon"] == pytest.approx(10.4), "lon deve essere preservato"
    assert row["denominazione"] == "Test Ente aggiornato"


def test_upsert_preserves_lat_lon_when_none_in_dict(mem_db):
    """Explicit None in dict must not erase existing coordinates."""
    upsert_ente(mem_db, {"id_runts": "TEST002", "denominazione": "X", "lat": 45.0, "lon": 9.0})

    upsert_ente(mem_db, {"id_runts": "TEST002", "denominazione": "X updated", "lat": None, "lon": None})

    row = mem_db.execute("SELECT lat, lon FROM enti WHERE id_runts='TEST002'").fetchone()
    assert row["lat"] == pytest.approx(45.0)
    assert row["lon"] == pytest.approx(9.0)


def test_upsert_sets_lat_lon_on_first_insert(mem_db):
    """New ente with coordinates must store them correctly."""
    upsert_ente(mem_db, {"id_runts": "TEST003", "denominazione": "Y", "lat": 41.9, "lon": 12.5})
    row = mem_db.execute("SELECT lat, lon FROM enti WHERE id_runts='TEST003'").fetchone()
    assert row["lat"] == pytest.approx(41.9)
    assert row["lon"] == pytest.approx(12.5)
