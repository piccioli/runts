## Context

Il progetto RUNTS CAI è un'applicazione FastAPI + Jinja2 che espone una web app per navigare gli enti CAI iscritti al RUNTS. Il dato viene scritto da uno scraper Playwright su SQLite (`runts.db`), letto dall'app web in sola lettura via Docker. Il geocoder (Nominatim, 1 req/s) popola le colonne `lat`/`lon` su un run separato.

Stato corrente dei componenti toccati da questo change:
- **Lista enti**: la vista mappa legge i marker da un array JS inline limitato alla pagina corrente (20 enti).
- **Export**: nessun endpoint esistente; l'unica uscita è il browser.
- **upsert_ente**: usa `INSERT OR REPLACE` che azzera `lat`/`lon` a ogni rerun dello scraper.
- **Scraper**: nessun retry; un timeout di rete su un ente lo perde silenziosamente.
- **Geocoder**: chiama Nominatim per ogni ente con `lat IS NULL`; nessuna cache.

## Goals / Non-Goals

**Goals:**
- Mappa che mostra tutti gli enti filtrati (non solo la pagina corrente), con clustering e filtri live client-side
- Export CSV, Excel e PDF della scheda ente con carta intestata Montagna Servizi
- `upsert_ente` non azzera più le coordinate a ogni rerun
- Retry con backoff esponenziale nell'estrazione dettaglio
- Cache geocoding per evitare chiamate Nominatim duplicate tra run

**Non-Goals:**
- Autenticazione o controllo accessi
- Scraper schedulato automaticamente
- Geocoding con provider commerciali (Google Maps, HERE)
- Supporto a dataset > 5000 enti (oltre quella soglia valutare MVT/PBF)

## Decisions

### D1. Endpoint GeoJSON vs array inline

**Scelta**: endpoint dedicato `GET /api/enti.geojson` + fetch dal template JS.

**Alternativa scartata**: array inline nel template. Funziona per 226 enti (~50 KB) ma non permette riuso esterno, non scala con filtri client-side e richiede ri-render del template per ogni cambio filtro.

**Rationale**: l'endpoint è riusabile (embed, integrazioni future), disaccoppia mappa da template lista, e abilita i filtri live senza ricaricamento pagina.

### D2. Clustering: Leaflet.markercluster

**Scelta**: `Leaflet.markercluster` 1.5.x via CDN, versione fissa per evitare breaking change silenzioso.

**Alternativa scartata**: nessun clustering — illeggibile in città con 5+ sezioni CAI vicine (es. Milano, Roma, Firenze).

### D3. Sidebar filtri: stato in URL tramite history.replaceState

**Scelta**: i filtri attivi nella sidebar mappa sono serializzati come `?regione=Toscana,Lombardia&sezione_registro=APS` (comma-separated) con `history.replaceState`. Il server accetta valori multi-valore splitting su `,`.

**Alternativa scartata**: parametri multipli stessa chiave (`?regione=Toscana&regione=Lombardia`) — supporto non uniforme in framework diversi.

### D4. upsert_ente: read-modify-write vs UPSERT condizionale

**Scelta**: read-modify-write — prima `SELECT lat, lon WHERE id_runts = ?`, poi fill del dict se `None`, poi `INSERT OR REPLACE`.

**Alternativa scartata**: `INSERT ... ON CONFLICT DO UPDATE SET lat = CASE WHEN excluded.lat IS NOT NULL THEN excluded.lat ELSE lat END` — più atomico e SQL-nativo, ma richiede riscrivere le 23 colonne dell'INSERT OR REPLACE. Preferita la semplicità per ora; migrare in futuro se emergono race condition.

### D5. Export Excel: openpyxl

**Scelta**: `openpyxl` — più semplice e più diffuso.

**Alternativa scartata**: `xlsxwriter` — output più compatto, ma API più verbosa e non necessaria per un singolo sheet senza formule.

### D6. PDF scheda ente: reportlab + pypdf merge

**Scelta**: contenuto generato con `reportlab` (font DejaVu per Unicode), poi overlay con `pypdf.merge_page` su `MS_Carta_Intestata.pdf` come sfondo.

**Alternativa scartata**: WeasyPrint (HTML→PDF) — più semplice ma meno controllo sul posizionamento sulla carta intestata; scartato per coerenza con la pipeline documentazione esistente.

**Fonte carta intestata**: `docs/PDF/MS_Carta_Intestata.pdf` copiato in `web/static/` al momento del build Docker.

### D7. Cache geocoding: tabella SQLite

**Scelta**: tabella `geocoding_cache` in `runts.db` con chiave normalizzata `<comune>|<provincia>|<regione>` (lowercase, strip). Lookup prima di ogni chiamata Nominatim; write in caso di miss + successo.

**Alternativa scartata**: file JSON locale — meno robusto a scritture concorrenti e non interrogabile con SQL.

**Cache key**: `comune.strip().lower() + "|" + (provincia or "").strip().lower() + "|" + (regione or "").strip().lower()`

## Risks / Trade-offs

- **Compatibilità markercluster**: testare con Leaflet 1.9.4 (versione corrente) prima di mergiare. Il plug-in 1.5.x è compatibile ma richiede verifica.
- **PDF con campi extra-lunghi**: `KeepInFrame` di reportlab previene lo sforamento pagina ma può troncare i valori — troncamento preferibile a layout rotto.
- **Cache geocoding desallineata** se i confini comunali cambiano (raro): aggiungere `python -m scraper.geocoder --refresh-cache` per invalidare in futuro (out of scope per questo change).
- **GeoJSON response size**: con 226 enti il payload è ~30 KB — accettabile. Con dataset molto più grandi valutare compressione gzip (FastAPI la supporta) o paginazione spaziale.
- **Read-only DB nel container**: gli endpoint CSV/Excel/GeoJSON non aprono connessioni in scrittura (coerente con il vincolo esistente).

## Migration Plan

1. Applicare le migrazioni DB (`_MIGRATIONS` idempotenti) al primo avvio dello scraper dopo il deploy.
2. Copiare `docs/PDF/MS_Carta_Intestata.pdf` in `web/static/` (step nel Dockerfile o manuale pre-build).
3. Ricostruire il container web (`docker compose build --no-cache && docker compose up -d`).
4. Lanciare il geocoder per popolare `geocoding_cache` dalla prima run post-deploy.
5. Verificare gli indici con `EXPLAIN QUERY PLAN` (scenario V.5 del doc di release).

**Rollback**: le modifiche al DB sono additive; il rollback del container web non richiede rollback schema. Le colonne/tabelle aggiunte sono tolerate dalle versioni precedenti del codice.

## Open Questions

- Il PDF scheda ente deve includere la mappa come immagine rasterizzata o solo il riferimento testuale alle coordinate? (Assunto: immagine statica generata via Leaflet statico o placeholder textuale nella v1.)
- La sidebar filtri mappa deve restare visibile anche su mobile o collassarsi in un drawer?
