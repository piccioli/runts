## MODIFIED Requirements

### Requirement: Pagina di dettaglio del singolo ente
Il sistema SHALL esporre una route `/ente/<id_runts>` che mostra tutti i campi disponibili per quell'ente, inclusa una mappa embedded della sede legale se le coordinate sono disponibili.

#### Scenario: Ente trovato con coordinate
- **WHEN** l'utente accede a `/ente/<id_runts>` con un ID valido e l'ente ha `lat` e `lon` valorizzati
- **THEN** il sistema mostra tutti i campi non nulli dell'ente e, dopo la scheda dati, una mappa Leaflet centrata sulla sede con un marker

#### Scenario: Ente trovato senza coordinate
- **WHEN** l'utente accede a `/ente/<id_runts>` con un ID valido ma l'ente non ha `lat`/`lon`
- **THEN** il sistema mostra i campi dell'ente senza la sezione mappa

#### Scenario: Ente non trovato
- **WHEN** l'utente accede a `/ente/<id_runts>` con un ID non presente nel DB
- **THEN** il sistema risponde con HTTP 404 e mostra una pagina di errore con messaggio "Ente non trovato"

#### Scenario: Campi assenti
- **WHEN** un campo dell'ente ha valore NULL nel database
- **THEN** quel campo non viene mostrato nella pagina di dettaglio (non viene visualizzata una riga vuota)
