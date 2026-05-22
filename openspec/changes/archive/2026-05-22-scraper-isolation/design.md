## Context

Struttura corrente alla radice del progetto:
```
scraper.py, db.py, main.py, requirements.txt   ← scraper
web/                                            ← app web
Dockerfile, docker-compose.yml                 ← infra web
```

La struttura target isola tutto ciò che riguarda lo scraper in `scraper/`, allineandola alla convenzione già usata per `web/`.

## Goals / Non-Goals

**Goals:**
- Spostare `scraper.py`, `db.py`, `main.py`, `requirements.txt` in `scraper/`
- Aggiungere `scraper/__init__.py` per rendere la directory un package importabile
- Aggiornare gli import in `main.py` (da `from db import` / `from scraper import` a import relativi)
- Nessuna modifica al comportamento funzionale

**Non-Goals:**
- Modificare la logica di scraping o del DB
- Modificare `web/` o la configurazione Docker
- Spostare `runts.db` (rimane alla radice, condiviso con il container web)

## Decisions

**Package Python con `__init__.py` vuoto**
Rende `scraper/` importabile come package, semplifica gli import relativi in `main.py`. Alternativa scartata: usare path manipulation in `sys.path` — più fragile e non idiomatico.

**Import relativi in `main.py`**
`from .db import ...` e `from .scraper import ...` dentro il package. Il punto di ingresso resta eseguibile come `python -m scraper.main` dalla radice.

**`requirements.txt` dello scraper in `scraper/requirements.txt`**
Mantiene la simmetria con `web/requirements.txt`. Chi vuole eseguire solo lo scraper installa `pip install -r scraper/requirements.txt`.

## Risks / Trade-offs

- **[Risk] Comando di esecuzione cambia** → Mitigation: documentare il nuovo comando `python -m scraper.main` nel README
- **[Risk] Import circolari se i moduli si importano a vicenda** → Non applicabile: `db.py` e `scraper.py` non si importano tra loro, solo `main.py` li importa entrambi
