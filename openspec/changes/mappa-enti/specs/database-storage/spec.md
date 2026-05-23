## MODIFIED Requirements

### Requirement: Inizializzazione del database SQLite
Il sistema SHALL creare automaticamente il file di database SQLite e le tabelle necessarie se non esistono. Lo schema SHALL includere le colonne `lat` e `lon` (REAL) per le coordinate geografiche. Su database esistenti, il sistema SHALL aggiungere le colonne mancanti senza perdere i dati esistenti.

#### Scenario: Prima esecuzione
- **WHEN** il database non esiste
- **THEN** il sistema crea `runts.db` e la tabella `enti` con le colonne `lat` e `lon` incluse

#### Scenario: Migrazione database esistente
- **WHEN** il database esiste ma le colonne `lat` e/o `lon` sono assenti
- **THEN** il sistema aggiunge le colonne mancanti senza errori e senza perdita di dati

#### Scenario: Esecuzioni successive (schema aggiornato)
- **WHEN** il database esiste già con schema aggiornato
- **THEN** il sistema usa il database esistente senza modifiche allo schema
