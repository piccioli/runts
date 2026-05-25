## ADDED Requirements

### Requirement: Estrazione atti e documenti dalla pagina di dettaglio RUNTS
Lo scraper SHALL, dopo l'estrazione dei campi anagrafici, individuare la sezione "Atti e documenti" della pagina di dettaglio RUNTS e raccogliere l'elenco degli allegati disponibili (nome documento, codice pratica, anno dalla colonna Data, URL del link PDF).

#### Scenario: Sezione atti e documenti presente
- **WHEN** la pagina di dettaglio RUNTS espone la sezione "Atti e documenti"
- **THEN** lo scraper raccoglie la lista completa di allegati e la restituisce per il download successivo

#### Scenario: Sezione atti e documenti assente
- **WHEN** la pagina di dettaglio non contiene la sezione "Atti e documenti"
- **THEN** lo scraper restituisce una lista vuota senza errori

### Requirement: Estrazione cariche sociali dalla pagina di dettaglio RUNTS
Lo scraper SHALL estrarre dalla sezione "Organi sociali" della pagina di dettaglio RUNTS l'elenco delle persone con carica: nome, cognome, codice fiscale, ruolo, date di carica.

#### Scenario: Sezione organi sociali presente
- **WHEN** la pagina di dettaglio RUNTS espone la sezione "Organi sociali"
- **THEN** lo scraper raccoglie l'elenco completo delle persone con i rispettivi ruoli e date

#### Scenario: Sezione organi sociali assente
- **WHEN** la pagina di dettaglio non contiene la sezione "Organi sociali"
- **THEN** lo scraper restituisce una lista vuota senza errori
