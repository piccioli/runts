## Context

Lo scraper esistente produce un database SQLite (`runts.db`) con 226+ enti CAI. Attualmente i dati sono consultabili solo via query SQL. Si vuole un'app web leggera, containerizzata, che legga il DB in sola lettura e lo esponga tramite interfaccia web. Lo scraper rimane un processo separato che aggiorna il DB periodicamente.

## Goals / Non-Goals

**Goals:**
- App web con lista filtrabile/cercabile e pagina di dettaglio
- Stack Python (FastAPI + Jinja2) per coerenza con il resto del progetto
- Docker + docker-compose per avvio con un solo comando
- DB SQLite montato come volume (condiviso con lo scraper)
- Interfaccia responsive, senza framework JS pesanti (HTML + CSS vanilla o Bootstrap)

**Non-Goals:**
- Autenticazione o autorizzazione
- Modifica dei dati dall'interfaccia web
- API REST pubblica
- Aggiornamento del DB dall'interno del container web

## Decisions

**Framework web: FastAPI + Jinja2**
Stessa tecnologia del progetto (Python). FastAPI offre routing semplice, Jinja2 permette template HTML server-side senza build step. Alternativa scartata: Flask (meno moderno); Django (troppo pesante per questo caso d'uso).

**Rendering: server-side (Jinja2)**
Evita la complessità di un frontend separato (React/Vue). Il dataset è piccolo (226 enti), il rendering lato server è più che sufficiente. La ricerca/filtro viene gestita via query string e SELECT SQL con LIKE/WHERE.

**Database: SQLite in sola lettura**
Il container web apre il DB con `check_same_thread=False` e in modalità read-only (`uri=True, ?mode=ro`). Nessun rischio di corruzione quando lo scraper scrive contemporaneamente (SQLite supporta lettori concorrenti).

**Docker: immagine Python slim + volume per il DB**
`Dockerfile` basato su `python:3.12-slim`. Il DB viene montato come volume in `docker-compose.yml` (`./runts.db:/app/runts.db:ro`). Lo scraper gira fuori dal container e aggiorna il file sul host.

**Paginazione: server-side con limit/offset**
Semplice e senza dipendenze JS. Parametri via query string: `?page=1&q=Milano&regione=Lombardia`.

## Risks / Trade-offs

- **SQLite + accesso concorrente** → Mitigazione: container web apre in modalità read-only, WAL mode abilitato dallo scraper
- **Nessun reload automatico quando il DB cambia** → Accettabile: l'utente aggiorna la pagina dopo un nuovo scraping
- **Layout senza JS pesante** → Trade-off: no ricerca live istantanea, ma UX semplice e manutenibile

## Migration Plan

1. Creare `web/` con `app.py`, `templates/`, `requirements.txt`
2. Creare `Dockerfile` e `docker-compose.yml` alla radice
3. Testare localmente: `docker compose up`
4. Verificare che il volume del DB sia accessibile e le query funzionino
