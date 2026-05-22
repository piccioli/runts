## Why

Attualmente `scraper.py`, `db.py`, `main.py` e `requirements.txt` dello scraper vivono alla radice del progetto insieme a `Dockerfile`, `docker-compose.yml` e `web/`. Con la crescita del progetto questa struttura piatta rende difficile capire cosa appartiene allo scraper e cosa all'app web. Il refactoring isola lo scraper in una directory dedicata `scraper/`, specchiando la struttura già adottata per `web/`.

## What Changes

- **BREAKING**: `scraper.py`, `db.py`, `main.py`, `requirements.txt` vengono spostati in `scraper/`
- Gli import interni di `main.py` vengono aggiornati (da `from db import` → `from scraper.db import` oppure gestiti con path relativo)
- Il comando di esecuzione cambia da `python main.py` a `python -m scraper.main` (o `python scraper/main.py`)
- `Dockerfile` e `docker-compose.yml` non cambiano (riguardano solo `web/`)
- Nessuna modifica al comportamento funzionale

## Capabilities

### New Capabilities

- `scraper-layout`: Struttura attesa della directory `scraper/` e convenzioni di esecuzione

### Modified Capabilities

## Impact

- File spostati: `scraper.py`, `db.py`, `main.py`, `requirements.txt` → `scraper/`
- Aggiornamento import in `main.py`
- Aggiunta `scraper/__init__.py` per rendere la directory un package Python
- Il file `runts.db` rimane alla radice (condiviso con il container web)
- Comando di esecuzione aggiornato nel README o nella documentazione
