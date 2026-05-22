## Context

Il portale RUNTS (https://servizi.lavoro.gov.it/runts/it-it/Ricerca-enti) è un'applicazione web Angular che carica i dati tramite chiamate API REST/JSON interne. La ricerca e il dettaglio degli enti avvengono via browser con rendering lato client. Non esistono API pubbliche documentate né export ufficiali.

L'obiettivo è estrarre i dati delle sezioni CAI presenti nel registro e mantenerli aggiornati in un database locale.

## Goals / Non-Goals

**Goals:**
- Automatizzare la ricerca per denominazione "CLUB ALPINO ITALIANO" sul portale RUNTS
- Estrarre tutti i campi disponibili dalla pagina di dettaglio di ciascun ente trovato
- Persistere i dati in SQLite con logica upsert (inserimento o aggiornamento)
- Fornire un unico script/comando eseguibile per avviare o aggiornare il database
- Gestire la paginazione dei risultati di ricerca

**Non-Goals:**
- Scheduling automatico (cron, daemon) — l'utente lancia manualmente quando vuole aggiornare
- Interfaccia grafica o web UI
- Esportazione in altri formati (CSV, JSON file) nella versione iniziale
- Scraping di altri enti oltre al CAI
- Autenticazione al portale (i dati sono pubblici)

## Decisions

### Browser automation: Playwright (Python) vs Selenium vs requests+BeautifulSoup

**Scelta: Playwright (Python)**

Il portale RUNTS è un'app Angular con rendering client-side. Le chiamate HTTP dirette (requests) non restituiscono dati utili perché il contenuto viene iniettato dal JavaScript. Playwright offre:
- API moderna e async-first
- Auto-wait integrato (evita sleep espliciti)
- Headless di default, headful per debug
- Installazione semplice (`playwright install chromium`)

Alternativa scartata: Selenium — più verboso, richiede gestione separata del WebDriver.
Alternativa scartata: requests+BeautifulSoup — non funziona con app Angular.

### Database: SQLite

**Scelta: SQLite (stdlib `sqlite3`)**

Dataset piccolo-medio (poche centinaia di sezioni CAI), uso locale, nessun accesso concorrente. SQLite è zero-config, file singolo, incluso nella stdlib Python.

Alternativa scartata: PostgreSQL/MySQL — sovradimensionati per questo use case.

### Strategia upsert

**Scelta: `INSERT OR REPLACE` basato su codice fiscale o ID RUNTS**

Ogni ente nel RUNTS ha un identificatore univoco (codice fiscale o ID interno). L'upsert usa questo identificatore come chiave primaria per aggiornare i record esistenti senza duplicati.

### Struttura del progetto

```
runts/
├── main.py          # entry point CLI (argparse)
├── scraper.py       # logica Playwright (ricerca + dettaglio)
├── db.py            # gestione SQLite (schema + upsert)
├── requirements.txt
└── runts.db         # database generato (gitignored)
```

### Intercettazione API interna vs parsing HTML

**Scelta: Intercettazione delle risposte di rete (Playwright `route` o `response` event)**

Il portale Angular fa chiamate XHR/fetch a endpoint interni che restituiscono JSON strutturato. Intercettare queste risposte è più robusto del parsing HTML perché:
- I dati sono già strutturati
- Non dipende da classi CSS o struttura DOM che possono cambiare
- Più veloce (nessun bisogno di estrarre testo dal DOM)

Alternativa: parsing DOM — fallback se l'intercettazione non è praticabile per via di CORS o autenticazione dei chiamate interne.

## Risks / Trade-offs

- [Il portale potrebbe cambiare struttura o endpoint interni] → Mitigation: loggare le risposte di rete per rilevare cambiamenti; mantenere anche un fallback DOM parser
- [Rate limiting o blocco IP] → Mitigation: delay configurabile tra richieste, User-Agent realistico
- [Paginazione non standard] → Mitigation: analizzare il comportamento di paginazione prima dell'implementazione; supportare sia paginazione numerica che "carica altri"
- [Campi del dettaglio variabili per ente] → Mitigation: salvare tutti i campi come colonne nullable; logghare campi inattesi
