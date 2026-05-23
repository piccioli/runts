# Pensieve — RUNTS-CAI

> Brain dump del progetto. Le idee nascono qui in IDEAS, scendono in TODO quando voglio includerle in un rilascio, e finiscono in DONE dopo il rilascio.

## Workflow

1. **IDEAS** — Aggiungo qui qualsiasi spunto, anche grezzo. Linguaggio naturale, una idea per voce, con tag d'area tra parentesi quadre per filtrarle a colpo d'occhio: `[web]`, `[scraper]`, `[db]`, `[geo]`, `[deploy]`, `[ux]`, `[data]`, `[devx]`.
2. **TODO** — Quando preparo un nuovo rilascio sposto qui (manualmente) le idee che entrano nello scope. Aggiungo eventualmente note sul perché ho scelto quelle.
3. **Specifiche** — Da TODO chiedo a Claude di redigere `docs/releases/cairunts_<N>.md`. Lo modifico a mano (aggiungendo screenshot, mockup, dettagli). Quando è pronto, chiedo a Claude di generare il PDF in carta intestata in `docs/PDF/`.
4. **OpenSpec** — Il file `.md` di release è il materiale di input per il change OpenSpec che ClaudeCode userà per implementare.
5. **DONE** — Dopo il rilascio sposto qui le voci, con il numero di release e un mini-commento.

### Naming convention release

- File specifica: `docs/releases/cairunts_<release_num>.md` — es. `cairunts_001.md`, `cairunts_002.md`. Usare zero-padding a tre cifre per ordinamento naturale.
- PDF: `docs/PDF/cairunts_<release_num>_v<x.y>_<YYYY-MM-DD>.pdf` — es. `cairunts_001_v1.0_2026-05-23.pdf`.
- In testa al file `.md` un blocco di metadati: titolo, numero release, data, stato (`draft` / `proposed` / `approved`), elenco capability OpenSpec impattate.

---

## IDEAS

### Web app & UX
- `[web][ux]` Mappa con **tutti gli enti del filtro corrente**, non solo quelli della pagina. Endpoint dedicato `/api/enti.geojson?<filtri>` o array JSON inline più ampio. Oggi la mappa nella lista mostra solo 20 marker per pagina ed è poco utile per la visione d'insieme.
- `[web][ux]` **Clustering dei marker** con `Leaflet.markercluster` quando ci sono molti enti vicini. Esplicitamente "out of scope" nel design originale della mappa, ma con ~226 sezioni CAI il valore si vede già.
- `[web][ux]` **Filtri laterali sulla mappa** — sidebar con elenco regioni/sezioni che agisce live sui marker via JS, mantenendo l'URL aggiornato.
- `[web][ux]` Pulsante "**Esporta CSV**" / "**Esporta Excel**" del dataset filtrato dalla lista. Utile per analisi offline da parte di ufficio o referenti CAI.
- `[web][ux]` **Vista statistiche** (`/stats`) con grafici aggregati: enti per regione, per sezione di registro, distribuzione temporale per data di iscrizione. Chart.js via CDN.
- `[web][ux]` **Filtri multipli**: selezione multipla di regioni/sezioni invece del singolo dropdown.
- `[web][ux]` **Scheda ente esportabile in PDF** — pulsante che genera il PDF singolo dell'ente con la carta intestata Montagna Servizi.
- `[web][ux]` **Ricerca full-text** con SQLite FTS5 su denominazione + comune + indirizzo, per trovare un ente anche con typo o frammenti.
- `[web][ux]` **Vista responsive ottimizzata** per consultazione da mobile, in particolare la tabella oggi è larga da scrollare orizzontalmente.

### Scraper
- `[scraper][db]` **Preservare lat/lon nell'upsert**: oggi un rerun dello scraper azzera le coordinate perché `INSERT OR REPLACE` riscrive tutte le colonne con valori nuovi (e `lat`/`lon` non sono nel dict dello scraper). Soluzione: fare un MERGE che preserva i valori non-NULL esistenti, oppure leggere lat/lon prima dell'upsert e reincludeli.
- `[scraper]` **Retry automatico** su singolo ente in caso di errore di rete o timeout (oggi viene saltato). Backoff esponenziale, max 3 tentativi.
- `[scraper]` **Parametrizzazione della denominazione** già esiste come parametro Python ma non è esposta a CLI; aggiungere `--denominazione` per riusare lo stesso codice su altre reti (es. UISP, FederTrek, ecc.).
- `[scraper]` **Modalità incrementale**: opzione `--only-new` che salta gli `id_runts` già presenti, utile per esecuzioni veloci.
- `[scraper]` **Estrazione di campi aggiuntivi**: settori di attività completi, organi sociali, importi del 5×1000 se presenti.
- `[scraper][devx]` **Salvataggio HTML grezzo** per ogni dettaglio (cartella `cache/<id_runts>.html`) per consentire ri-parsing offline in caso di cambio di estrazione.

### Database
- `[db]` **Versionamento schema** con `PRAGMA user_version` e migrazioni numerate, invece di lista `_MIGRATIONS` con try/except. Pulisce la gestione e permette downgrade.
- `[db]` **Indici** su `sede_regione` e `sezione_registro` per quando il dataset cresce (oggi i filtri fanno scan completi).
- `[db]` **Storia delle modifiche** — tabella `enti_history` che conserva versioni precedenti dei record, con `valid_from` / `valid_to`. Permette di rispondere a domande tipo "quando ha cambiato sede questo ente?".
- `[db]` **Tabella `geocoding_cache`** comune → (lat, lon, ts) condivisa, per non ri-interrogare Nominatim se due enti hanno stesso comune.

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

_(vuoto — sposterò qui le idee selezionate per il prossimo rilascio)_

---

## DONE

_(vuoto — qui finiranno le idee dopo l'effettivo rilascio, con riferimento alla release e mini-retrospettiva)_
