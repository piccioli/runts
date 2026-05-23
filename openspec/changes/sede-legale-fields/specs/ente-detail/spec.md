## MODIFIED Requirements

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
