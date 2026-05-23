## ADDED Requirements

### Requirement: Pulsante download PDF nella pagina dettaglio
Il template `detail.html` SHALL esporre un pulsante "Scarica scheda PDF" che avvia il download del PDF dell'ente corrente.

#### Scenario: Pulsante visibile nella pagina dettaglio
- **WHEN** l'utente visualizza la scheda di qualsiasi ente
- **THEN** la pagina mostra un pulsante "Scarica scheda PDF" che punta a `/ente/{id_runts}/pdf`

#### Scenario: Download avviato al click
- **WHEN** l'utente clicca "Scarica scheda PDF"
- **THEN** il browser avvia il download del file PDF senza navigare fuori dalla pagina
