## 1. Spostamento file

- [x] 1.1 Creare directory `scraper/` e aggiungere `scraper/__init__.py` vuoto
- [x] 1.2 Spostare `scraper.py` → `scraper/scraper.py`
- [x] 1.3 Spostare `db.py` → `scraper/db.py`
- [x] 1.4 Spostare `main.py` → `scraper/main.py`
- [x] 1.5 Spostare `requirements.txt` → `scraper/requirements.txt`

## 2. Aggiornamento import

- [x] 2.1 Aggiornare `scraper/main.py`: sostituire `from db import` con `from .db import` e `from scraper import` con `from .scraper import`

## 3. Verifica

- [x] 3.1 Verificare che `python -m scraper.main --help` funzioni dalla radice
- [x] 3.2 Verificare che `python -m scraper.main --db runts.db --headless` esegua lo scraper correttamente (almeno la navigazione iniziale)
- [x] 3.3 Verificare che l'app web (`docker compose up`) continui a funzionare invariata
