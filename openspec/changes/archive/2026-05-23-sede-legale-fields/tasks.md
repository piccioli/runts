## 1. Scraper — estrazione sede legale

- [x] 1.1 Aggiungere `_PROVINCIA_TO_REGIONE` dict in `scraper/scraper.py` con tutte le 107 province italiane
- [x] 1.2 Aggiungere funzione JS `_EXTRACT_SEDE_LEGALE_JS` che individua il container "Sede legale" nel DOM ed estrae stato, provincia, comune, indirizzo, civico, CAP come campi separati
- [x] 1.3 Aggiornare `extract_fields()`: chiamare la nuova funzione JS per sede legale, popolare `sede_stato`, `sede_civico`; derivare `sede_regione` da `_PROVINCIA_TO_REGIONE` se assente dal DOM
- [x] 1.4 Rimuovere da `_DETAIL_IDS` i campi sede che ora vengono estratti dalla funzione JS dedicata (`sede_provincia`, `sede_comune`, `sede_regione`), per evitare sovrascrittura

## 2. Database

- [x] 2.1 Aggiungere colonne `sede_stato TEXT` e `sede_civico TEXT` allo schema in `scraper/db.py`
- [x] 2.2 Aggiungere migrazione in `init_db()`: `ALTER TABLE enti ADD COLUMN sede_stato TEXT` e `ALTER TABLE enti ADD COLUMN sede_civico TEXT` con gestione errore se la colonna esiste già
- [x] 2.3 Aggiungere `sede_stato` e `sede_civico` alla lista `columns` in `upsert_ente()`

## 3. App web

- [x] 3.1 Aggiungere `sede_stato` e `sede_civico` al dict `labels` in `web/templates/detail.html`

## 4. Verifica

- [x] 4.1 Eseguire scraper con denominazione esatta `"CLUB ALPINO ITALIANO SEZIONE DI PISA- APS-ETS"` e verificare che il dizionario estratto contenga: `sede_stato`="I", `sede_provincia`="PI", `sede_comune`="PISA", `sede_indirizzo`="VIA DEL CHIASSATELLO", `sede_civico`="38-39-40", `sede_cap`="56122", `sede_regione`="Toscana"
- [x] 4.2 Verificare che DB esistente (`runts.db`) venga migrato correttamente senza errori
- [x] 4.3 Verificare che la pagina di dettaglio web mostri stato, civico e regione per CAI Pisa
