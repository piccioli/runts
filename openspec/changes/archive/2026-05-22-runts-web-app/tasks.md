## 1. Struttura progetto web

- [x] 1.1 Creare directory `web/` con `app.py`, `templates/`, `static/`
- [x] 1.2 Creare `web/requirements.txt` con dipendenze: `fastapi`, `uvicorn[standard]`, `jinja2`
- [x] 1.3 Aggiornare `.gitignore` per escludere `*.db` se non già coperto

## 2. Applicazione FastAPI (`web/app.py`)

- [x] 2.1 Implementare connessione SQLite read-only al DB montato in `/app/runts.db`
- [x] 2.2 Implementare route `GET /` con query params `q`, `regione`, `sezione_registro`, `page`; eseguire SELECT con filtri LIKE/WHERE e paginazione limit/offset
- [x] 2.3 Implementare route `GET /ente/{id_runts}` che restituisce il record o 404
- [x] 2.4 Esporre valori distinti per `sede_regione` e `sezione_registro` per popolare i menu a tendina

## 3. Template HTML (Jinja2)

- [x] 3.1 Creare `web/templates/base.html` con layout comune (navbar, contenitore, link CSS Bootstrap via CDN)
- [x] 3.2 Creare `web/templates/list.html`: tabella enti con link al dettaglio, form di ricerca/filtri, paginazione, conteggio risultati
- [x] 3.3 Creare `web/templates/detail.html`: scheda ente con tutti i campi non nulli, link "Torna alla lista", link "Vedi su RUNTS"
- [x] 3.4 Creare `web/templates/404.html`: pagina di errore per ente non trovato

## 4. Docker

- [x] 4.1 Creare `Dockerfile` basato su `python:3.12-slim`: copia `web/`, installa `web/requirements.txt`, espone porta 8000, CMD uvicorn
- [x] 4.2 Creare `docker-compose.yml`: servizio `web`, build dal Dockerfile, porta `8000:8000`, volume `./runts.db:/app/runts.db:ro`

## 5. Verifica e test manuale

- [x] 5.1 Buildare l'immagine Docker e avviare con `docker compose up`
- [x] 5.2 Verificare che la lista mostri gli enti e la paginazione funzioni
- [x] 5.3 Verificare che ricerca e filtri producano risultati corretti
- [x] 5.4 Verificare che la pagina di dettaglio mostri i campi di un ente e il link RUNTS
- [x] 5.5 Verificare che navigare a un ID inesistente restituisca la pagina 404
