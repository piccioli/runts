# geocoding Specification

## Purpose
TBD - created by archiving change mappa-enti. Update Purpose after archive.
## Requirements
### Requirement: Geocodifica degli enti tramite Nominatim
Il sistema SHALL geocodificare gli enti con `lat IS NULL OR lon IS NULL`, cercando prima nella `geocoding_cache` e ricadendo su Nominatim solo in caso di miss. Il report finale SHALL distinguere tra coordinate risolte da cache e da Nominatim.

#### Scenario: Cache hit — nessuna chiamata Nominatim
- **WHEN** la `cache_key` dell'ente corrente è presente in `geocoding_cache`
- **THEN** il geocoder usa le coordinate dalla cache senza effettuare chiamate HTTP; il report incrementa `from_cache`

#### Scenario: Cache miss — chiamata Nominatim
- **WHEN** la `cache_key` non è in cache
- **THEN** il geocoder esegue le query Nominatim con fallback progressivo, applica le coordinate e scrive il risultato in `geocoding_cache`; il report incrementa `from_nominatim`

#### Scenario: Nominatim non trova le coordinate
- **WHEN** Nominatim non restituisce risultati per un ente dopo tutti i fallback
- **THEN** il geocoder logga un warning e lascia `lat`/`lon` a NULL, continuando con l'ente successivo

#### Scenario: Ente già geocodificato
- **WHEN** un ente ha già `lat` e `lon` valorizzati nel DB
- **THEN** il geocoder lo salta senza effettuare richieste a Nominatim né consultare la cache

#### Scenario: Report con contatori separati
- **WHEN** l'esecuzione del geocoder è completata
- **THEN** il report finale mostra: `Totale processati`, `Geocodificati (da cache)`, `Geocodificati (da Nominatim)`, `Non trovati`, `Errori HTTP`, `Saltati (no comune)`

#### Scenario: Secondo run con cache popolata
- **WHEN** il geocoder viene eseguito una seconda volta sullo stesso DB
- **THEN** il contatore `from_cache` è > 0 e `from_nominatim` è ridotto rispetto al primo run

