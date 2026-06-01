# PRD: UX — Header/Footer fissi, Menu di navigazione, Filtri e nuove pagine

## Introduction

La web app attuale ha un header minimale senza navigazione, nessun footer, una lista limitata a 20 risultati per pagina e nessuna vista dedicata agli enti RUNTS o ai Gruppi Regionali CAI. Questa release aggiunge struttura navigazionale completa (header sticky, footer, menu a 4 voci), migliora l'usabilità della lista (50 risultati/pagina, filtro sanity check), introduce una pagina ETS dedicata e una pagina Gruppi Regionali alimentata da un nuovo scraper.

---

## Goals

- Navigazione coerente e persistente su tutte le pagine
- Identità visiva Montagna Servizi SCPA nel footer
- Lista più densa (50 vs 20 risultati)
- Filtro rapido per sezioni con anomalie nei dati
- Pagina ETS: visione completa degli enti RUNTS con evidenza dei non-agganciati
- Pagina Gruppi Regionali: 21 GR CAI con collegamento agli enti RUNTS corrispondenti

---

## Mapping campi API CAI → tabella `gruppi_regionali_cai`

Endpoint: `GET https://www.cai.it/wp-json/cai-section/v2/regional-groups-list`
Header: `Origin: https://www.cai.it`

| Campo API | Colonna DB | Tipo |
|-----------|-----------|------|
| `code` | `gr_codice` | TEXT PK |
| `name` | `gr_nome` | TEXT NOT NULL |
| `cf` | `gr_codice_fiscale` | TEXT nullable |
| `vat` | `gr_partita_iva` | TEXT nullable |
| `email` | `gr_email` | TEXT nullable |
| `pec` | `gr_pec` | TEXT nullable |
| `officePhone` | `gr_telefono_sede` | TEXT nullable |
| `phone` | `gr_telefono` | TEXT nullable |
| `fax` | `gr_fax` | TEXT nullable |
| `officeAddress` | `gr_indirizzo_sede` | TEXT JSON nullable |
| `postalAddress` | `gr_indirizzo_postale` | TEXT JSON nullable |
| `website` | `gr_sito_web` | TEXT nullable |
| `description` | `gr_descrizione` | TEXT nullable |
| `lastyearMembershipsCount` | `gr_soci_ultimo_anno` | INTEGER nullable |
| *(generato)* | `gr_scraped_at` | TEXT |
| *(matching)* | `gr_id_runts` | TEXT nullable (FK → enti.id_runts, popolato post-matching) |

---

## User Stories

### US-001: Header sticky Bootstrap
**Description:** As a user, I want the header to stay visible while scrolling so that I can always access navigation.

**Acceptance Criteria:**
- [ ] In `web/templates/base.html`, aggiungere classe `sticky-top` al `<nav class="navbar">`
- [ ] L'header rimane visibile durante lo scroll su tutte le pagine
- [ ] Nessuna regressione nel layout esistente
- [ ] Typecheck passes
- [ ] Verify in browser: scrollare la lista con 529 sezioni, l'header resta in cima

### US-002: Footer fisso con info Montagna Servizi SCPA
**Description:** As a user, I want a footer with company information so that I know who maintains this tool.

**Acceptance Criteria:**
- [ ] In `web/templates/base.html`, aggiungere un `<footer>` dopo il `<div class="container">` principale
- [ ] Il footer mostra: "Montagna Servizi S.C.P.A. — Via Errico Petrella 19, 20124 Milano — montagnaservizi.com"
- [ ] Il footer è sticky bottom (sempre visibile in fondo alla viewport), sfondo `bg-dark text-white` Bootstrap
- [ ] Il footer è presente su tutte le pagine (list, detail, ecc.)
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-003: Menu di navigazione con 4 voci
**Description:** As a user, I want a navigation menu so that I can move between the main sections of the app.

**Acceptance Criteria:**
- [ ] In `web/templates/base.html`, aggiungere 4 voci `<a class="nav-link">` nella navbar: **Sezioni** (→ `/`), **Gruppi Regionali** (→ `/gruppi-regionali`), **ETS** (→ `/ets`), **Statistiche** (→ `/stats`)
- [ ] La voce attiva viene evidenziata con classe `active` (determinata dal path corrente passato dal backend come variabile `active_page`)
- [ ] In `web/app.py`, tutte le route passano `active_page` al template (`"sezioni"`, `"gruppi-regionali"`, `"ets"`, `"stats"`)
- [ ] Il menu è collassabile su mobile (Bootstrap `navbar-toggler`)
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-004: Lista risultati a 50 elementi per pagina
**Description:** As a user, I want to see 50 results per page so that I scroll less and find items faster.

**Acceptance Criteria:**
- [ ] In `web/app.py`, cambiare `PAGE_SIZE = 20` in `PAGE_SIZE = 50`
- [ ] Il numero di pagine totali si aggiorna di conseguenza
- [ ] La paginazione funziona correttamente (LIMIT/OFFSET)
- [ ] Typecheck passes
- [ ] Verify in browser: la lista mostra 50 sezioni sulla prima pagina

### US-005: Filtro "Sanity check" nella lista Sezioni
**Description:** As a user, I want to filter the section list to show only entries with data quality issues so that I can identify and report problems.

**Acceptance Criteria:**
- [ ] Aggiungere un terzo filtro opzionale `?issues=1` alla lista `/`
- [ ] Quando attivo, la query mostra sezioni con almeno uno dei seguenti problemi:
  - `cai_match_note = 'fuzzy_nome'` → CF mancante nel registro CAI
  - `cai_match_note LIKE 'cf_mismatch%'` → CF diverso tra CAI e RUNTS
  - `e.lat IS NULL OR e.lon IS NULL` → coordinate geografiche mancanti nell'ente RUNTS collegato
  - `e.id_runts IS NOT NULL AND NOT EXISTS (SELECT 1 FROM bilanci b WHERE b.id_runts = e.id_runts)` → ente ETS senza bilanci
  - `e.id_runts IS NOT NULL AND NOT EXISTS (SELECT 1 FROM allegati a WHERE a.id_runts = e.id_runts)` → ente ETS senza allegati
- [ ] Aggiungere checkbox "Solo problemi dati" nella barra filtri, accanto a "Solo sezioni ETS"
- [ ] Il filtro si riflette nell'URL (`?issues=1`) e persiste nella paginazione
- [ ] Il contatore aggiornato mostra quante sezioni con problemi esistono
- [ ] Typecheck passes
- [ ] Verify in browser: attivare il filtro e verificare che compaiano solo sezioni con badge ⚠ o enti senza bilanci/allegati

### US-006: Pagina ETS (`/ets`)
**Description:** As a user, I want a dedicated page showing all RUNTS entities so that I can see the complete ETS list and spot those not linked to a CAI section.

**Acceptance Criteria:**
- [ ] Creare route `GET /ets` in `web/app.py` che fa SELECT su `enti` (tutti i 226 enti RUNTS) con LEFT JOIN `sezioni_cai`
- [ ] Creare template `web/templates/ets.html` che mostra una tabella con colonne: Denominazione (link a `/ente/<id_runts>`), Comune, Regione, Codice CAI (da sezioni_cai, o "—" se non agganciato), Status
- [ ] La colonna Status mostra: badge verde "Agganciato" se match sezioni_cai, badge arancione "Non agganciato" se no match, badge giallo "⚠ CF mancante CAI" o rosso "⚠ CF discordante" se match fuzzy
- [ ] Gli enti "Non agganciati" compaiono in cima alla lista (ORDER BY match status DESC)
- [ ] La pagina mostra il totale: "226 enti ETS — X agganciati, Y non agganciati"
- [ ] Typecheck passes
- [ ] Verify in browser: aprire `/ets` e verificare che i 31 enti non agganciati compaiano in cima con badge arancione

### US-007: DB — tabella `gruppi_regionali_cai` + migration
**Description:** As a developer, I need a database table for CAI regional groups so that they can be stored and displayed.

**Acceptance Criteria:**
- [ ] In `scraper/db.py`, aggiungere `CREATE TABLE IF NOT EXISTS gruppi_regionali_cai` con tutte le colonne del mapping sopra; `gr_codice` come PRIMARY KEY
- [ ] Aggiungere migration a `_MIGRATIONS`
- [ ] Aggiungere indice `idx_gr_cai_cf` su `gr_codice_fiscale`
- [ ] Implementare `upsert_gruppo_regionale(conn, data)` in `scraper/db.py`: INSERT OR REPLACE su `gr_codice`
- [ ] Typecheck passes

### US-008: Scraper Gruppi Regionali (`scraper/cai_scraper.py`)
**Description:** As a developer, I need a function to fetch the 21 CAI regional groups from the REST API so that the table is populated.

**Acceptance Criteria:**
- [ ] In `scraper/cai_scraper.py`, aggiungere funzione `fetch_regional_groups() -> list[dict]`
- [ ] Chiama `GET https://www.cai.it/wp-json/cai-section/v2/regional-groups-list` con header `Origin: https://www.cai.it`
- [ ] Normalizza con prefisso `gr_`: mappa `code→gr_codice`, `name→gr_nome`, `cf→gr_codice_fiscale`, ecc.
- [ ] Serializza `officeAddress`/`postalAddress` come JSON string
- [ ] Retry max 3 tentativi con backoff esponenziale
- [ ] Typecheck passes

### US-009: CLI scraper Gruppi Regionali (`scraper/cai_main.py`)
**Description:** As a developer, I need the CAI CLI to also fetch regional groups so they can be updated with a single command.

**Acceptance Criteria:**
- [ ] In `scraper/cai_main.py`, aggiungere flag `--no-groups` (skip GR fetch)
- [ ] Senza `--no-groups`, chiama `fetch_regional_groups()` e `upsert_gruppo_regionale()` per ogni record
- [ ] Tenta matching automatico con `enti` in ordine di priorità: (1) match esatto per `gr_codice_fiscale = enti.codice_fiscale` quando `gr_codice_fiscale` non è NULL; (2) fallback fuzzy per nome normalizzato (stesso algoritmo già in uso per sezioni) con score ≥ 0.5; aggiorna `gr_id_runts` se trovato
- [ ] Il report finale include: GR scaricati, inseriti, aggiornati, agganciati a RUNTS
- [ ] Typecheck passes

### US-010: Pagina Gruppi Regionali (`/gruppi-regionali`)
**Description:** As a user, I want a page showing all 21 CAI regional groups with their contact info and RUNTS link so that I have a complete overview of the CAI governance structure.

**Acceptance Criteria:**
- [ ] Creare route `GET /gruppi-regionali` in `web/app.py` che fa SELECT su `gruppi_regionali_cai` ORDER BY `gr_nome`
- [ ] Creare template `web/templates/gruppi_regionali.html` con tabella: Nome GR, Provincia (da `gr_indirizzo_sede` JSON campo province), Email, Telefono, Sito web, Ente RUNTS (link a `/ente/<gr_id_runts>` se agganciato, altrimenti "Non agganciato")
- [ ] Riga con `gr_id_runts` null evidenziata con sfondo `table-warning`
- [ ] In cima alla pagina: contatore "21 Gruppi Regionali — X agganciati a RUNTS"
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-011: Route stub `/stats`
**Description:** As a developer, I need a placeholder stats route so that the menu link doesn't return 404.

**Acceptance Criteria:**
- [ ] Creare route `GET /stats` in `web/app.py` che renderizza un template minimale `web/templates/stats.html`
- [ ] Il template mostra: titolo "Statistiche", sottotitolo "In costruzione", e alcuni numeri di riepilogo già disponibili senza costi aggiuntivi: totale sezioni CAI, totale enti ETS, totale allegati, totale bilanci analizzati
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

---

## Functional Requirements

- FR-1: `sticky-top` Bootstrap sul `<nav>` in `base.html`
- FR-2: Footer `bg-dark text-white` con ragione sociale, indirizzo, sito MS SCPA in `base.html`
- FR-3: Navbar con 4 link — Sezioni `/`, Gruppi Regionali `/gruppi-regionali`, ETS `/ets`, Statistiche `/stats`
- FR-4: `PAGE_SIZE = 50` in `web/app.py`
- FR-5: Filtro `?issues=1` nella lista Sezioni con 5 condizioni di problema (CF, coordinate, bilanci, allegati)
- FR-6: Pagina `/ets` con 226 enti RUNTS ordinati per status match (non agganciati in cima)
- FR-7: Tabella `gruppi_regionali_cai` con prefisso `gr_` + colonna `gr_id_runts` per matching RUNTS
- FR-8: `fetch_regional_groups()` in `cai_scraper.py` via `regional-groups-list` API
- FR-9: Matching automatico GR↔enti per nome normalizzato (score ≥ 0.5)
- FR-10: Pagina `/gruppi-regionali` con 21 GR, evidenzia non agganciati
- FR-11: Route stub `/stats` senza 404

---

## Non-Goals

- Nessun contenuto effettivo per la pagina `/stats` (solo stub)
- Nessuna autenticazione o gestione utenti
- Nessuna modifica alle schede ente esistenti
- Nessun matching manuale UI (solo automatico per nome)
- Nessuna modifica agli scraper RUNTS esistenti

---

## Design Considerations

- Tutti i componenti Bootstrap 5 già inclusi — `sticky-top`, `navbar-toggler`, `table-warning` disponibili
- Il footer non deve essere fixed (position fixed) ma solo alla fine del contenuto
- La voce attiva nel menu: il backend passa `active_page` come stringa, il template applica `{% if active_page == 'sezioni' %}active{% endif %}`
- La pagina ETS può riusare il template `list.html` come base, ma ha colonne diverse

---

## Technical Considerations

- `PAGE_SIZE = 50` tocca anche le API GeoJSON/CSV/Excel — verificare che non cambino comportamento (usano query separate)
- Il filtro `?issues=1` può essere combinato con `?ets=1` e `?regione=XX` — la query deve supportare AND multipli
- `gr_id_runts` è nullable e popolato solo se il matching automatico trova un match; non è una FK hard con REFERENCES per evitare errori su enti non ancora presenti

---

## Success Metrics

- Header visibile dopo 500px di scroll
- Footer presente su tutte le pagine
- Lista mostra 50 elementi sulla prima pagina
- Filtro "Problemi dati" restituisce risultati coerenti con i badge ⚠ già visibili
- Pagina ETS mostra correttamente i 31 non agganciati in cima
- Pagina GR mostra 21 gruppi senza 404

---

## Decisioni prese

- **Footer**: sticky bottom ✓ — sempre visibile in fondo alla viewport (`fixed-bottom` Bootstrap)
- **Statistiche**: stub con numeri di riepilogo (sezioni, enti ETS, allegati, bilanci) — contenuto completo in release futura
- **Matching GR↔enti**: CF esatto quando `gr_codice_fiscale` non è NULL, fallback fuzzy per nome normalizzato ✓
