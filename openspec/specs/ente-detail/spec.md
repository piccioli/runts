# Spec: Ente Detail

## Purpose
Definire la pagina di dettaglio del singolo ente, che espone tutti i campi disponibili e permette la navigazione verso il portale RUNTS ufficiale.
## Requirements
### Requirement: Pagina di dettaglio del singolo ente
Il sistema SHALL esporre una route `/ente/<id_runts>` che mostra tutti i campi disponibili per quell'ente, inclusi i nuovi campi `sede_stato` e `sede_civico`.

#### Scenario: Ente trovato
- **WHEN** l'utente accede a `/ente/<id_runts>` con un ID valido
- **THEN** il sistema mostra una pagina con tutti i campi non nulli dell'ente: denominazione, codice fiscale, forma giuridica, natura giuridica, sede (stato, indirizzo, civico, comune, provincia, regione, CAP), data iscrizione, sezione del registro, PEC, sito web, rappresentante legale e URL dettaglio RUNTS

#### Scenario: Ente non trovato
- **WHEN** l'utente accede a `/ente/<id_runts>` con un ID non presente nel DB
- **THEN** il sistema risponde con HTTP 404 e mostra una pagina di errore con messaggio "Ente non trovato"

#### Scenario: Campi assenti
- **WHEN** un campo dell'ente ha valore NULL nel database
- **THEN** quel campo non viene mostrato nella pagina di dettaglio (non viene visualizzata una riga vuota)

### Requirement: Link di ritorno alla lista
Il sistema SHALL mostrare nella pagina di dettaglio un link per tornare alla lista, preservando i filtri precedentemente attivi.

#### Scenario: Ritorno alla lista
- **WHEN** l'utente clicca "Torna alla lista" dalla pagina di dettaglio
- **THEN** il browser naviga alla lista con i parametri di ricerca/filtro originali (passati come parametro `back` nell'URL del dettaglio)

### Requirement: Link al portale RUNTS
Il sistema SHALL mostrare nella pagina di dettaglio un link diretto alla scheda ufficiale sul portale RUNTS.

#### Scenario: URL dettaglio disponibile
- **WHEN** il campo `url_dettaglio` è valorizzato
- **THEN** il sistema mostra un link "Vedi su RUNTS" che apre l'URL in una nuova scheda

### Requirement: Mappa della sede legale
Il sistema SHALL mostrare nella pagina di dettaglio una mappa interattiva della sede legale quando le coordinate geografiche sono disponibili.

#### Scenario: Coordinate disponibili
- **WHEN** i campi `lat` e `lon` dell'ente sono valorizzati nel database
- **THEN** il sistema mostra una mappa Leaflet centrata sulle coordinate con un marker e popup con la denominazione dell'ente

#### Scenario: Coordinate non disponibili
- **WHEN** i campi `lat` e `lon` dell'ente sono NULL nel database
- **THEN** il sistema non mostra la sezione mappa e non carica le librerie Leaflet

### Requirement: Pulsante download PDF nella pagina dettaglio
Il template `detail.html` SHALL esporre un pulsante "Scarica scheda PDF" che avvia il download del PDF dell'ente corrente.

#### Scenario: Pulsante visibile nella pagina dettaglio
- **WHEN** l'utente visualizza la scheda di qualsiasi ente
- **THEN** la pagina mostra un pulsante "Scarica scheda PDF" che punta a `/ente/{id_runts}/pdf`

#### Scenario: Download avviato al click
- **WHEN** l'utente clicca "Scarica scheda PDF"
- **THEN** il browser avvia il download del file PDF senza navigare fuori dalla pagina

