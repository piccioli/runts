# Spec: Web Docker

## Purpose
Definire la containerizzazione dell'applicazione web tramite Docker, con separazione tra scraper (host) e web app (container) che condividono solo il file `runts.db`.

## Requirements

### Requirement: Containerizzazione dell'applicazione web
Il sistema SHALL fornire un `Dockerfile` e un `docker-compose.yml` che permettono di avviare l'applicazione web con il comando `docker compose up`.

#### Scenario: Avvio con docker compose
- **WHEN** l'utente esegue `docker compose up` nella directory del progetto
- **THEN** il container dell'app web si avvia, monta `runts.db` in sola lettura e l'app è raggiungibile su `http://localhost:8000`

#### Scenario: DB non presente all'avvio
- **WHEN** il file `runts.db` non esiste nella directory del progetto al momento dell'avvio
- **THEN** il container si avvia comunque ma le pagine mostrano lista vuota anziché errore

### Requirement: Separazione tra scraper e app web
Il sistema SHALL mantenere scraper e applicazione web come componenti indipendenti che condividono solo il file `runts.db`.

#### Scenario: Aggiornamento del DB da parte dello scraper
- **WHEN** lo scraper viene eseguito sul host e aggiorna `runts.db`
- **THEN** l'app web serve i dati aggiornati alla successiva richiesta HTTP, senza necessità di riavviare il container

#### Scenario: App web e scraper non hanno dipendenze reciproche
- **WHEN** l'app web è in esecuzione
- **THEN** non importa né esegue alcun modulo dello scraper (`scraper.py`, `main.py`, `db.py`)

### Requirement: Dipendenze web isolate
Il sistema SHALL definire le dipendenze dell'applicazione web in un file separato da quelle dello scraper.

#### Scenario: Installazione dipendenze web
- **WHEN** il `Dockerfile` viene costruito
- **THEN** installa solo le dipendenze definite in `web/requirements.txt`, non quelle di `requirements.txt` dello scraper
