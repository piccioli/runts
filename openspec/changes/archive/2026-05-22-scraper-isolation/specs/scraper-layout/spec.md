## ADDED Requirements

### Requirement: Codice scraper isolato in directory dedicata
Il progetto SHALL organizzare tutto il codice relativo allo scraping nella directory `scraper/`, separata dall'app web in `web/` e dalla configurazione Docker alla radice.

#### Scenario: Struttura directory corretta
- **WHEN** si elenca la radice del progetto
- **THEN** i file `scraper.py`, `db.py`, `main.py` e `requirements.txt` dello scraper sono assenti dalla radice e presenti in `scraper/`

#### Scenario: Directory scraper è un package Python
- **WHEN** si esegue `python -c "import scraper"` dalla radice del progetto
- **THEN** il package viene importato senza errori

### Requirement: Punto di ingresso dello scraper eseguibile come modulo
Il sistema SHALL permettere di eseguire lo scraper con `python -m scraper.main` dalla radice del progetto.

#### Scenario: Esecuzione come modulo
- **WHEN** si esegue `python -m scraper.main --help` dalla radice
- **THEN** viene mostrato l'help CLI senza errori di import

#### Scenario: Percorso del DB invariato
- **WHEN** lo scraper viene eseguito con il comando aggiornato
- **THEN** il file `runts.db` viene creato/aggiornato alla radice del progetto (non dentro `scraper/`)

### Requirement: Dipendenze scraper in file separato
Il sistema SHALL definire le dipendenze dello scraper in `scraper/requirements.txt`, separato da `web/requirements.txt`.

#### Scenario: Installazione dipendenze scraper
- **WHEN** si esegue `pip install -r scraper/requirements.txt`
- **THEN** vengono installate solo le dipendenze dello scraper (playwright) senza quelle web
