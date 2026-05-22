## Why

I dati RUNTS raccolti dallo scraper sono accessibili solo tramite query SQLite dirette. Serve un'interfaccia web che permetta di consultare, cercare e filtrare gli enti senza competenze tecniche, deployabile facilmente tramite Docker.

## What Changes

- Nuova applicazione web (separata dallo scraper) con lista filtrabile/cercabile degli enti
- Pagina di dettaglio per ogni singolo ente
- Containerizzazione dell'intera applicazione web con Docker
- Il database SQLite prodotto dallo scraper viene montato come volume nel container web
- Lo scraper rimane un processo standalone indipendente dall'app web

## Capabilities

### New Capabilities

- `enti-list`: Lista paginata e filtrabile degli enti con ricerca testuale e filtri per regione, sezione del registro e forma giuridica
- `ente-detail`: Pagina di dettaglio del singolo ente con tutti i campi estratti
- `web-docker`: Configurazione Docker (Dockerfile + docker-compose) per avviare l'applicazione web

### Modified Capabilities

## Impact

- Nuovi file: `web/` directory con app web, `Dockerfile`, `docker-compose.yml`
- Nessuna modifica a `scraper.py`, `db.py`, `main.py`
- Dipendenze web aggiunte in un file separato (`web/requirements.txt`)
- Il DB `runts.db` viene condiviso tra scraper e container web tramite volume Docker
