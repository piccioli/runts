## ADDED Requirements

### Requirement: Vista mappa alternativa nella lista enti
Il sistema SHALL mostrare nella pagina lista un toggle che permette di passare dalla vista tabella alla vista mappa interattiva (Leaflet.js), mantenendo attivi i filtri correnti.

#### Scenario: Attivazione vista mappa
- **WHEN** l'utente clicca il pulsante "Mappa"
- **THEN** la tabella viene nascosta, compare una mappa interattiva con un marker per ogni ente geocodificato tra quelli filtrati, e il pulsante passa a "Lista"

#### Scenario: Ritorno alla vista lista
- **WHEN** l'utente clicca il pulsante "Lista" mentre è attiva la vista mappa
- **THEN** la mappa viene nascosta e la tabella torna visibile

#### Scenario: Marker sulla mappa
- **WHEN** la mappa è visualizzata
- **THEN** ogni ente con `lat` e `lon` valorizzati appare come marker; cliccando il marker si apre un popup con denominazione e link alla pagina di dettaglio

#### Scenario: Enti senza coordinate
- **WHEN** alcuni enti filtrati non hanno coordinate
- **THEN** quei enti non appaiono come marker sulla mappa ma rimangono visibili nella vista lista

#### Scenario: Nessun ente geocodificato
- **WHEN** nessun ente tra quelli filtrati ha coordinate
- **THEN** la mappa viene mostrata centrata sull'Italia senza marker, con un messaggio "Nessun ente con coordinate disponibili"
