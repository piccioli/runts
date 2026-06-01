## ADDED Requirements

### Requirement: Scoperta e classificazione atti e documenti RUNTS
Lo scraper SHALL individuare nella pagina di dettaglio RUNTS la sezione "Atti e documenti" e leggere la tabella con colonne Documento, Codice pratica, Data, Allegato (link PDF). Per ogni riga SHALL derivare il tipo canonico dal codice pratica secondo la mappa ufficiale: `B00`→`bilancio_esercizio`, `B03`→`situazione_patrimoniale`, `B08`→`bilancio_sociale`, `C01`→`atto_costitutivo`, `C02`→`statuto`, `D00`→`dichiarazione`, `E32`→`provvedimento_autorita`, `R06`→`relazione_controllo`, `PROVISC`→`provvedimento_iscrizione`, `99`→`altro`. Codici non presenti in mappa cadono su `altro` mantenendo il `codice_pratica` originale.

#### Scenario: Sezione atti e documenti presente
- **WHEN** la pagina di dettaglio RUNTS espone la sezione "Atti e documenti" con una tabella di allegati
- **THEN** lo scraper raccoglie per ogni riga: `documento` (testo originale), `codice_pratica` (es. "B00"), `anno` (dalla colonna Data, NULL se assente), `url` del link PDF, `tipo` canonico derivato dalla mappa

#### Scenario: Codice pratica sconosciuto
- **WHEN** la tabella contiene un codice pratica non presente nella mappa ufficiale
- **THEN** il campo `tipo` viene impostato a `"altro"` e il `codice_pratica` originale viene conservato invariato nel DB

#### Scenario: Sezione atti assente
- **WHEN** la pagina di dettaglio non contiene la sezione "Atti e documenti"
- **THEN** lo scraper prosegue senza errore, nessuna riga viene aggiunta in `allegati` per quell'ente

### Requirement: Download allegati su filesystem
Il sistema SHALL scaricare i file allegati tramite `httpx.AsyncClient` (max 4 connessioni parallele) e salvarli in `attachments/<id_runts>/<filename_normalizzato>`. Il filename normalizzato segue la convenzione `<codice_pratica>_<anno>_<slug-documento>.pdf`; in caso di collisione (stesso codice e anno) viene aggiunto un suffisso progressivo `_2`, `_3`, ecc. Il sistema SHALL calcolare l'hash SHA-256 del file scaricato.

#### Scenario: Primo download
- **WHEN** lo scraper incontra un allegato non presente nel filesystem
- **THEN** il file viene scaricato, salvato con filename normalizzato, e l'hash SHA-256 viene calcolato e salvato in `allegati`

#### Scenario: Collisione nome file stesso anno
- **WHEN** un ente ha più allegati con stesso codice pratica e anno (es. tre B00 del 2023)
- **THEN** il sistema salva i file come `B00_2023_bilancio_desercizio.pdf`, `B00_2023_bilancio_desercizio_2.pdf`, `B00_2023_bilancio_desercizio_3.pdf`

#### Scenario: Allegato troppo grande
- **WHEN** un allegato supera il limite configurato (default 50 MB)
- **THEN** il file non viene scaricato, la riga in `allegati` viene inserita con `path` NULL e `skip_reason = "size_exceeded"`, il report incrementa "saltati per dimensione"

### Requirement: Upsert allegati per hash SHA-256
Il sistema SHALL persistere ogni documento nella tabella `allegati` con upsert sulla combinazione `(id_runts, hash_sha256)`. Se un documento con stesso hash è già presente, il file non viene riscaricato e la riga viene aggiornata solo nel campo `downloaded_at`.

#### Scenario: Allegato già presente (cache hit)
- **WHEN** lo scraper rilancia su un ente e un allegato ha lo stesso `hash_sha256` di una riga già nel DB
- **THEN** il file non viene riscaricato, `downloaded_at` viene aggiornato, il report incrementa "già presenti"

#### Scenario: Allegato nuovo (cache miss)
- **WHEN** lo scraper incontra un allegato il cui hash non è presente in `allegati` per quell'ente
- **THEN** il file viene scaricato, il record inserito, il report incrementa "scaricati"

### Requirement: Report allegati nel report finale scraper
Il report finale dello scraper SHALL includere il conteggio degli allegati per ogni ente processato: scoperti, scaricati, già presenti (cache hit), saltati per dimensione, falliti.

#### Scenario: Report dopo run completo
- **WHEN** il run dello scraper termina
- **THEN** il report include: allegati scoperti totali, scaricati, già presenti, saltati per dimensione, falliti — con breakdown per codice pratica
