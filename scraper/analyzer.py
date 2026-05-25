"""Offline analyzer for ETS financial statements (rendiconto gestionale DM 39/2020)."""
import argparse
import logging
import re
import sqlite3
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Each field has a list of regex patterns tried in order (first match wins).
# Supports both Rendiconto Gestionale (Mod.B) and Rendiconto di Cassa formats.
_PATTERNS: dict[str, list[str]] = {
    "oneri_a_interesse_generale": [
        # Rendiconto di cassa (subtotal row): "Totale uscite da attività di interesse generale 122.929"
        r"[Tt]otale uscite da attivit[^\n]{1,20}interesse generale\s+([\d\.,]+)",
        # Mod.B standard: "A) Costi e oneri da attività di interesse generale ... 502.912,98"
        r"A\)\s*[Cc]osti e oneri da attivit[àa] di interesse generale[\s\S]{0,500}?([\d\.\s]+,\d{2})",
    ],
    "oneri_b_attivita_diverse": [
        r"[Tt]otale uscite da attivit[\wà\.]{1,20} diverse\s+([\d\.,]+)",
        r"B\)\s*[Cc]osti e oneri da attivit[àa] diverse[\s\S]{0,500}?([\d\.\s]+,\d{2})",
    ],
    "oneri_c_raccolta_fondi": [
        r"[Tt]otale uscite da attivit[\wà\.]{1,20} di raccolta fondi\s+([\d\.,]+)",
        r"C\)\s*[Cc]osti e oneri da attivit[àa] di raccolta fondi[\s\S]{0,500}?([\d\.\s]+,\d{2})",
    ],
    "oneri_d_finanziarie_patrimoniali": [
        r"[Tt]otale uscite da attivit[\wà\.]{1,20} finanziarie e patrimoniali\s+([\d\.,]+)",
        r"D\)\s*[Cc]osti e oneri da attivit[àa] finanziarie e patrimoniali[\s\S]{0,500}?([\d\.\s]+,\d{2})",
    ],
    "oneri_e_supporto_generale": [
        r"[Tt]otale uscite di supporto generale\s+([\d\.,]+)",
        r"E\)\s*[Cc]osti e oneri di supporto generale[\s\S]{0,500}?([\d\.\s]+,\d{2})",
    ],
    "totale_oneri": [
        r"[Tt]otale uscite della gestione\s+([\d\.,]+)",
        r"[Tt]otale [Oo]neri e [Cc]osti(?!\s*x\s*1)[\s\S]{0,200}?([\d\.\s]+,\d{2})",
    ],
    "proventi_a_interesse_generale": [
        r"[Tt]otale entrate da attivit[^\n]{1,20}interesse generale\s+([\d\.,]+)",
        r"A\)\s*[Rr]icavi[,\s].*?proventi da attivit[àa] di interesse generale[\s\S]{0,500}?([\d\.\s]+,\d{2})",
    ],
    "proventi_b_attivita_diverse": [
        r"[Tt]otale entrate da attivit[\wà\.]{1,20} diverse\s+([\d\.,]+)",
        r"B\)\s*[Rr]icavi[,\s].*?proventi da attivit[àa] diverse[\s\S]{0,500}?([\d\.\s]+,\d{2})",
    ],
    "proventi_c_raccolta_fondi": [
        r"[Tt]otale entrate da attivit[\wà\.]{1,20} di raccolta fondi\s+([\d\.,]+)",
        r"C\)\s*[Rr]icavi e proventi da attivit[àa] di raccolta fondi[\s\S]{0,500}?([\d\.\s]+,\d{2})",
    ],
    "proventi_d_finanziarie_patrimoniali": [
        r"[Tt]otale entrate da attivit[\wà\.]{1,20} finanziarie e patrimoniali\s+([\d\.,]+)",
        r"D\)\s*[Rr]icavi e proventi da attivit[àa] finanziarie e patrimoniali[\s\S]{0,500}?([\d\.\s]+,\d{2})",
    ],
    "proventi_e_supporto_generale": [
        r"[Tt]otale entrate di supporto generale\s+([\d\.,]+)",
        r"E\)\s*[Pp]roventi di supporto generale[\s\S]{0,500}?([\d\.\s]+,\d{2})",
    ],
    "totale_proventi": [
        r"[Tt]otale entrate della gestione\s+([\d\.,]+)",
        r"[Tt]otale [Pp]roventi e [Rr]icavi(?!\s*x\s*1)[\s\S]{0,200}?([\d\.\s]+,\d{2})",
    ],
    "risultato_ante_imposte": [
        r"[Aa]vanzo/disavanzo d.esercizio prima delle imposte[^0-9]+([\d\.,]+)",
        r"(?:[Dd]isavanzo|[Aa]vanzo)\s+(?:prima|ante)\s+(?:delle\s+)?imposte[\s\S]{0,200}?([\d\.\s]+,\d{2})",
    ],
    "imposte": [
        r"\bImposte\s+([\d\.,]+)",
    ],
    "risultato_esercizio": [
        r"[Aa]vanzo/disavanzo complessivo[^0-9]+([\d\.,]+)",
        r"(?:[Dd]isavanzo|[Aa]vanzo)\s+(?:dopo|netto)\s+(?:le\s+)?imposte[\s\S]{0,200}?([\d\.\s]+,\d{2})",
    ],
}

_ONERI_SUBTOTALS = [
    "oneri_a_interesse_generale", "oneri_b_attivita_diverse",
    "oneri_c_raccolta_fondi", "oneri_d_finanziarie_patrimoniali",
    "oneri_e_supporto_generale",
]
_PROVENTI_SUBTOTALS = [
    "proventi_a_interesse_generale", "proventi_b_attivita_diverse",
    "proventi_c_raccolta_fondi", "proventi_d_finanziarie_patrimoniali",
    "proventi_e_supporto_generale",
]


def parse_italian_number(s: str) -> float | None:
    """Parse Italian-formatted number. Supports: '1.234,56', '1 234,56', '1\'234,56', '122929', '122.929'."""
    if not s:
        return None
    s = s.strip()
    # Remove spaces, apostrophes (thousands separator)
    s = re.sub(r"[\s ’']", "", s)
    # Italian: dot = thousands, comma = decimal
    if "," in s:
        # Remove dot thousands separators, replace comma decimal
        s = s.replace(".", "").replace(",", ".")
    else:
        # No comma: dot could be thousands sep (e.g. '122.929') or decimal ('122.9')
        parts = s.split(".")
        if len(parts) == 2 and len(parts[1]) == 3:
            # '122.929' → thousands sep, no decimals
            s = s.replace(".", "")
        # else leave as-is (plain float like '122929')
    try:
        return float(s)
    except ValueError:
        return None


def extract_bilancio_pdf(path: str) -> dict:
    """Extract 13 ETS financial fields from a PDF. Returns dict with field→float|None."""
    import pdfplumber

    result: dict[str, float | None] = {k: None for k in _PATTERNS}
    raw_text = ""

    try:
        with pdfplumber.open(path) as pdf:
            pages_text = []
            for page in pdf.pages:
                txt = page.extract_text(layout=True) or ""
                pages_text.append(txt)
            raw_text = "\n".join(pages_text)
    except Exception as exc:
        logger.warning("Errore apertura PDF %s: %s", path, exc)
        return {**result, "_raw_text": ""}

    for field, patterns in _PATTERNS.items():
        for pattern in patterns:
            m = re.search(pattern, raw_text, re.IGNORECASE | re.DOTALL)
            if m:
                candidate = m.group(1).strip()
                value = parse_italian_number(candidate)
                if value is not None:
                    result[field] = value
                    break

    result["_raw_text"] = raw_text[:50000]
    return result


def _check_coherence(result: dict, subtotals: list[str], total_key: str) -> None:
    if result.get(total_key) is None:
        return
    if any(result.get(k) is None for k in subtotals):
        return
    computed = sum(result[k] for k in subtotals)
    declared = result[total_key]
    if abs(computed - declared) > 0.01:
        logger.warning(
            "Incoerenza %s: somma A-E = %.2f, totale = %.2f (diff %.2f)",
            total_key, computed, declared, abs(computed - declared),
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analizza i bilanci ETS scaricati e ne estrae i totali finanziari."
    )
    parser.add_argument("--db", default="runts.db", metavar="PATH")
    parser.add_argument("--id-runts", metavar="ID", help="Analizza solo l'ente specificato")
    parser.add_argument("--force", action="store_true", help="Ri-analizza anche i bilanci già analizzati")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    where_clauses = ["a.tipo IN ('bilancio_esercizio', 'situazione_patrimoniale')", "a.path IS NOT NULL", "a.anno IS NOT NULL"]
    params: list = []

    if args.id_runts:
        where_clauses.append("a.id_runts = ?")
        params.append(args.id_runts)

    if not args.force:
        where_clauses.append(
            "NOT EXISTS (SELECT 1 FROM bilanci b WHERE b.id_runts = a.id_runts AND b.allegato_id = a.id)"
        )

    where_sql = " AND ".join(where_clauses)
    allegati = conn.execute(
        f"SELECT a.id, a.id_runts, a.anno, a.path FROM allegati a WHERE {where_sql}",
        params,
    ).fetchall()

    logger.info("Allegati da analizzare: %d", len(allegati))

    success = partial = failed = 0

    from .db import upsert_bilancio

    for row in allegati:
        path_rel = row["path"]
        path = Path(path_rel)
        if not path.exists():
            logger.warning("File non trovato: %s", path)
            failed += 1
            continue

        result = extract_bilancio_pdf(str(path))
        _check_coherence(result, _ONERI_SUBTOTALS, "totale_oneri")
        _check_coherence(result, _PROVENTI_SUBTOTALS, "totale_proventi")

        raw_text = result.pop("_raw_text", "")
        numeric_fields = [k for k in result if result[k] is not None]

        data = {
            "id_runts": row["id_runts"],
            "anno": row["anno"],
            "raw_text": raw_text,
            "allegato_id": row["id"],
            **result,
        }

        try:
            upsert_bilancio(conn, data)
        except Exception as exc:
            logger.error("Errore upsert bilancio %s anno %s: %s", row["id_runts"], row["anno"], exc)
            failed += 1
            continue

        if numeric_fields:
            logger.info("✓ %s anno %s — %d campi estratti", row["id_runts"], row["anno"], len(numeric_fields))
            success += 1
        else:
            logger.info("~ %s anno %s — solo raw_text (nessun campo numerico)", row["id_runts"], row["anno"])
            partial += 1

    conn.close()

    print()
    print("=" * 50)
    print("  REPORT ANALYZER BILANCI")
    print("=" * 50)
    print(f"  Analizzati con successo  : {success}")
    print(f"  Parziali (solo raw_text) : {partial}")
    print(f"  Falliti                  : {failed}")
    print("=" * 50)


if __name__ == "__main__":
    main()
