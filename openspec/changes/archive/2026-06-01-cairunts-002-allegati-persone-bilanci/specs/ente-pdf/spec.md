## MODIFIED Requirements

### Requirement: Endpoint PDF scheda ente
Il sistema SHALL esporre `GET /ente/{id_runts}/pdf` che restituisce un PDF della scheda dell'ente con carta intestata Montagna Servizi. Il PDF SHALL includere, oltre alle informazioni anagrafiche già presenti: sezione "Atti e documenti" (elenco con tipo, anno, dimensione, link al file RUNTS originale), sezione "Indicatori di bilancio" (tabella anni con totale proventi, oneri, risultato), sezione "Persone e cariche" (lista attive + storiche). Le sezioni SHALL essere omesse se l'ente non ha allegati, bilanci o persone rispettivamente. Il PDF può estendersi su più pagine mantenendo la carta intestata su tutte.

#### Scenario: Download PDF ente con coordinate
- **WHEN** il client chiama `/ente/83894/pdf` (CAI Pisa, che ha `lat` e `lon` valorizzati)
- **THEN** il sistema risponde con `Content-Type: application/pdf`, header `Content-Disposition: attachment; filename="ente_83894.pdf"` e un PDF con: intestazione con denominazione e codice fiscale, tabella di tutti i campi non nulli, coordinate della sede legale, sezioni allegati/bilanci/persone popolate, tutto sovrapposto alla carta intestata Montagna Servizi

#### Scenario: Download PDF ente senza coordinate
- **WHEN** il client chiama `/ente/{id_runts}/pdf` per un ente senza `lat`/`lon`
- **THEN** il sistema genera il PDF senza la sezione coordinate, includendo tutti gli altri campi disponibili e le nuove sezioni se presenti

#### Scenario: Ente non trovato
- **WHEN** il client chiama `/ente/{id_runts}/pdf` con un `id_runts` non presente nel DB
- **THEN** il sistema risponde con HTTP 404

#### Scenario: PDF minimale — nessun allegato né bilancio né persona
- **WHEN** l'utente scarica il PDF di un ente senza allegati, bilanci o persone registrate
- **THEN** il PDF contiene solo la scheda anagrafica come nella release 001, senza sezioni vuote aggiuntive

#### Scenario: PDF multi-pagina con carta intestata
- **WHEN** il PDF si estende su più pagine per via del volume di allegati e/o cariche
- **THEN** la carta intestata Montagna Servizi è presente su tutte le pagine

### Requirement: Layout PDF con carta intestata Montagna Servizi
Il PDF generato SHALL utilizzare `MS_Carta_Intestata.pdf` come sfondo sovrapposto al contenuto generato con reportlab.

#### Scenario: Carta intestata presente
- **WHEN** il file `web/static/MS_Carta_Intestata.pdf` è disponibile
- **THEN** ogni pagina del PDF ha la carta intestata come sfondo e il contenuto testuale sovrapposto senza sovrascrivere loghi o decorazioni marginali

#### Scenario: Campi con testo lungo
- **WHEN** un campo dell'ente ha un valore molto lungo (es. denominazione > 100 caratteri)
- **THEN** il testo va a capo entro i margini del layout senza sforare la pagina

### Requirement: Pulsante "Scarica scheda PDF" nella pagina dettaglio
Il template `detail.html` SHALL esporre un pulsante "Scarica scheda PDF" che porta all'endpoint PDF dell'ente corrente.

#### Scenario: Click su Scarica scheda PDF
- **WHEN** l'utente visualizza la scheda di un ente e clicca "Scarica scheda PDF"
- **THEN** il browser avvia il download del PDF corrispondente a quell'ente
