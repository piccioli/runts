## Context

Il portale RUNTS mostra la sede legale in una sezione dedicata con header testuale "Sede legale". I selettori attuali (`spnSedeProvincia`, `spnSedeComune`, ecc.) funzionano per alcune pagine ma non garantiscono di leggere la sezione corretta quando esistono più sezioni sede (es. sede operativa vs sede legale). Il campo `sede_regione` non è esposto direttamente dal portale ma è derivabile dal codice provincia (es. PI → Toscana).

## Goals / Non-Goals

**Goals:**
- Individuare il container DOM della sezione "Sede legale" e limitare l'estrazione a quel perimetro
- Estrarre separatamente: `sede_stato`, `sede_provincia`, `sede_comune`, `sede_indirizzo`, `sede_civico`, `sede_cap`
- Derivare `sede_regione` dal codice provincia tramite mappatura statica (fallback se non presente nel DOM)
- Aggiornare lo schema DB aggiungendo `sede_stato` e `sede_civico`; gestire DB esistenti con `ALTER TABLE ... ADD COLUMN`
- Aggiornare `detail.html` per mostrare i nuovi campi

**Non-Goals:**
- Gestire sedi operative o altre sedi alternative
- Geocodifica o normalizzazione degli indirizzi
- Modificare la logica di paginazione o navigazione

## Decisions

**Scoping DOM alla sezione "Sede legale"**
Cercare nel body text il pattern "Sede legale" per individuare il container padre, poi cercare i campi all'interno di quel container. Alternativa: continuare a usare ID globali (`spnSede*`) — scartata perché non garantisce la sezione corretta.

**JavaScript per estrazione sede legale**
Aggiungere una funzione JS dedicata `_EXTRACT_SEDE_LEGALE_JS` che:
1. Trova tutti i tag con testo "Sede legale" (label o header)
2. Risale al container padre comune
3. Estrae label/valore dei campi Stato, Provincia, Comune, Indirizzo, Civico, CAP all'interno di quel container

**Mappatura Provincia → Regione**
Dict statico `_PROVINCIA_TO_REGIONE` in `scraper.py` con tutte le 107 province italiane. Usato come fallback se `spnSedeRegione` è vuoto. Priorità: valore dal DOM > valore dalla mappatura.

**Migrazione DB**
`init_db()` esegue `ALTER TABLE enti ADD COLUMN sede_stato TEXT` e `ALTER TABLE enti ADD COLUMN sede_civico TEXT` con `IF NOT EXISTS` (supportato da SQLite ≥ 3.37). Per versioni precedenti, usa `try/except` sull'`ALTER TABLE`.

## Risks / Trade-offs

- **[Risk] Il portale cambia il markup della sezione "Sede legale"** → Mitigation: la funzione JS è isolata e facilmente aggiornabile; fallback ai selettori ID globali già esistenti
- **[Risk] Provincia non presente nel dict** → Mitigation: `sede_regione` rimane `None` senza errori, con log di avviso
