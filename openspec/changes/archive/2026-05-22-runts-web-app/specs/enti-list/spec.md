## ADDED Requirements

### Requirement: Lista paginata degli enti
Il sistema SHALL esporre una pagina web alla route `/` che mostra la lista degli enti presenti nel database, paginata con 20 risultati per pagina.

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
