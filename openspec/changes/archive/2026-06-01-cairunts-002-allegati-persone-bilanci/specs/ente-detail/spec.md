## ADDED Requirements

### Requirement: Sezione "Atti e documenti" nella scheda ente
Il template `detail.html` SHALL mostrare la sezione "Atti e documenti" quando l'ente ha almeno un allegato. La sezione SHALL elencare i documenti con: tipo documento, codice pratica, anno (se applicabile), dimensione human-readable (KB/MB), link di download diretto al file locale (`/attachments/<id_runts>/<filename>`), link al portale RUNTS originale. La sezione SHALL essere omessa se l'ente non ha allegati.

#### Scenario: Ente con allegati
- **WHEN** l'utente apre la scheda di un ente che ha allegati in DB
- **THEN** la pagina mostra la sezione "Atti e documenti" con l'elenco dei file scaricabili

#### Scenario: Ente senza allegati
- **WHEN** l'utente apre la scheda di un ente senza allegati in DB
- **THEN** la sezione "Atti e documenti" non viene renderizzata (nessun titolo orfano)

#### Scenario: Download diretto del file
- **WHEN** l'utente clicca il link di download di un allegato
- **THEN** il browser scarica il file da `/attachments/<id_runts>/<filename>` servito da FastAPI

### Requirement: Sezione "Indicatori di bilancio" nella scheda ente
Il template `detail.html` SHALL mostrare la sezione "Indicatori di bilancio" quando l'ente ha almeno un record in `bilanci`. La sezione SHALL mostrare una tabella con colonne: anno, totale proventi, totale oneri, risultato d'esercizio; ordinata per anno decrescente. Valori NULL renderizzati come "—". La sezione SHALL essere omessa se l'ente non ha bilanci analizzati.

#### Scenario: Ente con bilanci analizzati
- **WHEN** l'utente apre la scheda di un ente con almeno una riga in `bilanci`
- **THEN** la pagina mostra la tabella degli indicatori di bilancio con i dati disponibili

#### Scenario: Ente senza bilanci
- **WHEN** l'utente apre la scheda di un ente senza record in `bilanci`
- **THEN** la sezione "Indicatori di bilancio" non viene renderizzata

### Requirement: Sezione "Persone e cariche" nella scheda ente
Il template `detail.html` SHALL mostrare la sezione "Persone e cariche" quando l'ente ha almeno una riga in `cariche_sociali`. Le cariche attive (`valid_to IS NULL`) sono mostrate in cima, quelle storiche in coda. Per ciascuna persona: ruolo, nome, cognome, periodo di carica. Il codice fiscale SHALL essere mascherato nella web UI (`XXX•••••12345`) tramite il filter Jinja `mask_cf`. La sezione SHALL essere omessa se l'ente non ha cariche registrate.

#### Scenario: Ente con cariche attive
- **WHEN** l'utente apre la scheda di un ente con cariche registrate
- **THEN** la pagina mostra prima le cariche attive (valid_to IS NULL), poi quelle storiche; il CF è mascherato

#### Scenario: Ente senza cariche
- **WHEN** l'utente apre la scheda di un ente senza record in `cariche_sociali`
- **THEN** la sezione "Persone e cariche" non viene renderizzata

### Requirement: Servizio file allegati tramite mount FastAPI
La web app SHALL servire i file in `attachments/<id_runts>/...` tramite `StaticFiles` mountato su `/attachments` in sola lettura. Il bind-mount Docker SHALL esporre la stessa cartella come volume in sola lettura.

#### Scenario: File allegato servito
- **WHEN** il browser richiede `/attachments/<id_runts>/<filename>`
- **THEN** il file viene restituito con il MIME type corretto e HTTP 200

#### Scenario: File non trovato
- **WHEN** il browser richiede un path sotto `/attachments/` che non esiste
- **THEN** FastAPI risponde con HTTP 404
