# 02 — Scraper RUNTS-CAI

> Comportamento osservato del modulo `scraper/` allo stato attuale.

## Scopo

Lo scraper acquisisce in modo automatico la lista delle sezioni del CAI dal portale RUNTS, estraendo da ciascuna scheda di dettaglio i campi strutturati, e li persiste nel database SQLite locale.

## Entrypoint CLI

File: `scraper/main.py`. Eseguibile come modulo:

```bash
python -m scraper.main [--db PATH] [--headless | --no-headless] [--delay MS] [--verbose]
```

Argomenti:

| Argomento | Default | Significato |
|---|---|---|
| `--db PATH` | `runts.db` | Percorso del file SQLite (verrà creato se non esiste). |
| `--headless` / `--no-headless` | `True` | Modalità Chromium. `--no-headless` apre una finestra visibile per debug. |
| `--delay MS` | `500` | Pausa in millisecondi dopo aver estratto un dettaglio, prima di tornare alla lista. |
| `--verbose`, `-v` | off | Livello log `DEBUG`. |

A fine esecuzione viene stampato un **report finale** con il conteggio di enti processati, inseriti, aggiornati, errori di salvataggio e totale presente nel DB (vedi `main.py:88-98`).

## URL e selettori target

| Costante | Valore | Funzione |
|---|---|---|
| `SEARCH_URL` | `https://servizi.lavoro.gov.it/runts/it-it/Ricerca-enti` | Form di ricerca pubblico RUNTS. |
| `DETAIL_URL_PATTERN` | `**/Ricerca-enti/Ente*` | Pattern per `wait_for_url` dopo click su "Dettaglio". |

Il portale gira su DotNetNuke e popola i campi via JavaScript: lo scraper attende sempre `networkidle` e poi i selettori specifici prima di estrarre.

## Flusso di esecuzione

1. **`init_db(args.db)`** — apre la connessione SQLite, abilita WAL, applica schema + migrazioni.
2. **`run_scraper(denominazione="CLUB ALPINO ITALIANO", headless, delay_ms)`** — orchestra l'intero scraping; restituisce `list[dict]` pronti per upsert.
3. **Loop di upsert** — per ogni dict restituito, `upsert_ente(conn, entity)` ritorna `"inserted"` o `"updated"` e i contatori vengono aggiornati.
4. **Report finale** — `get_stats(conn)` legge il totale aggiornato e viene stampato il riepilogo.

In caso di **eccezione fatale durante `run_scraper`**, la connessione DB viene chiusa e il processo esce con `sys.exit(1)` (`main.py:67-70`).

## Fase 1 — Ricerca (`search_enti`)

1. Naviga su `SEARCH_URL` con `wait_until="domcontentloaded"`.
2. Attesa fissa di 2000 ms per il rendering DNN.
3. Riempie `input[id*="denominazione" i]` con la denominazione (default `"CLUB ALPINO ITALIANO"`).
4. Click su `input[type="submit"]`.
5. Attende `input[value="Dettaglio"]` (timeout 30 s) come segnale di tabella risultati popolata.
6. Pausa di 500 ms per stabilizzare la pagina.

### Conteggio risultati

- **Totale enti** (`_get_total_items`): legge l'attributo `value` di `[id*="hdnListEntiTotalItems"]`. Fallback a 0 se assente.
- **Paginazione** (`_get_page_info`): estrae `(N, M)` dalla label `[id*="spnLabelNumeroPagina"]` con la regex `(\d+)\s+di\s+(\d+)`. Fallback a `(1, 1)`.

Se `total_items == 0` lo scraper logga `"Nessun ente trovato per '<denominazione>'."` e restituisce lista vuota senza errore.

## Fase 2 — Paginazione (`_go_to_next_page`)

1. Controlla `(cur, tot)` correnti; se `cur >= tot` ritorna `False`.
2. Click su `a[id*="ltlProssimaPagina"]`.
3. **Attesa specifica** della label paginazione che mostra `"Pagina <expected_page>"` (timeout 20 s) — workaround per la race condition tra DOM aggiornato e label DNN.
4. Attesa di `input[value="Dettaglio"]` (timeout 10 s).

Se la transizione fallisce, viene loggato un warning e si ritorna `False` (il ciclo principale si fermerà).

## Fase 3 — Estrazione metadati di riga (`_collect_row_metadata`)

Per ogni `tr` in `table tbody`, legge le prime tre `td`:

- `denominazione` (cella 0)
- `sede_comune` (cella 1)
- `sezione_registro` (cella 2)

Queste informazioni sono raccolte **prima** di navigare al dettaglio: vengono unite ai campi estratti dalla scheda di dettaglio per gli eventuali valori non trovati lì.

## Fase 4 — Navigazione al dettaglio

Per ogni indice `i` dei pulsanti `input[value="Dettaglio"]`:

1. Click sull'i-esimo pulsante.
2. `page.wait_for_url(DETAIL_URL_PATTERN, timeout=15s)`.
3. `page.wait_for_load_state("networkidle", timeout=20s)`.
4. `extract_fields(page)` — vedi fase 5.
5. `await asyncio.sleep(delay_ms / 1000)`.
6. `_back_to_results(page)` — `page.go_back()` + attesa pulsanti Dettaglio (timeout 10 s).
7. Se il back fallisce, lo scraper **ri-esegue la ricerca** e naviga fino alla pagina corrente con `_go_to_next_page` ripetuto.

In caso di eccezione su un singolo ente, viene loggato l'errore con denominazione e indice, e si tenta il back; se il back fallisce si ri-esegue la ricerca dalla pagina 1.

I dialog del browser sono accettati automaticamente: `page.on("dialog", lambda d: asyncio.ensure_future(d.accept()))`.

## Fase 5 — Estrazione campi (`extract_fields`)

### 5.1 Campi base via selettori ID

| Chiave | Selettore (substring match) | Note |
|---|---|---|
| `id_runts` | `spnRepertorio` | Numero di repertorio RUNTS. Usato come chiave primaria. |
| `codice_fiscale` | `spnCodiceFiscale` | Codice fiscale dell'ente. |
| `pec` | `spnEmailPec` | Email PEC. |
| `sito_web` | `spnSitoInternet` | URL sito web. |

Attesa preliminare di `[id*="spnRepertorio"]` (timeout 10 s) come gate sull'avvenuto rendering del dettaglio.

### 5.2 Sede legale via JS scoped

Lo script `_EXTRACT_SEDE_LEGALE_JS` cerca un container `[id*="divSedeLegale"]` e all'interno estrae i campi via selettori con suffisso `SL` (Sede Legale):

| Chiave nel dict | Selettore | Colonna DB |
|---|---|---|
| `stato` | `[id*="spnStatoSL"]` | `sede_stato` |
| `provincia` | `[id*="spnProvinciaSL"]` | `sede_provincia` |
| `comune` | `[id*="spnComuneSL"]` | `sede_comune` |
| `indirizzo` | `[id*="spnIndirizzoSL"]` | `sede_indirizzo` |
| `civico` | `[id*="spnCivicoSL"]` | `sede_civico` |
| `cap` | `[id*="spnCAP_SL"]` | `sede_cap` |
| `regione` | `[id*="spnRegioneSL"]` | `sede_regione` |

Il container `divSedeLegale` **scopa** l'estrazione, evitando collisioni con altri blocchi (es. sede operativa, sede amministrativa).

#### 5.2.1 Derivazione regione da sigla provincia

Se `sede_regione` non viene trovata nel DOM ma `sede_provincia` sì, viene applicata la mappa statica `_PROVINCIA_TO_REGIONE` (sigle di tutte le province italiane). Se la sigla non è mappata, viene loggato un debug e la regione resta nulla.

Esempi: `"PI"` → `"Toscana"`, `"BZ"` → `"Trentino-Alto Adige"`, `"MI"` → `"Lombardia"`.

### 5.3 Data di iscrizione

`[id*="spnIscrittoIl"]` con strip del prefisso `"Iscritto il "` (case insensitive) → `data_iscrizione`.

### 5.4 Coppie label/valore generiche

Lo script `_EXTRACT_BOLD_JS` itera su `.ente_bold`, prende l'elemento adiacente `[class*="ente_testo"]:not(.ente_bold)` e restituisce un dict `{label: value}`. Le label vengono normalizzate da `_normalize_label`:

| Label italiana (sostringa, lowercase) | Colonna DB |
|---|---|
| `sezione del registro` / `sezione` | `sezione_registro` |
| `forma giuridica` | `forma_giuridica` |
| `natura giuridica` | `natura_giuridica` |
| `codice fiscale` | `codice_fiscale` |
| `email pec` | `pec` |
| `sito internet` | `sito_web` |
| `denominazione` | `denominazione` |
| `provincia` | `sede_provincia` |
| `comune` | `sede_comune` |
| `regione` | `sede_regione` |
| `indirizzo` | `sede_indirizzo` |
| `cap` | `sede_cap` |

Label sconosciute con lunghezza ≤ 50 caratteri vengono incluse con chiave snake_case derivata; quelle più lunghe (header di sezione) sono scartate. Una chiave già presente nel dict non viene sovrascritta.

### 5.5 Rappresentante legale e raw_json

- Tutto il testo del `<body>` viene letto e troncato ai primi 10000 caratteri in `data["raw_json"]` come backup grezzo per debug/verifiche.
- Regex sul body: `Rappresentante legale\s+S[ìi]\b.*?Nome\s+(\S+).*?Cognome\s+(\S+)` (case insensitive, dotall). Se trovata, popola `rappresentante_legale` come `"Cognome Nome"` (solo se non già presente).

### 5.6 URL del dettaglio

`data["url_dettaglio"] = page.url` viene sempre impostato (URL diretto della scheda RUNTS).

## Configurazione browser

```python
browser = pw.chromium.launch(headless=headless)
context = browser.new_context(
    user_agent=(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
)
```

User-agent mascherato come Chrome su macOS per ridurre il rischio di blocchi lato server. Nessuna persistenza di stato/cookies tra esecuzioni.

## Logging

| Livello | Eventi |
|---|---|
| INFO | navigazione, totale enti, cambio pagina, ogni ente processato (`[N/TOT] <denominazione>`), apertura DB, report finale. |
| WARNING | timeout label paginazione, errore Nominatim (geocoder), errore salvataggio, back navigation fallita. |
| ERROR | eccezione su singolo ente, errore fatale globale. |
| DEBUG | dettagli di estrazione JS, mismatch provincia→regione, fallback go_back. |

Formato: `%(asctime)s  %(levelname)-8s  %(message)s` con `datefmt="%H:%M:%S"`.

## Test esistenti

`scraper/test_sede_legale.py` (pytest) verifica l'estrazione della sede legale per casi noti. Va eseguito nell'ambiente con `playwright` installato.

## Comportamenti non garantiti

- Estrazione dipende dalla struttura HTML/ID del portale RUNTS; cambi lato server possono rompere lo scraping.
- Nessun retry automatico in caso di errore di rete: l'ente fallito viene saltato e segnalato come errore.
- Lo scraper non gestisce captcha o blocchi lato server diversi dall'errore generico.
- Le label normalizzate da `_normalize_label` con la fallback snake_case possono produrre colonne extra non presenti nello schema; queste vengono ignorate da `upsert_ente` perché filtrate sulla lista `columns` (vedi spec database).
