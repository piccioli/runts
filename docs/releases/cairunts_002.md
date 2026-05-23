# CAI-RUNTS — Release 002

**Numero release**: 002
**Versione**: v1.2
**Data**: 23 maggio 2026
**Stato**: draft
**Capability OpenSpec impattate** (proposte):
- modificate: `runts-detail`, `ente-detail`, `database-storage`, `enti-export`
- nuove: `allegati-ingest`, `allegati-analisi`, `cariche-sociali`

---

## Sommario

Questa release porta il sistema oltre l'anagrafica di base degli enti. Si occupa di **acquisire e mostrare i documenti allegati** alle schede RUNTS (statuti, bilanci, ecc.), di **estrarre informazioni strutturate dai bilanci** (totali patrimoniali e di esercizio), di **registrare le persone fisiche con cariche sociali** (presidente, consiglio direttivo, altre cariche) e di **arricchire la scheda PDF** dell'ente con tutti questi nuovi dati.

L'obiettivo è trasformare la pagina di dettaglio da semplice riepilogo anagrafico a vera scheda informativa dell'ente.

## Motivazione (Why)

- Le schede RUNTS contengono **PDF allegati ufficiali** (atto costitutivo, statuto, bilanci annuali, ecc.) che oggi il nostro sistema ignora completamente: l'operatore deve sempre tornare al portale del Ministero per consultarli.
- I **bilanci** sono la fonte primaria per valutare la sostenibilità economica di una sezione CAI: estrarne automaticamente i totali (attivo, passivo, ricavi, costi, 5×1000) permette analisi aggregate utili a Montagna Servizi e ai referenti regionali.
- Le **cariche sociali** (presidente in particolare) sono l'informazione più richiesta da Montagna Servizi quando deve contattare una sezione. Oggi recuperiamo solo il "rappresentante legale" via regex; serve un modello strutturato con ruolo e contatti.
- Estendere il **PDF della scheda ente** con allegati e persone chiude il loop: l'output stampabile diventa la sintesi completa di un ente, anche offline.

## Cosa cambia (What)

### Utente finale (web app)
- Nella **scheda ente** compare una nuova sezione **"Atti e documenti"** con l'elenco dei documenti scaricabili, classificati per codice pratica RUNTS (Bilancio d'esercizio, Statuto, Atto costitutivo, ecc.). Ogni voce mostra: tipo documento, codice pratica, anno (se applicabile), dimensione del file, e link al download.
- Nella scheda ente compare la sezione **"Indicatori di bilancio"** (se almeno un bilancio è stato analizzato) con i principali totali estratti: attivo/passivo, ricavi, costi, contributi del 5×1000, anno di riferimento.
- Nella scheda ente compare la sezione **"Persone e cariche"** con presidente, consiglieri e altre cariche: nome, cognome, ruolo, eventuale periodo di carica.
- Il pulsante **"Scarica scheda PDF"** (introdotto in release 001) produce ora un PDF aggiornato che include anche atti e documenti, indicatori di bilancio e persone.

### Scraper
- Lo scraper, **per ogni ente**, naviga alla sezione **"Atti e documenti"** della scheda di dettaglio, raccoglie l'elenco dei file disponibili (4 colonne sul portale: Documento, Codice pratica, Data, Allegato), scarica i PDF e li salva nel filesystem in `attachments/<id_runts>/<filename>`.
- Lo scraper estrae **presidente, consiglieri e altre cariche** dalla pagina di dettaglio RUNTS (sezione "Organi sociali") e li salva nel DB come record strutturati.
- Un nuovo modulo `scraper/analyzer.py` (eseguibile come `python -m scraper.analyzer`) **analizza i PDF di bilancio** già scaricati ed estrae i principali totali, popolando una nuova tabella `bilanci`.

### Database
- Nuova tabella `allegati(id, id_runts, documento, codice_pratica, tipo, anno, filename, path, mime, size, hash_sha256, url_originale, downloaded_at)`.
- Nuova tabella `bilanci` modellata sul **rendiconto gestionale ETS** (DM 39/2020): per ciascun anno, costi e ricavi suddivisi nelle 5 categorie A-E previste dal Ministero, totali, e risultato d'esercizio. Schema completo nelle note di design.
- Nuova tabella `cariche_sociali(id, id_runts, ruolo, nome, cognome, codice_fiscale, valid_from, valid_to)`.
- Tutte le nuove tabelle sono additive e idempotenti via `_MIGRATIONS`.

## Requisiti funzionali

### A. Ingestion atti e documenti (scraper)

**A1.** Lo scraper SHALL, durante l'estrazione del dettaglio di un ente, individuare nella pagina RUNTS la sezione **"Atti e documenti"** e leggerne la tabella le cui colonne sono: **Documento**, **Codice pratica**, **Data**, **Allegato** (icona PDF cliccabile).

**A2.** Per ogni riga della tabella "Atti e documenti", il sistema SHALL raccogliere i seguenti metadati: nome del documento (es. "BILANCIO D'ESERCIZIO"), **codice pratica** (es. `B00`, `B08`, `C02`), anno di riferimento se presente nella colonna Data, URL di download dell'allegato. Il "tipo" canonico SHALL essere derivato dal codice pratica secondo la tassonomia ufficiale (vedi nota di design).

**A3.** Lo scraper SHALL scaricare il file allegato, calcolare il suo hash SHA-256, e salvarlo in `attachments/<id_runts>/<filename_normalizzato>`. Il filename normalizzato segue la convenzione `<codice_pratica>_<anno?>_<slug-documento>.pdf` (es. `B00_2024_bilancio_desercizio.pdf`).

**A4.** Il sistema SHALL persistere ogni documento nella tabella `allegati` con upsert sulla combinazione `(id_runts, hash_sha256)`: se un documento con stesso hash è già presente per lo stesso ente, non viene riscaricato e la riga viene solo aggiornata nel campo `downloaded_at`.

**A5.** Il sistema SHALL gestire allegati di dimensione massima configurabile (default 50 MB); allegati più grandi sono saltati con log WARNING e contabilizzati nel report finale.

**A6.** Il report finale dello scraper SHALL includere il conteggio degli allegati scoperti, scaricati, già presenti (cache hit), saltati per dimensione, falliti — con breakdown per codice pratica.

**A7.** Il sistema SHALL conservare nel campo `codice_pratica` della tabella `allegati` il valore originale letto dal portale RUNTS, anche se il codice non è presente nella tassonomia canonica. In quel caso il campo `tipo` ricade su `altro`. Questo garantisce robustezza a nuovi codici pratica introdotti dal Ministero senza richiedere modifiche di schema.

### B. Analisi dei bilanci (analyzer)

**B1.** Il sistema SHALL fornire un nuovo modulo eseguibile `python -m scraper.analyzer --db runts.db [--id-runts <id>] [--force]` che processa tutti gli allegati di tipo `bilancio_esercizio` non ancora analizzati (o solo quelli di un singolo ente se specificato).

**B2.** Per ogni allegato di tipo `bilancio_esercizio`, l'analyzer SHALL estrarne il testo tramite `pdfplumber` e tentare di identificare le seguenti **13 voci numeriche** del rendiconto gestionale ETS (DM 39/2020):

*Oneri / Costi*
- A) Costi e oneri da attività di interesse generale → `oneri_a_interesse_generale`
- B) Costi e oneri da attività diverse → `oneri_b_attivita_diverse`
- C) Costi e oneri da attività di raccolta fondi → `oneri_c_raccolta_fondi`
- D) Costi e oneri da attività finanziarie e patrimoniali → `oneri_d_finanziarie_patrimoniali`
- E) Costi e oneri di supporto generale → `oneri_e_supporto_generale`
- Totale oneri e costi → `totale_oneri`

*Proventi / Ricavi*
- A) Ricavi, rendite e proventi da attività di interesse generale → `proventi_a_interesse_generale`
- B) Ricavi, rendite e proventi da attività diverse → `proventi_b_attivita_diverse`
- C) Ricavi e proventi da attività di raccolta fondi → `proventi_c_raccolta_fondi`
- D) Ricavi e proventi da attività finanziarie e patrimoniali → `proventi_d_finanziarie_patrimoniali`
- E) Proventi di supporto generale → `proventi_e_supporto_generale`
- Totale proventi e ricavi → `totale_proventi`

*Risultato*
- Disavanzo/avanzo prima delle imposte → `risultato_ante_imposte`
- Imposte → `imposte`
- Disavanzo/avanzo dopo le imposte (risultato d'esercizio) → `risultato_esercizio`

**B3.** Il sistema SHALL persistere il risultato dell'estrazione nella tabella `bilanci` con un'unica riga per `(id_runts, anno)`. Il testo grezzo del PDF SHALL essere salvato nel campo `raw_text` (troncato a 50000 caratteri) per audit.

**B4.** Se uno dei valori non è estraibile, il campo corrispondente SHALL restare NULL; il record viene comunque creato con i campi disponibili. Tutti gli importi monetari SHALL essere salvati come `REAL` in euro (es. `502912.98`).

**B5.** Il report finale dell'analyzer SHALL stampare il conteggio dei bilanci analizzati con successo (almeno un campo valorizzato), parzialmente analizzati (raw_text salvato ma nessun totale estratto) e falliti.

**B6.** Il sistema SHALL eseguire un **controllo di coerenza** dopo l'estrazione: se sia `totale_oneri` sia tutte le voci A-E degli oneri sono valorizzate, allora la somma A+B+C+D+E DEVE coincidere con `totale_oneri` (tolleranza ±0,01 €); analogamente per i proventi. In caso di scostamento, l'analyzer logga WARNING ma persiste comunque i dati.

**B7.** L'analyzer SHALL essere testabile **offline**: il modulo include una suite di test unitari che usa come fixture i due PDF di riferimento in `scraper/test_data/bilanci/` e verifica i valori attesi (vedi sezione "Casi di test").

### C. Cariche sociali (scraper)

**C1.** Lo scraper SHALL estrarre dalla sezione "Organi sociali" della pagina RUNTS le seguenti informazioni per ciascuna persona: nome, cognome, codice fiscale, ruolo (presidente, vicepresidente, consigliere, segretario, tesoriere, revisore, altro), data di inizio carica (`valid_from`), data di fine carica (`valid_to`, se presente).

**C2.** Il sistema SHALL persistere ogni carica nella tabella `cariche_sociali` con upsert sulla combinazione `(id_runts, codice_fiscale, ruolo, valid_from)` per gestire correttamente i cambi di ruolo nel tempo.

**C3.** Quando un nuovo run dello scraper trova una carica che non è più presente sul portale ma esisteva nel DB con `valid_to IS NULL`, il sistema SHALL aggiornare `valid_to` alla data corrente per tracciare la cessazione (logica di chiusura della carica).

**C4.** Il campo `rappresentante_legale` di `enti` continua a essere popolato come oggi (`"Cognome Nome"` del presidente al momento dell'estrazione), per retrocompatibilità con la lista enti.

### D. Web app — visualizzazione

**D1.** La route `GET /ente/{id_runts}` SHALL caricare anche gli allegati, i bilanci analizzati e le cariche sociali dell'ente, passandoli al template.

**D2.** Il template `detail.html` SHALL mostrare tre nuove sezioni: **Atti e documenti**, **Indicatori di bilancio** e **Persone e cariche**. Ogni sezione è renderizzata solo se contiene almeno una riga.

**D3.** La sezione "Atti e documenti" SHALL elencare i documenti raggruppati per codice pratica, con: nome documento, codice pratica, anno (se applicabile), dimensione human-readable, link di download diretto al file locale (`/attachments/<id_runts>/<filename>`), link al RUNTS originale (icona "↗").

**D4.** La sezione Indicatori di bilancio SHALL mostrare una tabella con anno, attivo, passivo, ricavi, costi, 5×1000; valori NULL renderizzati come "—". Se sono presenti più anni, ordinati per anno decrescente.

**D5.** La sezione Persone e cariche SHALL elencare le persone con `valid_to IS NULL` (cariche attive) in cima e quelle storiche in coda, ognuna con: ruolo, nome, cognome, periodo di carica.

**D6.** La web app SHALL servire i file da `attachments/<id_runts>/...` come static files in sola lettura tramite mount FastAPI dedicato (`/attachments`).

### E. PDF scheda ente esteso

**E1.** L'endpoint `GET /ente/{id_runts}/pdf` (introdotto in release 001) SHALL includere, oltre alle informazioni anagrafiche già presenti, anche: sezione Allegati (elenco con tipo, anno, dimensione, link al file su RUNTS), sezione Indicatori di bilancio (tabella anni), sezione Persone e cariche (lista attive + storiche).

**E2.** Il PDF SHALL mantenere la carta intestata Montagna Servizi su tutte le pagine, anche quando si estende su più pagine.

**E3.** Se l'ente non ha allegati, bilanci o persone, le sezioni corrispondenti SHALL essere omesse (non mostrare "—" su intere sezioni vuote).

## Requisiti non funzionali

- **Storage allegati**: i file PDF vivono su filesystem in `attachments/<id_runts>/`, **non** nel DB SQLite. Il DB conserva solo il path e i metadati. Il volume deve essere bind-mountato anche in Docker (sola lettura lato web, scrittura solo dal lato scraper/host).
- **Performance ingestion**: lo scaricamento di N allegati per ente non SHALL aumentare il tempo totale dello scraper di più del 50% rispetto al run precedente, grazie al filtro per `hash_sha256` che evita download ripetuti.
- **Dipendenze nuove**: `httpx` o `aiohttp` per il download asincrono degli allegati (`urllib` resta ok ma serializza). `pdfplumber` per l'analyzer (già usato nello skill PDF).
- **Compatibilità DB**: `_MIGRATIONS` aggiunge le nuove tabelle con `CREATE TABLE IF NOT EXISTS`; nessun cambio distruttivo allo schema esistente.
- **Privacy / GDPR**: le persone fisiche con cariche sociali sono dati pubblici esposti dal RUNTS, quindi pubblicabili. Il codice fiscale è dato pubblico per i rappresentanti di persone giuridiche, ma per scrupolo lo si mostra **mascherato** nella web UI pubblica (`XXX...XXX12345`) e completo solo nel PDF e nel DB.

## Scenari (WHEN / THEN)

### A. Allegati

**Scenario A.1 — Primo download di allegati**
- WHEN lo scraper processa un ente la cui scheda RUNTS espone 3 PDF (statuto, bilancio 2024, bilancio 2023)
- THEN i 3 file vengono scaricati in `attachments/<id_runts>/`, i record vengono inseriti in `allegati`, e il report finale incrementa "scaricati: 3"

**Scenario A.2 — Allegato già presente (cache)**
- WHEN lo scraper rilancia sullo stesso ente e un allegato ha lo stesso `hash_sha256` di una riga già nel DB
- THEN il file non viene riscaricato, la riga di `allegati` viene aggiornata solo per `downloaded_at`, e il report incrementa "già presenti"

**Scenario A.3 — Allegato troppo grande**
- WHEN un allegato supera il limite configurato (default 50 MB)
- THEN lo scraper logga WARNING, non scarica il file, ma inserisce comunque la riga in `allegati` con `path` NULL e una nota in un campo `skip_reason`; il report incrementa "saltati per dimensione"

### B. Bilanci

**Scenario B.1 — Analisi bilancio con tutti i campi**
- WHEN l'analyzer processa un bilancio PDF leggibile contenente la sezione "Stato patrimoniale" e "Conto economico"
- THEN viene inserita una riga in `bilanci` con `totale_attivo`, `totale_passivo`, `ricavi`, `costi` valorizzati

**Scenario B.2 — Bilancio parzialmente analizzato**
- WHEN il PDF non rispetta lo schema atteso e nessun totale viene estratto
- THEN viene comunque inserita una riga in `bilanci` con `raw_text` valorizzato e tutti i campi numerici a NULL; il record può essere rivisto manualmente

**Scenario B.3 — Bilancio già analizzato**
- WHEN l'analyzer trova un record `bilanci` con stesso `(id_runts, anno)` e `analyzed_at` recente
- THEN lo salta senza re-analizzarlo; l'utente può forzare con `--force`

### C. Cariche sociali

**Scenario C.1 — Nuovo presidente eletto**
- WHEN lo scraper trova un presidente con codice fiscale diverso da quello attualmente in carica nel DB (`valid_to IS NULL`)
- THEN il record precedente viene chiuso (`valid_to` = data corrente) e viene inserito un nuovo record per il nuovo presidente

**Scenario C.2 — Carica invariata**
- WHEN lo scraper trova esattamente le stesse persone già in `cariche_sociali` con `valid_to IS NULL`
- THEN nessun record viene modificato

**Scenario C.3 — Cessazione di un consigliere**
- WHEN una persona presente nel DB con `valid_to IS NULL` non è più nell'elenco RUNTS al run corrente
- THEN il suo `valid_to` viene impostato alla data del run

### D. Web app

**Scenario D.1 — Scheda completa (CAI Parma)**
- WHEN l'utente apre la scheda di CAI Parma, che sul portale RUNTS ha ~22 documenti (bilanci d'esercizio, bilanci sociali, situazione patrimoniale, relazione organo di controllo, statuto, atto costitutivo, dichiarazioni, ecc., vedi screenshot in `002_docs/`)
- THEN la pagina mostra le tre nuove sezioni con tutti i documenti scaricati, gli indicatori di bilancio degli anni 2021-2024 e l'elenco di presidente + consiglieri + altre cariche

**Scenario D.2 — Scheda minimale (CAI Pisa)**
- WHEN l'utente apre la scheda di CAI Pisa (`id_runts=83894`, vedi screenshot in `002_docs/`), che sul portale RUNTS ha 8 documenti (6 bilanci d'esercizio 2021-2024, atto costitutivo, statuto) e meno cariche
- THEN la pagina mostra la sezione "Atti e documenti" con gli 8 documenti, la sezione "Indicatori di bilancio" con gli anni analizzati e la sezione "Persone e cariche" coerentemente

**Scenario D.3 — Ente senza documenti**
- WHEN l'utente apre la scheda di un ente che non ha documenti pubblicati
- THEN la sezione "Atti e documenti" non viene renderizzata (no titolo orfano)

**Scenario D.4 — Download diretto**
- WHEN l'utente clicca su un link di un documento
- THEN il browser scarica il file `attachments/<id_runts>/<filename>` servito da FastAPI

### E. PDF esteso

**Scenario E.1 — PDF con tutte le sezioni**
- WHEN l'utente scarica il PDF di CAI Pisa
- THEN il PDF contiene la scheda anagrafica, gli allegati, gli indicatori di bilancio, le persone, con carta intestata MS e numerazione pagine

**Scenario E.2 — PDF minimale**
- WHEN l'utente scarica il PDF di un ente senza allegati, bilanci o persone
- THEN il PDF contiene solo la scheda anagrafica come nella release 001, nessuna sezione vuota aggiuntiva

## Note di design

### Tassonomia degli atti e documenti — codici pratica RUNTS
Il portale RUNTS fornisce per ogni documento un **codice pratica** ufficiale che è la chiave più affidabile per la classificazione. La mappa di derivazione `codice_pratica → tipo` canonico è la seguente (osservata sugli enti di test Pisa e Parma, screenshot in `002_docs/`):

| Codice pratica | Documento RUNTS | `tipo` canonico nel DB |
|---|---|---|
| `B00` | BILANCIO D'ESERCIZIO | `bilancio_esercizio` |
| `B03` | SITUAZIONE PATRIMONIALE | `situazione_patrimoniale` |
| `B08` | BILANCIO SOCIALE | `bilancio_sociale` |
| `C01` | ATTO COSTITUTIVO | `atto_costitutivo` |
| `C02` | STATUTO | `statuto` |
| `D00` | DICHIARAZIONE | `dichiarazione` |
| `E32` | PROVVEDIMENTO AUTORITA' GOVERNATIVA | `provvedimento_autorita` |
| `R06` | RELAZIONE ORGANO DI CONTROLLO | `relazione_controllo` |
| `PROVISC` | PROVVEDIMENTO DI ISCRIZIONE | `provvedimento_iscrizione` |
| `99` | ALTRO DOCUMENTO | `altro` |

Codici pratica non presenti in questa tabella vengono salvati nel DB con `tipo = "altro"` e il `codice_pratica` originale conservato per analisi successive. Il campo `codice_pratica` resta sempre il valore originale dal portale.

Per quanto riguarda l'analyzer dei bilanci (sezione B), si processano i documenti con `tipo IN ('bilancio_esercizio', 'situazione_patrimoniale')`. La colonna **Data** del portale RUNTS contiene direttamente l'anno (es. `2024`, `2023`); per i documenti senza data (es. Statuto, Atto costitutivo) il campo `anno` resta NULL.

### Estrazione bilanci: strategia
I bilanci RUNTS sono pubblicati nel modello "**Rendiconto Gestionale**" previsto dal DM 39/2020 per gli ETS. La struttura ha due colonne (Oneri/Proventi) suddivise in cinque blocchi A-E e termina con il risultato d'esercizio. Strategia di parsing:

1. Estrarre testo con `pdfplumber.extract_text(layout=True)` per preservare colonne; eventualmente leggere anche le tabelle con `page.extract_tables()` per i layout più tabellari.
2. Identificare le sezioni **"ONERI E COSTI"** e **"PROVENTI E RICAVI"** (case insensitive). Il modello ufficiale usa una struttura ricorrente "A) ... B) ... C) ... D) ... E) ..." con punto e parentesi.
3. Per ogni voce A-E usare ancoraggi testuali stabili. Esempi di pattern (case insensitive, multiline):
   - `r"A\)\s*Costi e oneri da attivit[àa] di interesse generale[\s\S]{0,400}?([\d\.\s]+,\d{2})"`
   - `r"B\)\s*Costi e oneri da attivit[àa] diverse[\s\S]{0,400}?([\d\.\s]+,\d{2})"`
   - `r"Totale oneri e costi[\s\S]{0,200}?([\d\.\s]+,\d{2})"`
   - `r"Totale proventi e ricavi[\s\S]{0,200}?([\d\.\s]+,\d{2})"`
   - `r"(?:Disavanzo|Avanzo)\s+(?:prima|ante)\s+(?:delle\s+)?imposte[\s\S]{0,200}?([\d\.\s]+,\d{2})"`
   - `r"Imposte[\s\S]{0,200}?([\d\.\s]+,\d{2})"`
4. Normalizzare i numeri italiani: `1.234,56` → `1234.56`; gestire anche varianti con spazi (`1 234,56`) e con apostrofo (`1'234,56`).
5. I bilanci spesso espongono **anno corrente vs. anno precedente** in colonne affiancate: il regex deve catturare il **primo** valore numerico dopo l'ancora di riga, perché è quello dell'anno di esercizio.
6. Per i bilanci che usano arrotondamento all'euro (caso Pisa, vedi screenshot in `002_docs/`), accettare anche numeri senza decimali: `r"([\d\.\s]+(?:,\d{2})?)"`.

### Numero dell'anno di esercizio
L'anno del bilancio viene già letto dalla colonna "Data" della tabella "Atti e documenti" del portale e salvato nel campo `allegati.anno`. L'analyzer eredita questo valore senza dover ri-estrarre l'anno dal contenuto del PDF.

### Test offline e fixture
I due bilanci di riferimento sono salvati come fixture in `scraper/test_data/bilanci/`:

- `Bilancio_Pisa_2024.pdf` — formato sintetico (importi arrotondati all'euro).
- `Bilancio_Parma_2025.pdf` — formato esteso (importi con 2 decimali, voci più articolate).

I valori attesi sono definiti nella sezione "Casi di test" e usati come oracoli nei test unitari `scraper/test_analyzer.py`.

### Storage e percorsi attachments
La cartella `attachments/` vive **alla radice del progetto**, allo stesso livello di `runts.db`. Sarà bind-mountata in Docker:

```yaml
volumes:
  - ./runts.db:/app/runts.db:ro
  - ./attachments:/app/attachments:ro
```

Il scraper scrive da host; il container web monta in sola lettura.

### Schema delle nuove tabelle

```sql
CREATE TABLE IF NOT EXISTS allegati (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    id_runts        TEXT NOT NULL REFERENCES enti(id_runts),
    documento       TEXT NOT NULL,            -- es. "BILANCIO D'ESERCIZIO" (originale RUNTS)
    codice_pratica  TEXT NOT NULL,            -- es. B00, B08, C02, PROVISC, 99
    tipo            TEXT NOT NULL,            -- canonico: bilancio_esercizio, statuto, ...
    anno            INTEGER,                  -- dalla colonna "Data" del portale, se presente
    filename        TEXT,                     -- nome file salvato (NULL se skipped)
    path            TEXT,                     -- path relativo (NULL se skipped)
    mime            TEXT,
    size            INTEGER,
    hash_sha256     TEXT,
    url_originale   TEXT,
    skip_reason     TEXT,                     -- es. "size_exceeded"
    downloaded_at   TEXT NOT NULL,
    UNIQUE (id_runts, hash_sha256)
);

CREATE TABLE IF NOT EXISTS bilanci (
    id                                INTEGER PRIMARY KEY AUTOINCREMENT,
    id_runts                          TEXT NOT NULL REFERENCES enti(id_runts),
    anno                              INTEGER NOT NULL,

    -- ONERI E COSTI (5 categorie + totale)
    oneri_a_interesse_generale        REAL,
    oneri_b_attivita_diverse          REAL,
    oneri_c_raccolta_fondi            REAL,
    oneri_d_finanziarie_patrimoniali  REAL,
    oneri_e_supporto_generale         REAL,
    totale_oneri                      REAL,

    -- PROVENTI E RICAVI (5 categorie + totale)
    proventi_a_interesse_generale     REAL,
    proventi_b_attivita_diverse       REAL,
    proventi_c_raccolta_fondi         REAL,
    proventi_d_finanziarie_patrimoniali REAL,
    proventi_e_supporto_generale      REAL,
    totale_proventi                   REAL,

    -- RISULTATO
    risultato_ante_imposte            REAL,
    imposte                           REAL,
    risultato_esercizio               REAL,

    -- audit / lineage
    raw_text                          TEXT,
    allegato_id                       INTEGER REFERENCES allegati(id),
    analyzed_at                       TEXT NOT NULL,

    UNIQUE (id_runts, anno)
);

CREATE TABLE IF NOT EXISTS cariche_sociali (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    id_runts        TEXT NOT NULL REFERENCES enti(id_runts),
    ruolo           TEXT NOT NULL,            -- presidente, vicepresidente, consigliere, ...
    nome            TEXT,
    cognome         TEXT,
    codice_fiscale  TEXT,
    valid_from      TEXT,
    valid_to        TEXT,                     -- NULL = carica attiva
    updated_at      TEXT NOT NULL,
    UNIQUE (id_runts, codice_fiscale, ruolo, valid_from)
);

CREATE INDEX IF NOT EXISTS idx_allegati_id_runts ON allegati(id_runts);
CREATE INDEX IF NOT EXISTS idx_allegati_tipo ON allegati(tipo);
CREATE INDEX IF NOT EXISTS idx_allegati_codice_pratica ON allegati(codice_pratica);
CREATE INDEX IF NOT EXISTS idx_bilanci_id_runts ON bilanci(id_runts);
CREATE INDEX IF NOT EXISTS idx_cariche_id_runts ON cariche_sociali(id_runts);
CREATE INDEX IF NOT EXISTS idx_cariche_attive ON cariche_sociali(id_runts, valid_to);
```

### Mascheramento del codice fiscale in web UI

```python
def mask_cf(cf: str) -> str:
    if not cf or len(cf) < 6:
        return "—"
    return f"{cf[:3]}{'•' * (len(cf) - 8)}{cf[-5:]}"
```

Il CF completo resta nel DB e nel PDF (output controllato), ma la web UI mostra la versione mascherata.

### Selezione del download client
- `urllib.request` (già usato nel geocoder): sincrono, ok per pochi allegati per ente.
- `httpx.AsyncClient`: meglio per scaricare in parallelo dentro la stessa task `async`.

**Scelta raccomandata**: `httpx.AsyncClient` con `limits=httpx.Limits(max_connections=4)` per non saturare il portale RUNTS.

### Alternative considerate

- **Salvare gli allegati come BLOB nel DB SQLite**: bocciato — i bilanci possono pesare 5-10 MB ciascuno e il DB diventerebbe ingombrante e lento da backuppare.
- **OCR sui bilanci scansionati**: rimandato — la grandissima maggioranza dei bilanci RUNTS è PDF testuale. Se in futuro troviamo molti scansionati, valutare `pytesseract` + `pdf2image`.
- **Tabella unica `persone` indipendente da `cariche_sociali`**: bocciato per ora — una persona può avere più cariche in più enti, ma per il volume attuale (~226 enti × ~7 cariche) la duplicazione è accettabile. In una release futura si potrà normalizzare.

## Rischi e mitigazioni

- **Cambio struttura RUNTS sulla sezione allegati**: rischio realistico (DNN aggiorna i template). Mitigazione: estrazione resiliente che cerca link a PDF tramite pattern URL noti, non solo selettori ID. Aggiungere test di estrazione con HTML registrato.
- **Volume disco crescente**: a regime, ~226 enti × ~5 allegati × ~2 MB ≈ 2-3 GB. Documentare in deploy e prevedere `attachments/` come volume montato.
- **Parsing bilancio fallisce silenziosamente** (raw_text salvato ma nessun campo estratto): mitigazione esplicita con report parziale; sarà evidente nei report e nei dashboard.
- **GDPR / esposizione dati personali**: i dati sono già pubblici sul RUNTS, ma il principio di minimizzazione suggerisce di mascherare il CF in UI come da decisione di design.
- **Download lento se RUNTS limita le connessioni**: limitare il parallelismo a 4 connessioni; aggiungere retry con backoff anche per i download (riusa la stessa logica del retry estrazione di release 001).

## Casi di test

I due enti di riferimento per il QA di questa release sono **CAI Pisa** e **CAI Parma**. Coprono due profili realistici molto diversi: una sezione con il set minimo di documenti (Pisa) e una sezione "storica" con documentazione abbondante (Parma). Gli screenshot reali della sezione "Atti e documenti" di entrambi sono disponibili in `docs/releases/002_docs/`.

### CAI Pisa — caso essenziale

`id_runts = 83894`. Set di documenti osservato sul portale (screenshot in `002_docs/Screenshot documenti pisa.png`):

| # | Documento | Codice pratica | Anno |
|---|---|---|---|
| 1 | BILANCIO D'ESERCIZIO | B00 | 2024 |
| 2 | BILANCIO D'ESERCIZIO | B00 | 2023 |
| 3 | BILANCIO D'ESERCIZIO | B00 | 2023 |
| 4 | BILANCIO D'ESERCIZIO | B00 | 2023 |
| 5 | BILANCIO D'ESERCIZIO | B00 | 2022 |
| 6 | BILANCIO D'ESERCIZIO | B00 | 2021 |
| 7 | ATTO COSTITUTIVO | C01 | — |
| 8 | STATUTO | C02 | — |

Totale: 8 documenti, tutti bilanci d'esercizio + statuto + atto costitutivo. Uso suggerito: test del caso **minimal viable** in cui non sono presenti bilanci sociali, relazioni di controllo o provvedimenti, e copertura del **caso con più allegati per stesso anno** (tre B00 del 2023, da deduplicare per hash o conservare con suffissi `_1`, `_2`, `_3` nel filename).

### CAI Parma — caso ricco

Set di documenti osservato sul portale (screenshot in `002_docs/Screenshot documenti parma.png`):

| # | Documento | Codice pratica | Anno |
|---|---|---|---|
| 1 | BILANCIO SOCIALE | B08 | 2024 |
| 2 | BILANCIO D'ESERCIZIO | B00 | 2024 |
| 3 | RELAZIONE ORGANO DI CONTROLLO | R06 | 2023 |
| 4 | BILANCIO D'ESERCIZIO | B00 | 2023 |
| 5 | BILANCIO SOCIALE | B08 | 2023 |
| 6 | BILANCIO SOCIALE | B08 | 2022 |
| 7 | BILANCIO D'ESERCIZIO | B00 | 2022 |
| 8 | PROVVEDIMENTO AUTORITA' GOVERNATIVA | E32 | 2021 |
| 9 | BILANCIO SOCIALE | B08 | 2021 |
| 10 | BILANCIO D'ESERCIZIO | B00 | 2021 |
| 11-13 | DICHIARAZIONE | D00 | 2021 |
| 14 | BILANCIO SOCIALE | B08 | 2021 |
| 15 | BILANCIO D'ESERCIZIO | B00 | 2021 |
| 16 | ALTRO DOCUMENTO | 99 | — |
| 17 | DICHIARAZIONE | D00 | — |
| 18 | ALTRO DOCUMENTO | 99 | — |
| 19 | PROVVEDIMENTO DI ISCRIZIONE | PROVISC | — |
| 20 | STATUTO | C02 | — |
| 21 | SITUAZIONE PATRIMONIALE | B03 | — |
| 22 | ATTO COSTITUTIVO | C01 | — |

Totale: ~22 documenti. Uso suggerito: test della **classificazione completa** (10 codici pratica diversi), del **rilevamento anno** sia con sia senza valore, della **deduplica per hash** quando esistono più documenti dello stesso tipo per più anni.

### Bilanci di test — valori attesi (oracoli per `scraper/test_analyzer.py`)

I due PDF di bilancio sono disponibili sia in `docs/releases/002_docs/` come riferimento documentale, sia in `scraper/test_data/bilanci/` come **fixture per i test unitari** dell'analyzer.

#### CAI Pisa — Bilancio d'esercizio 2024

Fixture: `scraper/test_data/bilanci/Bilancio_Pisa_2024.pdf` (formato sintetico, importi arrotondati all'euro).

| Campo nel DB | Valore atteso (€) |
|---|---:|
| `oneri_a_interesse_generale` | 122 929,00 |
| `oneri_b_attivita_diverse` | 3 762,00 |
| `oneri_c_raccolta_fondi` | 0,00 |
| `oneri_d_finanziarie_patrimoniali` | 0,00 |
| `oneri_e_supporto_generale` | 0,00 |
| `totale_oneri` | 126 691,00 |
| `proventi_a_interesse_generale` | 166 860,00 |
| `proventi_b_attivita_diverse` | 4 368,00 |
| `proventi_c_raccolta_fondi` | 0,00 |
| `proventi_d_finanziarie_patrimoniali` | 0,00 |
| `proventi_e_supporto_generale` | 0,00 |
| `totale_proventi` | 171 228,00 |
| `risultato_ante_imposte` | 44 537,00 |
| `imposte` | 0,00 |
| `risultato_esercizio` | 44 537,00 |

#### CAI Parma — Bilancio d'esercizio 2025

Fixture: `scraper/test_data/bilanci/Bilancio_Parma_2025.pdf` (formato esteso, importi con 2 decimali).

| Campo nel DB | Valore atteso (€) |
|---|---:|
| `oneri_a_interesse_generale` | 502 912,98 |
| `oneri_b_attivita_diverse` | 24 238,92 |
| `oneri_c_raccolta_fondi` | 0,00 |
| `oneri_d_finanziarie_patrimoniali` | 3 826,97 |
| `oneri_e_supporto_generale` | 0,00 |
| `totale_oneri` | 530 978,87 |
| `proventi_a_interesse_generale` | 467 553,84 |
| `proventi_b_attivita_diverse` | 80 150,77 |
| `proventi_c_raccolta_fondi` | 2 804,10 |
| `proventi_d_finanziarie_patrimoniali` | 0,00 |
| `proventi_e_supporto_generale` | 0,00 |
| `totale_proventi` | 550 508,71 |
| `risultato_ante_imposte` | 19 529,84 |
| `imposte` | 784,00 |
| `risultato_esercizio` | 18 745,84 |

#### Suggerimento per i test

```python
# scraper/test_analyzer.py (estratto)
PISA_2024_EXPECTED = {
    "oneri_a_interesse_generale": 122929.00,
    "oneri_b_attivita_diverse": 3762.00,
    # ...
    "totale_proventi": 171228.00,
    "risultato_esercizio": 44537.00,
}

PARMA_2025_EXPECTED = {
    "oneri_a_interesse_generale": 502912.98,
    "oneri_b_attivita_diverse": 24238.92,
    # ...
    "totale_proventi": 550508.71,
    "risultato_esercizio": 18745.84,
}

def test_extract_bilancio_pisa_2024():
    result = extract_bilancio_pdf("test_data/bilanci/Bilancio_Pisa_2024.pdf")
    for key, expected in PISA_2024_EXPECTED.items():
        assert abs(result[key] - expected) < 0.01, f"{key}: atteso {expected}, ottenuto {result[key]}"

def test_extract_bilancio_parma_2025():
    result = extract_bilancio_pdf("test_data/bilanci/Bilancio_Parma_2025.pdf")
    for key, expected in PARMA_2025_EXPECTED.items():
        assert abs(result[key] - expected) < 0.01, f"{key}: atteso {expected}, ottenuto {result[key]}"
```

L'uso di tolleranza `< 0.01` permette di assorbire eventuali differenze di rendering numerico del PDF.

## Mockup e screenshot

Posizionare in `docs/releases/cairunts_002_assets/` (cartella da creare):

- `cairunts_002_assets/mockup_scheda_atti_documenti.png` — mockup della sezione "Atti e documenti" nella scheda ente.
- `cairunts_002_assets/mockup_scheda_bilanci.png` — mockup della sezione "Indicatori di bilancio".
- `cairunts_002_assets/mockup_scheda_persone.png` — mockup della sezione "Persone e cariche".
- `cairunts_002_assets/mockup_pdf_esteso.png` — anteprima del PDF aggiornato (release 002).
- `cairunts_002_assets/runts_organi_sociali.png` — screenshot della sezione organi sociali sul portale RUNTS, per riferimento dei selettori.

Già disponibili come riferimento in `docs/releases/002_docs/`:

- `002_docs/Screenshot documenti pisa.png` — sezione "Atti e documenti" di CAI Pisa.
- `002_docs/Screenshot documenti parma.png` — sezione "Atti e documenti" di CAI Parma.
- `002_docs/Bilancio_Pisa_2024.pdf` — bilancio d'esercizio CAI Pisa 2024 (formato sintetico, importi arrotondati all'euro).
- `002_docs/Bilancio_Parma_2025.pdf` — bilancio d'esercizio CAI Parma 2025 (formato esteso, importi con 2 decimali).

Gli stessi due PDF sono anche **fixture di test unitario** in `scraper/test_data/bilanci/` con identico nome file: vedi "Casi di test → Bilanci di test — valori attesi".

## Tasks tecniche

### A. Database — nuove tabelle
- [ ] A.1 In `scraper/db.py`, aggiungere `CREATE TABLE IF NOT EXISTS allegati (...)` allo schema canonico e in `_MIGRATIONS` come `CREATE TABLE` separato (idempotente).
- [ ] A.2 Aggiungere `CREATE TABLE IF NOT EXISTS bilanci (...)`.
- [ ] A.3 Aggiungere `CREATE TABLE IF NOT EXISTS cariche_sociali (...)`.
- [ ] A.4 Aggiungere gli indici `idx_allegati_id_runts`, `idx_bilanci_id_runts`, `idx_cariche_id_runts`, `idx_cariche_attive`.
- [ ] A.5 Aggiornare il documento `docs/03-database.md` con le nuove tabelle.

### B. Scraper — atti e documenti
- [ ] B.1 Aggiungere `httpx` a `scraper/requirements.txt`.
- [ ] B.2 In `scraper/scraper.py`, dopo `extract_fields`, aggiungere `extract_atti_documenti(page)` che individua la sezione "Atti e documenti" della pagina RUNTS e legge la tabella (colonne: Documento, Codice pratica, Data, Allegato). Restituisce lista di dict `{documento, codice_pratica, anno, url}`.
- [ ] B.3 Implementare `classify_codice_pratica(codice_pratica) -> tipo` che applica la mappa ufficiale (`B00`→`bilancio_esercizio`, `B03`→`situazione_patrimoniale`, `B08`→`bilancio_sociale`, `C01`→`atto_costitutivo`, `C02`→`statuto`, `D00`→`dichiarazione`, `E32`→`provvedimento_autorita`, `R06`→`relazione_controllo`, `PROVISC`→`provvedimento_iscrizione`, `99`→`altro`). Codici non mappati cadono su `altro`.
- [ ] B.4 Creare `scraper/downloader.py` con funzione async `download_attachments(client, id_runts, attachments, dest_dir, max_size_mb=50)`.
- [ ] B.5 Funzione `upsert_allegato(conn, data)` in `scraper/db.py` con upsert su `(id_runts, hash_sha256)`. I campi `documento`, `codice_pratica`, `tipo`, `anno` sono obbligatori in input (eccetto `anno` opzionale).
- [ ] B.6 Integrare il download nel main loop dello scraper (dopo `extract_fields` + `upsert_ente`).
- [ ] B.7 Estendere il report finale di `main.py` con i conteggi degli allegati.

### C. Scraper — cariche sociali
- [ ] C.1 In `scraper/scraper.py`, aggiungere `extract_cariche(page)` che legge la sezione organi sociali e restituisce lista di dict `{ruolo, nome, cognome, codice_fiscale, valid_from, valid_to}`.
- [ ] C.2 Implementare la mappa `ruolo_raw → ruolo_canonico` per normalizzare le diciture RUNTS (es. "Presidente del consiglio" → `presidente`).
- [ ] C.3 Funzione `sync_cariche(conn, id_runts, cariche_new)` in `scraper/db.py` che:
    - chiude (`valid_to` = oggi) le cariche già presenti con `valid_to IS NULL` ma non più nella lista nuova;
    - inserisce le nuove;
    - lascia invariate quelle che coincidono.
- [ ] C.4 Mantenere il popolamento esistente di `enti.rappresentante_legale` per retrocompatibilità.

### D. Analyzer — bilanci
- [ ] D.1 Aggiungere `pdfplumber` a `scraper/requirements.txt`.
- [ ] D.2 Creare `scraper/analyzer.py` con CLI argparse (`--db`, `--id-runts`, `--force`, `--verbose`).
- [ ] D.3 Funzione `extract_bilancio_pdf(path) -> dict` che restituisce i **13 campi** del rendiconto gestionale ETS (5 oneri A-E + totale, 5 proventi A-E + totale, 3 risultato). Campi non estraibili a `None`.
- [ ] D.4 Funzione `parse_italian_number(s) -> float | None` per gestire formato italiano (punto migliaia, virgola decimali, eventuali spazi/apostrofi). Casi da supportare: `"502.912,98"`, `"502 912,98"`, `"502'912,98"`, `"122929"`, `"122.929,00"`.
- [ ] D.5 Funzione `upsert_bilancio(conn, data)` con upsert su `(id_runts, anno)`.
- [ ] D.6 Controllo di coerenza somma A-E vs. totali (tolleranza 0,01 €) con log WARNING in caso di scostamento.
- [ ] D.7 Report finale: analizzati con successo, parziali, falliti.
- [ ] D.8 Suite di test in `scraper/test_analyzer.py` con fixture `Bilancio_Pisa_2024.pdf` e `Bilancio_Parma_2025.pdf` e i valori attesi documentati in "Casi di test".
- [ ] D.9 Aggiungere `scraper/test_data/bilanci/` al package (esistente al momento della stesura), con i due PDF già in posizione.

### E. Web app — visualizzazione
- [ ] E.1 In `web/app.py`, route `/ente/{id_runts}`: aggiungere SELECT su `allegati`, `bilanci`, `cariche_sociali`.
- [ ] E.2 In `web/templates/detail.html`, aggiungere le tre nuove sezioni con i template Jinja relativi.
- [ ] E.3 Helper `mask_cf` come Jinja filter custom.
- [ ] E.4 Helper `human_size` (KB/MB) come Jinja filter custom.
- [ ] E.5 Montare `/attachments` come `StaticFiles(directory="/app/attachments", check_dir=False)` in `web/app.py`.
- [ ] E.6 Aggiornare il `docker-compose.yml` con il bind-mount `./attachments:/app/attachments:ro`.

### F. PDF esteso
- [ ] F.1 Estendere `build_release_pdf.py` (o creare `web/pdf_scheda_ente.py` dedicato) con i flowable per le nuove sezioni.
- [ ] F.2 Aggiungere parametri al generatore: lista allegati, lista bilanci, lista cariche.
- [ ] F.3 Endpoint `/ente/{id_runts}/pdf` aggiornato per passare i nuovi dati al generatore.
- [ ] F.4 Mantenere il merge con la carta intestata MS invariato.

### Verifica
- [ ] V.1 Test manuale su **CAI Pisa** (`id_runts=83894`): 8 documenti scaricati (6 bilanci d'esercizio B00 per gli anni 2021-2024, C01, C02). Verificare la gestione dei tre B00 con stesso anno 2023 (deduplica per hash o suffisso). Confrontare con `002_docs/Screenshot documenti pisa.png`.
- [ ] V.2 Test manuale su **CAI Parma**: tutti i ~22 documenti del portale scaricati, righe in `allegati` con i 10 codici pratica diversi rappresentati (B00, B03, B08, C01, C02, D00, E32, R06, PROVISC, 99). Confrontare con `002_docs/Screenshot documenti parma.png`.
- [ ] V.3 Eseguire `python -m scraper.analyzer --db runts.db --id-runts 83894` e verificare righe in `bilanci` per gli anni 2021-2024. Per l'anno 2024 i 15 campi devono coincidere con i valori attesi documentati in "Casi di test → CAI Pisa Bilancio 2024" (tolleranza 0,01 €).
- [ ] V.4 Eseguire lo stesso per CAI Parma e verificare la presenza dei 4 anni di bilancio. Per il bilancio 2025 i 15 campi devono coincidere con i valori attesi documentati in "Casi di test → CAI Parma Bilancio 2025" (tolleranza 0,01 €).
- [ ] V.4b Eseguire `pytest scraper/test_analyzer.py` e verificare che i due test offline (Pisa 2024, Parma 2025) passino. Questo test è la **regressione automatica** dell'estrazione.
- [ ] V.5 Aprire le schede web di Pisa e Parma e verificare che le 3 sezioni appaiano con dati coerenti.
- [ ] V.6 Scaricare i PDF di Pisa e Parma e verificare che contengano tutte le sezioni aggiuntive.
- [ ] V.7 Re-eseguire lo scraper sui due enti: gli allegati con hash invariato non vengono riscaricati (`cache_hits > 0`).
- [ ] V.8 Test del cambio di carica: simulare un nuovo presidente e verificare che il vecchio record sia chiuso con `valid_to`.
- [ ] V.9 Test della tassonomia: verificare che un eventuale codice pratica sconosciuto (es. uno nuovo introdotto dal Ministero) ricada su `tipo = "altro"` mantenendo `codice_pratica` originale.

## Note per OpenSpec

Si propongono tre change OpenSpec separati per non sovraccaricare un singolo delta:

1. **`cairunts-002a-allegati`**: capability nuove `allegati-ingest`, `allegati-analisi`; capability modificate `database-storage`, `runts-detail`.
2. **`cairunts-002b-cariche-sociali`**: capability nuova `cariche-sociali`; capability modificate `database-storage`, `runts-detail`.
3. **`cairunts-002c-scheda-ente-estesa`**: capability modificate `ente-detail` (visualizzazione web), `enti-export` (PDF esteso).

In alternativa, un singolo change `cairunts-002-arricchimento-ente` se si preferisce un unico delta. La scelta dipende dalla granularità che si vuole tenere nelle review.

---

## Nota redazionale

Sul punto **"Persone — Mostrare nella scheda ente i metadati relativi agli allegati scaricati"** in TODO sembra esserci un copia-incolla: il testo è identico alla voce precedente sugli allegati. Ho interpretato l'intento come **"mostrare nella scheda ente i metadati relativi alle persone e cariche sociali"** (presidente, consiglieri, ecc.) e l'ho recepito in `D5`. Confermare in fase di revisione.
