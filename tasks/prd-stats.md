# PRD: Pagina Statistiche `/stats`

## Introduction

La pagina `/stats` mostra oggi solo 4 contatori e il testo "In costruzione". Questa release la trasforma in una dashboard analitica completa con KPI estesi, grafici Chart.js (bar, line, donut), mappa coropleta D3 e tabelle di qualità dati — tutto alimentato dai dati reali già in DB.

**Librerie:**
- **Chart.js 4.x** via CDN — bar chart, line chart, donut chart
- **D3.js 7.x** via CDN — solo per la mappa coropleta SVG
- **GeoJSON regioni italiane** — file statico in `web/static/it-regions.geojson`

**Dati reali disponibili:**
- 529 sezioni CAI, 367.665 soci totali, 21 GR (5 agganciati)
- 226 enti ETS, 20 con bilanci, 21 con allegati, 184 agganciati a sezione CAI
- Bilanci 2021-2025 su 20 enti (dati completi su ~10 enti ER)
- 224 sottosezioni, 101 sezioni con sottosezioni

---

## Goals

- Offrire una visione d'insieme immediata della rete CAI tramite KPI e grafici
- Evidenziare le lacune di dati per guidare le priorità di scraping
- Nessuna dipendenza da server-side rendering complesso: i dati vengono iniettati come JSON inline nel template

---

## Technical Considerations

- **Dati come JSON inline**: la route `/stats` calcola tutte le aggregazioni SQL e le passa al template come variabili; il template le serializza con `tojson` e le passa ai costruttori Chart.js e D3. Nessuna chiamata AJAX.
- **GeoJSON**: scaricare `https://raw.githubusercontent.com/openpolis/geoboundaries-ita/main/geojson/limits_IT_regions.geojson` (o equivalente con nomi regione uppercase) e salvarlo in `web/static/it-regions.geojson`. Il server FastAPI deve montare `web/static/` come `StaticFiles` se non già fatto.
- **Normalizzazione nomi regione**: il DB ha `cai_regione` in uppercase (es. "LOMBARDIA") mentre il GeoJSON potrebbe avere varianti. La mappatura va gestita in JavaScript con un dizionario di normalizzazione.
- **Chart.js** e **D3** inclusi via CDN solo nel blocco `{% block head %}` di `stats.html`, non in `base.html`.

---

## User Stories

### US-001: KPI riepilogo esteso (7 card)
**Description:** As a user, I want to see the key numbers at a glance so that I can immediately understand the scale of the CAI network.

**Acceptance Criteria:**
- [ ] La route `/stats` in `web/app.py` calcola e passa al template: `sezioni_totali`, `soci_totali`, `enti_ets`, `ets_agganciati`, `gr_totali`, `gr_agganciati`, `copertura_bilanci_pct` (= round(enti_con_bilanci / enti_ets * 100, 1))
- [ ] `web/templates/stats.html`: sostituisce le 4 card attuali con 7 card Bootstrap in riga: Sezioni CAI, Soci totali, Enti ETS, ETS agganciati CAI (con badge "X/226"), GR agganciati (con badge "5/21"), Bilanci analizzati, Copertura bilanci %
- [ ] Rimosso il testo "In costruzione"
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-002: Backend — aggregazioni SQL per tutti i grafici
**Description:** As a developer, I need all chart data pre-computed server-side so that the template can render charts without AJAX calls.

**Acceptance Criteria:**
- [ ] La route `/stats` calcola e passa: `soci_per_regione` (lista di dict {regione, n_sezioni, soci} ordinata per soci DESC), `proventi_2024_per_regione` (lista {regione, totale_proventi} per regione degli enti ETS con anno=2024), `top10_soci` (lista {cai_denominazione, cai_soci_ultimo_anno, codice_cai} LIMIT 10), `top10_sottosezioni` (lista {cai_denominazione, n_sottosezioni, codice_cai} LIMIT 10), `allegati_per_tipo` (lista {tipo, n}), `bilanci_per_ente` (lista {id_runts, denominazione, anni: [{anno, totale_proventi}]} per enti con almeno 2 anni di dati)
- [ ] `copertura_ets` dict: {totale: 226, agganciati: 184, con_bilanci: 20, con_allegati: 21, con_coordinate: 226}
- [ ] `qualita_dati` lista di 4 dict: {label, n, url} per i 4 problemi documentati
- [ ] Tutti i dati serializzati con `tojson` disponibili come variabili Jinja2
- [ ] Typecheck passes

### US-003: Scarica e integra GeoJSON regioni italiane
**Description:** As a developer, I need the Italian regions GeoJSON so that D3 can render the choropleth map.

**Acceptance Criteria:**
- [ ] Scaricare il file GeoJSON delle regioni italiane con nomi in italiano (es. da `https://raw.githubusercontent.com/openpolis/geoboundaries-ita/main/geojson/limits_IT_regions.geojson`) e salvarlo in `web/static/it-regions.geojson`
- [ ] In `web/app.py`, montare `StaticFiles(directory="web/static")` su `/static` se non già presente
- [ ] Verificare che `GET /static/it-regions.geojson` risponda 200
- [ ] Typecheck passes

### US-004: Grafico — bar chart soci per regione (Chart.js)
**Description:** As a user, I want to see how members are distributed across regions so that I can understand the geographic weight of each area.

**Acceptance Criteria:**
- [ ] In `stats.html`, aggiungere sezione "Soci per regione" con `<canvas id="chart-soci-regione">`
- [ ] Chart.js horizontal bar chart: asse Y = regioni ordinate per soci DESC, asse X = numero soci, colore `rgba(13,110,253,0.7)` (Bootstrap primary)
- [ ] Tooltip mostra: "X soci — Y sezioni"
- [ ] Dati provengono da `soci_per_regione | tojson` iniettato inline
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-005: Tabella — top 10 sezioni per soci
**Description:** As a user, I want to see the largest sections by membership so that I know the heavyweights of the network.

**Acceptance Criteria:**
- [ ] In `stats.html`, sezione "Top 10 sezioni per numero soci" con tabella: Pos, Denominazione (link a `/sezione/<codice_cai>`), Soci, barra progress `<div class="progress">` proporzionale al massimo (SEZ. S.A.T. = 28.992)
- [ ] Dati da `top10_soci | tojson`
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-006: Progress bars — copertura dati ETS
**Description:** As a user, I want to see data coverage for ETS entities so that I know how complete the dataset is.

**Acceptance Criteria:**
- [ ] In `stats.html`, sezione "Copertura dati ETS" con 4 righe: Agganciati a sezione CAI (184/226), Con bilanci analizzati (20/226), Con allegati scaricati (21/226), Con coordinate geografiche (226/226)
- [ ] Ogni riga: etichetta, barra `progress-bar` Bootstrap con larghezza proporzionale, testo "X/226 (Y%)"
- [ ] Dati da `copertura_ets | tojson`
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-007: Grafico — distribuzione proventi 2024 per regione (Chart.js)
**Description:** As a user, I want to see the financial distribution of ETS entities by region so that I know which areas have the most complete financial data.

**Acceptance Criteria:**
- [ ] In `stats.html`, sezione "Proventi ETS 2024 per regione" con `<canvas id="chart-proventi-regione">`
- [ ] Chart.js vertical bar chart: asse X = regioni, asse Y = totale proventi €, colore `rgba(25,135,84,0.7)` (Bootstrap success)
- [ ] Tooltip mostra il valore formattato in €
- [ ] Nota sotto il grafico: "Dati parziali — solo enti con bilancio 2024 analizzato"
- [ ] Dati da `proventi_2024_per_regione | tojson`
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-008: Grafico — evoluzione proventi nel tempo, singolo ente (Chart.js)
**Description:** As a user, I want to select an entity and see its revenue trend over the years so that I can assess financial trajectory.

**Acceptance Criteria:**
- [ ] In `stats.html`, sezione "Evoluzione proventi nel tempo" con `<select id="sel-ente">` popolato con gli enti che hanno ≥ 2 anni di dati (da `bilanci_per_ente`)
- [ ] `<canvas id="chart-proventi-tempo">` con line chart Chart.js: asse X = anni (2021-2025), asse Y = totale proventi €
- [ ] Cambiando la select, il grafico si aggiorna via JavaScript (sostituzione `chart.data.datasets`)
- [ ] All'avvio mostra il primo ente della lista (Bologna Mario Fantin, 5 anni)
- [ ] Dati da `bilanci_per_ente | tojson`
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-009: Grafico — donut allegati per tipo (Chart.js)
**Description:** As a user, I want to see the breakdown of attachment types so that I know what document coverage we have.

**Acceptance Criteria:**
- [ ] In `stats.html`, sezione "Distribuzione allegati per tipo" con `<canvas id="chart-allegati-tipo">`
- [ ] Chart.js doughnut chart con 8 colori Bootstrap distinti per tipo
- [ ] Legenda destra con tipo e conteggio
- [ ] Dati da `allegati_per_tipo | tojson`
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-010: Tabella — top 10 sezioni per sottosezioni
**Description:** As a user, I want to see which sections have the most sub-sections so that I understand the network hierarchy.

**Acceptance Criteria:**
- [ ] In `stats.html`, sezione "Sezioni con più sottosezioni" con tabella: Pos, Denominazione (link a `/sezione/<codice_cai>?tab=sottosezioni`), N. sottosezioni, barra progress proporzionale al massimo (Bergamo = 30)
- [ ] Dati da `top10_sottosezioni | tojson`
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-011: Tabella — qualità dati con link ai filtri
**Description:** As a user, I want to see known data quality issues with direct links to the relevant filtered views so that I can act on them immediately.

**Acceptance Criteria:**
- [ ] In `stats.html`, sezione "Qualità dati" con tabella: Problema, N. elementi, Azione
- [ ] 4 righe: "Sezioni senza CF nel registro CAI" (n=6, link `/?issues=1`), "Enti ETS non agganciati a sezione CAI" (n=31, link `/ets`), "Sezioni CAI senza dati soci" (n=6, link `/?issues=1`), "Gruppi Regionali non agganciati RUNTS" (n=16, link `/gruppi-regionali`)
- [ ] La colonna Azione ha un link `<a href="...">Vedi →</a>`
- [ ] Dati da `qualita_dati | tojson`
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-012: Mappa coropleta regioni (D3 + GeoJSON)
**Description:** As a user, I want to see a color-coded map of Italy showing sections per region so that I can understand geographic distribution at a glance.

**Acceptance Criteria:**
- [ ] In `stats.html`, sezione "Sezioni CAI per regione" con `<div id="map-regioni">` di altezza 400px
- [ ] D3.js carica `/static/it-regions.geojson` e colora ogni regione con scala di colori proporzionale al numero di sezioni (bianco=0, blu scuro=152 Lombardia). Usa `d3.scaleSequential(d3.interpolateBlues)`
- [ ] Tooltip on hover: "REGIONE — N sezioni, X soci"
- [ ] Normalizzazione nomi: dizionario JS per mappare nomi GeoJSON → nomi DB (es. "Trentino-Alto Adige/Südtirol" → "TRENTINO-ALTO ADIGE")
- [ ] Dati da `soci_per_regione | tojson`
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

---

## Functional Requirements

- FR-1: Route `/stats` calcola tutte le aggregazioni SQL server-side e le serializza come JSON nel template
- FR-2: 7 KPI card nella parte superiore della pagina
- FR-3: Chart.js horizontal bar — soci per regione
- FR-4: Tabella top 10 sezioni per soci con progress bar
- FR-5: Progress bars copertura dati ETS (4 metriche)
- FR-6: Chart.js vertical bar — proventi ETS 2024 per regione
- FR-7: Chart.js line + select dropdown — evoluzione proventi singolo ente
- FR-8: Chart.js donut — distribuzione allegati per tipo
- FR-9: Tabella top 10 sezioni per sottosezioni con progress bar
- FR-10: Tabella qualità dati con 4 righe e link ai filtri
- FR-11: D3 mappa coropleta SVG con tooltip hover
- FR-12: `web/static/it-regions.geojson` servito come file statico

---

## Non-Goals

- Nessun aggiornamento real-time (no WebSocket, no polling)
- Nessun filtro interattivo sulla pagina stats (i link portano ad altre pagine)
- Nessuna esportazione PNG/SVG dei grafici
- Nessuna auth o personalizzazione per utente

---

## Design Considerations

- Layout a due colonne (Bootstrap `row g-4 col-md-6`) dove possibile per affiancare i grafici
- Ogni sezione ha un titolo `<h5>` con `border-bottom pb-2 mb-3`
- Chart.js e D3 inclusi solo nel `{% block head %}` di `stats.html`, non nel layout globale
- La mappa SVG va posizionata in evidenza (prima riga dopo i KPI, full-width)

---

## Success Metrics

- Tutti i 12 componenti visibili senza errori JS in console
- La mappa colora correttamente almeno 15 delle 20 regioni italiane
- Il dropdown evoluzione proventi aggiorna il grafico senza ricaricare la pagina

---

## Open Questions

- Il GeoJSON delle regioni italiane da `openpolis/geoboundaries-ita` usa nomi italiani? Verificare prima di scrivere il dizionario di normalizzazione.
- Le province autonome di Trento e Bolzano sono regioni separate nel GeoJSON o unite in Trentino-Alto Adige? (il DB usa "TRENTINO-ALTO ADIGE" come unica voce)
