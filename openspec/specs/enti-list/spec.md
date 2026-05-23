# Spec: Enti List

## Purpose
Definire la pagina principale con la lista degli enti, inclusa la ricerca testuale, i filtri e la visualizzazione alternativa su mappa.
## Requirements
### Requirement: Lista paginata degli enti
Il sistema SHALL esporre una pagina web alla route `/` che mostra la lista degli enti presenti nel database, paginata con 20 risultati per pagina, con la possibilità di passare alla vista mappa.

#### Scenario: Visualizzazione lista
- **WHEN** l'utente accede alla root `/`
- **THEN** il sistema mostra una tabella con denominazione, sede comune, sede regione e sezione del registro per ogni ente della pagina corrente, con link di navigazione alla pagina precedente/successiva

#### Scenario: Nessun risultato
- **WHEN** la ricerca o i filtri non producono risultati
- **THEN** il sistema mostra un messaggio "Nessun ente trovato" senza errori

### Requirement: Ricerca testuale
Il sistema SHALL permettere la ricerca per testo libero sul campo denominazione tramite parametro query string `q`.

#### Scenario: Ricerca per denominazione
- **WHEN** l'utente inserisce un testo nel campo di ricerca e invia il form
- **THEN** il sistema filtra gli enti la cui denominazione contiene il testo cercato (case-insensitive) e mostra i risultati paginati

#### Scenario: Ricerca preservata tra pagine
- **WHEN** l'utente naviga alla pagina successiva di una ricerca
- **THEN** il parametro `q` viene mantenuto nella query string e i risultati rimangono filtrati

### Requirement: Filtri per regione e sezione del registro
Il sistema SHALL permettere di filtrare la lista per `sede_regione` e `sezione_registro` tramite menu a tendina.

#### Scenario: Filtro per regione
- **WHEN** l'utente seleziona una regione dal menu a tendina
- **THEN** il sistema mostra solo gli enti con quella `sede_regione`, combinando eventualmente con altri filtri attivi

#### Scenario: Filtro per sezione del registro
- **WHEN** l'utente seleziona una sezione del registro
- **THEN** il sistema mostra solo gli enti iscritti in quella sezione

#### Scenario: Reset filtri
- **WHEN** l'utente seleziona il valore vuoto nei menu a tendina
- **THEN** il filtro corrispondente viene rimosso e la lista mostra tutti gli enti (soggetti agli altri filtri attivi)

### Requirement: Link al dettaglio dalla lista
Il sistema SHALL rendere ogni riga della lista cliccabile per navigare alla pagina di dettaglio dell'ente.

#### Scenario: Click su ente in lista
- **WHEN** l'utente clicca sulla denominazione di un ente nella lista
- **THEN** il browser naviga alla route `/ente/<id_runts>`

### Requirement: Vista mappa alternativa
Il sistema SHALL offrire una visualizzazione alternativa degli enti su mappa interattiva con clustering, attivabile tramite toggle dalla vista lista. La mappa carica tutti gli enti filtrati (non solo la pagina corrente) tramite chiamata fetch all'endpoint `/api/enti.geojson`.

#### Scenario: Attivazione vista mappa — tutti gli enti filtrati
- **WHEN** l'utente apre la vista mappa con `regione=Toscana`
- **THEN** la mappa mostra i marker di **tutti** gli enti toscani con coordinate, non solo i primi 20; i marker sono caricati tramite fetch a `/api/enti.geojson?regione=Toscana`

#### Scenario: Clustering attivo
- **WHEN** due o più marker sono geograficamente vicini al livello di zoom corrente
- **THEN** i marker sono rappresentati da un cluster con il numero di enti contenuti; un click sul cluster ne effettua lo zoom in

#### Scenario: Ritorno alla vista lista
- **WHEN** l'utente clicca il pulsante "Lista"
- **THEN** la mappa viene nascosta e la tabella torna visibile

#### Scenario: Enti non geocodificati
- **WHEN** alcuni enti non hanno coordinate lat/lon nel database
- **THEN** quelli senza coordinate non compaiono sulla mappa, ma rimangono visibili nella lista

### Requirement: Toggle lista/mappa nella pagina lista
Il sistema SHALL includere nella pagina lista un pulsante toggle che permette di passare dalla visualizzazione tabella alla visualizzazione mappa e viceversa, senza ricaricare la pagina.

#### Scenario: Cambio a vista mappa
- **WHEN** l'utente clicca il toggle "Mappa"
- **THEN** la tabella viene nascosta e viene mostrata la mappa con i marker degli enti geocodificati filtrati correnti

#### Scenario: Cambio a vista lista
- **WHEN** l'utente clicca il toggle "Lista" mentre è attiva la vista mappa
- **THEN** la mappa viene nascosta e la tabella torna visibile

### Requirement: Dati geografici passati alla lista
Il sistema SHALL includere nella response HTML della lista le coordinate `lat` e `lon` di tutti gli enti filtrati (pagina corrente), come JSON inline, per alimentare la mappa lato client senza richieste aggiuntive.

#### Scenario: Enti con coordinate
- **WHEN** la pagina lista viene caricata
- **THEN** il template riceve i dati degli enti includendo `lat`, `lon`, `denominazione` e `id_runts` per costruire i marker Leaflet

### Requirement: Sidebar filtri nella vista mappa
Il sistema SHALL mostrare nella vista mappa una sidebar con checkbox per regioni e sezioni del registro, con conteggio enti per opzione, che filtra i marker in tempo reale.

#### Scenario: Filtro live da sidebar
- **WHEN** l'utente, nella vista mappa, deseleziona la checkbox "Lombardia" dalla sidebar regioni
- **THEN** i marker lombardi spariscono immediatamente dalla mappa senza ricaricamento e la query string nell'URL viene aggiornata tramite `history.replaceState`

#### Scenario: URL persistente con filtri mappa
- **WHEN** l'utente condivide l'URL della mappa con filtri attivi a un collega
- **THEN** il collega aprendolo vede la stessa selezione di marker

### Requirement: Parametri filtro multi-valore
Il sistema SHALL accettare valori multipli comma-separated nei parametri `regione` e `sezione_registro` per supportare la selezione di più opzioni dalla sidebar mappa.

#### Scenario: Multi-regione
- **WHEN** la query string contiene `?regione=Toscana,Lombardia`
- **THEN** sia la lista che il GeoJSON restituiscono enti di entrambe le regioni

