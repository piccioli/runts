## Why

La lista degli enti mostra solo dati testuali; una mappa interattiva permette di visualizzare la distribuzione geografica delle sezioni CAI e di localizzare rapidamente quella più vicina. Il dettaglio del singolo ente beneficia di una mappa integrata per contestualizzare la sede.

## What Changes

- Aggiunta geocodifica delle sedi: coordinate lat/lon derivate da comune + provincia tramite Nominatim (OpenStreetMap), salvate nel DB
- Nuovo script di geocodifica eseguibile separatamente per popolare le coordinate
- Lista enti: nuova vista mappa alternativa (toggle lista/mappa) con marker per ogni ente, basata su Leaflet.js
- Dettaglio ente: mappa embedded che mostra la sede legale come marker

## Capabilities

### New Capabilities
- `geocoding`: script per derivare lat/lon da comune+provincia e salvarle nel DB
- `mappa-lista`: vista mappa alternativa nella pagina lista enti con toggle lista/mappa
- `mappa-dettaglio`: mappa embedded nella pagina di dettaglio del singolo ente

### Modified Capabilities
- `database-storage`: aggiunta colonne `lat` e `lon` (REAL) allo schema con relativa migrazione
- `enti-list`: aggiunta vista mappa alternativa con toggle
- `ente-detail`: aggiunta sezione mappa integrata

## Impact

- `scraper/db.py`: nuove colonne `lat`, `lon`
- Nuovo modulo `scraper/geocoder.py`: chiama Nominatim, salva coordinate nel DB
- `web/templates/list.html`: toggle lista/mappa + blocco Leaflet
- `web/templates/detail.html`: mappa embedded Leaflet
- Dipendenza front-end: Leaflet.js via CDN (nessuna API key richiesta)
- Nessuna modifica al flusso di scraping esistente
