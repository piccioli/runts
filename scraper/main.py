import argparse
import asyncio
import logging
import sys
from pathlib import Path

import httpx

from .db import get_stats, init_db, upsert_allegato, upsert_ente, sync_cariche
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
        "--verbose",
        "-v",
        action="store_true",
        help="Abilita log di debug",
    )
    parser.add_argument(
        "--attachments-dir",
        default="attachments",
        metavar="DIR",
        help="Cartella dove salvare i file allegati (default: attachments/)",
    )
    parser.add_argument(
        "--no-attachments",
        action="store_true",
        help="Salta il download degli allegati",
    )
    parser.add_argument(
        "--denominazione",
        default="CLUB ALPINO ITALIANO",
        metavar="NOME",
        help="Denominazione da cercare nel RUNTS (default: CLUB ALPINO ITALIANO)",
    )
    parser.add_argument(
        "--codice-fiscale",
        default=None,
        metavar="CF",
        dest="codice_fiscale",
        help="Cerca per codice fiscale invece che per denominazione (ritorna un solo ente)",
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
    att_dir = Path(args.attachments_dir)
    logger.info(
        "Avvio scraping (headless=%s, delay=%dms)...", args.headless, args.delay
    )
    try:
        entities, retry_stats = await run_scraper(
            denominazione=args.denominazione,
            headless=args.headless,
            delay_ms=args.delay,
            codice_fiscale=args.codice_fiscale,
            attachments_dir=att_dir if not args.no_attachments else None,
        )
    except Exception as exc:
        logger.error("Errore fatale durante lo scraping: %s", exc)
        conn.close()
        sys.exit(1)

    # 3. Upsert enti + allegati + cariche
    inserted = updated = errors = 0
    att_scoperti = att_scaricati = att_cache = att_saltati = att_falliti = 0

    async with httpx.AsyncClient(
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        },
        limits=httpx.Limits(max_connections=4),
        timeout=httpx.Timeout(60.0),
    ) as _http_client:
        for entity in entities:
            atti = entity.pop("atti_documenti", []) or []
            cariche = entity.pop("cariche", []) or []

            try:
                action = upsert_ente(conn, entity)
                if action == "inserted":
                    inserted += 1
                else:
                    updated += 1
            except Exception as exc:
                logger.warning(
                    "Errore salvataggio ente '%s': %s", entity.get("denominazione"), exc
                )
                errors += 1
                continue

            id_runts = entity.get("id_runts")
            if not id_runts:
                continue

            # Allegati — già scaricati via Playwright durante lo scraping
            if atti and not args.no_attachments:
                att_scoperti += len(atti)
                for att in atti:
                    try:
                        att["id_runts"] = id_runts
                        result = upsert_allegato(conn, att)
                        if result == "cache_hit":
                            att_cache += 1
                        elif att.get("skip_reason"):
                            att_saltati += 1
                        else:
                            att_scaricati += 1
                    except Exception as exc:
                        logger.warning(
                            "Errore upsert allegato per %s: %s", id_runts, exc
                        )
                        att_falliti += 1

            # Cariche sociali
            if cariche:
                try:
                    sync_cariche(conn, id_runts, cariche)
                except Exception as exc:
                    logger.warning("Errore sync cariche per %s: %s", id_runts, exc)

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
    print(
        f"  Totale nel DB            : {stats_after['total']}  (prima: {stats_before['total']})"
    )
    print()
    print(f"  Recuperati al 1° tentativo: {retry_stats['attempt_1']}")
    print(f"  Recuperati al 2° tentativo: {retry_stats['attempt_2']}")
    print(f"  Recuperati al 3° tentativo: {retry_stats['attempt_3']}")
    print(f"  Falliti definitivamente   : {retry_stats['failed_after_retry']}")
    print()
    print(f"  Allegati scoperti        : {att_scoperti}")
    print(f"  Allegati scaricati       : {att_scaricati}")
    print(f"  Allegati (cache hit)     : {att_cache}")
    print(f"  Allegati saltati         : {att_saltati}")
    print(f"  Allegati falliti         : {att_falliti}")
    print("=" * 55)


if __name__ == "__main__":
    asyncio.run(main())
