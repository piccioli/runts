# PRD: Integrazione dati CAI — Scraping sezioni, nuova lista e filtro ETS

## Introduction

Il sito cai.it espone una REST API (`/wp-json/cai-section/v2/sections-list-simple?region=<REGIONE>`) che contiene i dati ufficiali di tutte le Sezioni CAI italiane: codice sezione, denominazione, contatti, coordinate, anno di fondazione, numero soci e — crucialmente — il **codice fiscale**, che permette il collegamento con i record RUNTS già in DB.

Con questa feature:
1. Uno scraper recupera tutti i dati CAI per le 20 regioni e li salva in una nuova tabella `sezioni_cai`
2. La lista principale (`/`) mostra le sezioni dalla tabella `sezioni_cai` (fonte CAI), non più dalla tabella `enti` RUNTS
3. Un nuovo filtro "Solo ETS" mostra solo le sezioni che hanno una corrispondenza su RUNTS (= registrate come ETS)

---

## Goals

- Avere un registro completo delle sezioni CAI (incluse quelle non ancora su RUNTS)
- Collegare automaticamente ogni sezione CAI alla sua scheda RUNTS tramite codice fiscale
- Permettere all'utente di filtrare la lista per vedere solo le sezioni ETS (registrate RUNTS)
- Arricchire la lista con il codice CAI ufficiale e i dati di contatto

---

## Mapping campi API CAI → tabella `sezioni_cai`

| Campo API | Colonna DB | Tipo | Note |
|-----------|-----------|------|------|
| `code` | `codice_cai` | TEXT PK | Codice numerico 7 cifre, es. "9226003" |
| `name` | `cai_denominazione` | TEXT NOT NULL | Es. "SEZ. PISA" |
| `cf` | `cai_codice_fiscale` | TEXT | FK → `enti.codice_fiscale` (nullable: sezioni non ETS) |
| `vat` | `cai_partita_iva` | TEXT | nullable |
| `email` | `cai_email` | TEXT | nullable |
| `pec` | `cai_pec` | TEXT | nullable |
| `officePhone` | `cai_telefono_sede` | TEXT | nullable |
| `phone` | `cai_telefono` | TEXT | nullable |
| `fax` | `cai_fax` | TEXT | nullable |
| `officeAddress` | `cai_indirizzo_sede` | TEXT | JSON serializzato |
| `postalAddress` | `cai_indirizzo_postale` | TEXT | JSON serializzato, nullable |
| `website` | `cai_sito_web` | TEXT | nullable |
| `timetable` | `cai_orari` | TEXT | HTML, nullable |
| `notice` | `cai_avvisi` | TEXT | HTML, nullable |
| `foundationYear` | `cai_anno_fondazione` | INTEGER | nullable |
| `lastyearMembershipsCount` | `cai_soci_ultimo_anno` | INTEGER | nullable |
| `latitude` | `cai_lat` | REAL | nullable |
| `longitude` | `cai_lon` | REAL | nullable |
| `region` | `cai_regione` | TEXT NOT NULL | Es. "TOSCANA" |
| *(generato)* | `cai_scraped_at` | TEXT | ISO timestamp |

---

## Mapping campi API CAI → tabella `sottosezioni_cai`

Endpoint: `GET https://www.cai.it/wp-json/cai-section/v2/sections/{codice}/sub-sections-list`
Header richiesto: `Origin: https://www.cai.it`

| Campo API | Colonna DB | Tipo | Note |
|-----------|-----------|------|------|
| `code` | `cai_codice` | TEXT PK | Codice numerico, es. "9116003" |
| *(FK parent)* | `cai_sezione_codice` | TEXT NOT NULL | FK → `sezioni_cai.codice_cai` |
| `name` | `cai_nome` | TEXT NOT NULL | Es. "S.SEZ. ALBINO" |
| `email` | `cai_email` | TEXT | nullable |
| `officePhone` | `cai_telefono_sede` | TEXT | nullable |
| `phone` | `cai_telefono` | TEXT | nullable |
| `officeAddress` | `cai_indirizzo_sede` | TEXT | JSON serializzato |
| `website` | `cai_sito_web` | TEXT | nullable |
| `timetable` | `cai_orari` | TEXT | HTML, nullable |
| `notice` | `cai_avvisi` | TEXT | HTML, nullable |
| `foundationYear` | `cai_anno_fondazione` | INTEGER | nullable |
| `currentMemberships` | `cai_soci` | INTEGER | nullable |
| `latitude` | `cai_lat` | REAL | nullable |
| `longitude` | `cai_lon` | REAL | nullable |
| *(generato)* | `cai_scraped_at` | TEXT | ISO timestamp |

---

## User Stories

### US-001: Tabelle `sezioni_cai` e `sottosezioni_cai` + migration DB
**Description:** As a developer, I need two database tables to store CAI section and sub-section data so that they can be queried independently and linked by parent code.

**Acceptance Criteria:**
- [ ] In `scraper/db.py`, aggiungere `CREATE TABLE IF NOT EXISTS sezioni_cai` con tutte le colonne del mapping sezioni; `codice_cai` come PRIMARY KEY
- [ ] Aggiungere `CREATE TABLE IF NOT EXISTS sottosezioni_cai` con tutte le colonne del mapping sottosezioni; `cai_codice` come PRIMARY KEY, `cai_sezione_codice` TEXT NOT NULL REFERENCES `sezioni_cai(codice_cai)`
- [ ] Aggiungere entrambe le migration a `_MIGRATIONS` con il DDL completo
- [ ] Aggiungere indice `idx_sezioni_cai_cf` su `cai_codice_fiscale` per il JOIN con `enti`
- [ ] Aggiungere indice `idx_sezioni_cai_regione` su `cai_regione`
- [ ] Aggiungere indice `idx_sottosezioni_cai_sezione` su `cai_sezione_codice`
- [ ] Implementare `upsert_sezione_cai(conn, data)` in `scraper/db.py`: INSERT OR REPLACE su `codice_cai`
- [ ] Implementare `upsert_sottosezione_cai(conn, data)` in `scraper/db.py`: INSERT OR REPLACE su `cai_codice`
- [ ] Typecheck passes

### US-002: Scraper CAI — fetch da REST API per tutte le regioni
**Description:** As a developer, I need a scraper module that fetches all CAI sections from the cai.it REST API so that the database stays up to date.

**Acceptance Criteria:**
- [ ] Creare `scraper/cai_scraper.py` con funzione `fetch_all_sections() -> list[dict]`
- [ ] La funzione itera sulle 20 regioni italiane: `["abruzzo","basilicata","calabria","campania","emilia-romagna","friuli-venezia-giulia","lazio","liguria","lombardia","marche","molise","piemonte","puglia","sardegna","sicilia","toscana","trentino-alto-adige","umbria","valle-d-aosta","veneto"]`
- [ ] Per ogni regione chiama `GET https://www.cai.it/wp-json/cai-section/v2/sections-list-simple?region=<regione>` con `httpx` (già in requirements)
- [ ] Normalizza la risposta JSON nel formato del mapping (incluso serializzare `officeAddress`/`postalAddress` come JSON string)
- [ ] Gestisce errori di rete con retry (max 3 tentativi, backoff esponenziale)
- [ ] Typecheck passes

### US-002b: Scraper CAI — fetch sottosezioni per ogni sezione
**Description:** As a developer, I need the scraper to also fetch sub-sections for each CAI section so that the `sottosezioni_cai` table is populated.

**Acceptance Criteria:**
- [ ] In `scraper/cai_scraper.py`, aggiungere funzione `fetch_subsections(codice_sezione: str) -> list[dict]`
- [ ] Chiama `GET https://www.cai.it/wp-json/cai-section/v2/sections/{codice_sezione}/sub-sections-list` con header `Origin: https://www.cai.it`
- [ ] Se la sezione non ha sottosezioni (risposta vuota o 404), ritorna lista vuota senza errore
- [ ] Normalizza la risposta aggiungendo `cai_sezione_codice = codice_sezione` a ogni record
- [ ] Gestisce errori di rete con retry (max 3 tentativi, backoff esponenziale), identico a `fetch_all_sections()`
- [ ] Typecheck passes

### US-003: CLI scraper CAI (`scraper/cai_main.py`)
**Description:** As a developer, I need a runnable CLI entry point for the CAI scraper so that it can be executed from the command line and scheduled.

**Acceptance Criteria:**
- [ ] Creare `scraper/cai_main.py` con argparse: `--db PATH` (default: `runts.db`), `--verbose`, `--no-subsections` (skip sottosezioni fetch)
- [ ] Esegue `fetch_all_sections()` e chiama `upsert_sezione_cai()` per ogni record
- [ ] Per ogni sezione inserita/aggiornata, chiama `fetch_subsections(codice)` e `upsert_sottosezione_cai()` per ogni risultato (salvo `--no-subsections`)
- [ ] Stampa un report finale: sezioni scaricate, sottosezioni scaricate, inserite, aggiornate, fallite
- [ ] Eseguibile come `python3 -m scraper.cai_main`
- [ ] Typecheck passes

### US-004: Lista principale usa `sezioni_cai` come sorgente primaria
**Description:** As a user, I want the main list to show all CAI sections (not just RUNTS entities) so that I have a complete view of the CAI network.

**Acceptance Criteria:**
- [ ] In `web/app.py`, la route `GET /` fa SELECT su `sezioni_cai` (non più su `enti`) come sorgente principale
- [ ] Per ogni riga, esegue LEFT JOIN con `enti` su `sezioni_cai.cai_codice_fiscale = enti.codice_fiscale` per arricchire con `id_runts` e `sezione_registro`
- [ ] Le colonne mostrate nella lista sono: `cai_denominazione`, `cai_regione`, `codice_cai`, comune (da `cai_indirizzo_sede` JSON), e badge "ETS" se la sezione ha un record RUNTS
- [ ] Il filtro per regione usa `sezioni_cai.cai_regione` (non più `enti.sede_regione`)
- [ ] La paginazione (LIMIT/OFFSET) funziona correttamente
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-005: Filtro "Solo ETS" nella lista
**Description:** As a user, I want to filter the list to show only sections registered on RUNTS so that I can focus on ETS entities.

**Acceptance Criteria:**
- [ ] Aggiungere checkbox o toggle "Solo sezioni ETS" nell'header della lista (accanto ai filtri esistenti)
- [ ] Quando attivo, la query filtra `WHERE sezioni_cai.cai_codice_fiscale IS NOT NULL AND enti.id_runts IS NOT NULL` (solo sezioni con match RUNTS)
- [ ] Il filtro si riflette nell'URL (`?ets=1`) e persiste tra le pagine
- [ ] Il contatore totale si aggiorna in base al filtro attivo
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-006: Colonna "Codice CAI" e badge ETS nella lista
**Description:** As a user, I want to see the CAI section code and an ETS badge in the list so that I can identify sections at a glance.

**Acceptance Criteria:**
- [ ] Ogni riga della lista mostra il `codice_cai` (es. "9226003") in una colonna dedicata
- [ ] Le righe con corrispondenza RUNTS mostrano un badge/icona "ETS" (es. badge Bootstrap `bg-success`)
- [ ] Le righe senza corrispondenza RUNTS non mostrano il badge e il link alla scheda è assente (o disabilitato)
- [ ] Il link alla scheda ente (`/ente/<id_runts>`) è presente solo se `id_runts` è non null
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-007: Scheda ente — quinta tab "Sottosezioni"
**Description:** As a user, I want a dedicated tab for sub-sections on the section detail page so that I can see all local groups at a glance without cluttering the main data tab.

**Acceptance Criteria:**
- [ ] In `web/app.py`, la route `GET /ente/{id_runts}`: recupera le sottosezioni tramite JOIN `sezioni_cai → sottosezioni_cai` su `codice_cai = cai_sezione_codice`, usando `cai_codice_fiscale` della sezione come ponte con `enti.codice_fiscale`; passa la lista come `sottosezioni` (ordinata per `cai_nome`)
- [ ] In `web/templates/detail.html`, aggiungere una quinta tab "Sottosezioni" (slug: `sottosezioni`) al menu `nav-tabs`, dopo "Mappa"
- [ ] Il pannello `tab-pane#sottosezioni` mostra una tabella con colonne: Nome, Comune, Telefono, Email, Soci, Anno fondazione
- [ ] Il comune viene estratto da `cai_indirizzo_sede` (JSON): campo `city`
- [ ] Se `sottosezioni` è lista vuota, il pannello mostra `<p class="text-muted">Nessuna sottosezione registrata.</p>`
- [ ] La tab è sempre visibile nel menu (non nascosta se vuota)
- [ ] Lo slug `sottosezioni` è aggiunto ai valori accettati in `app.py` (`_VALID_TABS`)
- [ ] `history.replaceState` già esistente gestisce automaticamente il nuovo slug
- [ ] Typecheck passes
- [ ] Verify in browser: aprire la scheda di CAI Bergamo (`cai_codice_fiscale = 80004970168`), tab "Sottosezioni" → deve mostrare le 30 sottosezioni; aprire CAI Pisa → deve mostrare il messaggio vuoto

---

## Functional Requirements

- FR-1: La tabella `sezioni_cai` contiene tutte le colonne del mapping con `codice_cai` come PK
- FR-2: La tabella `sottosezioni_cai` contiene tutte le colonne del mapping con `cai_codice` come PK e FK `cai_sezione_codice → sezioni_cai.codice_cai`
- FR-3: Lo scraper sezioni usa `GET /wp-json/cai-section/v2/sections-list-simple?region=<regione>` per le 20 regioni
- FR-4: Lo scraper sottosezioni usa `GET /wp-json/cai-section/v2/sections/{codice}/sub-sections-list` con header `Origin: https://www.cai.it` per ogni sezione
- FR-5: Il collegamento tra `sezioni_cai` e `enti` avviene su `cai_codice_fiscale = enti.codice_fiscale` (LEFT JOIN)
- FR-6: La lista principale mostra sezioni da `sezioni_cai`, non da `enti`
- FR-7: Il filtro `?ets=1` restringe la lista alle sole sezioni con match RUNTS
- FR-8: Il link alla scheda ente è presente solo per le sezioni con corrispondenza RUNTS
- FR-9: La scheda ente ha una quinta tab "Sottosezioni" (slug: `sottosezioni`) che mostra nome, comune, contatti, soci, anno fondazione di ogni sottosezione

---

## Non-Goals

- Nessun scraping delle pagine HTML individuali (solo REST API)
- Nessuna pagina di dettaglio dedicata per le sottosezioni (solo riga nella scheda della sezione padre)
- Nessuna modifica alla scheda ente (`/ente/<id_runts>`)
- Nessuna sincronizzazione bidirezionale (i dati CAI non sovrascrivono i dati RUNTS)
- Nessuna schedulazione automatica dello scraper (esecuzione manuale)
- Nessun matching fuzzy per denominazione: solo CF

---

## Technical Considerations

- **API CAI**: endpoint REST già identificato `/wp-json/cai-section/v2/sections-list-simple?region=<regione>`, risponde JSON, nessuna autenticazione richiesta
- **httpx**: già presente in `scraper/requirements.txt`, usare client sincrono (non async) per semplicità
- **officeAddress/postalAddress**: oggetti JSON annidati → serializzare con `json.dumps()` e salvare come TEXT; il web app li deserializza con `json.loads()` al momento della visualizzazione
- **Regioni da interrogare**: 20 slug in minuscolo corrispondenti alla naming CAI (attenzione: "emilia-romagna", "friuli-venezia-giulia", "trentino-alto-adige", "valle-d-aosta")
- **Impatto sulla lista esistente**: la route `GET /` cambia sorgente da `enti` a `sezioni_cai` — i filtri esistenti per `sezione_registro` diventano inutilizzabili (erano specifici RUNTS); vanno sostituiti con filtri su `sezioni_cai.regione` e il nuovo `?ets=1`

---

## Design Considerations

- Il badge ETS può essere un `<span class="badge bg-success">ETS</span>` Bootstrap già disponibile
- Le righe senza ETS (sezioni non RUNTS) mostrano la denominazione in testo normale (non link)
- Il toggle "Solo ETS" può essere un checkbox nella barra filtri esistente o un tab separato

---

## Success Metrics

- Lo scraper recupera sezioni da tutte le 20 regioni senza errori
- La lista mostra sezioni anche non presenti su RUNTS (es. nuove sezioni o non ancora iscritte)
- Il filtro "Solo ETS" mostra esattamente le sezioni con `id_runts` non null
- Il codice CAI è visibile per ogni riga

---

## Open Questions

- Le sezioni CAI non ancora su RUNTS devono avere una pagina di dettaglio propria, o solo la riga nella lista? (per ora: solo la riga, nessuna pagina dettaglio per le non-ETS)
- Il filtro regione esistente nella lista va mantenuto compatibile dopo il cambio di sorgente? (sì, ma usa `sezioni_cai.cai_regione` invece di `enti.sede_regione`)
- Se una sezione ha `cai_codice_fiscale` valorizzato ma il CF non esiste in `enti`, mostrare comunque `cai_codice_fiscale` come testo nella lista? (da decidere)
