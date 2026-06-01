## ADDED Requirements

### Requirement: Tabella allegati per i documenti RUNTS
Il sistema SHALL creare la tabella `allegati` tramite migrazione idempotente (`CREATE TABLE IF NOT EXISTS`) con i campi: `id`, `id_runts`, `documento`, `codice_pratica`, `tipo`, `anno`, `filename`, `path`, `mime`, `size`, `hash_sha256`, `url_originale`, `skip_reason`, `downloaded_at`; vincolo UNIQUE su `(id_runts, hash_sha256)`; indici `idx_allegati_id_runts`, `idx_allegati_tipo`, `idx_allegati_codice_pratica`.

#### Scenario: Creazione tabella allegati su DB vuoto
- **WHEN** il database viene inizializzato per la prima volta
- **THEN** la tabella `allegati` con tutti i campi e i tre indici è presente

#### Scenario: Migrazione DB esistente
- **WHEN** la migrazione viene eseguita su un DB che non ha ancora la tabella `allegati`
- **THEN** la tabella e gli indici vengono creati senza errori e senza alterare i dati esistenti

### Requirement: Tabella bilanci per i rendiconti gestionali ETS
Il sistema SHALL creare la tabella `bilanci` tramite migrazione idempotente con i campi: `id`, `id_runts`, `anno`, le 13 voci numeriche REAL del rendiconto (5 oneri A-E + totale, 5 proventi A-E + totale, 3 risultato), `raw_text`, `allegato_id`, `analyzed_at`; vincolo UNIQUE su `(id_runts, anno)`; indice `idx_bilanci_id_runts`.

#### Scenario: Creazione tabella bilanci
- **WHEN** il database viene inizializzato o migrato
- **THEN** la tabella `bilanci` con tutti i campi REAL e il vincolo UNIQUE su `(id_runts, anno)` è presente

#### Scenario: Upsert bilancio stesso anno
- **WHEN** l'analyzer inserisce un bilancio per `(id_runts, anno)` già presente
- **THEN** il record esistente viene aggiornato senza duplicati

### Requirement: Tabella cariche_sociali per gli organi sociali
Il sistema SHALL creare la tabella `cariche_sociali` tramite migrazione idempotente con i campi: `id`, `id_runts`, `ruolo`, `nome`, `cognome`, `codice_fiscale`, `valid_from`, `valid_to`, `updated_at`; vincolo UNIQUE su `(id_runts, codice_fiscale, ruolo, valid_from)`; indici `idx_cariche_id_runts`, `idx_cariche_attive` su `(id_runts, valid_to)`.

#### Scenario: Creazione tabella cariche_sociali
- **WHEN** il database viene inizializzato o migrato
- **THEN** la tabella `cariche_sociali` con vincolo UNIQUE e i due indici è presente

#### Scenario: Query cariche attive ottimizzata
- **WHEN** si esegue `SELECT * FROM cariche_sociali WHERE id_runts = ? AND valid_to IS NULL`
- **THEN** il piano di query usa `idx_cariche_attive`
