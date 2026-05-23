## Why

La mappa attuale mostra solo i 20 enti della pagina corrente, rendendo la vista d'insieme inefficace; gli operatori non hanno modo di esportare il dataset; ogni rerun dello scraper azzera le coordinate già geocodificate; un singolo timeout di rete fa perdere un ente senza retry. Questo primo rilascio incrementale risolve tutti e quattro i problemi con modifiche additive e idempotenti.

## What Changes

- **Mappa potenziata**: endpoint GeoJSON dedicato che restituisce tutti gli enti filtrati (senza paginazione), clustering via `Leaflet.markercluster`, sidebar filtri con checkbox e filtro live client-side con sincronizzazione URL.
- **Export del dato**: endpoint CSV (UTF-8 BOM, separatore `;`), Excel (openpyxl, header congelato) e PDF scheda ente (reportlab + carta intestata Montagna Servizi) con pulsanti nei template.
- **Resilienza scraper**: `upsert_ente` preserva `lat`/`lon` esistenti se assenti nel dict in input; retry fino a 3 volte con backoff esponenziale (1 s, 2 s, 4 s) su eccezioni di rete.
- **Performance e cache geocoding**: indici DB su `sede_regione` e `sezione_registro`; nuova tabella `geocoding_cache` con lookup prima di ogni chiamata Nominatim; report finale con contatori `from_cache` / `from_nominatim`.

## Capabilities

### New Capabilities
- `enti-geojson`: endpoint `GET /api/enti.geojson` che restituisce GeoJSON FeatureCollection filtrato e senza paginazione
- `enti-export`: endpoint CSV e Excel degli enti filtrati con i relativi pulsanti UI
- `ente-pdf`: endpoint PDF scheda ente con carta intestata Montagna Servizi
- `geocoding-cache`: tabella `geocoding_cache` e logica di lookup/write nel geocoder
- `scraper-resilience`: retry con backoff esponenziale nell'estrazione dettaglio ente

### Modified Capabilities
- `enti-list`: la vista mappa passa da array inline a fetch verso `/api/enti.geojson`; aggiunta sidebar filtri con clustering; parametri `regione`/`sezione_registro` accettano valori multipli comma-separated
- `ente-detail`: aggiunta pulsante "Scarica scheda PDF"
- `database-storage`: nuovi indici su `enti(sede_regione)` e `enti(sezione_registro)`; nuova tabella `geocoding_cache`; `upsert_ente` preserva `lat`/`lon`
- `geocoding`: report finale esteso con contatori cache/Nominatim; lookup cache prima di ogni richiesta HTTP

## Impact

- **`web/app.py`**: 3 nuovi endpoint (`/api/enti.geojson`, `/api/enti.csv`, `/api/enti.xlsx`, `/ente/{id_runts}/pdf`); refactoring logica filtri in funzione condivisa; accettazione multi-valore per `regione` e `sezione_registro`
- **`web/templates/list.html`**: sostituzione array inline con fetch; integrazione markercluster; sidebar filtri; pulsanti CSV/Excel
- **`web/templates/detail.html`**: pulsante "Scarica scheda PDF"
- **`web/requirements.txt`**: aggiunta `openpyxl`, `reportlab`, `pypdf`
- **`scraper/db.py`**: schema e migrazioni per indici e `geocoding_cache`; modifica `upsert_ente`
- **`scraper/scraper.py`**: wrapper retry attorno all'estrazione dettaglio; report esteso
- **`scraper/geocoder.py`**: funzioni `cache_key`, `lookup_cache`, `write_cache`; report esteso
- **`web/static/`**: copia di `MS_Carta_Intestata.pdf` per uso nel PDF scheda ente
- **CDN**: aggiunta `leaflet.markercluster` 1.5.x nei template
