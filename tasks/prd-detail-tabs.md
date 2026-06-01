# PRD: Tab Navigation nella Scheda Ente

## Introduction

La pagina di dettaglio della singola sezione CAI (`/ente/<id_runts>`) mostra oggi tutte le informazioni in un'unica pagina scorrevole (anagrafica, mappa, allegati, bilanci, cariche). Con questa feature la pagina viene riorganizzata in quattro tab navigabili:

1. **Dati principali** — anagrafica
2. **Indicatori di bilancio** — tabella anni con proventi/oneri/risultato
3. **Atti e documenti** — tabella allegati scaricabili
4. **Mappa** — mappa full-width della sede

La tab attiva è riflessa nell'URL tramite query string (`?tab=bilanci`), in modo che i link diretti a una specifica tab funzionino. All'apertura senza parametro si atterisce sempre su "Dati principali".

---

## Goals

- Ridurre il cognitive load della scheda ente separando informazioni eterogenee
- Permettere link diretti a una tab specifica (es. deep-link al bilancio)
- Mantenere il pulsante "Scarica PDF" accessibile da qualsiasi tab
- Mostrare sempre tutte e quattro le tab, anche quando i dati mancano

---

## User Stories

### US-001: Struttura HTML/CSS delle tab
**Description:** As a developer, I need the tab skeleton in `detail.html` so that all other stories have a container to work in.

**Acceptance Criteria:**
- [ ] `detail.html` include un `<ul class="nav nav-tabs">` con quattro voci: Dati principali, Indicatori di bilancio, Atti e documenti, Mappa
- [ ] Sotto le tab c'è un `<div class="tab-content">` con quattro pannelli `tab-pane` corrispondenti
- [ ] Il markup usa Bootstrap 5 `nav-tabs` / `tab-pane` standard (nessuna libreria aggiuntiva)
- [ ] Il pulsante "Scarica PDF" rimane nell'header della card esterna, visibile sopra le tab
- [ ] Typecheck/lint passa

### US-002: Attivazione tab via URL query string
**Description:** As a user, I want to share a direct link to a specific tab so that my colleague opens the right section immediately.

**Acceptance Criteria:**
- [ ] Il parametro `?tab=<slug>` controlla la tab attiva al caricamento (slug: `principale`, `bilanci`, `allegati`, `mappa`)
- [ ] Senza parametro (o slug non riconosciuto) si attiva `principale`
- [ ] Jinja2 legge il parametro dalla request e inietta la classe `active` sul tab e sul pane corretti
- [ ] Cliccare un tab aggiorna l'URL via JavaScript (`history.replaceState`) senza ricaricare la pagina
- [ ] Verify in browser: aprire `/ente/83894?tab=bilanci` mostra direttamente la tab bilanci
- [ ] Verify in browser: cliccare "Mappa" aggiorna l'URL a `?tab=mappa`

### US-003: Tab "Dati principali"
**Description:** As a user, I want to see the core registry data of a section in its own tab so that the page is not cluttered.

**Acceptance Criteria:**
- [ ] Il pannello contiene: CF, forma giuridica, sezione registro, data iscrizione, stato, indirizzo sede, CAP, comune, provincia, regione, PEC, sito web, rappresentante legale
- [ ] Il contenuto è identico alle informazioni anagrafica presenti oggi nella scheda (nessuna informazione persa)
- [ ] La sezione "Persone e cariche" (se presente) va in questo pannello
- [ ] Verify in browser: tutti i campi anagrafici di CAI Pisa (id 83894) sono visibili

### US-004: Tab "Indicatori di bilancio"
**Description:** As a user, I want to see the financial data isolated in its own tab so that I can focus on the numbers.

**Acceptance Criteria:**
- [ ] Il pannello mostra la tabella bilanci (anno, totale proventi, totale oneri, risultato) identica a quella attuale
- [ ] Se `bilanci` è lista vuota, il pannello mostra `<p class="text-muted">Nessun dato di bilancio disponibile.</p>`
- [ ] La tab è sempre visibile nel menu (non nascosta anche se vuota)
- [ ] Verify in browser: CAI Pisa mostra i 4 anni di bilancio nella tab; un ente senza bilanci mostra il messaggio vuoto

### US-005: Tab "Atti e documenti"
**Description:** As a user, I want to browse attachments in a dedicated tab so that I don't have to scroll past all the financial data.

**Acceptance Criteria:**
- [ ] Il pannello mostra la tabella allegati (tipo, codice pratica, anno, dimensione, link download, link RUNTS) identica all'attuale
- [ ] Se `allegati` è lista vuota, mostra `<p class="text-muted">Nessun documento disponibile.</p>`
- [ ] La tab è sempre visibile nel menu
- [ ] Verify in browser: CAI Parma mostra gli allegati nella tab; un ente senza allegati mostra il messaggio vuoto

### US-006: Tab "Mappa"
**Description:** As a user, I want to see a full-width map of the section's headquarters so that I can orient myself geographically.

**Acceptance Criteria:**
- [ ] Il pannello mostra una mappa Leaflet con il pin della sede, larghezza 100% del contenitore, altezza 450px
- [ ] La mappa è inizializzata solo quando il tab "Mappa" diventa visibile (lazy init, per evitare il bug di rendering Leaflet su tab nascoste)
- [ ] Se `lat`/`lon` sono assenti, il pannello mostra `<p class="text-muted">Coordinate non disponibili.</p>`
- [ ] La mappa precedente (nella sezione "Sede legale — mappa" sotto l'anagrafica) viene rimossa dal template
- [ ] La tab è sempre visibile nel menu
- [ ] Verify in browser: CAI Pisa — aprire la tab Mappa mostra il pin correttamente centrato sulla sede

### US-007: Aggiornamento route `/ente/<id_runts>` in app.py
**Description:** As a developer, I need the backend to pass the active tab to the template so that server-side rendering selects the correct tab.

**Acceptance Criteria:**
- [ ] La route legge `request.query_params.get("tab", "principale")` e passa `active_tab` al contesto Jinja2
- [ ] Valori non riconosciuti vengono normalizzati a `"principale"`
- [ ] Il contesto template già esistente (allegati, bilanci, cariche, lat, lon, ecc.) non viene modificato

---

## Functional Requirements

- FR-1: Il menu tab contiene esattamente 4 voci nell'ordine: Dati principali · Indicatori di bilancio · Atti e documenti · Mappa
- FR-2: La tab attiva è determinata da `?tab=<slug>` nell'URL; default `principale`
- FR-3: Cliccando un tab il browser aggiorna l'URL senza ricaricare la pagina (`history.replaceState`)
- FR-4: La mappa Leaflet viene inizializzata solo alla prima apertura della tab Mappa (lazy init)
- FR-5: Tab con lista dati vuota mostra messaggio testuale, non viene nascosta
- FR-6: Il pulsante "Scarica PDF" rimane nell'header della card esterna, sopra il menu tab
- FR-7: La vecchia sezione "Sede legale — mappa" (attualmente sotto l'anagrafica) viene eliminata dal template

---

## Non-Goals

- Nessuna animazione di transizione tra tab
- Nessuna memorizzazione della tab in localStorage
- Nessuna modifica al PDF generato (continua a contenere tutto)
- Nessuna tab aggiuntiva (es. "Persone e cariche" come tab separata — va in "Dati principali")
- Nessuna modifica alla lista enti o ad altre pagine

---

## Design Considerations

- Usare Bootstrap 5 `nav nav-tabs` già incluso nel progetto (nessuna dipendenza nuova)
- Il layout della scheda rimane una singola `card` con `card-header` (titolo ente + PDF button) e `card-body` che contiene il menu tab + pannelli
- Breakpoint mobile: le tab diventano scrollabili orizzontalmente (`flex-nowrap overflow-auto`) se troppo larghe

---

## Technical Considerations

- **Bug Leaflet su tab nascoste**: Leaflet non calcola le dimensioni correttamente se inizializzato su un elemento `display:none`. Usare l'evento `shown.bs.tab` di Bootstrap per chiamare `map.invalidateSize()` o inizializzare la mappa solo al primo click.
- **Template**: tutto il lavoro è in `web/templates/detail.html` + piccola modifica in `web/app.py` (lettura query param `tab`)
- **Slug tab**: `principale`, `bilanci`, `allegati`, `mappa` — tutti lowercase, senza accenti

---

## Success Metrics

- La pagina non perde nessuna informazione rispetto alla versione attuale
- Il link `/ente/83894?tab=mappa` apre direttamente la mappa
- La mappa non appare bianca/vuota quando si apre la tab per la prima volta

---

## Open Questions

- La sezione "Persone e cariche" va in "Dati principali" o merita una quinta tab in futuro? (per ora: Dati principali)
- Il back-link "← Torna alla lista" deve aggiornarsi per preservare il tab corrente nell'URL? (per ora: no, fuori scope)
