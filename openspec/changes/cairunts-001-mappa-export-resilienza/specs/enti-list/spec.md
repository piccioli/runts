## MODIFIED Requirements

### Requirement: Lista paginata degli enti
Il sistema SHALL esporre una pagina web alla route `/` che mostra la lista degli enti presenti nel database, paginata con 20 risultati per pagina, con la possibilità di passare alla vista mappa.

#### Scenario: Visualizzazione lista
- **WHEN** l'utente accede alla root `/`
- **THEN** il sistema mostra una tabella con denominazione, sede comune, sede regione e sezione del registro per ogni ente della pagina corrente, con link di navigazione alla pagina precedente/successiva

#### Scenario: Nessun risultato
- **WHEN** la ricerca o i filtri non producono risultati
- **THEN** il sistema mostra un messaggio "Nessun ente trovato" senza errori

## MODIFIED Requirements

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

## ADDED Requirements

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
