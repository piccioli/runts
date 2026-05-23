## ADDED Requirements

### Requirement: Tabella geocoding_cache nel database
Il sistema SHALL creare la tabella `geocoding_cache` in `runts.db` tramite migrazione idempotente.

#### Scenario: Prima inizializzazione
- **WHEN** il database viene inizializzato e la tabella non esiste
- **THEN** il sistema crea `geocoding_cache(cache_key TEXT PRIMARY KEY, lat REAL NOT NULL, lon REAL NOT NULL, source TEXT NOT NULL, ts TEXT NOT NULL)` senza errori

#### Scenario: Database esistente senza tabella cache
- **WHEN** il database esiste già ma la tabella `geocoding_cache` è assente
- **THEN** la migrazione aggiunge la tabella senza perdita di dati esistenti

### Requirement: Lookup della cache prima di Nominatim
Il geocoder SHALL verificare la presenza della `cache_key` corrente in `geocoding_cache` prima di eseguire qualsiasi chiamata HTTP a Nominatim.

#### Scenario: Cache hit
- **WHEN** due enti hanno stessa terna `(comune, provincia, regione)` e il primo è già stato geocodificato
- **THEN** il secondo viene risolto da `geocoding_cache` senza chiamata HTTP; il report incrementa il contatore `from_cache`

#### Scenario: Cache miss
- **WHEN** la `cache_key` dell'ente corrente non è presente in `geocoding_cache`
- **THEN** il geocoder procede con la chiamata Nominatim

### Requirement: Scrittura della cache dopo successo Nominatim
Il geocoder SHALL inserire una riga in `geocoding_cache` ogni volta che Nominatim restituisce coordinate con successo.

#### Scenario: Inserimento in cache dopo Nominatim
- **WHEN** Nominatim restituisce `lat` e `lon` per un ente
- **THEN** il geocoder esegue `INSERT OR REPLACE INTO geocoding_cache` con `source='nominatim'` e `ts` in formato ISO UTC; il report incrementa il contatore `from_nominatim`

### Requirement: Normalizzazione della cache key
La `cache_key` SHALL essere costruita in modo robusto a variazioni di maiuscole/minuscole e spazi.

#### Scenario: Chiave normalizzata
- **WHEN** due enti hanno comune "PISA" e "Pisa" rispettivamente
- **THEN** entrambi producono la stessa `cache_key` e il secondo beneficia della cache hit del primo
