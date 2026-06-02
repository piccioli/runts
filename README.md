# RUNTS-CAI

Applicazione per la visualizzazione dei dati RUNTS (Registro Unico Nazionale del Terzo Settore) con integrazione dati CAI (Club Alpino Italiano).

## Setup

### Sviluppo locale

```bash
pip install -r scraper/requirements.txt -r web/requirements.txt
pip install -r requirements-dev.txt
pre-commit install
uvicorn web.app:app --reload
```

### Dev container

Dev container disponibile — aprire in VS Code e selezionare Reopen in Container.

### Docker

```bash
docker compose up
```

## Versioning

Per creare una nuova release:

```bash
bash scripts/bump-version.sh patch   # oppure minor o major
```
