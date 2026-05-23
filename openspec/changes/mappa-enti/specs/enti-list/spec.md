## MODIFIED Requirements

### Requirement: Lista paginata degli enti
Il sistema SHALL esporre una pagina web alla route `/` che mostra la lista degli enti presenti nel database, paginata con 20 risultati per pagina, con la possibilità di passare alla vista mappa.

#### Scenario: Visualizzazione lista
- **WHEN** l'utente accede alla root `/`
- **THEN** il sistema mostra una tabella con denominazione, sede comune, sede regione e sezione del registro per ogni ente della pagina corrente, con link di navigazione alla pagina precedente/successiva

#### Scenario: Nessun risultato
- **WHEN** la ricerca o i filtri non producono risultati
- **THEN** il sistema mostra un messaggio "Nessun ente trovato" senza errori

## ADDED Requirements

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
