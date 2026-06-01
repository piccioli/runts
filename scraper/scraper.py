import asyncio
import json
import logging
import re

from playwright.async_api import Page, async_playwright

logger = logging.getLogger(__name__)

SEARCH_URL = "https://servizi.lavoro.gov.it/runts/it-it/Ricerca-enti"
DETAIL_URL_PATTERN = "**/Ricerca-enti/Ente*"

# IDs present on the detail page (sede fields handled by _EXTRACT_SEDE_LEGALE_JS)
_DETAIL_IDS = {
    "id_runts":       "spnRepertorio",
    "codice_fiscale": "spnCodiceFiscale",
    "pec":            "spnEmailPec",
    "sito_web":       "spnSitoInternet",
}

_PROVINCIA_TO_REGIONE: dict[str, str] = {
    # Valle d'Aosta
    "AO": "Valle d'Aosta",
    # Piemonte
    "AL": "Piemonte", "AT": "Piemonte", "BI": "Piemonte", "CN": "Piemonte",
    "NO": "Piemonte", "TO": "Piemonte", "VB": "Piemonte", "VC": "Piemonte",
    # Liguria
    "GE": "Liguria", "IM": "Liguria", "SP": "Liguria", "SV": "Liguria",
    # Lombardia
    "BG": "Lombardia", "BS": "Lombardia", "CO": "Lombardia", "CR": "Lombardia",
    "LC": "Lombardia", "LO": "Lombardia", "MB": "Lombardia", "MI": "Lombardia",
    "MN": "Lombardia", "PV": "Lombardia", "SO": "Lombardia", "VA": "Lombardia",
    # Trentino-Alto Adige
    "BZ": "Trentino-Alto Adige", "TN": "Trentino-Alto Adige",
    # Veneto
    "BL": "Veneto", "PD": "Veneto", "RO": "Veneto", "TV": "Veneto",
    "VE": "Veneto", "VI": "Veneto", "VR": "Veneto",
    # Friuli-Venezia Giulia
    "GO": "Friuli-Venezia Giulia", "PN": "Friuli-Venezia Giulia",
    "TS": "Friuli-Venezia Giulia", "UD": "Friuli-Venezia Giulia",
    # Emilia-Romagna
    "BO": "Emilia-Romagna", "FE": "Emilia-Romagna", "FC": "Emilia-Romagna",
    "MO": "Emilia-Romagna", "PR": "Emilia-Romagna", "PC": "Emilia-Romagna",
    "RA": "Emilia-Romagna", "RE": "Emilia-Romagna", "RN": "Emilia-Romagna",
    # Toscana
    "AR": "Toscana", "FI": "Toscana", "GR": "Toscana", "LI": "Toscana",
    "LU": "Toscana", "MS": "Toscana", "PI": "Toscana", "PT": "Toscana",
    "PO": "Toscana", "SI": "Toscana",
    # Umbria
    "PG": "Umbria", "TR": "Umbria",
    # Marche
    "AN": "Marche", "AP": "Marche", "FM": "Marche", "MC": "Marche", "PU": "Marche",
    # Lazio
    "FR": "Lazio", "LT": "Lazio", "RI": "Lazio", "RM": "Lazio", "VT": "Lazio",
    # Abruzzo
    "AQ": "Abruzzo", "CH": "Abruzzo", "PE": "Abruzzo", "TE": "Abruzzo",
    # Molise
    "CB": "Molise", "IS": "Molise",
    # Campania
    "AV": "Campania", "BN": "Campania", "CE": "Campania", "NA": "Campania", "SA": "Campania",
    # Puglia
    "BA": "Puglia", "BT": "Puglia", "BR": "Puglia", "FG": "Puglia",
    "LE": "Puglia", "TA": "Puglia",
    # Basilicata
    "MT": "Basilicata", "PZ": "Basilicata",
    # Calabria
    "CZ": "Calabria", "CS": "Calabria", "KR": "Calabria", "RC": "Calabria", "VV": "Calabria",
    # Sicilia
    "AG": "Sicilia", "CL": "Sicilia", "CT": "Sicilia", "EN": "Sicilia",
    "ME": "Sicilia", "PA": "Sicilia", "RG": "Sicilia", "SR": "Sicilia", "TP": "Sicilia",
    # Sardegna
    "CA": "Sardegna", "CI": "Sardegna", "MD": "Sardegna", "NU": "Sardegna",
    "OG": "Sardegna", "OR": "Sardegna", "OT": "Sardegna", "SS": "Sardegna",
    "SU": "Sardegna", "VS": "Sardegna",
}

# Extracts sede legale fields from the divSedeLegale container (IDs use SL suffix).
_EXTRACT_SEDE_LEGALE_JS = """
() => {
    const result = {};
    const container = document.querySelector('[id*="divSedeLegale"]');
    const scope = container || document;
    const fields = {
        'stato':     '[id*="spnStatoSL"]',
        'provincia': '[id*="spnProvinciaSL"]',
        'comune':    '[id*="spnComuneSL"]',
        'indirizzo': '[id*="spnIndirizzoSL"]',
        'civico':    '[id*="spnCivicoSL"]',
        'cap':       '[id*="spnCAP_SL"]',
        'regione':   '[id*="spnRegioneSL"]',
    };
    for (const [key, sel] of Object.entries(fields)) {
        const el = scope.querySelector(sel);
        if (el) { const v = el.innerText.trim(); if (v) result[key] = v; }
    }
    return result;
}
"""

_EXTRACT_BOLD_JS = """
() => {
    const out = {};
    document.querySelectorAll('.ente_bold').forEach(el => {
        const label = el.innerText.replace(':', '').trim();
        if (!label || label.length > 100) return;
        const parent = el.parentElement;
        const valueEl = parent.querySelector('[class*="ente_testo"]:not(.ente_bold)');
        if (valueEl) {
            const val = valueEl.innerText.trim();
            if (val) out[label] = val;
        }
    });
    return out;
}
"""


_CODICE_PRATICA_MAP: dict[str, str] = {
    "B00": "bilancio_esercizio",
    "B03": "situazione_patrimoniale",
    "B08": "bilancio_sociale",
    "C01": "atto_costitutivo",
    "C02": "statuto",
    "D00": "dichiarazione",
    "E32": "provvedimento_autorita",
    "R06": "relazione_controllo",
    "PROVISC": "provvedimento_iscrizione",
    "99": "altro",
}

_RUOLO_MAP: dict[str, str] = {
    "presidente": "presidente",
    "vice presidente": "vicepresidente",
    "vicepresidente": "vicepresidente",
    "consigliere": "consigliere",
    "segretario": "segretario",
    "tesoriere": "tesoriere",
    "revisore": "revisore",
    "revisore dei conti": "revisore",
    "organo di controllo": "revisore",
}


def classify_codice_pratica(codice_pratica: str) -> str:
    return _CODICE_PRATICA_MAP.get(codice_pratica.strip().upper(), "altro")


def normalize_ruolo(ruolo_raw: str) -> str:
    key = ruolo_raw.lower().strip()
    for pattern, canonical in _RUOLO_MAP.items():
        if pattern in key:
            return canonical
    return "altro"


async def extract_atti_documenti(page: Page) -> list[dict]:
    """Extract the 'Atti e documenti' table from the RUNTS detail page."""
    try:
        # Find the heading containing "Atti e documenti"
        heading = page.locator('text="Atti e documenti"').first
        if await heading.count() == 0:
            return []

        # Find the nearest table sibling/descendant after the heading
        table = page.locator('table').filter(has=page.locator('text="Codice pratica"')).first
        if await table.count() == 0:
            return []

        rows = await table.locator("tbody tr").all()
        results = []
        for row in rows:
            cells = await row.locator("td").all()
            if len(cells) < 4:
                continue

            documento = (await cells[0].inner_text()).strip()
            codice_pratica = (await cells[1].inner_text()).strip()
            data_text = (await cells[2].inner_text()).strip()

            anno = None
            if data_text and data_text.isdigit():
                anno = int(data_text)

            if documento and codice_pratica:
                results.append({
                    "documento": documento,
                    "codice_pratica": codice_pratica,
                    "tipo": classify_codice_pratica(codice_pratica),
                    "anno": anno,
                    "url": None,
                    "_row_index": len(results),
                })
        return results
    except Exception as exc:
        logger.debug("extract_atti_documenti error: %s", exc)
        return []


def _strip_p7m(path: "Path") -> "Path":
    """Extract the inner file from a CAdES .p7m envelope using OpenSSL.

    Returns the new path (without .p7m extension). Deletes the original .p7m.
    Raises subprocess.CalledProcessError if OpenSSL fails.
    """
    import subprocess
    from pathlib import Path as _Path

    path = _Path(path)
    if path.suffix.lower() != ".p7m":
        return path

    out_path = _Path(str(path)[:-4])  # remove .p7m
    subprocess.run(
        ["openssl", "cms", "-verify", "-noverify", "-inform", "DER",
         "-in", str(path), "-out", str(out_path)],
        check=True,
        capture_output=True,
    )
    path.unlink()
    return out_path


async def _playwright_download_allegati(
    page: Page,
    allegati: list[dict],
    dest_dir: "Path",
) -> list[dict]:
    """Click each download button on the RUNTS detail page and save the file.

    RUNTS uses ASP.NET WebForms image-buttons — there is no downloadable URL;
    we must use the active Playwright session to trigger the form POST.
    """
    import hashlib
    from pathlib import Path as _Path

    dest_dir = _Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    enriched: list[dict] = []
    used_names: set[str] = set()

    for att in allegati:
        idx = att.get("_row_index", 0)
        selector = f'input[id*="gvAttiDocumenti_btnDownload_{idx}"]'

        btn = page.locator(selector).first
        if await btn.count() == 0:
            enriched.append({**att, "skip_reason": "no_button"})
            logger.warning("Download button non trovato: row %d", idx)
            continue

        try:
            async with page.expect_download(timeout=30000) as dl_info:
                await btn.click()
            download = await dl_info.value

            suggested = download.suggested_filename or f"allegato_{idx}.pdf"
            base_name = f"{att.get('codice_pratica','XX')}_{att.get('anno') or 'nd'}_{suggested}"

            # Save to a hidden temp file that preserves the extension (needed for .p7m check)
            tmp_path = dest_dir / f".dl_{idx}_{base_name}"
            await download.save_as(str(tmp_path))

            # Unwrap CAdES .p7m envelope → plain PDF
            if tmp_path.suffix.lower() == ".p7m":
                try:
                    tmp_path = _strip_p7m(tmp_path)
                    base_name = _Path(base_name).stem  # drop .p7m, keep stem
                    logger.info("  Estratto da .p7m → %s", base_name)
                except Exception as exc:
                    logger.warning("  Conversione .p7m fallita per %s: %s", base_name, exc)

            new_size = tmp_path.stat().st_size
            hasher = hashlib.sha256()
            with open(tmp_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    hasher.update(chunk)
            new_hash = hasher.hexdigest()

            # If base_name already on disk with identical content → reuse, skip copy
            base_path = dest_dir / base_name
            if base_path.exists() and base_name not in used_names:
                existing_hasher = hashlib.sha256()
                with open(base_path, "rb") as f:
                    for chunk in iter(lambda: f.read(65536), b""):
                        existing_hasher.update(chunk)
                if existing_hasher.hexdigest() == new_hash:
                    tmp_path.unlink(missing_ok=True)
                    used_names.add(base_name)
                    enriched.append({
                        **att,
                        "filename": base_name,
                        "path": str(base_path),
                        "size": new_size,
                        "hash_sha256": new_hash,
                        "mime": "application/pdf",
                        "url_originale": None,
                    })
                    logger.info("↓ Cache hit (disco): %s", base_name)
                    continue

            # Determine final filename, handle within-batch collisions
            filename = base_name
            counter = 2
            while filename in used_names or (dest_dir / filename).exists():
                filename = f"{base_name.rsplit('.', 1)[0]}_{counter}.{base_name.rsplit('.', 1)[1]}" if "." in base_name else f"{base_name}_{counter}"
                counter += 1
            used_names.add(filename)
            save_path = dest_dir / filename
            tmp_path.rename(save_path)

            enriched.append({
                **att,
                "filename": filename,
                "path": str(save_path),
                "size": new_size,
                "hash_sha256": new_hash,
                "mime": "application/pdf",
                "url_originale": None,
            })
            logger.info("↓ Scaricato: %s", filename)
        except Exception as exc:
            logger.warning("Download fallito per allegato row %d (%s/%s): %s", idx, att.get("codice_pratica"), att.get("anno"), exc)
            enriched.append({**att, "skip_reason": "download_error"})

    return enriched


async def extract_cariche(page: Page) -> list[dict]:
    """Extract 'Organi sociali' entries from the RUNTS detail page."""
    try:
        section = page.locator('text="Organi sociali"').first
        if await section.count() == 0:
            return []

        table = page.locator('table').filter(has=page.locator('text="Ruolo"')).first
        if await table.count() == 0:
            return []

        rows = await table.locator("tbody tr").all()
        results = []
        for row in rows:
            cells = await row.locator("td").all()
            if len(cells) < 3:
                continue

            # Typical columns: Ruolo | Nome | Cognome | CF | Dal | Al
            ruolo_raw = (await cells[0].inner_text()).strip()
            nome = (await cells[1].inner_text()).strip() if len(cells) > 1 else None
            cognome = (await cells[2].inner_text()).strip() if len(cells) > 2 else None
            cf = (await cells[3].inner_text()).strip() if len(cells) > 3 else None
            valid_from = (await cells[4].inner_text()).strip() if len(cells) > 4 else None
            valid_to_raw = (await cells[5].inner_text()).strip() if len(cells) > 5 else None

            if not ruolo_raw:
                continue

            results.append({
                "ruolo": normalize_ruolo(ruolo_raw),
                "nome": nome or None,
                "cognome": cognome or None,
                "codice_fiscale": cf or None,
                "valid_from": valid_from or None,
                "valid_to": valid_to_raw or None,
            })
        return results
    except Exception as exc:
        logger.debug("extract_cariche error: %s", exc)
        return []


async def search_enti(page: Page, denominazione: str, codice_fiscale: str | None = None) -> None:
    """Navigate to RUNTS, fill search fields and submit."""
    logger.info("Navigazione alla pagina di ricerca RUNTS...")
    await page.goto(SEARCH_URL, wait_until="domcontentloaded")
    await page.wait_for_timeout(2000)

    if codice_fiscale:
        await page.fill('input[id*="codiceFiscale" i]', codice_fiscale)
    else:
        await page.fill('input[id*="denominazione" i]', denominazione)
    await page.click('input[type="submit"]')
    logger.info("Ricerca avviata — attesa risultati...")
    # Wait for results table to appear
    await page.wait_for_selector('input[value="Dettaglio"]', timeout=30000)
    await page.wait_for_timeout(500)


async def _get_page_info(page: Page) -> tuple[int, int]:
    """Return (current_page, total_pages). Falls back to (1, 1) if not found."""
    label = page.locator('[id*="spnLabelNumeroPagina"]').first
    if await label.count() == 0:
        return 1, 1
    text = await label.inner_text()
    m = re.search(r"(\d+)\s+di\s+(\d+)", text)
    if m:
        return int(m.group(1)), int(m.group(2))
    return 1, 1


async def _get_total_items(page: Page) -> int:
    el = page.locator('[id*="hdnListEntiTotalItems"]').first
    if await el.count() > 0:
        val = await el.get_attribute("value")
        if val and val.isdigit():
            return int(val)
    return 0


async def _collect_row_metadata(page: Page) -> list[dict]:
    """Read denomination / comune / sezione from visible table rows (no navigation)."""
    rows = await page.locator("table tbody tr").all()
    results = []
    for row in rows:
        cells = await row.locator("td").all()
        if len(cells) < 3:
            continue
        results.append({
            "denominazione":    (await cells[0].inner_text()).strip(),
            "sede_comune":      (await cells[1].inner_text()).strip(),
            "sezione_registro": (await cells[2].inner_text()).strip(),
        })
    return results


async def _go_to_next_page(page: Page) -> bool:
    """Click 'Successiva' and wait for next page to fully render. Returns False if no next page."""
    cur, tot = await _get_page_info(page)
    if cur >= tot:
        return False

    next_link = page.locator('a[id*="ltlProssimaPagina"]').first
    if await next_link.count() == 0:
        return False

    expected_page = cur + 1
    await next_link.click()

    # Wait specifically for the pagination label to show the expected page number.
    # The label may lag behind the Dettaglio buttons appearing (cached DOM race).
    try:
        await page.wait_for_function(
            f"""() => {{
                const els = document.querySelectorAll('[id*="spnLabelNumeroPagina"]');
                for (const el of els) {{
                    if (el.innerText.includes('Pagina {expected_page}')) return true;
                }}
                return false;
            }}""",
            timeout=20000,
        )
    except Exception as exc:
        logger.warning("Timeout waiting for page %d label: %s", expected_page, exc)
        return False

    await page.wait_for_selector('input[value="Dettaglio"]', timeout=10000)
    return True


async def _back_to_results(page: Page) -> bool:
    """Go back from /Ente detail page to search results. Returns True on success."""
    try:
        await page.go_back(wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_selector('input[value="Dettaglio"]', timeout=10000)
        return True
    except Exception as exc:
        logger.debug("go_back failed: %s", exc)
        return False


async def extract_fields(page: Page) -> dict:
    """
    Extract structured fields from the detail page (/Ente).
    Must be called after waiting for the page to fully render (~2.5s after networkidle).
    """
    data: dict = {}

    # Wait for content to be available
    try:
        await page.wait_for_selector('[id*="spnRepertorio"]', timeout=10000)
    except Exception:
        logger.warning("Timeout waiting for detail content at %s", page.url)
        return data

    # Known ID-based fields
    for key, id_part in _DETAIL_IDS.items():
        el = page.locator(f'[id*="{id_part}"]').first
        if await el.count() > 0:
            data[key] = (await el.inner_text()).strip() or None

    # Sede legale: scoped JS extraction
    try:
        sede: dict = await page.evaluate(_EXTRACT_SEDE_LEGALE_JS)
        if sede.get("stato"):
            data["sede_stato"] = sede["stato"]
        if sede.get("provincia"):
            data["sede_provincia"] = sede["provincia"]
        if sede.get("comune"):
            data["sede_comune"] = sede["comune"]
        if sede.get("indirizzo"):
            data["sede_indirizzo"] = sede["indirizzo"]
        if sede.get("civico"):
            data["sede_civico"] = sede["civico"]
        if sede.get("cap"):
            data["sede_cap"] = sede["cap"]
        if sede.get("regione"):
            data["sede_regione"] = sede["regione"]
        # Derive regione from province code if not available from DOM
        if not data.get("sede_regione") and data.get("sede_provincia"):
            prov = data["sede_provincia"].strip().upper()
            regione = _PROVINCIA_TO_REGIONE.get(prov)
            if regione:
                data["sede_regione"] = regione
            else:
                logger.debug("Provincia '%s' non trovata nel mapping regioni", prov)
    except Exception as exc:
        logger.debug("Sede legale JS extraction error: %s", exc)

    # Iscrizione date
    iscr_el = page.locator('[id*="spnIscrittoIl"]').first
    if await iscr_el.count() > 0:
        txt = (await iscr_el.inner_text()).strip()
        data["data_iscrizione"] = re.sub(r"^Iscritto il\s+", "", txt, flags=re.I) or None

    # General label/value pairs via JavaScript (runs after content is rendered)
    try:
        bold_pairs: dict = await page.evaluate(_EXTRACT_BOLD_JS)
        for label, value in bold_pairs.items():
            normalized = _normalize_label(label)
            if normalized and normalized not in data:
                data[normalized] = value or None
    except Exception as exc:
        logger.debug("JS extraction error: %s", exc)

    # Rappresentante legale: first person marked as such
    try:
        body_text = await page.locator("body").inner_text()
        data["raw_json"] = body_text[:10000]

        # Simple text-based extraction for rappresentante legale
        m = re.search(
            r"Rappresentante legale\s+S[ìi]\b.*?Nome\s+(\S+).*?Cognome\s+(\S+)",
            body_text, re.DOTALL | re.IGNORECASE
        )
        if m and "rappresentante_legale" not in data:
            data["rappresentante_legale"] = f"{m.group(2)} {m.group(1)}"
    except Exception:
        pass

    data["url_dettaglio"] = page.url
    return data


def _normalize_label(label: str) -> str:
    """Map an Italian label to a DB column name."""
    mapping = {
        "sezione":              "sezione_registro",
        "sezione del registro": "sezione_registro",
        "forma giuridica":      "forma_giuridica",
        "natura giuridica":     "natura_giuridica",
        "codice fiscale":       "codice_fiscale",
        "email pec":            "pec",
        "sito internet":        "sito_web",
        "denominazione":        "denominazione",
        "provincia":            "sede_provincia",
        "comune":               "sede_comune",
        "regione":              "sede_regione",
        "indirizzo":            "sede_indirizzo",
        "cap":                  "sede_cap",
    }
    key = label.lower().strip()
    for raw, normalized in mapping.items():
        if raw in key:
            return normalized
    # Skip long section headers
    if len(key) > 50:
        return ""
    # Generic snake_case fallback
    return re.sub(r"\s+", "_", re.sub(r"[^\w\s]", "", key)).strip("_")


async def run_scraper(
    denominazione: str = "CLUB ALPINO ITALIANO",
    headless: bool = True,
    delay_ms: int = 500,
    filter_denominazione: str | None = None,
    codice_fiscale: str | None = None,
    attachments_dir: "Path | None" = None,
) -> tuple[list[dict], dict]:
    """
    Full scrape: search → paginate → extract detail for each ente.
    Returns (entities, retry_stats). Each entity dict includes:
    atti_documenti: list[dict] and cariche: list[dict] for further processing.
    retry_stats keys: attempt_1, attempt_2, attempt_3, failed_after_retry.
    """
    all_entities: list[dict] = []
    retry_stats = {"attempt_1": 0, "attempt_2": 0, "attempt_3": 0, "failed_after_retry": 0}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()
        page.on("dialog", lambda d: asyncio.ensure_future(d.accept()))

        try:
            await search_enti(page, denominazione, codice_fiscale=codice_fiscale)

            total_items = await _get_total_items(page)
            _, total_pages = await _get_page_info(page)

            if total_items == 0:
                logger.info("Nessun ente trovato per '%s'.", denominazione)
                return []

            logger.info("Trovati %d enti su %d pagine", total_items, total_pages)

            while True:
                cur, tot = await _get_page_info(page)
                logger.info("--- Pagina %d di %d ---", cur, tot)

                # Collect metadata from visible rows before any navigation
                row_meta = await _collect_row_metadata(page)
                num_buttons = await page.locator('input[value="Dettaglio"]').count()

                for i in range(num_buttons):
                    meta = row_meta[i] if i < len(row_meta) else {}
                    den = meta.get("denominazione", f"ente_{len(all_entities)+1}")

                    logger.info(
                        "Processato [%d/%d] %s",
                        len(all_entities) + 1, total_items, den
                    )

                    fields = None
                    for attempt in range(3):
                        try:
                            # Re-find buttons after each back navigation
                            btn = page.locator('input[value="Dettaglio"]').nth(i)
                            await btn.click()

                            # Wait for navigation to /Ente
                            await page.wait_for_url(DETAIL_URL_PATTERN, timeout=15000)
                            await page.wait_for_load_state("networkidle", timeout=20000)

                            # The detail content renders after networkidle via DNN JS
                            fields = await extract_fields(page)
                            fields.update({k: v for k, v in meta.items() if v and k not in fields})
                            atti = await extract_atti_documenti(page)
                            if attachments_dir is not None and atti:
                                id_r = fields.get("id_runts") or den
                                from pathlib import Path as _Path
                                ente_dir = _Path(attachments_dir) / str(id_r)
                                atti = await _playwright_download_allegati(page, atti, ente_dir)
                            fields["atti_documenti"] = atti
                            fields["cariche"] = await extract_cariche(page)
                            retry_stats[f"attempt_{attempt + 1}"] += 1
                            break
                        except Exception as exc:
                            if attempt < 2:
                                logger.warning(
                                    "Errore su ente '%s' (tentativo %d/3): %s — retry tra %ds",
                                    den, attempt + 1, exc, 2 ** attempt,
                                )
                                try:
                                    if "/Ente" in page.url:
                                        await _back_to_results(page)
                                except Exception:
                                    pass
                                await asyncio.sleep(2 ** attempt)
                            else:
                                logger.error("Errore definitivo su ente '%s' dopo 3 tentativi: %s", den, exc)
                                retry_stats["failed_after_retry"] += 1
                                try:
                                    if "/Ente" in page.url:
                                        await _back_to_results(page)
                                except Exception:
                                    await search_enti(page, denominazione, codice_fiscale=codice_fiscale)
                                    for _ in range(cur - 1):
                                        if not await _go_to_next_page(page):
                                            break

                    if fields is not None:
                        all_entities.append(fields)

                        if delay_ms > 0:
                            await asyncio.sleep(delay_ms / 1000)

                        # Return to search results
                        recovered = await _back_to_results(page)
                        if not recovered:
                            logger.warning("Back navigation failed — re-executing search and navigating to page %d", cur)
                            await search_enti(page, denominazione, codice_fiscale=codice_fiscale)
                            for _ in range(cur - 1):
                                if not await _go_to_next_page(page):
                                    break
                            row_meta = await _collect_row_metadata(page)
                    else:
                        pass  # already handled in the retry loop

                if cur >= tot:
                    break
                moved = await _go_to_next_page(page)
                if not moved:
                    break

        finally:
            await browser.close()

    logger.info("Scraping completato. Totale enti estratti: %d", len(all_entities))
    return all_entities, retry_stats
