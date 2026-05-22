## Why

Il Registro Unico Nazionale del Terzo Settore (RUNTS) espone dati pubblici sugli enti del terzo settore tramite un portale web, ma non offre API o export strutturati. Occorre un'applicazione che estragga automaticamente i dati delle sezioni del Club Alpino Italiano (CAI) presenti nel RUNTS, li strutturi e li persista in un database aggiornabile periodicamente.

## What Changes

- Nuova applicazione Python standalone con scraper per il portale RUNTS
- Ricerca automatica per denominazione "CLUB ALPINO ITALIANO" sulla pagina di ricerca enti
- Navigazione automatica al dettaglio di ciascun risultato per raccogliere tutti i campi disponibili
- Persistenza dei dati in un database SQLite locale
- Comando/script per aggiornare il database con i dati più recenti (upsert per evitare duplicati)

## Capabilities

### New Capabilities

- `runts-search`: Ricerca enti sul portale RUNTS per denominazione e raccolta dei risultati paginati
- `runts-detail`: Navigazione alla pagina di dettaglio di ciascun ente e estrazione di tutti i campi
- `database-storage`: Persistenza dei dati estratti in SQLite con supporto upsert per aggiornamenti incrementali

### Modified Capabilities

## Impact

- Nuove dipendenze Python: `playwright` o `selenium` (browser automation), `sqlite3` (stdlib), `click` o argparse per CLI
- Nessun impatto su sistemi esistenti (applicazione standalone)
- Il database SQLite viene creato localmente nella directory del progetto
