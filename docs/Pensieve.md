# Pensieve — RUNTS-CAI


## IDEAS

### Web app & UX


- `[web][ux]` **Vista statistiche** (`/stats`) con grafici aggregati: enti per regione, per sezione di registro, distribuzione temporale per data di iscrizione. Chart.js via CDN.
- `[web][ux]` **Filtri multipli**: selezione multipla di regioni/sezioni invece del singolo dropdown.
- `[web][ux]` **Ricerca full-text** con SQLite FTS5 su denominazione + comune + indirizzo, per trovare un ente anche con typo o frammenti.
- `[web][ux]` **Vista responsive ottimizzata** per consultazione da mobile, in particolare la tabella oggi è larga da scrollare orizzontalmente.

### Scraper
- `[scraper]` **Parametrizzazione della denominazione** già esiste come parametro Python ma non è esposta a CLI; aggiungere `--denominazione` per riusare lo stesso codice su altre reti (es. UISP, FederTrek, ecc.).
- `[scraper]` **Modalità incrementale**: opzione `--only-new` che salta gli `id_runts` già presenti, utile per esecuzioni veloci.
- `[scraper]` **Estrazione di campi aggiuntivi**: settori di attività completi, organi sociali, importi del 5×1000 se presenti.
- `[scraper][devx]` **Salvataggio HTML grezzo** per ogni dettaglio (cartella `cache/<id_runts>.html`) per consentire ri-parsing offline in caso di cambio di estrazione.

### Database
- `[db]` **Versionamento schema** con `PRAGMA user_version` e migrazioni numerate, invece di lista `_MIGRATIONS` con try/except. Pulisce la gestione e permette downgrade.
- `[db]` **Storia delle modifiche** — tabella `enti_history` che conserva versioni precedenti dei record, con `valid_from` / `valid_to`. Permette di rispondere a domande tipo "quando ha cambiato sede questo ente?".

### Geocoder 
- `[geo]` **Geocodifica più precisa** usando indirizzo + civico + CAP quando disponibili, con fallback a comune+regione se non si trova nulla.
- `[geo]` **Cache locale dei comuni** già geocodificati (vedi sopra) per ridurre richieste e tempo.
- `[geo]` **Provider alternativo** opzionale (es. Photon, MapTiler) come fallback quando Nominatim non trova nulla.

### Deploy & DevOps
- `[deploy]` **Healthcheck** su `/health` (DB readable + count enti > 0) per Docker `healthcheck`.
- `[deploy]` **Reverse proxy + HTTPS** con Caddy/Traefik, esempio nel `docker-compose.yml`.
- `[deploy][devx]` **GitHub Actions CI/CD**: lint, test, build immagine, push su registry.
- `[deploy]` **Backup automatico** del file `runts.db` (cron container o sidecar) con rotation settimanale.
- `[deploy]` **Schedulazione scraper** come container separato con cron (es. settimanale), che scrive sul volume condiviso.

### Dati & API
- `[data]` **Endpoint JSON** `/api/enti` per consumo programmatico (paginato, filtri identici alla web UI).
- `[data]` **Open Data export** del dataset completo come dump CSV/JSON aggiornato giornalmente, scaricabile da `/data/runts-cai-latest.csv`.
- `[data]` **Diff/notifica** quando nuovi enti compaiono o spariscono dal RUNTS rispetto all'esecuzione precedente.

### Dev experience
- `[devx]` **Test end-to-end della web app** con `httpx` async client + DB SQLite di test in memoria.
- `[devx]` **Pre-commit hooks**: `ruff`, `black`, `mypy` su scraper e web.
- `[devx]` **Type hints** completi su `scraper/` e `web/` (oggi parziali).
- `[devx]` **Dev container** (`.devcontainer/`) con tutte le deps preinstallate (Playwright + browser inclusi).

---

## TODO

- `[web][ux]` **Fissare header** Header fisso allo scroll 
- `[web][ux]` **Aggiungere footer** Aggiungere footer fisso in fondo con informazioni su Montagna Servizi SCPA
- `[web][ux]` **Menu** Aggiungere menu con le seguenti voci: Sezioni, Gruppi Regionali, Statistiche, ETS  
- `[web][ux]` **Risultati su lista a 50** nelle pagine che prevedono liste di risultati portare a 50 gli elementi visualizzati
- `[web][ux]` **Sanitiy check filter** Aggiungere un filtro in Sezioni che mostra le sezioni che hanno qualche problema sui dati 
- `[web][ux]` **Menu ETS** Mostra tutti gli elementi ETS scaricati con lo scraper, in particolare quelli che non hanno elementi associati
- `[web][ux]` **Menu Regioni** Nuovo elementi scraper da dati CAI https://www.cai.it/organizzazione/gruppi-regionali-e-provinciali/ da associare agli elementi mancanti ETS che riguardano la regione

---

## DONE

- `[scraper]` **Aggiungere lo scraping dei dati provenienti dal CAI** Partendo da https://www.cai.it/sezioni-territoriali/sezioni-e-sottosezioni/ recuperare tutte le informazioni che riguardano le Sezioni (compreso codice Sezione e informazioni che riguardano le sottosezioni)
- `[web][ux]` **Cambiare contenuto lista Sezioni** La lsita delle sezioni deve arrivare dalla tabella "sezioni CAI"
- `[web][ux]` **Cambiare contenuto lista Sezioni** Filtro Mostra solo Sezioni ETS

REV 002:
- `[scraper]` **Documenti allegati** Scaricare i documenti allegati alle pagine RUNTS asociandoli ai rispettivi enti 
- `[scraper]` **Analisi Documenti allegati** Analizzare i documenti allegati di bilancio e patrimonio per aggiungere informazioni alla scheda ente 
- `[scraper]` **Presidente** Recuperare le informazioni che riguardano il presidente dell'Ente e salvarle nel DB
- `[scraper]` **Consiglieri** Recuperare le informazioni che riguardano i consiglieri dell'Ente e salvarle nel DB
- `[scraper]` **Alter cariche** Recuperare le informazioni che riguardano le altre cariche dell'Ente e salvarle nel DB
- `[web][ux]` **Allegati RUNTS** Mopstrare nella scheda ente gli allegati scaricabili classificati per tipo
- `[web][ux]` **Allegati RUNTS** Mostrare nella scheda ente i metadati relativi agli allegati scaricati
- `[web][ux]` **Persone** Mostrare nella scheda ente i metadati relativi agli allegati scaricati
- `[web][ux]` **PDF** Aggiornare il PDF scaricabile dall'ente con info relative Allegati / Metadati allegati / Persone

REV 001:
- `[web][ux]` Mappa con **tutti gli enti del filtro corrente**, non solo quelli della pagina. Endpoint dedicato `/api/enti.geojson?<filtri>` o array JSON inline più ampio. Oggi la mappa nella lista mostra solo 20 marker per pagina ed è poco utile per la visione d'insieme.
- `[web][ux]` **Clustering dei marker** con `Leaflet.markercluster` quando ci sono molti enti vicini. Esplicitamente "out of scope" nel design originale della mappa, ma con ~226 sezioni CAI il valore si vede già.
- `[web][ux]` **Filtri laterali sulla mappa** — sidebar con elenco regioni/sezioni che agisce live sui marker via JS, mantenendo l'URL aggiornato.
- `[web][ux]` Pulsante "**Esporta CSV**" / "**Esporta Excel**" del dataset filtrato dalla lista. Utile per analisi offline da parte di ufficio o referenti CAI.
- `[web][ux]` **Scheda ente esportabile in PDF** — pulsante che genera il PDF singolo dell'ente con la carta intestata Montagna Servizi.
- `[scraper][db]` **Preservare lat/lon nell'upsert**: oggi un rerun dello scraper azzera le coordinate perché `INSERT OR REPLACE` riscrive tutte le colonne con valori nuovi (e `lat`/`lon` non sono nel dict dello scraper). Soluzione: fare un MERGE che preserva i valori non-NULL esistenti, oppure leggere lat/lon prima dell'upsert e reincludeli.
- `[scraper]` **Retry automatico** su singolo ente in caso di errore di rete o timeout (oggi viene saltato). Backoff esponenziale, max 3 tentativi.
- `[db]` **Indici** su `sede_regione` e `sezione_registro` per quando il dataset cresce (oggi i filtri fanno scan completi).
- `[db]` **Tabella `geocoding_cache`** comune → (lat, lon, ts) condivisa, per non ri-interrogare Nominatim se due enti hanno stesso comune.
