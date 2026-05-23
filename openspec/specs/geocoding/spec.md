# geocoding Specification

## Purpose
TBD - created by archiving change mappa-enti. Update Purpose after archive.
## Requirements
### Requirement: Geocodifica degli enti tramite Nominatim
Il sistema SHALL esporre un modulo `scraper/geocoder.py` eseguibile come `python3 -m scraper.geocoder` che legge gli enti senza coordinate dal DB e ne deriva `lat` e `lon` tramite l'API Nominatim (OpenStreetMap), rispettando il rate limit di 1 richiesta al secondo.

#### Scenario: Ente senza coordinate
- **WHEN** un ente ha `lat` o `lon` NULL nel DB
- **THEN** il geocoder interroga Nominatim con `comune` e `provincia` dell'ente, salva le coordinate nel DB e logga il risultato

#### Scenario: Nominatim non trova le coordinate
- **WHEN** Nominatim non restituisce risultati per un ente
- **THEN** il geocoder logga un warning e lascia `lat`/`lon` a NULL, continuando con l'ente successivo senza interrompere l'esecuzione

#### Scenario: Ente già geocodificato
- **WHEN** un ente ha già `lat` e `lon` valorizzati nel DB
- **THEN** il geocoder lo salta senza effettuare richieste a Nominatim

#### Scenario: Report finale
- **WHEN** il geocoder ha processato tutti gli enti
- **THEN** stampa il numero di enti geocodificati con successo, quelli non trovati e quelli già presenti

