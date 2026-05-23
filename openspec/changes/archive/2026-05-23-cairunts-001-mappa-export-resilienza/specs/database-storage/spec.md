## ADDED Requirements

### Requirement: Indici DB per le colonne di filtro principali
Il sistema SHALL creare gli indici `idx_enti_sede_regione` su `enti(sede_regione)` e `idx_enti_sezione_registro` su `enti(sezione_registro)` tramite migrazione idempotente (`CREATE INDEX IF NOT EXISTS`).

#### Scenario: Query filtrata su regione ottimizzata
- **WHEN** si esegue `EXPLAIN QUERY PLAN SELECT * FROM enti WHERE sede_regione = 'Toscana'`
- **THEN** il piano mostra l'uso di `idx_enti_sede_regione`

#### Scenario: Migrazione idempotente
- **WHEN** la migrazione viene eseguita su un DB che ha già gli indici
- **THEN** non si verifica alcun errore e il DB rimane invariato

## MODIFIED Requirements

### Requirement: Inizializzazione del database SQLite
Il sistema SHALL creare automaticamente il file di database SQLite e le tabelle necessarie se non esistono. Lo schema SHALL includere le colonne `lat` e `lon` (REAL) per le coordinate geografiche e la tabella `geocoding_cache`. Su database esistenti, il sistema SHALL aggiungere le colonne e tabelle mancanti senza perdere i dati esistenti.

#### Scenario: Prima esecuzione
- **WHEN** il database non esiste
- **THEN** il sistema crea `runts.db` con la tabella `enti` (incluse `lat`, `lon`), la tabella `geocoding_cache` e gli indici su `sede_regione` e `sezione_registro`

#### Scenario: Migrazione database esistente
- **WHEN** il database esiste ma mancano tabella `geocoding_cache` o gli indici
- **THEN** il sistema aggiunge gli elementi mancanti senza errori e senza perdita di dati

### Requirement: Persistenza con upsert degli enti
Il sistema SHALL inserire nuovi record o aggiornare quelli esistenti usando il codice fiscale come chiave univoca, preservando i valori esistenti di `lat` e `lon` quando non presenti o nulli nel dict in input.

#### Scenario: Rerun scraper su ente già geocodificato
- **WHEN** lo scraper rilancia su un ente già geocodificato (dict senza `lat`/`lon` o con valori `None`)
- **THEN** i valori di `lat` e `lon` nel DB restano invariati

#### Scenario: Primo inserimento
- **WHEN** un ente estratto non è presente nel database
- **THEN** il sistema inserisce un nuovo record con tutti i campi estratti e il timestamp di aggiornamento
