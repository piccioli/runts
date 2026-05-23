## ADDED Requirements

### Requirement: Export CSV degli enti filtrati
Il sistema SHALL esporre `GET /api/enti.csv` che restituisce il dataset filtrato in formato CSV UTF-8 con BOM e separatore `;`.

#### Scenario: Download CSV completo
- **WHEN** il client chiama `/api/enti.csv` senza filtri
- **THEN** il sistema risponde con `Content-Type: text/csv; charset=utf-8-sig`, header `Content-Disposition: attachment; filename="enti.csv"` e un file con tutti gli enti, una riga di intestazione e i campi: `id_runts, denominazione, codice_fiscale, sede_indirizzo, sede_civico, sede_comune, sede_provincia, sede_regione, sede_cap, sezione_registro, forma_giuridica, natura_giuridica, data_iscrizione, pec, sito_web, url_dettaglio, lat, lon`

#### Scenario: CSV con filtro regione
- **WHEN** il client chiama `/api/enti.csv?regione=Toscana`
- **THEN** il CSV contiene solo gli enti con `sede_regione = 'Toscana'`

#### Scenario: Caratteri speciali nel CSV
- **WHEN** la denominazione contiene caratteri accentati (à, è, ì, ò, ù)
- **THEN** il file CSV è correttamente leggibile in Excel e LibreOffice grazie al BOM UTF-8

### Requirement: Export Excel degli enti filtrati
Il sistema SHALL esporre `GET /api/enti.xlsx` che restituisce lo stesso dataset del CSV in formato Excel con un foglio "Enti" e header congelato.

#### Scenario: Download Excel completo
- **WHEN** il client chiama `/api/enti.xlsx`
- **THEN** il sistema risponde con `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, header `Content-Disposition: attachment; filename="enti.xlsx"` e un file `.xlsx` con foglio "Enti", header congelato alla prima riga e larghezza colonne adeguata al contenuto

#### Scenario: Excel con filtro combinato
- **WHEN** il client chiama `/api/enti.xlsx?q=Pisa&regione=Toscana`
- **THEN** il file Excel contiene solo gli enti che corrispondono a entrambi i filtri

### Requirement: Filtri uniformi tra lista ed export
Gli endpoint di export SHALL accettare gli stessi parametri di filtro della lista (`q`, `regione`, `sezione_registro`) e applicarli identicamente tramite la stessa logica condivisa.

#### Scenario: Coerenza tra lista ed export
- **WHEN** la lista mostra N enti con un certo set di filtri attivi
- **THEN** il CSV e l'Excel scaricati con gli stessi parametri contengono esattamente N enti

### Requirement: Pulsanti export nella pagina lista
Il template `list.html` SHALL esporre i pulsanti "Esporta CSV" e "Esporta Excel" che trasmettono i filtri correnti all'endpoint corrispondente.

#### Scenario: Click su Esporta CSV
- **WHEN** l'utente ha attivo il filtro `regione=Toscana` e clicca "Esporta CSV"
- **THEN** il browser avvia il download di `enti.csv` contenente solo gli enti toscani
