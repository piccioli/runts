## ADDED Requirements

### Requirement: Mappa embedded nella pagina di dettaglio
Il sistema SHALL mostrare nella pagina di dettaglio dell'ente una mappa Leaflet.js centrata sulle coordinate della sede legale, se disponibili.

#### Scenario: Coordinate disponibili
- **WHEN** l'ente ha `lat` e `lon` valorizzati nel DB
- **THEN** la pagina di dettaglio mostra una mappa centrata su quelle coordinate con un marker sulla sede, posizionata dopo i campi di dettaglio

#### Scenario: Coordinate non disponibili
- **WHEN** l'ente non ha `lat` o `lon` nel DB
- **THEN** la sezione mappa non viene renderizzata nella pagina di dettaglio
