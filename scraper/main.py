import argparse
import asyncio
import logging
import sys

from .db import get_stats, init_db, upsert_ente
from .scraper import run_scraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scarica i dati delle sezioni CAI dal registro RUNTS e li salva in SQLite."
    )
    parser.add_argument(
        "--db",
        default="runts.db",
        metavar="PATH",
        help="Percorso del database SQLite (default: runts.db)",
    )
    parser.add_argument(
        "--headless",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Esegui il browser in modalità headless (default: sì). Usa --no-headless per vederlo.",
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=500,
        metavar="MS",
        help="Millisecondi di attesa tra una pagina dettaglio e la successiva (default: 500)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Abilita log di debug",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 1. Init DB
    logger.info("Apertura database: %s", args.db)
    conn = init_db(args.db)
    stats_before = get_stats(conn)

    # 2. Scrape
    logger.info("Avvio scraping (headless=%s, delay=%dms)...", args.headless, args.delay)
    try:
        entities, retry_stats = await run_scraper(
            denominazione="CLUB ALPINO ITALIANO",
            headless=args.headless,
            delay_ms=args.delay,
        )
    except Exception as exc:
        logger.error("Errore fatale durante lo scraping: %s", exc)
        conn.close()
        sys.exit(1)

    # 3. Upsert
    inserted = updated = errors = 0
    for entity in entities:
        try:
            action = upsert_ente(conn, entity)
            if action == "inserted":
                inserted += 1
            else:
                updated += 1
        except Exception as exc:
            logger.warning("Errore salvataggio ente '%s': %s", entity.get("denominazione"), exc)
            errors += 1

    conn.close()

    # 4. Report finale
    stats_after = get_stats(init_db(args.db))
    print()
    print("=" * 55)
    print("  REPORT FINALE")
    print("=" * 55)
    print(f"  Enti processati          : {len(entities)}")
    print(f"  Inseriti                 : {inserted}")
    print(f"  Aggiornati               : {updated}")
    print(f"  Errori salvataggio       : {errors}")
    print(f"  Totale nel DB            : {stats_after['total']}  (prima: {stats_before['total']})")
    print()
    print(f"  Recuperati al 1° tentativo: {retry_stats['attempt_1']}")
    print(f"  Recuperati al 2° tentativo: {retry_stats['attempt_2']}")
    print(f"  Recuperati al 3° tentativo: {retry_stats['attempt_3']}")
    print(f"  Falliti definitivamente   : {retry_stats['failed_after_retry']}")
    print("=" * 55)


if __name__ == "__main__":
    asyncio.run(main())
