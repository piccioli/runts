## Why

L'estrazione della sede legale è inaffidabile: i selettori attuali non sono vincolati alla sezione "Sede legale" della pagina, mancano i campi `sede_stato` e `sede_civico` come colonne separate, e `sede_regione` spesso risulta vuota perché il portale non la espone direttamente. Il caso di test (CAI Pisa, CF 80009440506) evidenzia che indirizzo, civico e CAP vengono persi o confusi.

## What Changes

- L'estrazione della sede legale viene riscritta per operare esclusivamente sulla sezione "Sede legale" della pagina di dettaglio RUNTS
- Aggiunto campo `sede_stato` (es. "I") estratto dal portale
- Il campo `sede_civico` viene salvato separatamente (attualmente veniva concatenato a `sede_indirizzo`)
- `sede_regione` viene derivata dal codice provincia tramite mappatura statica quando non disponibile direttamente
- Schema DB aggiornato con le nuove colonne `sede_stato` e `sede_civico`
- App web aggiornata per mostrare i nuovi campi nella pagina di dettaglio

## Capabilities

### New Capabilities

### Modified Capabilities

- `runts-detail`: L'estrazione dei campi sede deve essere vincolata alla sezione "Sede legale" e includere stato e civico separati
- `database-storage`: Schema aggiornato con colonne `sede_stato` e `sede_civico`
- `ente-detail`: Pagina di dettaglio aggiornata per mostrare stato, civico e regione

## Impact

- `scraper/scraper.py`: riscrittura logica estrazione sede legale
- `scraper/db.py`: aggiunta colonne `sede_stato`, `sede_civico`; ALTER TABLE su DB esistente
- `web/templates/detail.html`: aggiunta label per nuovi campi
- Caso di test: CF 80009440506 (CAI Pisa) — deve restituire Stato=I, Provincia=PI, Comune=PISA, Indirizzo=VIA DEL CHIASSATELLO, Civico=38-39-40, CAP=56122, Regione=Toscana
