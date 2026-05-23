## ADDED Requirements

### Requirement: Retry con backoff esponenziale sull'estrazione dettaglio
Lo scraper SHALL ritentare l'estrazione del dettaglio di un singolo ente fino a 3 volte in caso di eccezione, con backoff esponenziale.

#### Scenario: Recupero al secondo tentativo
- **WHEN** l'estrazione di un ente fallisce per timeout al primo tentativo ma riesce al secondo
- **THEN** l'ente è correttamente salvato nel DB; il report finale registra 1 ente nel contatore `recovered_attempt_2`; il sistema attende 1 secondo prima del secondo tentativo

#### Scenario: Recupero al terzo tentativo
- **WHEN** i primi due tentativi di estrazione falliscono ma il terzo riesce
- **THEN** l'ente è correttamente salvato; il report finale registra 1 nel contatore `recovered_attempt_3`; i tempi di attesa sono 1 s e 2 s rispettivamente

#### Scenario: Fallimento definitivo dopo 3 tentativi
- **WHEN** tutti e 3 i tentativi di estrazione falliscono
- **THEN** lo scraper logga ERROR con `id_runts` e denominazione, incrementa `failed_after_retry` nel report, e prosegue con l'ente successivo senza interrompersi

### Requirement: Report scraper esteso con contatori retry
Il report finale dello scraper SHALL riportare in modo distinto gli enti recuperati a ogni tentativo e quelli definitivamente falliti.

#### Scenario: Report con retry
- **WHEN** l'esecuzione dello scraper è completata e alcuni enti hanno richiesto retry
- **THEN** il report finale mostra: `Recuperati al 1° tentativo`, `Recuperati al 2° tentativo`, `Recuperati al 3° tentativo`, `Falliti definitivamente`
