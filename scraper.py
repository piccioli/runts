import asyncio
import json
import logging
import re

from playwright.async_api import Page, async_playwright

logger = logging.getLogger(__name__)

SEARCH_URL = "https://servizi.lavoro.gov.it/runts/it-it/Ricerca-enti"
DETAIL_URL_PATTERN = "**/Ricerca-enti/Ente*"

# IDs present on the detail page
_DETAIL_IDS = {
    "id_runts":         "spnRepertorio",
    "codice_fiscale":   "spnCodiceFiscale",
    "pec":              "spnEmailPec",
    "sito_web":         "spnSitoInternet",
    "sede_provincia":   "spnSedeProvincia",
    "sede_comune":      "spnSedeComune",
    "sede_regione":     "spnSedeRegione",
}

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


async def search_enti(page: Page, denominazione: str) -> None:
    """Navigate to RUNTS, fill DENOMINAZIONE and submit the search."""
    logger.info("Navigazione alla pagina di ricerca RUNTS...")
    await page.goto(SEARCH_URL, wait_until="domcontentloaded")
    await page.wait_for_timeout(2000)

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

    # Sede indirizzo + civico (might be separate elements)
    indirizzo_parts = []
    for id_part in ["spnSedeIndirizzo", "spnSedeCivico"]:
        el = page.locator(f'[id*="{id_part}"]').first
        if await el.count() > 0:
            val = (await el.inner_text()).strip()
            if val:
                indirizzo_parts.append(val)
    if indirizzo_parts:
        data["sede_indirizzo"] = " ".join(indirizzo_parts)

    sede_cap_el = page.locator('[id*="spnSedeCap"]').first
    if await sede_cap_el.count() > 0:
        data["sede_cap"] = (await sede_cap_el.inner_text()).strip() or None

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
) -> list[dict]:
    """
    Full scrape: search → paginate → extract detail for each ente.
    Returns list of entity dicts ready for upsert.
    """
    all_entities: list[dict] = []

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
            await search_enti(page, denominazione)

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
                        all_entities.append(fields)

                        if delay_ms > 0:
                            await asyncio.sleep(delay_ms / 1000)

                        # Return to search results
                        recovered = await _back_to_results(page)
                        if not recovered:
                            logger.warning("Back navigation failed — re-executing search and navigating to page %d", cur)
                            await search_enti(page, denominazione)
                            for _ in range(cur - 1):
                                if not await _go_to_next_page(page):
                                    break
                            row_meta = await _collect_row_metadata(page)

                    except Exception as exc:
                        logger.error("Errore su ente %d ('%s'): %s", i + 1, den, exc)
                        try:
                            if "/Ente" in page.url:
                                await _back_to_results(page)
                        except Exception:
                            await search_enti(page, denominazione)
                            for _ in range(cur - 1):
                                if not await _go_to_next_page(page):
                                    break

                if cur >= tot:
                    break
                moved = await _go_to_next_page(page)
                if not moved:
                    break

        finally:
            await browser.close()

    logger.info("Scraping completato. Totale enti estratti: %d", len(all_entities))
    return all_entities
