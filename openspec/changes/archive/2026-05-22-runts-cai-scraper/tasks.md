## 1. Setup progetto

- [x] 1.1 Creare `requirements.txt` con dipendenze: `playwright`
- [x] 1.2 Creare struttura file: `main.py`, `scraper.py`, `db.py`
- [x] 1.3 Aggiungere `runts.db` a `.gitignore`
- [x] 1.4 Installare dipendenze con `pip install -r requirements.txt && playwright install chromium`

## 2. Modulo database (`db.py`)

- [x] 2.1 Implementare `init_db(db_path)`: crea il file SQLite e la tabella `enti` se non esiste, con colonne per tutti i campi attesi + `updated_at`
- [x] 2.2 Implementare `upsert_ente(conn, data)`: inserisce o aggiorna un record usando il codice fiscale come chiave univoca (`INSERT OR REPLACE`)
- [x] 2.3 Implementare `get_stats(conn)`: restituisce il conteggio totale dei record nel database

## 3. Modulo scraper — ricerca (`scraper.py`)

- [x] 3.1 Implementare `search_enti(page, denominazione)`: naviga sulla pagina di ricerca RUNTS, compila il campo DENOMINAZIONE e avvia la ricerca
- [x] 3.2 Analizzare le chiamate di rete del portale RUNTS per identificare l'endpoint API interno usato dalla ricerca
- [x] 3.3 Implementare `collect_all_results(page)`: raccoglie i link/ID di tutti gli enti nei risultati, gestendo la paginazione fino all'ultima pagina
- [x] 3.4 Loggare "Trovati N enti" al termine della raccolta

## 4. Modulo scraper — dettaglio (`scraper.py`)

- [x] 4.1 Implementare `get_detail(page, ente_ref)`: naviga alla pagina di dettaglio di un ente e attende il caricamento completo
- [x] 4.2 Implementare `extract_fields(page)`: estrae tutti i campi dalla pagina di dettaglio in un dizionario; campi assenti → `None`
- [x] 4.3 Gestire gli errori di navigazione: loggare l'errore e proseguire con il prossimo ente
- [x] 4.4 Loggare il progresso "Processato [N/TOT] <denominazione>" per ogni ente

## 5. Entry point CLI (`main.py`)

- [x] 5.1 Implementare il punto di ingresso con `argparse`: argomenti opzionali `--db` (path del database, default `runts.db`) e `--headless` (flag, default True)
- [x] 5.2 Orchestrare il flusso completo: init DB → apri browser → ricerca → raccolta risultati → loop dettagli → upsert → chiudi browser
- [x] 5.3 Stampare il report finale: inseriti / aggiornati / totale nel DB

## 6. Verifica e test manuale

- [x] 6.1 Eseguire `python main.py` e verificare che il browser navighi correttamente sul portale RUNTS
- [x] 6.2 Verificare che la ricerca per "CLUB ALPINO ITALIANO" produca risultati
- [x] 6.3 Verificare che i dettagli vengano estratti correttamente per almeno 3 enti
- [x] 6.4 Verificare che una seconda esecuzione aggiorni i record senza duplicati
- [x] 6.5 Verificare il report finale con conteggi corretti
