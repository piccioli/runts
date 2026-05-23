## 1. Database

- [x] 1.1 Aggiungere colonne `lat REAL` e `lon REAL` allo schema in `scraper/db.py`
- [x] 1.2 Aggiungere migrazioni `ALTER TABLE enti ADD COLUMN lat REAL` e `lon REAL` in `_MIGRATIONS` con gestione errore se già esistono
- [x] 1.3 Aggiungere `lat` e `lon` alla lista `columns` in `upsert_ente()`

## 2. Geocoder

- [x] 2.1 Creare `scraper/geocoder.py` con funzione `geocode_enti(conn, db_path)` che interroga Nominatim per gli enti con `lat`/`lon` NULL, rispettando 1 req/s di rate limit
- [x] 2.2 Aggiungere entry point `__main__` in `scraper/geocoder.py` con argparse (`--db`, `--verbose`) e report finale (geocodificati / non trovati / già presenti)

## 3. App web — lista con mappa

- [x] 3.1 Aggiungere `lat` e `lon` ai dati passati al template `list.html` nella route `/` di `web/app.py`
- [x] 3.2 Aggiungere in `web/templates/list.html` il pulsante toggle Lista/Mappa e il div `<div id="map">` con altezza fissa
- [x] 3.3 Aggiungere in `web/templates/list.html` il blocco Leaflet (CSS + JS via CDN) e lo script che inizializza la mappa, posiziona i marker con popup (denominazione + link dettaglio) e gestisce il toggle mostra/nascondi

## 4. App web — dettaglio con mappa

- [x] 4.1 Aggiungere `lat` e `lon` ai dati passati al template `detail.html` nella route `/ente/<id_runts>` di `web/app.py`
- [x] 4.2 Aggiungere in `web/templates/detail.html` il blocco Leaflet e la sezione mappa (condizionale: renderizzata solo se `lat` e `lon` sono valorizzati)

## 5. Verifica

- [x] 5.1 Eseguire `python3 -m scraper.geocoder --db runts.db` e verificare che almeno 200/226 enti vengano geocodificati correttamente
- [x] 5.2 Verificare che la lista mostri il toggle Lista/Mappa e che i marker appaiano sulla mappa con popup corretti
- [x] 5.3 Verificare che la pagina di dettaglio di CAI Pisa (id_runts=83894) mostri la mappa centrata su Pisa
- [x] 5.4 Verificare che un ente senza coordinate non mostri la sezione mappa nel dettaglio
