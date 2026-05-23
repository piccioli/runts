## MODIFIED Requirements

### Requirement: Geocodifica degli enti
Il sistema SHALL geocodificare gli enti con `lat IS NULL OR lon IS NULL`, cercando prima nella `geocoding_cache` e ricadendo su Nominatim solo in caso di miss.

#### Scenario: Cache hit — nessuna chiamata Nominatim
- **WHEN** la `cache_key` dell'ente corrente è presente in `geocoding_cache`
- **THEN** il geocoder usa le coordinate dalla cache senza effettuare chiamate HTTP; il report incrementa `from_cache`

#### Scenario: Cache miss — chiamata Nominatim
- **WHEN** la `cache_key` non è in cache
- **THEN** il geocoder esegue le query Nominatim con fallback progressivo, applica le coordinate e scrive il risultato in `geocoding_cache`; il report incrementa `from_nominatim`

## MODIFIED Requirements

### Requirement: Report finale del geocoder
Il sistema SHALL stampare a fine esecuzione un riepilogo delle operazioni di geocodifica, distinguendo tra coordinate risolte da cache e da Nominatim.

#### Scenario: Report con contatori separati
- **WHEN** l'esecuzione del geocoder è completata
- **THEN** il report finale mostra: `Totale processati`, `Geocodificati (da cache)`, `Geocodificati (da Nominatim)`, `Non trovati`, `Errori HTTP`, `Saltati (no comune)`

#### Scenario: Secondo run successivo al primo
- **WHEN** il geocoder viene eseguito una seconda volta sullo stesso DB
- **THEN** il contatore `from_cache` è > 0 e `from_nominatim` è ridotto rispetto al primo run
