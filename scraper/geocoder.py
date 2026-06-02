import argparse
import json
import logging
import re as _re
import sqlite3
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_USER_AGENT = "runts-cai-geocoder/1.0 (https://github.com/piccioli/runts)"
_WEB_BASE = "http://localhost:8000"


def _strip_abbreviations(via: str) -> str:
    """Rimuove iniziali puntate tipo 'G.M.' lasciando solo le parole intere."""
    return _re.sub(r"\b([A-Z]\.)+", "", via).strip()


def _build_queries(
    indirizzo: str | None,
    civico: str | None,
    cap: str | None,
    comune: str,
) -> list[str]:
    """Restituisce query in ordine dal più specifico al meno specifico."""
    comune_t = comune.title()
    cap_part = [cap] if cap else []
    queries = []

    if indirizzo:
        via = indirizzo.title()
        via_no_abbr = _strip_abbreviations(via)

        # 1. indirizzo completo + civico + CAP + comune
        if civico:
            queries.append(
                ", ".join([f"{via} {civico}"] + cap_part + [comune_t, "Italia"])
            )
        # 2. indirizzo + CAP + comune (senza civico)
        queries.append(", ".join([via] + cap_part + [comune_t, "Italia"]))
        # 3. indirizzo senza abbreviazioni + CAP + comune
        if via_no_abbr and via_no_abbr != via:
            queries.append(", ".join([via_no_abbr] + cap_part + [comune_t, "Italia"]))

    # 4. CAP + comune
    queries.append(", ".join(cap_part + [comune_t, "Italia"]))
    # 5. solo comune
    queries.append(f"{comune_t}, Italia")

    # deduplicazione mantenendo ordine
    seen: set[str] = set()
    return [q for q in queries if not (q in seen or seen.add(q))]  # type: ignore[func-returns-value]


def _nominatim_fetch(query: str) -> tuple[float, float] | None:
    params = urllib.parse.urlencode({"q": query, "format": "json", "limit": "1"})
    url = f"{_NOMINATIM_URL}?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            results = json.loads(resp.read())
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
        return None
    except Exception as exc:
        raise RuntimeError(f"Richiesta HTTP fallita: {exc}") from exc


def _cache_key(comune: str, provincia: str | None, regione: str | None) -> str:
    parts = [
        (comune or "").strip().lower(),
        (provincia or "").strip().lower(),
        (regione or "").strip().lower(),
    ]
    return "|".join(parts)


def _lookup_cache(conn: sqlite3.Connection, key: str) -> tuple[float, float] | None:
    row = conn.execute(
        "SELECT lat, lon FROM geocoding_cache WHERE cache_key = ?", (key,)
    ).fetchone()
    if row:
        return float(row["lat"]), float(row["lon"])
    return None


def _write_cache(
    conn: sqlite3.Connection, key: str, lat: float, lon: float, source: str
) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT OR REPLACE INTO geocoding_cache (cache_key, lat, lon, source, ts) VALUES (?, ?, ?, ?, ?)",
        (key, lat, lon, source, ts),
    )
    conn.commit()


def geocode_enti(conn: sqlite3.Connection, error_log_path: Path) -> dict:
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT id_runts, denominazione, sede_indirizzo, sede_civico, sede_cap, sede_comune,
                  sede_provincia, sede_regione
           FROM enti WHERE lat IS NULL OR lon IS NULL
           ORDER BY denominazione"""
    ).fetchall()

    total = len(rows)
    geocoded = skipped = not_found = errors = from_cache = from_nominatim = 0

    with error_log_path.open("w", encoding="utf-8") as err_file:
        err_file.write(
            f"# Geocoder error log\n# Totale enti da processare: {total}\n\n"
        )

        for i, row in enumerate(rows, 1):
            id_runts = row["id_runts"]
            denominazione = row["denominazione"] or id_runts
            comune = row["sede_comune"]
            prefix = f"[{i}/{total}] {denominazione}"

            if not comune:
                msg = f"{prefix} — SALTATO (nessun comune)"
                logger.warning(msg)
                err_file.write(f"SALTATO  {msg}\n  → {_WEB_BASE}/ente/{id_runts}\n\n")
                skipped += 1
                continue

            # Check cache before hitting Nominatim
            key = _cache_key(comune, row["sede_provincia"], row["sede_regione"])
            cached = _lookup_cache(conn, key)
            if cached:
                lat, lon = cached
                conn.execute(
                    "UPDATE enti SET lat = ?, lon = ? WHERE id_runts = ?",
                    (lat, lon, id_runts),
                )
                conn.commit()
                logger.info("%s\n  → %.6f, %.6f ✓  (da cache)", prefix, lat, lon)
                geocoded += 1
                from_cache += 1
                continue

            queries = _build_queries(
                row["sede_indirizzo"],
                row["sede_civico"],
                row["sede_cap"],
                comune,
            )
            logger.info("%s\n  Query: %s", prefix, queries[0])

            coords = None
            winning_query = None
            last_exc = None

            for attempt, query in enumerate(queries):
                if attempt > 0:
                    logger.info(
                        "  Fallback [%d/%d]: %s", attempt + 1, len(queries), query
                    )
                    time.sleep(1)
                try:
                    coords = _nominatim_fetch(query)
                    time.sleep(1)
                    if coords:
                        winning_query = query
                        break
                except RuntimeError as exc:
                    last_exc = exc
                    time.sleep(1)

            if coords:
                lat, lon = coords
                conn.execute(
                    "UPDATE enti SET lat = ?, lon = ? WHERE id_runts = ?",
                    (lat, lon, id_runts),
                )
                conn.commit()
                _write_cache(conn, key, lat, lon, "nominatim")
                if winning_query != queries[0]:
                    logger.info(
                        "  → %.6f, %.6f ✓  (via fallback: %s)", lat, lon, winning_query
                    )
                else:
                    logger.info("  → %.6f, %.6f ✓", lat, lon)
                geocoded += 1
                from_nominatim += 1
            elif last_exc:
                msg = f"{prefix} — ERRORE HTTP: {last_exc}\n  Query tentate: {queries}"
                logger.error("  → %s", last_exc)
                err_file.write(f"ERRORE  {msg}\n  → {_WEB_BASE}/ente/{id_runts}\n\n")
                errors += 1
            else:
                msg = f"{prefix} — NON TROVATO\n  Query tentate: {queries}"
                logger.warning("  → nessun risultato dopo %d tentativi", len(queries))
                err_file.write(
                    f"NON TROVATO  {msg}\n  → {_WEB_BASE}/ente/{id_runts}\n\n"
                )
                not_found += 1
                errors += 1

    return {
        "total": total,
        "geocoded": geocoded,
        "from_cache": from_cache,
        "from_nominatim": from_nominatim,
        "not_found": not_found,
        "skipped": skipped,
        "errors": errors,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Geocodifica gli enti nel DB tramite Nominatim (OpenStreetMap)."
    )
    parser.add_argument("--db", default="runts.db", metavar="PATH")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Azzera lat/lon esistenti e ri-geocodifica tutto",
    )
    parser.add_argument(
        "--log-dir",
        default="scraper/logs",
        metavar="DIR",
        help="Directory dove salvare i file di log (default: scraper/logs)",
    )
    args = parser.parse_args()

    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    main_log = log_dir / "geocoder.log"
    error_log = log_dir / "geocoder_errors.log"

    # Console + file handler
    fmt = "%(asctime)s  %(levelname)-8s  %(message)s"
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format=fmt,
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(main_log, encoding="utf-8"),
        ],
    )

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    if args.reset:
        conn.execute("UPDATE enti SET lat = NULL, lon = NULL")
        conn.commit()
        logger.info("Coordinate azzerate per tutti gli enti.")

    already = conn.execute(
        "SELECT COUNT(*) FROM enti WHERE lat IS NOT NULL AND lon IS NOT NULL"
    ).fetchone()[0]
    total_db = conn.execute("SELECT COUNT(*) FROM enti").fetchone()[0]
    logger.info(
        "DB: %d enti totali, %d già geocodificati, %d da processare",
        total_db,
        already,
        total_db - already,
    )
    logger.info("Log principale : %s", main_log.resolve())
    logger.info("Log errori     : %s", error_log.resolve())

    stats = geocode_enti(conn, error_log)
    conn.close()

    print()
    print("=" * 55)
    print("  REPORT GEOCODIFICA")
    print("=" * 55)
    print(f"  Totale processati    : {stats['total']}")
    print(f"  Geocodificati ✓      : {stats['geocoded']}")
    print(f"    da cache           : {stats['from_cache']}")
    print(f"    da Nominatim       : {stats['from_nominatim']}")
    print(f"  Non trovati          : {stats['not_found']}")
    print(f"  Errori HTTP          : {stats['errors']}")
    print(f"  Saltati (no comune)  : {stats['skipped']}")
    print(f"  Log principale       : {main_log.resolve()}")
    print(f"  Log errori           : {error_log.resolve()}")
    print("=" * 55)
