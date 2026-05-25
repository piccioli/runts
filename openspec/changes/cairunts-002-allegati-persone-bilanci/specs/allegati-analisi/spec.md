## ADDED Requirements

### Requirement: Modulo analyzer CLI per bilanci ETS
Il sistema SHALL fornire un modulo eseguibile `python -m scraper.analyzer` con argomenti CLI `--db <path>`, `--id-runts <id>` (opzionale, per singolo ente), `--force` (ri-analizza anche record già analizzati), `--verbose`. Il modulo processa tutti gli allegati con `tipo IN ('bilancio_esercizio', 'situazione_patrimoniale')` non ancora analizzati (o tutti se `--force`).

#### Scenario: Esecuzione su tutti gli enti
- **WHEN** l'utente esegue `python -m scraper.analyzer --db runts.db`
- **THEN** il sistema processa tutti gli allegati di bilancio non ancora analizzati e stampa il report finale

#### Scenario: Esecuzione su singolo ente
- **WHEN** l'utente esegue `python -m scraper.analyzer --db runts.db --id-runts 83894`
- **THEN** il sistema processa solo gli allegati di bilancio di CAI Pisa

#### Scenario: Skip se già analizzato
- **WHEN** l'analyzer trova un record `bilanci` con stesso `(id_runts, anno)` e `analyzed_at` valorizzato
- **THEN** salta il file senza riaprirlo; l'utente può forzare con `--force`

### Requirement: Estrazione 13 voci numeriche del rendiconto gestionale ETS
Per ogni allegato di bilancio, il sistema SHALL estrarre tramite `pdfplumber` le seguenti 13 voci del rendiconto gestionale ETS (DM 39/2020): 5 categorie oneri A-E (`oneri_a_interesse_generale`, `oneri_b_attivita_diverse`, `oneri_c_raccolta_fondi`, `oneri_d_finanziarie_patrimoniali`, `oneri_e_supporto_generale`) più `totale_oneri`; 5 categorie proventi A-E (`proventi_a_interesse_generale`, `proventi_b_attivita_diverse`, `proventi_c_raccolta_fondi`, `proventi_d_finanziarie_patrimoniali`, `proventi_e_supporto_generale`) più `totale_proventi`; e i tre campi risultato: `risultato_ante_imposte`, `imposte`, `risultato_esercizio`. Importi in euro come REAL. Campi non estraibili restano NULL.

#### Scenario: Bilancio con tutti i campi
- **WHEN** l'analyzer processa un bilancio PDF testuale contenente le sezioni "ONERI E COSTI" e "PROVENTI E RICAVI" nel formato DM 39/2020
- **THEN** viene inserita una riga in `bilanci` con tutti i 13 campi valorizzati, `raw_text` (troncato a 50000 caratteri) e `analyzed_at`

#### Scenario: Bilancio parzialmente analizzato
- **WHEN** il PDF non rispetta lo schema atteso e nessun totale viene estratto
- **THEN** viene comunque inserita una riga in `bilanci` con `raw_text` valorizzato e tutti i campi numerici a NULL; il report lo conta come "parziale"

#### Scenario: Formato italiano con arrotondamento all'euro
- **WHEN** il bilancio riporta importi senza decimali (es. "122.929" o "122 929")
- **THEN** l'analyzer li normalizza correttamente in float (es. 122929.0)

### Requirement: Normalizzazione numeri in formato italiano
Il sistema SHALL supportare la funzione `parse_italian_number(s) -> float | None` che gestisce: punto come separatore migliaia e virgola come decimale (`1.234,56`), spazio come separatore migliaia (`1 234,56`), apostrofo come separatore migliaia (`1'234,56`), numeri interi senza decimali (`122929`). La funzione restituisce `None` se la stringa non è parsabile.

#### Scenario: Formato standard con decimali
- **WHEN** la stringa è `"502.912,98"`
- **THEN** `parse_italian_number` restituisce `502912.98`

#### Scenario: Formato senza decimali
- **WHEN** la stringa è `"122929"` o `"122.929"`
- **THEN** `parse_italian_number` restituisce `122929.0`

### Requirement: Controllo coerenza somme A-E vs totali
Dopo l'estrazione, il sistema SHALL verificare che la somma delle voci A-E coincida con il totale (tolleranza ±0,01 €) sia per gli oneri sia per i proventi. In caso di scostamento logga WARNING ma persiste comunque i dati.

#### Scenario: Coerenza verificata
- **WHEN** la somma oneri_a + ... + oneri_e coincide con totale_oneri (±0,01 €)
- **THEN** nessun warning viene emesso e il record è marcato come coerente

#### Scenario: Incoerenza rilevata
- **WHEN** la somma delle voci A-E degli oneri differisce da totale_oneri per più di 0,01 €
- **THEN** il sistema logga WARNING con i valori discordanti ma persiste comunque il record

### Requirement: Test offline con fixture reali
Il sistema SHALL includere `scraper/test_analyzer.py` con test unitari che usano i PDF in `scraper/test_data/bilanci/` come fixture e verificano i valori attesi (tolleranza 0,01 €): per `Bilancio_Pisa_2024.pdf` i 15 campi come da documentazione release 002; per `Bilancio_Parma_2025.pdf` i 15 campi come da documentazione release 002.

#### Scenario: Test Pisa 2024
- **WHEN** si esegue `pytest scraper/test_analyzer.py::test_extract_bilancio_pisa_2024`
- **THEN** il test passa: tutti i valori estratti coincidono con gli attesi entro 0,01 €

#### Scenario: Test Parma 2025
- **WHEN** si esegue `pytest scraper/test_analyzer.py::test_extract_bilancio_parma_2025`
- **THEN** il test passa: tutti i valori estratti coincidono con gli attesi entro 0,01 €
