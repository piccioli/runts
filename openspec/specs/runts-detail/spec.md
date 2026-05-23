# Spec: RUNTS Detail Extraction

## Purpose
Definire come il sistema estrae i campi informativi dalla pagina di dettaglio di un ente sul portale RUNTS, inclusi i campi della sede legale tramite selettori DOM specifici.
## Requirements
### Requirement: Navigazione alla pagina di dettaglio
Il sistema SHALL navigare alla pagina di dettaglio di ciascun ente raccolto dalla fase di ricerca, cliccando sul link "DETTAGLIO" o equivalente.

#### Scenario: Navigazione al dettaglio riuscita
- **WHEN** il sistema processa un ente dalla lista dei risultati
- **THEN** il browser naviga alla pagina di dettaglio di quell'ente e attende il caricamento completo

#### Scenario: Errore di navigazione
- **WHEN** la navigazione al dettaglio fallisce (timeout, errore HTTP)
- **THEN** il sistema logga l'errore con l'identificatore dell'ente e prosegue con il successivo

### Requirement: Estrazione dei campi dalla pagina di dettaglio
Il sistema SHALL estrarre tutti i campi informativi dalla pagina di dettaglio dell'ente. I campi della sede legale (stato, provincia, comune, indirizzo, civico, CAP) SHALL essere estratti esclusivamente dalla sezione "Sede legale" della pagina, per evitare confusione con altre sezioni sede. Il campo `sede_regione` SHALL essere derivato dal codice provincia tramite mappatura statica se non disponibile direttamente nel DOM.

#### Scenario: Tutti i campi presenti
- **WHEN** la pagina di dettaglio contiene tutti i campi attesi
- **THEN** il sistema estrae il valore di ciascun campo e lo struttura in un dizionario con chiave = nome campo

#### Scenario: Estrazione sede legale completa
- **WHEN** la pagina di dettaglio contiene la sezione "Sede legale" con stato, provincia, comune, indirizzo, civico e CAP valorizzati
- **THEN** il sistema popola separatamente `sede_stato`, `sede_provincia`, `sede_comune`, `sede_indirizzo`, `sede_civico`, `sede_cap` con i valori corretti di quella sezione

#### Scenario: Regione derivata da provincia
- **WHEN** `sede_regione` non è disponibile direttamente nel DOM ma `sede_provincia` è valorizzata
- **THEN** il sistema deriva `sede_regione` dal codice provincia tramite mappatura statica (es. PI → Toscana)

#### Scenario: Campo assente o vuoto
- **WHEN** un campo atteso non è presente o ha valore vuoto nella pagina di dettaglio
- **THEN** il sistema assegna `None` a quel campo nel dizionario senza interrompere l'estrazione

#### Scenario: Campo inatteso trovato
- **WHEN** la pagina di dettaglio contiene un campo non previsto nello schema
- **THEN** il sistema logga il nome del campo inatteso e lo include nell'estrazione

#### Scenario: Test case CAI Pisa
- **WHEN** lo scraper processa l'ente con codice fiscale 80009440506 (CAI Sezione di Pisa)
- **THEN** il dizionario estratto contiene: `sede_stato`="I", `sede_provincia`="PI", `sede_comune`="PISA", `sede_indirizzo`="VIA DEL CHIASSATELLO", `sede_civico`="38-39-40", `sede_cap`="56122", `sede_regione`="Toscana"

### Requirement: Estrazione sede legale con selettori DOM specifici
Il sistema SHALL estrarre i campi della sede legale (stato, provincia, comune, indirizzo, civico, CAP) usando selettori CSS con suffisso `SL` scoped al container `divSedeLegale`.

#### Scenario: Estrazione sede legale
- **WHEN** la pagina di dettaglio contiene il container `[id*="divSedeLegale"]`
- **THEN** il sistema legge `spnStatoSL`, `spnProvinciaSL`, `spnComuneSL`, `spnIndirizzoSL`, `spnCivicoSL`, `spnCAP_SL` e popola i campi `sede_stato`, `sede_provincia`, `sede_comune`, `sede_indirizzo`, `sede_civico`, `sede_cap`

#### Scenario: Regione derivata dalla provincia
- **WHEN** il campo `sede_regione` non è presente nel DOM ma `sede_provincia` è disponibile
- **THEN** il sistema deriva `sede_regione` dalla mappa statica provincia → regione

### Requirement: Logging del progresso per dettaglio
Il sistema SHALL stampare su stdout il progresso durante la fase di estrazione dei dettagli.

#### Scenario: Dettaglio estratto con successo
- **WHEN** il dettaglio di un ente viene estratto con successo
- **THEN** il sistema logga "Processato [N/TOT] <denominazione>"

