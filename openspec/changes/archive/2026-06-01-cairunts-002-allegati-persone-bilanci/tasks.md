## 1. Database — nuove tabelle e indici

- [x] 1.1 In `scraper/db.py`, aggiungere `CREATE TABLE IF NOT EXISTS allegati (...)` allo schema canonico e a `_MIGRATIONS` (con tutti i campi: id, id_runts, documento, codice_pratica, tipo, anno, filename, path, mime, size, hash_sha256, url_originale, skip_reason, downloaded_at; UNIQUE su (id_runts, hash_sha256))
- [x] 1.2 Aggiungere `CREATE TABLE IF NOT EXISTS bilanci (...)` con le 13 voci REAL del rendiconto ETS, raw_text, allegato_id, analyzed_at; UNIQUE su (id_runts, anno)
- [x] 1.3 Aggiungere `CREATE TABLE IF NOT EXISTS cariche_sociali (...)` con ruolo, nome, cognome, codice_fiscale, valid_from, valid_to, updated_at; UNIQUE su (id_runts, codice_fiscale, ruolo, valid_from)
- [x] 1.4 Aggiungere gli indici: `idx_allegati_id_runts`, `idx_allegati_tipo`, `idx_allegati_codice_pratica`, `idx_bilanci_id_runts`, `idx_cariche_id_runts`, `idx_cariche_attive` su (id_runts, valid_to)

## 2. Database — funzioni di persistenza

- [x] 2.1 Implementare `upsert_allegato(conn, data) -> str` in `scraper/db.py` con upsert su `(id_runts, hash_sha256)`; ritorna `"inserted"` o `"cache_hit"`
- [x] 2.2 Implementare `upsert_bilancio(conn, data)` in `scraper/db.py` con upsert su `(id_runts, anno)`
- [x] 2.3 Implementare `sync_cariche(conn, id_runts, cariche_new)` in `scraper/db.py`: chiude le cariche attive non più presenti (valid_to = oggi), inserisce quelle nuove, lascia invariate quelle corrispondenti

## 3. Scraper — estrazione atti e documenti

- [x] 3.1 Aggiungere `httpx>=0.27` a `scraper/requirements.txt`
- [x] 3.2 In `scraper/scraper.py`, implementare `extract_atti_documenti(page) -> list[dict]` che individua la sezione "Atti e documenti" RUNTS e legge la tabella (documento, codice_pratica, anno, url)
- [x] 3.3 Implementare `classify_codice_pratica(codice_pratica: str) -> str` con la mappa ufficiale (B00→bilancio_esercizio, B03→situazione_patrimoniale, B08→bilancio_sociale, C01→atto_costitutivo, C02→statuto, D00→dichiarazione, E32→provvedimento_autorita, R06→relazione_controllo, PROVISC→provvedimento_iscrizione, 99→altro); fallback su `"altro"`

## 4. Scraper — download allegati

- [x] 4.1 Creare `scraper/downloader.py` con funzione async `download_attachments(client, id_runts, attachments, dest_dir, max_size_mb=50) -> dict` che scarica i file, calcola SHA-256, normalizza i filename (con suffisso progressivo per collisioni), gestisce skip per dimensione
- [x] 4.2 Integrare il download nel main loop di `scraper/scraper.py`: dopo `upsert_ente`, chiamare `extract_atti_documenti` + `download_attachments` + `upsert_allegato` per ogni risultato
- [x] 4.3 Estendere il report finale di `scraper/main.py` con: allegati scoperti, scaricati, cache_hit, saltati per dimensione, falliti

## 5. Scraper — cariche sociali

- [x] 5.1 In `scraper/scraper.py`, implementare `extract_cariche(page) -> list[dict]` che legge la sezione "Organi sociali" RUNTS e restituisce lista di dict {ruolo, nome, cognome, codice_fiscale, valid_from, valid_to}
- [x] 5.2 Implementare `normalize_ruolo(ruolo_raw: str) -> str` con la mappa di normalizzazione verso i ruoli canonici (presidente, vicepresidente, consigliere, segretario, tesoriere, revisore, altro)
- [x] 5.3 Integrare l'estrazione cariche nel main loop: dopo `upsert_ente`, chiamare `extract_cariche` + `sync_cariche`
- [x] 5.4 Mantenere il popolamento di `enti.rappresentante_legale` con il nome del presidente corrente estratto

## 6. Analyzer — modulo bilanci

- [x] 6.1 Aggiungere `pdfplumber>=0.11` a `scraper/requirements.txt`
- [x] 6.2 Creare `scraper/analyzer.py` con CLI argparse: `--db`, `--id-runts`, `--force`, `--verbose`
- [x] 6.3 Implementare `parse_italian_number(s: str) -> float | None` che gestisce: "1.234,56", "1 234,56", "1'234,56", "122929", "122.929,00"
- [x] 6.4 Implementare `extract_bilancio_pdf(path: str) -> dict` che usa `pdfplumber.extract_text(layout=True)` e regex ancorati per le 13 voci del rendiconto ETS; cattura sempre il primo valore numerico dopo l'ancora di riga (anno corrente vs. precedente); campi non trovati = None
- [x] 6.5 Aggiungere il controllo di coerenza: se totale_oneri e voci A-E sono tutti valorizzati, verificare che la somma A+B+C+D+E ≈ totale (tolleranza 0,01 €); stessa verifica per proventi; loggare WARNING in caso di scostamento
- [x] 6.6 Implementare il main loop dell'analyzer: SELECT allegati con tipo IN ('bilancio_esercizio', 'situazione_patrimoniale') AND (bilanci non presenti OR --force); per ciascuno estrarre e upsertare
- [x] 6.7 Implementare il report finale: analizzati con successo (≥1 campo valorizzato), parziali (solo raw_text), falliti

## 7. Test analyzer

- [x] 7.1 Creare `scraper/test_analyzer.py` con `test_extract_bilancio_pisa_2024`: usa `scraper/test_data/bilanci/Bilancio_Pisa_2024.pdf`, verifica i 15 valori attesi entro tolleranza 0,01 €
- [x] 7.2 Aggiungere `test_extract_bilancio_parma_2025`: usa `scraper/test_data/bilanci/Bilancio_Parma_2025.pdf`, verifica i 15 valori attesi entro tolleranza 0,01 €
- [x] 7.3 Aggiungere test `test_parse_italian_number` che copre i 5 formati: punto migliaia + virgola decimale, spazio migliaia, apostrofo migliaia, intero senza separatori, intero con punto migliaia

## 8. Web app — visualizzazione scheda ente

- [x] 8.1 In `web/app.py`, route `/ente/{id_runts}`: aggiungere SELECT su `allegati` (ORDER BY codice_pratica, anno), `bilanci` (ORDER BY anno DESC), `cariche_sociali` (ORDER BY valid_to IS NULL DESC, ruolo)
- [x] 8.2 Aggiungere Jinja filter `mask_cf(cf)` che restituisce `XXX•••••12345` (primi 3 + punti + ultimi 5) e `human_size(bytes)` che restituisce "123 KB" o "1.2 MB"
- [x] 8.3 Montare `/attachments` come `StaticFiles(directory="/app/attachments", check_dir=False)` in `web/app.py`
- [x] 8.4 In `web/templates/detail.html`, aggiungere sezione "Atti e documenti": tabella con tipo, codice pratica, anno, dimensione, link download locale, link RUNTS originale; omessa se lista vuota
- [x] 8.5 Aggiungere sezione "Indicatori di bilancio": tabella con anno, totale proventi, totale oneri, risultato; valori NULL = "—"; omessa se lista vuota
- [x] 8.6 Aggiungere sezione "Persone e cariche": lista cariche attive in cima, storiche in coda; CF mascherato con filter mask_cf; omessa se lista vuota
- [x] 8.7 Aggiornare `docker-compose.yml` aggiungendo `- ./attachments:/app/attachments:ro` ai volumes

## 9. PDF scheda ente esteso

- [x] 9.1 In `web/pdf_utils.py`, aggiungere funzione `_build_allegati_section(allegati, styles)` che genera flowable reportlab per la sezione "Atti e documenti" (tabella tipo, anno, dimensione, link RUNTS)
- [x] 9.2 Aggiungere `_build_bilanci_section(bilanci, styles)` che genera tabella anni con totale proventi, oneri, risultato; valori None = "—"
- [x] 9.3 Aggiungere `_build_cariche_section(cariche, styles)` che genera lista cariche attive + storiche con ruolo, nome, cognome, periodo
- [x] 9.4 Modificare firma `build_ente_pdf(ente_row, allegati=None, bilanci=None, cariche=None) -> bytes`; aggiungere le sezioni alla story solo se la lista è non vuota
- [x] 9.5 Aggiornare route `/ente/{id_runts}/pdf` in `web/app.py` per passare le liste allegati, bilanci, cariche al generatore PDF

## 10. Verifiche

- [x] 10.1 Eseguire `pytest scraper/test_analyzer.py -v` e verificare che i tre test (Pisa 2024, Parma 2025, parse_italian_number) passino
- [x] 10.2 Eseguire lo scraper su CAI Pisa (`id_runts=83894`): verificare 8 allegati scaricati in `attachments/83894/`, deduplicati per hash, con i tre B00 del 2023 disambiguati per filename
- [x] 10.3 Eseguire `python -m scraper.analyzer --db runts.db --id-runts 83894` e verificare le righe in `bilanci` per gli anni 2021-2024; per anno 2024 i valori devono coincidere con gli attesi (tolleranza 0,01 €)
- [x] 10.4 Eseguire lo scraper su CAI Parma: verificare ~22 allegati con i 10 codici pratica diversi in `allegati`; eseguire analyzer e verificare righe bilanci 2021-2024
- [x] 10.5 Rieseguire lo scraper su entrambi gli enti: nessun file riscaricato (cache_hit = totale allegati)
- [x] 10.6 Aprire la scheda web di Pisa e Parma: verificare che le tre sezioni (allegati, bilanci, cariche) appaiano con dati coerenti
- [x] 10.7 Scaricare i PDF di Pisa e Parma: verificare che contengano le tre sezioni aggiuntive con carta intestata su tutte le pagine
- [x] 10.8 Verificare che un ente senza documenti non mostri titoli di sezione orfani nella scheda web né nel PDF
