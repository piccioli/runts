## ADDED Requirements

### Requirement: Pagina di dettaglio del singolo ente
Il sistema SHALL esporre una route `/ente/<id_runts>` che mostra tutti i campi disponibili per quell'ente.

#### Scenario: Ente trovato
- **WHEN** l'utente accede a `/ente/<id_runts>` con un ID valido
- **THEN** il sistema mostra una pagina con tutti i campi non nulli dell'ente: denominazione, codice fiscale, forma giuridica, natura giuridica, sede (indirizzo, comune, provincia, regione, CAP), data iscrizione, sezione del registro, PEC, sito web, rappresentante legale e URL dettaglio RUNTS

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
