## ADDED Requirements

### Requirement: Estrazione cariche sociali dalla pagina RUNTS
Lo scraper SHALL estrarre dalla sezione "Organi sociali" della pagina di dettaglio RUNTS le seguenti informazioni per ciascuna persona: nome, cognome, codice fiscale, ruolo canonico, `valid_from`, `valid_to` (se presente). I ruoli SHALL essere normalizzati dalla dicitura RUNTS al canonico: `presidente`, `vicepresidente`, `consigliere`, `segretario`, `tesoriere`, `revisore`, `altro`.

#### Scenario: Sezione organi sociali presente
- **WHEN** la pagina di dettaglio RUNTS contiene la sezione "Organi sociali" con un elenco di persone
- **THEN** lo scraper raccoglie per ciascuna: nome, cognome, CF (se disponibile), ruolo canonico, date di carica

#### Scenario: Ruolo non mappato
- **WHEN** la dicitura del ruolo RUNTS non è presente nella mappa di normalizzazione
- **THEN** il ruolo viene salvato come `"altro"` con la dicitura originale conservata in un campo note

#### Scenario: Sezione organi assente
- **WHEN** la pagina di dettaglio non espone la sezione "Organi sociali"
- **THEN** lo scraper prosegue senza errore, nessuna riga viene aggiunta in `cariche_sociali` per quell'ente

### Requirement: Persistenza con tracciamento temporale delle cariche
Il sistema SHALL persistere ogni carica nella tabella `cariche_sociali` con upsert sulla chiave `(id_runts, codice_fiscale, ruolo, valid_from)`. Quando il CF non è disponibile, SHALL usare come chiave fallback `(id_runts, nome, cognome, ruolo, valid_from)`.

#### Scenario: Nuova carica inserita
- **WHEN** lo scraper trova una persona non presente in `cariche_sociali` con `valid_to IS NULL`
- **THEN** viene inserita una nuova riga con `valid_to = NULL` (carica attiva)

#### Scenario: Carica invariata
- **WHEN** lo scraper trova esattamente le stesse persone già in `cariche_sociali` con `valid_to IS NULL`
- **THEN** nessun record viene modificato

### Requirement: Chiusura automatica cariche cessate
Il sistema SHALL aggiornare `valid_to` alla data corrente per le cariche attive (`valid_to IS NULL`) non più presenti nell'elenco RUNTS al run corrente.

#### Scenario: Presidente sostituito
- **WHEN** lo scraper trova un presidente con CF diverso da quello attualmente in carica (`valid_to IS NULL`)
- **THEN** il record del vecchio presidente viene chiuso (`valid_to` = data corrente), il nuovo viene inserito

#### Scenario: Consigliere cessato
- **WHEN** una persona presente nel DB con `valid_to IS NULL` non è più nell'elenco RUNTS al run corrente
- **THEN** il suo `valid_to` viene impostato alla data del run corrente

### Requirement: Retrocompatibilità campo rappresentante_legale
Il sistema SHALL continuare a popolare il campo `enti.rappresentante_legale` con il nome del presidente estratto, per compatibilità con la lista enti e le funzionalità esistenti.

#### Scenario: Presidente estratto
- **WHEN** lo scraper estrae il presidente dalle cariche sociali
- **THEN** `enti.rappresentante_legale` viene aggiornato con `"Cognome Nome"` del presidente corrente
