## ADDED Requirements

### Requirement: Endpoint GeoJSON degli enti filtrati
Il sistema SHALL esporre `GET /api/enti.geojson` che restituisce un GeoJSON `FeatureCollection` con tutti gli enti del DB che corrispondono ai filtri della query string e che hanno `lat` e `lon` valorizzati, senza paginazione.

#### Scenario: Risposta GeoJSON completa
- **WHEN** il client chiama `/api/enti.geojson` senza parametri
- **THEN** il sistema restituisce un JSON con `type: "FeatureCollection"` e un array `features` contenente tutti gli enti con coordinate, con `Content-Type: application/geo+json`

#### Scenario: Filtro per regione
- **WHEN** il client chiama `/api/enti.geojson?regione=Toscana`
- **THEN** l'array `features` contiene solo gli enti con `sede_regione = 'Toscana'` che hanno `lat` e `lon` valorizzati

#### Scenario: Filtro per sezione del registro
- **WHEN** il client chiama `/api/enti.geojson?sezione_registro=APS`
- **THEN** l'array `features` contiene solo gli enti APS con coordinate

#### Scenario: Filtri multipli combinati
- **WHEN** il client chiama `/api/enti.geojson?regione=Toscana,Lombardia`
- **THEN** il sistema restituisce enti di entrambe le regioni, accettando valori comma-separated

#### Scenario: Nessun ente con coordinate
- **WHEN** il DB non ha enti con `lat` e `lon` valorizzati
- **THEN** il sistema restituisce `{"type":"FeatureCollection","features":[]}` con HTTP 200

### Requirement: Struttura delle Feature GeoJSON
Ogni `Feature` nell'array SHALL contenere geometria `Point` e le proprietà necessarie per i marker della mappa.

#### Scenario: Feature valida
- **WHEN** un ente ha `lat=43.7` e `lon=10.4`
- **THEN** la Feature corrispondente ha `geometry.type="Point"`, `geometry.coordinates=[10.4, 43.7]` (lon, lat) e `properties` con `id_runts`, `denominazione`, `sede_comune`, `sede_regione`, `sezione_registro`
