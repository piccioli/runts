# 04 — Geocoder (Nominatim)

> Comportamento osservato di `scraper/geocoder.py`.

## Scopo

Arricchire gli enti già presenti nel DB con coordinate geografiche `(lat, lon)` da usare per la mappa Leaflet della web app. Il geocoder è **uno script standalone**, eseguibile separatamente dallo scraper.

## Entrypoint CLI

File: `scraper/geocoder.py`. Eseguibile come modulo:

```bash
python -m scraper.geocoder [--db PATH] [--verbose]
```

Argomenti:

| Argomento | Default | Significato |
|---|---|---|
| `--db PATH` | `runts.db` | Percorso del file SQLite da arricchire. |
| `--verbose`, `-v` | off | Livello log `DEBUG`. |

Output finale stampato su stdout (`geocoder.py:96-104`):

```
==================================================
  REPORT GEOCODIFICA
==================================================
  Già presenti     : <count>
  Geocodificati    : <count>
  Non trovati      : <count>
  Saltati (no comune): <count>
==================================================
```

## Funzione principale

`geocode_enti(conn: sqlite3.Connection) -> dict`:

1. Imposta `conn.row_factory = sqlite3.Row`.
2. Seleziona gli enti da geocodificare:
   ```sql
   SELECT id_runts, sede_comune, sede_regione
   FROM enti
   WHERE lat IS NULL OR lon IS NULL
   ```
3. Per ogni riga:
   - Se `sede_comune` è vuoto/nullo → `skipped += 1`, log DEBUG, continue.
   - Chiama `_nominatim_query(comune, regione)`.
   - **Dorme 1 secondo** (`time.sleep(1)`) **dopo ogni richiesta**, indipendentemente dall'esito, per rispettare il rate limit di Nominatim.
   - Se ottiene `(lat, lon)`: esegue `UPDATE enti SET lat = ?, lon = ? WHERE id_runts = ?` e committa. Log INFO.
   - Se non trova coordinate: `not_found += 1`, log WARNING.
4. Ritorna `{"geocoded": N, "not_found": N, "skipped": N}`.

Il conteggio "Già presenti" viene letto **prima** della funzione (`geocoder.py:90`) con `SELECT COUNT(*) FROM enti WHERE lat IS NOT NULL AND lon IS NOT NULL`.

## Query Nominatim (`_nominatim_query`)

```python
_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_USER_AGENT = "runts-cai-geocoder/1.0 (https://github.com/piccioli/runts)"
```

Costruzione query:

1. Parti: `[comune.title()]`, se `regione` è valorizzata aggiunge `regione`, in coda `"Italia"`.
2. Join con `", "` → es. `"Pisa, Toscana, Italia"`.
3. Querystring: `q=<query>&format=json&limit=1`.
4. Richiesta `GET` con header `User-Agent` (obbligatorio per la policy Nominatim) e `timeout=10`.
5. Parsing JSON: se la lista è non vuota, estrae `(float(lat), float(lon))` dal primo risultato. Altrimenti ritorna `None`.

In caso di **qualsiasi eccezione** (rete, JSON malformato, timeout), logga warning e ritorna `None` — l'errore non blocca il batch.

## Vincoli operativi

| Vincolo | Valore | Sorgente |
|---|---|---|
| Rate limit Nominatim | 1 req/s | Policy ufficiale OSM Nominatim. |
| User-Agent obbligatorio | sì | Policy: identificare l'applicazione. |
| Timeout per richiesta | 10 s | Hardcoded in `_nominatim_query`. |
| Idempotenza | sì | Filtro `WHERE lat IS NULL OR lon IS NULL` salta gli enti già geocodificati. |

Per ~226 enti senza coordinate, il batch dura circa **4 minuti** (rate limit + tempo di risposta).

## Precisione e granularità

La query usa **comune + regione**, **non l'indirizzo completo**. Conseguenze:

- Le coordinate ottenute sono **a livello di centroide del comune**, non dell'indirizzo esatto.
- Buono per la mappa d'insieme a scala nazionale/regionale; meno preciso per la mappa di dettaglio del singolo ente (lo zoom 14 della pagina di dettaglio mostra comunque la città).
- Più affidabile rispetto a query con indirizzi RUNTS spesso incompleti o malformattati.

Decisione architetturale (vedi `openspec/changes/mappa-enti/design.md`): la precisione "civico esatto" è esplicitamente fuori scope.

## Casi di fallimento

| Caso | Comportamento |
|---|---|
| `sede_comune` NULL | Salto (`skipped`), log debug. |
| Nominatim non trova nulla | `not_found`, log warning, lat/lon restano NULL. |
| Errore di rete o timeout | Log warning con il messaggio dell'eccezione, lat/lon restano NULL. |
| JSON malformato | Idem: log warning, valore `None`. |

In nessun caso il geocoder esce con codice di errore: termina sempre con il report finale e codice 0.

## Esito tipico

Sul dataset attuale (~226 enti CAI), un'esecuzione completa geocodifica **>= 200 enti** correttamente. Le 20-26 mancate corrispondono solitamente a:

- Comuni con varianti ortografiche non riconosciute da Nominatim.
- Comuni con omonimi multipli risolti su un'area diversa (raro grazie all'aggiunta della regione).

## Logging

| Livello | Eventi |
|---|---|
| INFO | apertura DB, count "già presenti", ogni geocodifica riuscita (`Geocodificato <id> (<comune>): <lat>, <lon>`). |
| WARNING | errore Nominatim per query, ente non trovato. |
| DEBUG | ente senza comune saltato. |

Formato: identico a quello dello scraper (`%(asctime)s  %(levelname)-8s  %(message)s`, `%H:%M:%S`).

## Comportamenti non garantiti

- **Re-run dopo scraper**: se lo scraper viene rieseguito (e `lat`/`lon` non sono nel dict di upsert), le coordinate vengono azzerate dall'`INSERT OR REPLACE`. Il geocoder andrà rieseguito per ripopolarle.
- **Cambio di policy Nominatim**: l'endpoint pubblico ha limiti d'uso e potrebbe rifiutare richieste anomale; non ci sono fallback a server alternativi.
- **Mancanza di cache locale**: non c'è una tabella di lookup persistente (comune → lat/lon) condivisa tra esecuzioni; ogni geocodifica fa una nuova richiesta.
