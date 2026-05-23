# 05 — Web app (FastAPI)

> Comportamento osservato di `web/app.py` e dei template Jinja2 in `web/templates/`.

## Scopo

Servire una mini-applicazione di consultazione (HTML) per gli enti CAI registrati nel RUNTS. Non espone API JSON, non gestisce autenticazione, non permette scrittura.

## Stack e bootstrap

| Voce | Valore |
|---|---|
| Framework | FastAPI |
| ASGI server | Uvicorn (`uvicorn[standard]`) |
| Templating | Jinja2 via `fastapi.templating.Jinja2Templates` |
| Static | `StaticFiles` montato su `/static` (directory `web/static/` attualmente vuota) |
| DB driver | `sqlite3` stdlib in modalità URI `mode=ro` |

Variabili e costanti chiave (`web/app.py`):

```python
DB_PATH = os.environ.get("DB_PATH", "/app/runts.db")
PAGE_SIZE = 20
```

L'app viene avviata con:

```bash
uvicorn web.app:app --host 0.0.0.0 --port 8000
```

(comando definito nel `Dockerfile`.)

## Route

### `GET /`

Funzione: `enti_list(request, q, regione, sezione_registro, page)`.

Query string supportata:

| Parametro | Tipo | Default | Effetto |
|---|---|---|---|
| `q` | `str?` | none | LIKE case-insensitive su `denominazione` (`%q%`). |
| `regione` | `str?` | none | Filtro esatto su `sede_regione`. |
| `sezione_registro` | `str?` | none | Filtro esatto su `sezione_registro`. |
| `page` | `int` | 1 | Pagina corrente, normalizzata a `[1, total_pages]`. |

#### Comportamento

1. Se `runts.db` non esiste (`_db_exists()` False) → render di `list.html` con dataset vuoto e zero filtri disponibili. **Nessun 500**.
2. Apre il DB in sola lettura, costruisce dinamicamente la `WHERE` con i filtri attivi, eseguendo SEMPRE con parametri posizionali.
3. Conta il totale (`SELECT COUNT(*) FROM enti <where>`).
4. Calcola `total_pages = ceil(total / PAGE_SIZE)` (con minimo 1) e clampa `page`.
5. Estrae la pagina di risultati:
   ```sql
   SELECT id_runts, denominazione, sede_comune, sede_regione,
          sezione_registro, lat, lon
   FROM enti
   <where>
   ORDER BY denominazione
   LIMIT ? OFFSET ?
   ```
6. Estrae le opzioni dei filtri (distinct sui campi `sede_regione` e `sezione_registro`, escludendo NULL, ordinati alfabeticamente).
7. Chiude la connessione (in `try/finally`).
8. Renderizza `list.html` con context:
   `enti`, `total`, `page`, `total_pages`, `q`, `regione`, `sezione_registro`, `regioni`, `sezioni`.

### `GET /ente/{id_runts}`

Funzione: `ente_detail(request, id_runts, back)`.

Query string supportata:

| Parametro | Tipo | Default | Effetto |
|---|---|---|---|
| `back` | `str?` | `"/"` | URL relativo a cui far tornare l'utente dal bottone "Torna alla lista". |

#### Comportamento

1. Se `runts.db` non esiste → render di `404.html` con HTTP **404**.
2. `SELECT * FROM enti WHERE id_runts = ?` (param posizionale).
3. Se `row is None` → `404.html` con HTTP **404**.
4. Costruisce `fields = {k: row[k] for k in row.keys() if row[k] is not None and k not in ("id_runts", "raw_json", "updated_at")}`. Quindi:
   - I campi `NULL` **non finiscono** nel dict (la pagina di dettaglio non mostrerà la riga corrispondente).
   - `id_runts`, `raw_json`, `updated_at` sono esclusi dalla visualizzazione.
5. Estrae `lat`/`lon` dalla riga se presenti.
6. Render `detail.html` con context: `ente` (`sqlite3.Row` originale), `fields`, `back`, `lat`, `lon`.

## Template

### `base.html`

Layout HTML5 in italiano (`<html lang="it">`):

- Bootstrap 5.3.3 via CDN: `https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css`.
- Sfondo `#f8f9fa`.
- Navbar dark con brand `RUNTS · Sezioni CAI` linkato a `/`.
- Blocco `head` e blocco `content` espandibili dai template figli.

### `list.html`

Eredita da `base.html`. Carica il CSS di Leaflet 1.9.4 via CDN solo in questa pagina (`{% block head %}`).

#### Sezioni della pagina

1. **Titolo**: `H1 "Enti iscritti al RUNTS"`.
2. **Form filtri** (`<form method="get" action="/">`): input `q` (testo libero), select `regione` (con `Tutte le regioni`), select `sezione_registro` (con `Tutte le sezioni`), pulsanti `Cerca` e `Reset` (link a `/`). Layout Bootstrap a 12 colonne (`row g-2`).
3. **Empty state**: se `total == 0`, alert info `"Nessun ente trovato."`. Nessun altro contenuto.
4. **Header risultati**: `"<total> enti trovati — pagina <page> di <total_pages>"` + button group `Lista` / `Mappa` (toggle JS, vedi sotto).
5. **Vista lista** (`#view-lista`):
   - Tabella Bootstrap `table-hover table-sm` con colonne: Denominazione (link a `/ente/<id_runts>?back=<back_url>`), Comune, Regione, Sezione.
   - Valori NULL renderizzati come `—`.
   - **Paginazione**: visibile solo se `total_pages > 1`. Mostra `‹`, prime/ultime pagine, le 5 pagine intorno alla corrente, ellipsis (`…`) tra blocchi, `›`. Tutti i link preservano `q`, `regione`, `sezione_registro` nella query string.
6. **Vista mappa** (`#view-mappa`, `display:none` di default):
   - `<div id="map">` con altezza 520 px e bordo arrotondato.

#### Toggle Lista/Mappa

Implementato in JS inline:

- `showLista()` / `showMappa()` mostrano/nascondono i due div e aggiornano lo stile dei bottoni (`btn-primary` vs `btn-outline-primary`).
- `showMappa()` chiama `initMap()` (idempotente: ritorna subito se la mappa è già stata creata) e poi `map.invalidateSize()` per gestire correttamente il layout dopo il display.

#### Mappa Leaflet (lista)

- Tile layer: `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png`, `maxZoom: 18`, con attribuzione OSM obbligatoria.
- Dati: array JS `ENTI_GEO`, generato dal template iterando su `enti` e includendo **solo** quelli con `lat` e `lon` valorizzati: `{id, nome, lat, lon}`.
- Marker per ogni ente con popup: `<strong>nome</strong><br><a href="/ente/<encoded_id>">Vedi dettaglio</a>`.
- Centra/zoom con `map.fitBounds(bounds, {padding: [30, 30]})`.
- Se `ENTI_GEO.length === 0`, mostra l'Italia (centroide `[42.5, 12.5]`, zoom 6) con popup `"Nessun ente con coordinate disponibili"`.

> Nota: la mappa mostra **solo gli enti della pagina corrente** (limitata da `PAGE_SIZE=20`), non l'intero dataset filtrato. Questo è il comportamento attuale del template.

### `detail.html`

Eredita da `base.html`. Carica il CSS di Leaflet solo se `lat` e `lon` sono valorizzati.

#### Sezioni della pagina

1. **Link di ritorno**: bottone outline `← Torna alla lista` con `href="{{ back }}"`.
2. **Card principale**: header dark con denominazione, body con `<dl class="row">` che itera su una mappa fissa di label/campo:

   ```
   codice_fiscale       → Codice fiscale
   forma_giuridica      → Forma giuridica
   natura_giuridica     → Natura giuridica
   sezione_registro     → Sezione del registro
   data_iscrizione      → Data iscrizione
   sede_stato           → Stato
   sede_indirizzo       → Indirizzo
   sede_civico          → Civico
   sede_comune          → Comune
   sede_provincia       → Provincia
   sede_regione         → Regione
   sede_cap             → CAP
   rappresentante_legale → Rappresentante legale
   pec                  → PEC
   sito_web             → Sito web
   settori_attivita     → Settori di attività
   ```

   Una riga viene renderizzata solo se `fields.get(key)` è truthy. Tre rendering speciali:
   - `pec` → `<a href="mailto:...">`.
   - `sito_web` → `<a href="..." target="_blank" rel="noopener">`.
   - Altri → testo semplice.

3. **Card footer** (condizionale su `ente.url_dettaglio`): bottone outline `Vedi su RUNTS ↗` che apre l'URL ufficiale in nuova tab (`target="_blank" rel="noopener"`).

4. **Mappa Leaflet** (condizionale su `lat and lon`):
   - Card separata con header `"Sede legale — mappa"` e `<div id="map">` 380 px.
   - Tile OSM identico alla lista.
   - Centrata su `[lat, lon]`, zoom 14.
   - Singolo marker con popup popolato da `ente.denominazione | tojson`.

### `404.html`

Pagina semplice in `text-center`:

- `H1 "404"`.
- `<p>Ente non trovato.</p>`.
- Bottone `← Torna alla lista` verso `/`.

## Sicurezza

- **Read-only DB**: connessione SQLite via URI `mode=ro` (impossibile scrivere anche se ci fosse un bug).
- **Parametri posizionali ovunque**: nessuna concatenazione di stringhe in SQL.
- **`tojson` e `urlencode`**: usati nei template per i campi che entrano in JavaScript/URL, riducendo rischio di XSS o di URL malformati.
- Nessun cookie, nessuna sessione, nessun CSRF token (non necessario senza scrittura).

## Comportamenti non garantiti

- **Mappa solo della pagina corrente**: l'utente che vuole vedere tutti gli enti filtrati deve passare in rassegna le pagine; non c'è una vista "tutti i marker contemporaneamente".
- **Nessuna cache HTTP**: ogni richiesta apre/chiude una connessione e rilegge il DB. Per il volume attuale è accettabile.
- **CDN-dependant**: senza internet o con CDN Bootstrap/Leaflet offline, l'interfaccia si degrada (HTML grezzo).
- **Nessun favicon**: la cartella `static/` è vuota.
- **Filtri esatti**: il filtro `regione` e `sezione_registro` non supporta valori multipli o ricerca parziale.
