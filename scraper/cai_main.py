import argparse
import logging
import sys

from .cai_scraper import fetch_all_sections, fetch_subsections
from .db import init_db, upsert_sezione_cai, upsert_sottosezione_cai

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scarica sezioni e sottosezioni CAI dalla REST API e le salva in SQLite."
    )
    parser.add_argument(
        "--db",
        default="runts.db",
        metavar="PATH",
        help="Percorso del database SQLite (default: runts.db)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Abilita log di debug",
    )
    parser.add_argument(
        "--no-subsections",
        action="store_true",
        dest="no_subsections",
        help="Salta il fetch delle sottosezioni",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("Apertura database: %s", args.db)
    conn = init_db(args.db)

    # --- Sezioni ---
    logger.info("Fetching tutte le sezioni CAI...")
    try:
        sections = fetch_all_sections()
    except Exception as exc:
        logger.error("Errore fatale durante il fetch delle sezioni: %s", exc)
        conn.close()
        sys.exit(1)

    sezioni_scaricate = len(sections)
    sezioni_inserite = sezioni_aggiornate = sezioni_fallite = 0

    for sec in sections:
        try:
            action = upsert_sezione_cai(conn, sec)
            if action == "inserted":
                sezioni_inserite += 1
            else:
                sezioni_aggiornate += 1
        except Exception as exc:
            logger.warning("Errore salvataggio sezione '%s': %s", sec.get("codice_cai"), exc)
            sezioni_fallite += 1

    # --- Sottosezioni ---
    sottosezioni_scaricate = sottosezioni_inserite = sottosezioni_aggiornate = sottosezioni_fallite = 0

    if not args.no_subsections:
        logger.info("Fetching sottosezioni per %d sezioni...", sezioni_scaricate)
        for sec in sections:
            codice = sec.get("codice_cai")
            if not codice:
                continue
            try:
                subsections = fetch_subsections(codice)
            except Exception as exc:
                logger.warning("Errore fetch sottosezioni per %s: %s", codice, exc)
                continue

            sottosezioni_scaricate += len(subsections)
            for sub in subsections:
                try:
                    action = upsert_sottosezione_cai(conn, sub)
                    if action == "inserted":
                        sottosezioni_inserite += 1
                    else:
                        sottosezioni_aggiornate += 1
                except Exception as exc:
                    logger.warning("Errore salvataggio sottosezione '%s': %s", sub.get("cai_codice"), exc)
                    sottosezioni_fallite += 1

    conn.close()

    print()
    print("=" * 55)
    print("  REPORT FINALE")
    print("=" * 55)
    print(f"  Sezioni scaricate        : {sezioni_scaricate}")
    print(f"  Sezioni inserite         : {sezioni_inserite}")
    print(f"  Sezioni aggiornate       : {sezioni_aggiornate}")
    print(f"  Sezioni fallite          : {sezioni_fallite}")
    if not args.no_subsections:
        print()
        print(f"  Sottosezioni scaricate   : {sottosezioni_scaricate}")
        print(f"  Sottosezioni inserite    : {sottosezioni_inserite}")
        print(f"  Sottosezioni aggiornate  : {sottosezioni_aggiornate}")
        print(f"  Sottosezioni fallite     : {sottosezioni_fallite}")
    print("=" * 55)


if __name__ == "__main__":
    main()
