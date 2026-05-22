## ADDED Requirements

### Requirement: Inizializzazione del database SQLite
Il sistema SHALL creare automaticamente il file di database SQLite e le tabelle necessarie se non esistono, senza richiedere configurazione manuale.

#### Scenario: Prima esecuzione
- **WHEN** il database non esiste
- **THEN** il sistema crea `runts.db` nella directory corrente e crea la tabella `enti` con le colonne corrispondenti ai campi estratti

#### Scenario: Esecuzioni successive
- **WHEN** il database esiste già
- **THEN** il sistema usa il database esistente senza sovrascriverlo

### Requirement: Persistenza con upsert degli enti
Il sistema SHALL inserire nuovi record o aggiornare quelli esistenti usando il codice fiscale come chiave univoca, in modo che esecuzioni successive aggiornino i dati senza creare duplicati.

#### Scenario: Inserimento di un nuovo ente
- **WHEN** un ente estratto non è presente nel database (codice fiscale non trovato)
- **THEN** il sistema inserisce un nuovo record con tutti i campi estratti e il timestamp di aggiornamento

#### Scenario: Aggiornamento di un ente esistente
- **WHEN** un ente estratto è già presente nel database (stesso codice fiscale)
- **THEN** il sistema aggiorna tutti i campi del record esistente con i nuovi valori e aggiorna il timestamp di aggiornamento

### Requirement: Tracciamento timestamp di aggiornamento
Il sistema SHALL salvare per ciascun record la data e ora dell'ultima estrazione.

#### Scenario: Record salvato
- **WHEN** un record viene inserito o aggiornato
- **THEN** il campo `updated_at` viene impostato all'ora UTC corrente

### Requirement: Report finale di esecuzione
Il sistema SHALL stampare a fine esecuzione un riepilogo delle operazioni effettuate sul database.

#### Scenario: Esecuzione completata
- **WHEN** tutti gli enti sono stati processati e salvati
- **THEN** il sistema stampa il numero di record inseriti, aggiornati e il totale presenti nel database
