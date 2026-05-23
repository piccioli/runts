# releases/ — Documenti di specifica per rilascio

Questa cartella contiene i documenti di specifica di ogni rilascio del progetto RUNTS-CAI. Sono il ponte tra il brain dump in `../Pensieve.md` (sezione TODO) e le spec OpenSpec formali in `openspec/changes/`.

## Naming convention

| File | Convenzione | Esempio |
|---|---|---|
| Specifica `.md` | `cairunts_<NNN>.md` con zero-padding a tre cifre | `cairunts_001.md` |
| PDF in carta intestata | `cairunts_<NNN>_v<x.y>_<YYYY-MM-DD>.pdf` | `cairunts_001_v1.0_2026-05-23.pdf` |

Lo zero-padding a tre cifre garantisce ordinamento naturale nel filesystem fino al 999esimo rilascio.

Il PDF vive in `../PDF/` e viene generato a partire dal `.md` con la stessa pipeline usata per la documentazione tecnica (carta intestata Montagna Servizi, copertina, indice se necessario).

## Struttura raccomandata del documento

In testa al file conviene avere un blocco di metadati, poi le sezioni canoniche:

```markdown
# CAI-RUNTS — Release <NNN>

**Numero release**: <NNN>
**Versione**: v<x.y>
**Data**: <YYYY-MM-DD>
**Stato**: draft | proposed | approved | released
**Capability OpenSpec impattate**: <elenco>

## Sommario
Descrizione di una/due frasi.

## Motivazione (Why)
Perché vale la pena fare questo rilascio.

## Cosa cambia (What)
Elenco delle modifiche utente-visibili e tecniche.

## Requisiti funzionali
Requisiti formalizzati come "Il sistema SHALL ...".

## Requisiti non funzionali
Performance, sicurezza, vincoli operativi.

## Scenari (WHEN / THEN)
Casi di accettazione, formato compatibile con OpenSpec.

## Note di design
Decisioni architetturali, alternative considerate, trade-off.

## Allegati
Screenshot, mockup, immagini — caricati nella sottocartella `cairunts_<NNN>_assets/` accanto al .md.

## Tasks tecniche
Checklist operativa per l'implementazione (consumabile da ClaudeCode).
```

## Flusso operativo

1. Si selezionano idee dalla sezione TODO di `Pensieve.md`.
2. Si chiede a Claude di redigere `cairunts_<NNN>.md` partendo da quelle voci.
3. Si modifica il file a mano: si rifiniscono descrizioni, si aggiungono screenshot/mockup negli `_assets/`.
4. Si chiede a Claude di generare il PDF in carta intestata in `../PDF/`.
5. Si passa il `.md` a OpenSpec / ClaudeCode per la creazione del change e l'implementazione.
6. Al termine del rilascio le voci in TODO si spostano in DONE nel `Pensieve.md`, marcando la release di riferimento.
