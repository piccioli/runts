### Requirement: Navigazione alla pagina di dettaglio
Il sistema SHALL navigare alla pagina di dettaglio di ciascun ente raccolto dalla fase di ricerca, cliccando sul link "DETTAGLIO" o equivalente.

#### Scenario: Navigazione al dettaglio riuscita
- **WHEN** il sistema processa un ente dalla lista dei risultati
- **THEN** il browser naviga alla pagina di dettaglio di quell'ente e attende il caricamento completo

#### Scenario: Errore di navigazione
- **WHEN** la navigazione al dettaglio fallisce (timeout, errore HTTP)
- **THEN** il sistema logga l'errore con l'identificatore dell'ente e prosegue con il successivo

### Requirement: Estrazione dei campi dalla pagina di dettaglio
Il sistema SHALL estrarre tutti i campi informativi disponibili nella pagina di dettaglio dell'ente, inclusi almeno: denominazione, codice fiscale, forma giuridica, sede legale, data iscrizione al RUNTS, settore di attività, rappresentante legale.

#### Scenario: Tutti i campi presenti
- **WHEN** la pagina di dettaglio contiene tutti i campi attesi
- **THEN** il sistema estrae il valore di ciascun campo e lo struttura in un dizionario con chiave = nome campo

#### Scenario: Campo assente o vuoto
- **WHEN** un campo atteso non è presente o ha valore vuoto nella pagina di dettaglio
- **THEN** il sistema assegna `None` a quel campo nel dizionario senza interrompere l'estrazione

#### Scenario: Campo inatteso trovato
- **WHEN** la pagina di dettaglio contiene un campo non previsto nello schema
- **THEN** il sistema logga il nome del campo inatteso e lo include nell'estrazione

### Requirement: Logging del progresso per dettaglio
Il sistema SHALL stampare su stdout il progresso durante la fase di estrazione dei dettagli.

#### Scenario: Dettaglio estratto con successo
- **WHEN** il dettaglio di un ente viene estratto con successo
- **THEN** il sistema logga "Processato [N/TOT] <denominazione>"
