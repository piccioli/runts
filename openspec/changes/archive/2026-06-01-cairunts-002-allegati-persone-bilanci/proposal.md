## Why

Le schede RUNTS contengono PDF allegati ufficiali (statuti, bilanci, atti), informazioni sugli organi sociali e dati economici strutturati che il sistema oggi ignora completamente: l'operatore deve tornare al portale del Ministero per qualsiasi consultazione. Acquisire questi dati trasforma la scheda ente da riepilogo anagrafico a sintesi informativa completa, utile sia per la consultazione quotidiana di Montagna Servizi sia per analisi aggregate sulle sezioni CAI.

## What Changes

- Lo scraper naviga la sezione "Atti e documenti" di ogni scheda RUNTS, scarica i PDF allegati e li salva in `attachments/<id_runts>/`, classificandoli per codice pratica ufficiale (B00, B08, C02, ecc.)
- Un nuovo modulo `scraper/analyzer.py` analizza i PDF di bilancio già scaricati ed estrae le 13 voci numeriche del rendiconto gestionale ETS (DM 39/2020): 5 categorie oneri A-E, 5 categorie proventi A-E, risultato d'esercizio
- Lo scraper estrae dalla sezione "Organi sociali" le cariche attive (presidente, consiglieri, altre cariche) con nome, CF e periodo; gestisce apertura/chiusura temporale delle cariche tra run successivi
- La scheda ente web mostra tre nuove sezioni: "Atti e documenti", "Indicatori di bilancio", "Persone e cariche"
- Il PDF scaricabile della scheda ente include le stesse tre sezioni aggiuntive, su più pagine se necessario
- Tre nuove tabelle nel DB: `allegati`, `bilanci`, `cariche_sociali` (additive, idempotenti)
- I file PDF vivono su filesystem (`attachments/`), non nel DB; il volume viene bind-mountato in Docker

## Capabilities

### New Capabilities

- `allegati-ingest`: scraping e download degli atti e documenti RUNTS; classificazione per codice pratica; upsert per hash SHA-256; gestione dimensione massima e report
- `allegati-analisi`: analisi offline dei PDF di bilancio ETS con `pdfplumber`; estrazione 13 voci numeriche; controllo coerenza somme; test unitari con fixture reali
- `cariche-sociali`: estrazione organi sociali RUNTS; persistenza con tracciamento temporale (valid_from/valid_to); chiusura automatica cariche cessate

### Modified Capabilities

- `database-storage`: tre nuove tabelle (`allegati`, `bilanci`, `cariche_sociali`) con relativi indici; storage allegati su filesystem non DB
- `runts-detail`: estrazione di atti e documenti e cariche sociali dalla pagina di dettaglio RUNTS (nuovi selettori Playwright)
- `ente-detail`: tre nuove sezioni nella scheda web (allegati, bilanci, persone); mount `/attachments` come static files; CF mascherato in UI
- `ente-pdf`: PDF scheda ente esteso con sezioni allegati, bilanci, persone; carta intestata MS su tutte le pagine

## Impact

- `scraper/db.py`: nuove tabelle e indici in `SCHEMA` e `_MIGRATIONS`; nuove funzioni `upsert_allegato`, `upsert_bilancio`, `sync_cariche`
- `scraper/scraper.py`: funzioni `extract_atti_documenti`, `extract_cariche`, integrazione nel main loop
- `scraper/downloader.py`: nuovo modulo async `download_attachments` (dipendenza `httpx`)
- `scraper/analyzer.py`: nuovo modulo eseguibile CLI (dipendenza `pdfplumber`)
- `scraper/requirements.txt`: aggiunta `httpx`, `pdfplumber`
- `web/app.py`: query allegati/bilanci/cariche nella route `/ente/{id_runts}`; mount `/attachments`; filtri Jinja `mask_cf`, `human_size`
- `web/templates/detail.html`: tre nuove sezioni
- `web/pdf_utils.py`: sezioni allegati, bilanci, persone nel PDF
- `docker-compose.yml`: bind-mount `./attachments:/app/attachments:ro`
- `scraper/requirements.txt`: aggiunta `httpx`, `pdfplumber`
