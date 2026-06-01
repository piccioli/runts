## Context

Il sistema è una FastAPI app con SQLite come unico storage strutturato. Lo scraper usa Playwright per navigare il portale RUNTS e salvare i dati degli enti. Release 001 ha introdotto geocodifica, export CSV/Excel/PDF, mappa con clustering e resilienza scraper. Questa release aggiunge allegati (PDF ufficiali RUNTS), analisi bilanci ETS e cariche sociali, che richiedono storage aggiuntivo (filesystem per file binari, tre nuove tabelle nel DB) e due nuovi flussi di elaborazione (download + analisi offline).

## Goals / Non-Goals

**Goals:**
- Scaricare e catalogare i documenti allegati alle schede RUNTS in `attachments/<id_runts>/`
- Estrarre le 13 voci numeriche del rendiconto gestionale ETS dai bilanci scaricati
- Registrare presidente, consiglieri e altre cariche con tracciamento temporale
- Mostrare allegati, bilanci e cariche nella scheda web e nel PDF scaricabile
- Mantenere idempotenza: re-run dello scraper non riscarica file con stesso hash, non duplica cariche

**Non-Goals:**
- OCR su bilanci scansionati (rimandato; la maggioranza sono PDF testuali)
- Normalizzazione entità persone tra enti diversi (tabella `persone` cross-ente)
- Versioning degli allegati (gestione modifiche allo stesso documento nel tempo)
- Ricerca full-text nel contenuto dei PDF

## Decisions

### Storage allegati su filesystem, non DB

**Decisione**: i file binari vivono in `attachments/<id_runts>/`; il DB conserva solo metadati e path.

**Rationale**: i bilanci pesano 2–10 MB ciascuno. Con ~226 enti × ~5 file ≈ 2-3 GB. Blob SQLite a queste dimensioni rendono il DB lento da backuppare e copiare; il mount Docker di un volume è più semplice di un DB di 3 GB.

**Alternativa scartata**: BLOB in SQLite — gestione backup scomoda, query lente.

### httpx AsyncClient per download allegati

**Decisione**: `httpx.AsyncClient` con `limits=httpx.Limits(max_connections=4)` per download allegati, integrato nel loop asincrono esistente di Playwright.

**Rationale**: il download di N file per ente dentro una task `async` è naturalmente parallelo con httpx. Il limite a 4 connessioni evita di sovraccaricare il portale RUNTS.

**Alternativa scartata**: `urllib.request` — sincrono, serializza i download per ente.

### Upsert allegati su hash SHA-256

**Decisione**: la chiave di upsert per `allegati` è `(id_runts, hash_sha256)`. Un file già presente (stesso hash) aggiorna solo `downloaded_at`.

**Rationale**: lo stesso bilancio può apparire più volte nella stessa scheda RUNTS (es. tre B00 per anno 2023 su CAI Pisa). L'hash garantisce che file identici non vengano riscaricati. Il `codice_pratica` + `anno` non sono sufficientemente univoci.

**Trade-off**: se il portale aggiorna un documento mantenendo lo stesso URL ma con contenuto diverso, l'hash cambia e il file viene riscaricato correttamente.

### Analyzer come modulo separato, eseguibile indipendentemente

**Decisione**: `python -m scraper.analyzer` è un processo separato dallo scraper; processa allegati già scaricati.

**Rationale**: il parsing PDF (pdfplumber) è CPU-bound e può fallire; mantenerlo separato dallo scraper evita che un bilancio malformato blocchi l'intera sessione. L'utente può ri-eseguire l'analyzer su singoli enti con `--id-runts`.

### Tracciamento temporale cariche

**Decisione**: `(id_runts, codice_fiscale, ruolo, valid_from)` come chiave univoca; `valid_to IS NULL` = carica attiva; ogni run chiude le cariche non più presenti.

**Rationale**: le cariche cambiano nel tempo (nuove elezioni). Il tracciamento permette di rispondere a domande tipo "chi era presidente nel 2023?". Un semplice UPSERT sovrascritterebbe la storia.

**Edge case**: se `codice_fiscale` è NULL (dati RUNTS incompleti), l'upsert usa `(id_runts, nome, cognome, ruolo, valid_from)` come fallback.

### Singolo change OpenSpec

**Decisione**: un unico change `cairunts-002-allegati-persone-bilanci` invece dei 3 proposti nelle Note per OpenSpec del release doc.

**Rationale**: le tre aree (allegati, analisi, cariche) condividono lo stesso schema DB e la stessa pagina di visualizzazione; spezzarli creerebbe dipendenze incrociate difficili da gestire nei delta spec. La complessità totale (38+ task) è gestibile in un singolo apply.

### Mascheramento CF in web UI

**Decisione**: la web UI mostra CF parzialmente mascherato (`XXX•••••12345`); PDF e DB conservano il valore completo.

**Rationale**: i CF delle persone fisiche con cariche sociali sono dati pubblici sul RUNTS, ma il principio di minimizzazione GDPR suggerisce di non esporli integralmente in una UI pubblica non autenticata.

## Risks / Trade-offs

- **Struttura RUNTS "Atti e documenti" potrebbe cambiare**: il portale DNN aggiorna template periodicamente. Mitigazione: selettori scritti per attributi semantici (testo "Atti e documenti", link PDF) piuttosto che ID/classi CSS.
- **Bilanci non testuali (scansionati)**: pdfplumber restituisce stringa vuota. Mitigazione: `raw_text` vuoto → record `bilanci` con soli metadati, segnalato nel report come "parziale".
- **Volume disco allegati**: 2–3 GB a regime. Mitigazione: documentare nel deploy; `attachments/` come volume Docker bind-mount.
- **Download lento per throttling RUNTS**: max_connections=4 + retry con backoff (riusa logica release 001). Il filtro per hash evita ri-download inutili.
- **CF NULL per alcune cariche**: RUNTS può non esporre il CF del consigliere. Il vincolo UNIQUE ammette NULL ripetuti in SQLite (NULL ≠ NULL), quindi ogni carica senza CF genera sempre un nuovo record. Mitigazione: usare `(nome, cognome, ruolo, valid_from)` come fallback di identificazione nella logica `sync_cariche`.

## Migration Plan

1. `scraper/db.py` aggiunge le tre tabelle e gli indici a `_MIGRATIONS` (idempotenti — nessun dato esistente a rischio)
2. Il volume `attachments/` viene creato su host prima del run dello scraper; il bind-mount Docker viene aggiunto al `docker-compose.yml`
3. Lo scraper può essere rieseguito sugli enti già presenti: `upsert_ente` è invariato, `upsert_allegato` deduplica per hash
4. L'analyzer viene eseguito separatamente dopo il run dello scraper

Rollback: rimuovere le tre tabelle dal DB (DROP TABLE), eliminare la cartella `attachments/`. I dati preesistenti degli enti non sono toccati.

## Open Questions

- **Gestione 3 B00 stesso anno (CAI Pisa 2023)**: tre bilanci con stesso codice e anno ma hash diversi. Tutti e tre vengono scaricati; il filename viene disambiguato con suffisso progressivo (`_2`, `_3`). Da verificare in V.1.
- **Sezione organi sociali — selettori Playwright**: da rilevare durante l'implementazione; gli screenshot di riferimento non mostrano questa sezione. Potrebbe richiedere navigazione a tab separato.
