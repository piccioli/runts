## 1. Database: migrazioni, indici e cache

- [x] 1.1 In `scraper/db.py`, aggiungere `CREATE INDEX IF NOT EXISTS idx_enti_sede_regione ON enti(sede_regione)` e `idx_enti_sezione_registro ON enti(sezione_registro)` allo schema e a `_MIGRATIONS`
- [x] 1.2 In `scraper/db.py`, aggiungere `CREATE TABLE IF NOT EXISTS geocoding_cache (cache_key TEXT PRIMARY KEY, lat REAL NOT NULL, lon REAL NOT NULL, source TEXT NOT NULL, ts TEXT NOT NULL)` allo schema e a `_MIGRATIONS`
- [x] 1.3 In `scraper/db.py`, modificare `upsert_ente` per leggere `lat`, `lon` esistenti prima dell'`INSERT OR REPLACE` se non presenti o `None` nel dict in input
- [x] 1.4 Aggiungere test in `scraper/test_upsert.py` che verifica che un rerun non azzeri `lat`/`lon` già presenti

## 2. Geocoder: cache e report esteso

- [x] 2.1 In `scraper/geocoder.py`, implementare `_cache_key(comune, provincia, regione) -> str` (normalizzazione lowercase + strip + `|`)
- [x] 2.2 Implementare `_lookup_cache(conn, key) -> tuple[float, float] | None` con SELECT su `geocoding_cache`
- [x] 2.3 Implementare `_write_cache(conn, key, lat, lon, source)` con `INSERT OR REPLACE INTO geocoding_cache`
- [x] 2.4 In `geocode_enti`, eseguire `_lookup_cache` prima di `_nominatim_fetch`; se hit, usare le coordinate e incrementare `from_cache`
- [x] 2.5 In caso di successo Nominatim, chiamare `_write_cache` con `source='nominatim'` e `ts` ISO UTC; incrementare `from_nominatim`
- [x] 2.6 Estendere il report finale con contatori `from_cache` e `from_nominatim` distinti

## 3. Scraper: retry con backoff

- [x] 3.1 In `scraper/scraper.py`, avvolgere il blocco di estrazione dettaglio in un loop `for attempt in range(3)` con `await asyncio.sleep(2 ** attempt)` su eccezione
- [x] 3.2 Dopo il 3° fallimento, loggare ERROR e proseguire (comportamento attuale invariato)
- [x] 3.3 Aggiungere contatori `recovered_attempt_2`, `recovered_attempt_3`, `failed_after_retry` al report finale di `main.py`

## 4. API: endpoint GeoJSON

- [x] 4.1 In `web/app.py`, estrarre la logica filtri SQL in una funzione condivisa `_build_filter_query(q, regione, sezione_registro)`
- [x] 4.2 Aggiungere route `GET /api/enti.geojson` che usa `_build_filter_query`, filtra solo gli enti con `lat IS NOT NULL AND lon IS NOT NULL`, e restituisce GeoJSON `FeatureCollection` con `Content-Type: application/geo+json`
- [x] 4.3 La route SHALL accettare `regione` e `sezione_registro` come valori comma-separated (split su `,` → `IN (?)`)

## 5. API: endpoint CSV ed Excel

- [x] 5.1 In `web/requirements.txt`, aggiungere `openpyxl`
- [x] 5.2 Aggiungere route `GET /api/enti.csv` con `StreamingResponse`, CSV UTF-8 BOM separatore `;`, campi secondo spec B1
- [x] 5.3 Aggiungere route `GET /api/enti.xlsx` con generazione in memoria via `openpyxl.Workbook` + `BytesIO`, foglio "Enti", header congelato

## 6. API: endpoint PDF scheda ente

- [x] 6.1 In `web/requirements.txt`, aggiungere `reportlab` e `pypdf`
- [x] 6.2 Copiare `docs/PDF/MS_Carta_Intestata.pdf` in `web/static/MS_Carta_Intestata.pdf`
- [x] 6.3 Creare `web/pdf_utils.py` con funzione `build_ente_pdf(ente_row) -> bytes` che genera il PDF con reportlab e sovrappone la carta intestata via pypdf
- [x] 6.4 Aggiungere route `GET /ente/{id_runts}/pdf` in `web/app.py` che chiama `build_ente_pdf` e restituisce `Response` con `Content-Type: application/pdf`

## 7. Frontend: mappa con GeoJSON, clustering e sidebar

- [x] 7.1 In `web/templates/list.html`, includere `Leaflet.markercluster` 1.5.x JS+CSS via CDN (versione fissa)
- [x] 7.2 Sostituire la costruzione dell'array marker inline con una funzione `fetchAndRenderMap()` che chiama `/api/enti.geojson` con i filtri correnti
- [x] 7.3 Sostituire `L.marker(...).addTo(map)` con `L.markerClusterGroup()` nel JS della mappa
- [x] 7.4 Aggiungere markup HTML della sidebar filtri (regioni e sezioni con checkbox e conteggio) — collassabile su mobile
- [x] 7.5 Implementare filtro client-side dei marker al cambio checkbox della sidebar
- [x] 7.6 Sincronizzare la query string del browser con `history.replaceState` al cambio checkbox

## 8. Frontend: pulsanti export e PDF

- [x] 8.1 In `web/templates/list.html`, aggiungere pulsanti "Esporta CSV" e "Esporta Excel" che trasmettono i filtri correnti agli endpoint `/api/enti.csv` e `/api/enti.xlsx`
- [x] 8.2 In `web/templates/detail.html`, aggiungere pulsante "Scarica scheda PDF" che punta a `/ente/{id_runts}/pdf`

## 9. Verifica e collaudo

- [x] 9.1 Rilanciare scraper su 3-4 enti già geocodificati e verificare che `lat`/`lon` siano ancora presenti nel DB
- [x] 9.2 Aprire la mappa con filtro regionale e verificare che tutti i marker della regione siano visibili (non solo i 20 della pagina)
- [x] 9.3 Esportare CSV e Excel, aprirli in LibreOffice/Excel e verificare encoding + caratteri italiani
- [x] 9.4 Generare scheda PDF di CAI Pisa (`id_runts=83894`), verificare layout + carta intestata
- [x] 9.5 Eseguire `EXPLAIN QUERY PLAN SELECT * FROM enti WHERE sede_regione = 'Toscana'` e verificare uso di `idx_enti_sede_regione`
- [x] 9.6 Eseguire geocoder due volte di fila: il secondo run deve avere `from_cache` > 0
- [x] 9.7 Ricostruire il container Docker (`docker compose build --no-cache`) e verificare che tutto funzioni in produzione
