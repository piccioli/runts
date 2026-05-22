## ADDED Requirements

### Requirement: Ricerca enti per denominazione
Il sistema SHALL eseguire una ricerca sul portale RUNTS compilando il campo "DENOMINAZIONE" con il valore "CLUB ALPINO ITALIANO" e avviando la ricerca tramite automazione browser.

#### Scenario: Ricerca completata con risultati
- **WHEN** lo scraper viene avviato
- **THEN** il browser naviga su https://servizi.lavoro.gov.it/runts/it-it/Ricerca-enti, compila il campo DENOMINAZIONE con "CLUB ALPINO ITALIANO" e clicca il pulsante di ricerca

#### Scenario: Nessun risultato trovato
- **WHEN** la ricerca non produce risultati
- **THEN** il sistema termina senza errore e logga "Nessun risultato trovato"

### Requirement: Raccolta di tutti i risultati paginati
Il sistema SHALL raccogliere i link o gli identificatori di tutti gli enti nei risultati di ricerca, navigando attraverso tutte le pagine disponibili prima di procedere all'estrazione dei dettagli.

#### Scenario: Risultati su pagina singola
- **WHEN** tutti i risultati sono visibili in una sola pagina
- **THEN** il sistema raccoglie tutti i risultati dalla pagina corrente senza tentare ulteriori navigazioni

#### Scenario: Risultati su più pagine
- **WHEN** i risultati sono distribuiti su più pagine
- **THEN** il sistema naviga su ogni pagina e raccoglie i riferimenti agli enti fino ad esaurire le pagine disponibili

### Requirement: Logging del progresso della ricerca
Il sistema SHALL stampare su stdout il numero totale di enti trovati al termine della fase di ricerca.

#### Scenario: Fine raccolta risultati
- **WHEN** la raccolta di tutti i risultati è completata
- **THEN** il sistema logga "Trovati N enti" dove N è il numero totale di enti raccolti
