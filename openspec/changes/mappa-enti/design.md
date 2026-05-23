## Context

L'app web mostra attualmente solo dati tabellari. Gli enti hanno campi sede (comune, provincia) ma non coordinate geografiche. Per mostrare una mappa serve geocodificare gli indirizzi e scegliere una libreria di mappe che non richieda API key.

## Goals / Non-Goals

**Goals:**
- Geocodifica automatica degli enti nel DB tramite Nominatim (OSM), senza costi e senza API key
- Vista mappa alternativa nella lista, attivabile via toggle, con tutti i marker filtrati
- Mappa embedded nella pagina di dettaglio centrata sulla sede dell'ente
- Coordinamento incrementale: geocoder eseguibile separatamente, non blocca lo scraper

**Non-Goals:**
- Geocodifica in tempo reale durante lo scraping
- Clustering avanzato dei marker (out of scope per ora)
- Mappe offline o tile server proprietario
- Routing o calcolo percorsi

## Decisions

### 1. Leaflet.js via CDN — no build step
Leaflet è la libreria OSS più matura per mappe interattive, non richiede API key, funziona via CDN. Alternativa scartata: Google Maps (richiede chiave + fatturazione), Mapbox (richiede token).

### 2. Nominatim per geocodifica — query per comune+provincia
Nominatim (api.nominatim.openstreetmap.org) è gratuito e non richiede autenticazione. Query con `city=<comune>&county=<provincia>&country=Italy` è sufficiente per la precisione richiesta (livello comune, non civico esatto). Rate limit: 1 req/s — il geocoder rispetta questo limite con `time.sleep(1)`.
Alternativa scartata: geocodifica per indirizzo completo (meno affidabile con dati RUNTS incompleti).

### 3. Colonne `lat` e `lon` REAL nel DB — geodata persistita
Le coordinate vengono salvate nel DB per evitare di interrogare Nominatim ad ogni caricamento della pagina. Il geocoder è uno script separato (`scraper/geocoder.py`) lanciabile manualmente o in cron.

### 4. Toggle lista/mappa lato client — nessuna nuova route
Il toggle mostra/nasconde il div della mappa e quello della tabella via JavaScript, mantenendo i filtri attivi. La mappa riceve i dati come JSON inline nella pagina (tutti gli enti filtrati già presenti nella response HTML). Nessuna nuova API route necessaria.

### 5. Tile layer OpenStreetMap — gratuito, nessun token
`https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png` con attribuzione obbligatoria. Alternativa: CartoDB (più leggero visivamente), ma per semplicità si usa OSM diretto.

## Risks / Trade-offs

- **Nominatim rate limit** → il geocoder dorme 1 secondo tra ogni richiesta; per 226 enti ~4 minuti totali. Accettabile per esecuzione manuale.
- **Indirizzi non trovati** → se Nominatim non trova coordinate, `lat`/`lon` restano NULL e l'ente non appare sulla mappa (ma compare in lista). Non è un errore bloccante.
- **Dati JSON inline nella lista** → per 226 enti il JSON è ~50KB, trascurabile. Se il dataset crescesse molto si rivaluterebbe un endpoint dedicato.
- **Enti senza coordinate nella mappa lista** → vengono semplicemente omessi dai marker; l'utente vede solo quelli geocodificati.

## Migration Plan

1. Eseguire `python3 -m scraper.geocoder --db runts.db` dopo il deploy per popolare `lat`/`lon`
2. Il DB esistente viene migrato automaticamente da `init_db()` con `ALTER TABLE`
3. Rollback: rimozione delle colonne non è necessaria — i template ignorano lat/lon se non visualizzati
