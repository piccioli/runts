# 03 — Database (SQLite)

> Schema, migrazioni e regole di persistenza implementati in `scraper/db.py`.

## File e modalità

- **Percorso default**: `runts.db` alla radice del progetto (configurabile via `--db` per scraper/geocoder e via `DB_PATH` per la web app).
- **Engine**: SQLite locale, accesso via `sqlite3` standard library.
- **Journal mode**: `WAL` abilitato in `init_db` (`PRAGMA journal_mode=WAL`). Consente letture concorrenti da parte della web app mentre lo scraper scrive.
- **Row factory**: `sqlite3.Row` ovunque, per accesso per nome di colonna.
- **Read-only lato web**: la connessione lato `web/app.py` usa l'URI `file:<path>?mode=ro` con `uri=True`, garantendo che il container non possa modificare il DB.

## Schema della tabella `enti`

Definizione canonica in `scraper/db.py` (costante `SCHEMA`):

```sql
CREATE TABLE IF NOT EXISTS enti (
    id_runts          TEXT PRIMARY KEY,
    codice_fiscale    TEXT UNIQUE,
    denominazione     TEXT,
    forma_giuridica   TEXT,
    natura_giuridica  TEXT,
    sede_stato        TEXT,
    sede_indirizzo    TEXT,
    sede_civico       TEXT,
    sede_comune       TEXT,
    sede_provincia    TEXT,
    sede_regione      TEXT,
    sede_cap          TEXT,
    lat               REAL,
    lon               REAL,
    data_iscrizione   TEXT,
    sezione_registro  TEXT,
    settori_attivita  TEXT,
    rappresentante_legale TEXT,
    sito_web          TEXT,
    pec               TEXT,
    url_dettaglio     TEXT,
    raw_json          TEXT,
    updated_at        TEXT NOT NULL
);
```

### Vincoli

| Colonna | Vincolo | Significato |
|---|---|---|
| `id_runts` | `PRIMARY KEY` | Identificatore RUNTS, **obbligatorio per ogni record persistito**. |
| `codice_fiscale` | `UNIQUE` | Non possono esistere due enti con lo stesso CF. |
| `updated_at` | `NOT NULL` | Timestamp ISO UTC dell'ultimo upsert. |

Tutte le altre colonne sono nullable: i campi non trovati nella scheda di dettaglio vengono salvati come `NULL`.

### Significato delle colonne

| Colonna | Origine dati | Esempio |
|---|---|---|
| `id_runts` | `spnRepertorio` (RUNTS) | `83894` |
| `codice_fiscale` | `spnCodiceFiscale` o normalizzazione label | `93000990503` |
| `denominazione` | tabella risultati o label | `CLUB ALPINO ITALIANO SEZIONE DI PISA` |
| `forma_giuridica` | label "Forma giuridica" | `Associazione` |
| `natura_giuridica` | label "Natura giuridica" | `Associazione non riconosciuta` |
| `sede_stato` | `spnStatoSL` | `ITALIA` |
| `sede_indirizzo` | `spnIndirizzoSL` | `Via Cesare Battisti` |
| `sede_civico` | `spnCivicoSL` | `1` |
| `sede_comune` | `spnComuneSL` | `PISA` |
| `sede_provincia` | `spnProvinciaSL` | `PI` |
| `sede_regione` | `spnRegioneSL` o derivata da provincia | `Toscana` |
| `sede_cap` | `spnCAP_SL` | `56125` |
| `lat`, `lon` | geocoder (Nominatim) | `43.7159, 10.4018` |
| `data_iscrizione` | `spnIscrittoIl` (con prefisso "Iscritto il" rimosso) | `15/02/2023` |
| `sezione_registro` | tabella risultati o label | `Associazioni di promozione sociale` |
| `settori_attivita` | label generica (se presente) | testo libero |
| `rappresentante_legale` | regex sul body (formato `Cognome Nome`) | `ROSSI MARIO` |
| `sito_web` | `spnSitoInternet` | `https://...` |
| `pec` | `spnEmailPec` | `cai.pisa@pec.it` |
| `url_dettaglio` | URL della scheda RUNTS | `https://servizi.lavoro.gov.it/...` |
| `raw_json` | primi 10000 caratteri del body | testo grezzo per audit |
| `updated_at` | `datetime.now(timezone.utc).isoformat()` | `2026-05-22T18:45:12.123456+00:00` |

## Migrazioni

`init_db()` esegue, dopo `CREATE TABLE IF NOT EXISTS`, un ciclo di `ALTER TABLE` definiti in `_MIGRATIONS`. Ogni `ALTER` è racchiuso in `try/except sqlite3.OperationalError` per essere idempotente (se la colonna esiste già, errore silenziato).

`_MIGRATIONS` attualmente contiene:

```python
"ALTER TABLE enti ADD COLUMN sede_stato TEXT",
"ALTER TABLE enti ADD COLUMN sede_civico TEXT",
"ALTER TABLE enti ADD COLUMN lat REAL",
"ALTER TABLE enti ADD COLUMN lon REAL",
```

### Regole per nuove migrazioni

1. Aggiungere la colonna a `SCHEMA` (per le installazioni nuove).
2. Aggiungere l'`ALTER TABLE ... ADD COLUMN ...` a `_MIGRATIONS` (per le installazioni esistenti).
3. Aggiungere la colonna alla lista `columns` di `upsert_ente()` (altrimenti il valore non verrà mai scritto).

Non c'è un sistema di versionamento esplicito (no `PRAGMA user_version`): l'idempotenza è garantita solo dal try/except.

## Upsert (`upsert_ente`)

Firma: `upsert_ente(conn: sqlite3.Connection, data: dict) -> "inserted" | "updated"`.

Comportamento:

1. Si fa una copia del dict in input e si imposta `data["updated_at"] = datetime.now(timezone.utc).isoformat()`.
2. Se `raw_json` non è presente, viene popolato con `json.dumps(data, ensure_ascii=False)`.
3. Si calcola `id_runts = data.get("id_runts") or data.get("codice_fiscale")`. Se entrambi sono nulli, viene sollevato `ValueError("Record senza id_runts né codice_fiscale, impossibile fare upsert")`.
4. Si verifica esistenza con `SELECT 1 FROM enti WHERE id_runts = ?` per decidere il valore di ritorno (`"inserted"` o `"updated"`).
5. Si esegue `INSERT OR REPLACE INTO enti (...) VALUES (...)` su una lista fissa di 23 colonne.
6. `conn.commit()` chiude la transazione.

### Lista canonica di colonne scritte dall'upsert

```
id_runts, codice_fiscale, denominazione, forma_giuridica,
natura_giuridica, sede_stato, sede_indirizzo, sede_civico,
sede_comune, sede_provincia, sede_regione, sede_cap,
lat, lon, data_iscrizione, sezione_registro, settori_attivita,
rappresentante_legale, sito_web, pec,
url_dettaglio, raw_json, updated_at
```

Eventuali chiavi extra nel dict (es. fallback snake_case da `_normalize_label`) vengono **ignorate**: non c'è schema flessibile.

### Conseguenze di `INSERT OR REPLACE`

Un upsert **riscrive sempre tutte le colonne**. Se in una nuova esecuzione un campo è assente, viene sovrascritto con `NULL`. Questo significa che:

- Lo scraper deve fornire i campi più completi possibili a ogni run.
- Il geocoder, che agisce con `UPDATE` mirato su `lat`/`lon`, non viene invalidato da un'esecuzione successiva dello scraper a patto che l'`upsert_ente` riceva `lat`/`lon` valorizzati nel dict — ma lo scraper **non** li popola, quindi un rerun dello scraper **azzera le coordinate**.

> ⚠️ Questo è un comportamento attuale del sistema da tenere presente nelle specifiche: dopo un rerun completo dello scraper occorre rilanciare il geocoder.

## Lettura aggregata (`get_stats`)

`get_stats(conn) -> {"total": int}`: ritorna il numero di righe nella tabella `enti`. Usato solo nel report finale dello scraper. Non c'è caching.

## Indici

Non esistono indici espliciti oltre alla `PRIMARY KEY` su `id_runts` e all'`UNIQUE` su `codice_fiscale`. Per i volumi attuali (~226 righe) la web app esegue scan completi senza problemi di performance. Eventuali indici aggiuntivi (es. su `sede_regione`, `sezione_registro`) sarebbero utili solo a partire da decine di migliaia di righe.

## Sicurezza e integrità

- **Nessun input utente arriva al DB**: lo scraper scrive dati pubblici e la web app è read-only.
- Le query della web app usano sempre **parametri posizionali** (`?`) con la `execute`, mai concatenazione di stringhe: protezione completa da SQL injection.
- Non esiste backup automatico né rotation; il DB è committato/gestito a mano dall'operatore.
