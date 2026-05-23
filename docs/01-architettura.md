# 01 — Architettura

> Fotografia dei componenti, delle loro interfacce e dei loro confini.

## Struttura del repository

```
RUNTS/
├── Dockerfile               # immagine container per la sola web app
├── docker-compose.yml       # servizio "web" con bind di runts.db in :ro
├── runts.db                 # database SQLite (popolato da scraper + geocoder)
├── openspec/                # spec OpenSpec (gestita da ClaudeCode)
│   ├── specs/               #   capability con spec correnti
│   └── changes/             #   change proposte e archiviate
├── docs/                    # materiale per generare nuove spec (questo dir)
├── scraper/                 # package Python dello scraper + geocoder
│   ├── __init__.py
│   ├── main.py              # entrypoint CLI: python -m scraper.main
│   ├── scraper.py           # logica Playwright: ricerca + estrazione
│   ├── db.py                # schema, migrazioni, upsert
│   ├── geocoder.py          # script Nominatim, eseguibile come modulo
│   ├── test_sede_legale.py  # test pytest sulla regex/estrazione sede
│   └── requirements.txt     # playwright + pytest
└── web/                     # web app FastAPI
    ├── app.py               # routes / e /ente/<id_runts>
    ├── requirements.txt     # fastapi, uvicorn[standard], jinja2
    ├── static/              # cartella montata (attualmente vuota)
    └── templates/           # Jinja2
        ├── base.html        # layout Bootstrap + navbar
        ├── list.html        # lista + filtri + toggle Lista/Mappa
        ├── detail.html      # scheda ente + mappa Leaflet condizionale
        └── 404.html         # ente non trovato
```

### Vincoli di layout

Lo scraper è isolato in `scraper/` come package importabile (`import scraper` funziona). I file dello scraper non devono comparire alla radice del progetto. Le dipendenze sono in `scraper/requirements.txt` per lo scraper e `web/requirements.txt` per la web app — i due file non condividono pacchetti.

Il file `runts.db` vive **alla radice del progetto** (non dentro `scraper/`): è l'unico canale di comunicazione tra scraper, geocoder e web app.

## Diagramma logico dei componenti

```
                    ┌────────────────────────────────────┐
                    │       RUNTS portal (esterno)       │
                    │ servizi.lavoro.gov.it/runts/it-it  │
                    └─────────────────┬──────────────────┘
                                      │ Chromium async (Playwright)
                                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                          scraper/                                │
│                                                                  │
│   main.py ──► scraper.py ──► extract_fields() ──► db.upsert_ente │
│        ▲              │                                          │
│        │              └─► search_enti / paginazione / back nav   │
│   argparse                                                       │
│   logging                                                        │
└──────────────────────────────────┬──────────────────────────────┘
                                   │ INSERT OR REPLACE
                                   ▼
                          ┌──────────────────┐
                          │    runts.db      │
                          │   SQLite WAL     │
                          │  tabella `enti`  │
                          └────┬─────────┬───┘
                       lat/lon │         │ read-only (mode=ro)
                       UPDATE  │         │
                               │         ▼
        ┌──────────────────────┘    ┌───────────────────────┐
        │                            │       web/app.py       │
        │   scraper/geocoder.py      │                        │
        │   (Nominatim, 1 req/s)     │  GET /                 │
        │                            │  GET /ente/<id_runts>  │
        └────────────────────────────┴──────────┬─────────────┘
                                                │ Jinja2
                                                ▼
                                       ┌────────────────────┐
                                       │ Bootstrap 5 +      │
                                       │ Leaflet 1.9.4      │
                                       │ (CDN)              │
                                       └────────────────────┘
```

## Interfacce tra componenti

### Scraper → DB
- API interna Python: `db.init_db(path) -> sqlite3.Connection` e `db.upsert_ente(conn, data) -> "inserted" | "updated"`.
- Chiave primaria: `id_runts` (fallback `codice_fiscale`).
- Tutti i campi sono `TEXT` tranne `lat`, `lon` (`REAL`) e `updated_at` (`TEXT NOT NULL` con timestamp ISO UTC).

### Geocoder → DB
- Apertura diretta del DB (`sqlite3.connect`), `row_factory = sqlite3.Row`.
- Lettura: `SELECT id_runts, sede_comune, sede_regione FROM enti WHERE lat IS NULL OR lon IS NULL`.
- Scrittura: `UPDATE enti SET lat = ?, lon = ? WHERE id_runts = ?`.

### Geocoder → Nominatim
- Endpoint: `https://nominatim.openstreetmap.org/search`.
- User-Agent obbligatorio (per Nominatim policy): `runts-cai-geocoder/1.0 (https://github.com/piccioli/runts)`.
- Parametri: `q=<Comune>, <Regione>, Italia`, `format=json`, `limit=1`.
- Rate limit applicato: `time.sleep(1)` dopo ogni richiesta.

### Web → DB
- `sqlite3.connect("file:<DB_PATH>?mode=ro", uri=True, check_same_thread=False)`.
- `row_factory = sqlite3.Row` per accesso per nome di colonna.
- Una connessione per request (apertura + `try/finally` di `close`).

### Web → Browser
- Risposta `text/html` via `TemplateResponse` di FastAPI.
- Asset frontend (Bootstrap, Leaflet, tile OSM) caricati da CDN, **nessun bundle locale**.
- La cartella `web/static/` è montata su `/static` ma attualmente è vuota.

## Configurazione

| Variabile | Default | Componente | Note |
|---|---|---|---|
| `DB_PATH` | `/app/runts.db` | web app | Letta da `os.environ` in `web/app.py`. |
| `--db` | `runts.db` | scraper / geocoder | Argomento CLI. |
| `--headless` | `True` | scraper | `--no-headless` per debug visivo del browser. |
| `--delay` | `500` ms | scraper | Pausa tra una pagina di dettaglio e la successiva. |
| `--verbose` / `-v` | `False` | scraper / geocoder | Abilita log a livello DEBUG. |

Non esistono altri file `.env`, secret manager o config esterni.

## Modello di esecuzione

Il sistema **non ha scheduler interno**. Ogni operazione è on-demand:

1. **Aggiornamento dati**: l'operatore lancia `python -m scraper.main` quando serve rinfrescare il DB. La durata dipende dal numero di enti (~226 × ~3 s di rendering + delay 0.5 s ≈ 12-15 minuti).
2. **Geocodifica**: l'operatore lancia `python -m scraper.geocoder --db runts.db` dopo lo scraper. Durata ~4 minuti per 226 enti (rate limit 1 req/s).
3. **Servizio web**: avviato una tantum con `docker compose up -d`, resta su finché non viene fermato; legge il DB ad ogni richiesta HTTP (nessuna cache applicativa).

Lo scraper può essere rieseguito mentre il container web è attivo: SQLite in WAL mode + montaggio `:ro` lato web permette letture concorrenti senza riavvio.

## Confini e non-goal architetturali

- Nessuna API REST/JSON: la web app serve solo HTML.
- Nessuna autenticazione: l'app è pensata per consultazione pubblica/interna.
- Nessuna scrittura via HTTP: il DB è read-only dal lato applicativo.
- Nessun job scheduler, message queue, cache distribuita.
- Nessun bundler frontend (no webpack/vite); tutto via CDN.
- Nessun ORM: SQL diretto via `sqlite3` standard library.
