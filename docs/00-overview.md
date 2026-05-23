# 00 — Panoramica del sistema RUNTS-CAI

> Fotografia dello stato attuale del sistema. Questo documento è materiale di input per la generazione di specifiche OpenSpec.

## Scopo del progetto

Il sistema **RUNTS-CAI** acquisisce, normalizza, persiste e pubblica i dati delle sezioni del **Club Alpino Italiano** iscritte al **Registro Unico Nazionale del Terzo Settore (RUNTS)** del Ministero del Lavoro.

L'obiettivo è disporre di un dataset locale interrogabile e di una mini-applicazione web di consultazione che mostri la lista, il dettaglio e la mappa delle sezioni CAI registrate.

## Attori e responsabilità

| Attore | Responsabilità |
|---|---|
| **Operatore (CLI)** | Lancia manualmente lo scraper e il geocoder per popolare e arricchire il DB. |
| **Scraper** (`scraper/`) | Automatizza la ricerca su `servizi.lavoro.gov.it/runts` ed estrae i dati di dettaglio di ciascun ente. |
| **Geocoder** (`scraper/geocoder.py`) | Aggiunge coordinate lat/lon agli enti interrogando Nominatim (OpenStreetMap). |
| **Database** (`runts.db`, SQLite) | Persiste gli enti in un'unica tabella `enti` con upsert per `id_runts`. |
| **Web app** (`web/`, FastAPI) | Consulta in sola lettura `runts.db` e serve lista filtrabile, dettaglio e mappa Leaflet. |
| **Utente finale (browser)** | Naviga la lista, applica filtri, apre il dettaglio del singolo ente, visualizza la mappa. |

## Componenti principali

Il sistema è composto da tre macro-componenti, debolmente accoppiati e condivisi solo attraverso il file `runts.db`:

1. **Scraper RUNTS** — Python + Playwright async, esegue una ricerca filtrata per la denominazione "CLUB ALPINO ITALIANO", pagina i risultati, naviga al dettaglio di ogni ente, estrae i campi e li salva nel DB.
2. **Geocoder Nominatim** — script Python standalone che legge dal DB gli enti senza coordinate e popola `lat`/`lon` via `nominatim.openstreetmap.org`, rispettando il rate limit di 1 req/s.
3. **Web app FastAPI** — applicazione Jinja2/Bootstrap che apre `runts.db` in sola lettura e serve due route HTML (`/`, `/ente/<id_runts>`), con vista lista, vista mappa e dettaglio singolo ente.

Lo scraper e il web sono **isolati**: hanno requirements separati, vivono in directory separate (`scraper/`, `web/`) e si parlano esclusivamente via il file `runts.db` alla radice del progetto.

## Flusso end-to-end

```
┌─────────────────┐
│ servizi.lavoro  │
│ .gov.it/runts   │
└────────┬────────┘
         │ HTTP + JS dinamico (DNN)
         ▼
┌─────────────────┐
│  Scraper        │  python -m scraper.main
│  Playwright     │  --headless --delay 500
└────────┬────────┘
         │ upsert per id_runts
         ▼
┌─────────────────┐      ┌─────────────────┐
│   runts.db      │◄─────│  Geocoder       │  python -m scraper.geocoder
│   (SQLite)      │      │  Nominatim      │  --db runts.db
└────────┬────────┘      └─────────────────┘
         │ read-only (mode=ro)
         ▼
┌─────────────────┐
│  Web FastAPI    │  uvicorn web.app:app
│  Jinja2 +       │  oppure docker compose up
│  Bootstrap +    │
│  Leaflet        │
└────────┬────────┘
         │ HTML
         ▼
┌─────────────────┐
│  Browser utente │
│  (Lista/Mappa/  │
│   Dettaglio)    │
└─────────────────┘
```

## Stack tecnologico

| Strato | Tecnologia |
|---|---|
| Linguaggio | Python 3.12 |
| Scraping | Playwright (Chromium async) |
| HTTP client (geocoder) | `urllib.request` (no dipendenze esterne) |
| Storage | SQLite con WAL journal |
| Backend web | FastAPI + Uvicorn |
| Templating | Jinja2 |
| UI | Bootstrap 5.3 (CDN) |
| Mappe | Leaflet 1.9.4 + tile OpenStreetMap (CDN) |
| Geocoding | Nominatim OSM (`nominatim.openstreetmap.org`) |
| Test | pytest |
| Deploy web | Docker + docker-compose |

## Vincoli e principi guida

- **Costo zero per servizi terzi**: nessuna API key richiesta (Nominatim e OSM sono gratuiti, Leaflet via CDN).
- **Idempotenza**: rieseguire scraper o geocoder non duplica record né riscrive coordinate già presenti se non necessario.
- **Separazione dei concern**: scraper e web non si importano a vicenda; il DB è l'unica interfaccia.
- **Read-only sul DB lato web**: il container web monta `runts.db` come `:ro`; nessuna possibilità di scrittura dal lato HTTP.
- **Resilienza dello scraper**: errori sul singolo ente non interrompono il batch; viene loggato e si prosegue.

## Glossario

| Termine | Significato |
|---|---|
| **RUNTS** | Registro Unico Nazionale del Terzo Settore, gestito dal Ministero del Lavoro. |
| **Ente** | Singola organizzazione iscritta al RUNTS (nel nostro dominio: una sezione CAI). |
| **Sezione del registro** | Categoria di iscrizione al RUNTS (es. APS, ODV, altri enti del terzo settore). |
| **`id_runts`** | Identificatore univoco assegnato dal RUNTS a un ente (numero di repertorio). |
| **Codice fiscale** | CF dell'ente, usato come chiave secondaria (`UNIQUE`). |
| **Sede legale** | Indirizzo registrato dell'ente; dal RUNTS si estraggono stato, indirizzo, civico, comune, provincia, regione, CAP. |
| **Geocodifica** | Conversione comune/provincia in coordinate geografiche (lat/lon) via Nominatim. |
| **Upsert** | `INSERT OR REPLACE` su `id_runts` come chiave primaria. |
| **DNN** | DotNetNuke, il CMS su cui gira il portale RUNTS (rilevante perché i campi vengono caricati via JavaScript dopo `networkidle`). |
| **Nominatim** | Servizio di geocoding gratuito basato su dati OpenStreetMap. |

## Dataset di riferimento

Al momento della scrittura, l'ente `id_runts=83894` (CAI Pisa) è usato come caso di test per validare estrazione di sede legale completa e visualizzazione mappa nel dettaglio. Il dataset complessivo è dell'ordine di ~226 enti (Sezioni del CAI nel registro).
