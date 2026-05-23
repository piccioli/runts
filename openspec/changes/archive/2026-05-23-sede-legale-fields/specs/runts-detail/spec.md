## MODIFIED Requirements

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
