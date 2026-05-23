# docs/ — Materiale per le specifiche OpenSpec

Questa cartella raccoglie la **fotografia dello stato attuale** del progetto RUNTS-CAI, scritta a partire dalla lettura diretta del codice. Serve come input umano per generare/aggiornare le spec OpenSpec in `openspec/specs/` e `openspec/changes/`.

> ⚠️ Convenzione di questo workspace: in `RUNTS/` ci sta già lavorando ClaudeCode. Da qui in poi gli aggiornamenti **descrittivi** vivono qui in `docs/`. Le spec OpenSpec restano la sorgente di verità formale e si aggiornano coordinandosi con ClaudeCode.

## Come è organizzato il materiale

| File | Contenuto |
|---|---|
| [`00-overview.md`](./00-overview.md) | Scopo del progetto, attori, componenti, flusso end-to-end, glossario, stack tecnologico. |
| [`01-architettura.md`](./01-architettura.md) | Struttura del repo, diagramma dei componenti, interfacce, configurazione, vincoli architetturali. |
| [`02-scraper.md`](./02-scraper.md) | Comportamento dello scraper Playwright: ricerca, paginazione, estrazione dei campi, mapping provincia→regione, gestione errori. |
| [`03-database.md`](./03-database.md) | Schema della tabella `enti`, migrazioni, upsert, regole di chiave, comportamento di `INSERT OR REPLACE`. |
| [`04-geocoder.md`](./04-geocoder.md) | Geocoder Nominatim: query, rate limit, derivazione regione, idempotenza, casi di fallimento. |
| [`05-web-app.md`](./05-web-app.md) | Web app FastAPI: route, parametri, template Jinja2, mappa Leaflet, sicurezza. |
| [`06-deploy.md`](./06-deploy.md) | Dockerfile, docker-compose, esecuzione tipica, variabili d'ambiente, gestione del DB. |

## Come usare questi documenti per OpenSpec

Ogni file in `docs/` può alimentare una o più capability OpenSpec. Mapping suggerito allo stato attuale:

| File `docs/` | Capability OpenSpec correlate |
|---|---|
| `02-scraper.md` | `runts-search`, `runts-detail`, `scraper-layout` |
| `03-database.md` | `database-storage` |
| `04-geocoder.md` | `geocoding` (proposta in `openspec/changes/mappa-enti/`) |
| `05-web-app.md` | `enti-list`, `ente-detail`, `mappa-lista`, `mappa-dettaglio` |
| `06-deploy.md` | `web-docker` |

Per ogni nuova proposta di modifica si può:

1. Identificare la capability impattata.
2. Aggiornare la sezione corrispondente in `docs/` con la nuova descrizione comportamentale.
3. Estrarre i requisiti SHALL e gli scenari WHEN/THEN da quella descrizione e formalizzarli in `openspec/changes/<change-name>/specs/<capability>/spec.md`.

## Convenzioni di scrittura

- **Italiano** in tutti i documenti, coerente con codice e commenti del progetto.
- **Markdown semplice**: titoli, paragrafi, tabelle, code-block. Niente HTML inline.
- **Riferimenti al codice ancorati**: ogni claim non ovvio cita il file e (quando utile) la funzione o le righe.
- **Niente decisioni nuove**: questi documenti **fotografano** lo stato attuale; le decisioni progettuali vanno in `openspec/changes/<change>/design.md`.

## Indicatori di stato

I documenti riflettono il codice presente nel repository alla data di stesura. Quando ClaudeCode modifica `scraper/`, `web/` o lo schema DB:

1. Aggiornare il file `docs/` corrispondente.
2. Aprire (o aggiornare) il change OpenSpec correlato.
3. Verificare che le affermazioni nel `docs/` siano ancora ancorate al codice.
