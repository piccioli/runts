# 06 — Deploy ed esecuzione

> Configurazione di Dockerfile, docker-compose, esecuzione manuale di scraper/geocoder e gestione di `runts.db`.

## Filosofia

Solo la **web app** viene containerizzata. Scraper e geocoder sono lanciati **dall'host** dall'operatore quando serve aggiornare i dati, perché:

- richiedono Playwright + browser headless, che pesano sull'immagine;
- vengono eseguiti raramente (manualmente, in modo batch);
- non c'è ragione operativa per averli sempre attivi.

Il file `runts.db` alla radice del progetto è il punto di sincronizzazione: lo scraper/geocoder vi scrivono dall'host, il container web lo monta in sola lettura.

## Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY web/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY web/ ./web/

EXPOSE 8000

CMD ["uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Punti chiave

- Base **python:3.12-slim**: image compatta, ufficiale.
- Si copia **solo** `web/requirements.txt` (non quello dello scraper): l'immagine non contiene Playwright né Chromium.
- Si copia **solo** la cartella `web/`: scraper non finisce nell'immagine.
- Nessun `runts.db` viene copiato dentro l'immagine: viene fornito a runtime via volume.
- `CMD` esegue uvicorn senza reload (servizio production-style).

## docker-compose.yml

```yaml
services:
  web:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./runts.db:/app/runts.db:ro
    environment:
      - DB_PATH=/app/runts.db
    restart: unless-stopped
```

### Punti chiave

- **Bind mount in sola lettura** del DB host (`./runts.db:/app/runts.db:ro`): il container non può corrompere il file, e qualsiasi scrittura dall'host (scraper/geocoder) viene vista dal container al prossimo SELECT.
- Variabile `DB_PATH=/app/runts.db` letta da `web/app.py` (default coincidente).
- `restart: unless-stopped`: si rialza automaticamente in caso di crash, ma si ferma con `docker compose down`.
- Nessun altro servizio dichiarato: niente proxy reverse, niente DB separato.

## Esecuzione tipica

### Bootstrap del progetto

```bash
# 1. Crea ambiente virtuale per scraper/geocoder
python3 -m venv .venv
source .venv/bin/activate

# 2. Installa scraper deps (Playwright + pytest)
pip install -r scraper/requirements.txt
playwright install chromium

# 3. Prima esecuzione: popola il DB
python -m scraper.main --headless

# 4. Geocodifica
python -m scraper.geocoder --db runts.db

# 5. Avvia la web app
docker compose up -d
# → http://localhost:8000
```

### Aggiornamento dati

```bash
# Lancia scraper (può girare con la web app attiva: SQLite WAL + ro mount)
source .venv/bin/activate
python -m scraper.main --headless

# Ri-geocodifica (lo scraper azzera lat/lon dei record aggiornati)
python -m scraper.geocoder --db runts.db
```

La web app vede i nuovi dati al prossimo SELECT, senza riavvio.

### Debug visivo dello scraper

```bash
python -m scraper.main --no-headless --delay 1000 --verbose
```

Browser visibile, pausa più lunga tra dettagli, log DEBUG.

## Gestione del DB

| Operazione | Modalità |
|---|---|
| Backup | Copia del file `runts.db` dall'host (è un singolo file). |
| Versionamento | `runts.db`, `runts.db-shm` e `runts.db-wal` sono in `.gitignore`: il DB non viene mai committato. |
| Reset | Eliminare il file `runts.db` e rilanciare lo scraper. |
| Migrazione schema | Automatica: `init_db()` esegue `CREATE TABLE IF NOT EXISTS` + `ALTER TABLE` idempotenti. |

`.gitignore` corrente esclude: `runts.db`, `runts.db-shm`, `runts.db-wal` (file WAL), `__pycache__/`, `*.pyc`, `.venv/`, `venv/`, `.claude/`.

## Network e porte

- Container web esposto su `0.0.0.0:8000`.
- Nessuna comunicazione di rete interna tra container (servizio singolo).
- Nominatim e tile OSM sono chiamati direttamente dall'host (geocoder) o dal browser dell'utente (Leaflet); il container web non chiama nessun servizio esterno.

## Risorse richieste

- **Web container**: ~50-80 MB RAM a regime, CPU trascurabile (workload I/O bound su SQLite locale).
- **Scraper (host)**: dipende da Chromium headless (~300-500 MB RAM durante l'esecuzione).
- **Geocoder (host)**: trascurabile (un singolo processo Python che dorme 1 s tra richieste).

## Configurazioni note non implementate

- Nessuna pipeline CI/CD: build e deploy sono manuali.
- Nessun reverse proxy / TLS: in produzione si dovrebbe anteporre nginx/Caddy/Traefik.
- Nessun logging strutturato verso un aggregatore: i log restano in stdout del container.
- Nessun health check definito in compose (`healthcheck`) o nel Dockerfile.
- Nessun limite di risorse (`mem_limit`, `cpus`) nel compose.

## Variabili d'ambiente complete

| Variabile | Componente | Default | Note |
|---|---|---|---|
| `DB_PATH` | web app | `/app/runts.db` | Percorso del DB SQLite letto dal container. |

Non esistono `.env` o secret manager; tutta la configurazione è in `docker-compose.yml` o negli argomenti CLI dello scraper.
