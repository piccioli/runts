import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_REGIONS = [
    "abruzzo", "basilicata", "calabria", "campania", "emilia-romagna",
    "friuli-venezia-giulia", "lazio", "liguria", "lombardia", "marche",
    "molise", "piemonte", "puglia", "sardegna", "sicilia", "toscana",
    "trentino-alto-adige", "umbria", "valle-d-aosta", "veneto",
]

_SECTIONS_URL = "https://www.cai.it/wp-json/cai-section/v2/sections-list-simple"
_SUBSECTIONS_URL = "https://www.cai.it/wp-json/cai-section/v2/sections/{code}/sub-sections-list"
_REGIONAL_GROUPS_URL = "https://www.cai.it/wp-json/cai-section/v2/regional-groups-list"
_MAX_RETRIES = 3


def _with_retry(fn: Any, max_retries: int = _MAX_RETRIES) -> Any:
    """Call fn() with exponential backoff on httpx failures."""
    for attempt in range(max_retries):
        try:
            return fn()
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            if attempt == max_retries - 1:
                raise
            wait = 2 ** attempt
            logger.warning("Attempt %d/%d failed, retrying in %ds: %s", attempt + 1, max_retries, wait, exc)
            time.sleep(wait)


def _normalize_section(raw: dict, regione: str) -> dict:
    """Map API response fields to sezioni_cai column names."""
    office_addr = raw.get("officeAddress") or raw.get("office_address")
    postal_addr = raw.get("postalAddress") or raw.get("postal_address")
    return {
        "codice_cai": raw.get("code"),
        "cai_denominazione": raw.get("name") or "",
        "cai_codice_fiscale": raw.get("cf") or None,
        "cai_partita_iva": raw.get("vat") or None,
        "cai_email": raw.get("email") or None,
        "cai_pec": raw.get("pec") or None,
        "cai_telefono_sede": raw.get("officePhone") or None,
        "cai_telefono": raw.get("phone") or None,
        "cai_fax": raw.get("fax") or None,
        "cai_indirizzo_sede": json.dumps(office_addr, ensure_ascii=False) if office_addr else None,
        "cai_indirizzo_postale": json.dumps(postal_addr, ensure_ascii=False) if postal_addr else None,
        "cai_sito_web": raw.get("website") or None,
        "cai_orari": raw.get("timetable") or None,
        "cai_avvisi": raw.get("notice") or None,
        "cai_anno_fondazione": raw.get("foundationYear") or None,
        "cai_soci_ultimo_anno": raw.get("lastyearMembershipsCount") or None,
        "cai_lat": raw.get("latitude") or None,
        "cai_lon": raw.get("longitude") or None,
        "cai_regione": regione,
        "cai_scraped_at": datetime.now(timezone.utc).isoformat(),
    }


def _normalize_subsection(raw: dict, codice_sezione: str) -> dict:
    """Map API response fields to sottosezioni_cai column names."""
    office_addr = raw.get("officeAddress") or raw.get("office_address")
    return {
        "cai_codice": raw.get("code"),
        "cai_sezione_codice": codice_sezione,
        "cai_nome": raw.get("name") or "",
        "cai_email": raw.get("email") or None,
        "cai_telefono_sede": raw.get("officePhone") or None,
        "cai_telefono": raw.get("phone") or None,
        "cai_indirizzo_sede": json.dumps(office_addr, ensure_ascii=False) if office_addr else None,
        "cai_sito_web": raw.get("website") or None,
        "cai_orari": raw.get("timetable") or None,
        "cai_avvisi": raw.get("notice") or None,
        "cai_anno_fondazione": raw.get("foundationYear") or None,
        "cai_soci": raw.get("currentMemberships") or raw.get("lastyearMembershipsCount") or None,
        "cai_lat": raw.get("latitude") or None,
        "cai_lon": raw.get("longitude") or None,
        "cai_scraped_at": datetime.now(timezone.utc).isoformat(),
    }


def fetch_subsections(codice_sezione: str) -> list[dict]:
    """Fetch sub-sections for a given CAI section code."""
    url = _SUBSECTIONS_URL.format(code=codice_sezione)
    try:
        with httpx.Client(timeout=30.0) as client:
            def _fetch(u: str = url, c: httpx.Client = client) -> Any:
                resp = c.get(u, headers={"Origin": "https://www.cai.it"})
                if resp.status_code == 404:
                    return []
                resp.raise_for_status()
                return resp.json()

            data = _with_retry(_fetch)
    except Exception as exc:
        logger.error("Failed to fetch subsections for %s: %s", codice_sezione, exc)
        return []

    if not data:
        return []
    if not isinstance(data, list):
        logger.warning("Unexpected response type for subsections of %s: %s", codice_sezione, type(data).__name__)
        return []
    return [_normalize_subsection(raw, codice_sezione) for raw in data]


def fetch_regional_groups() -> list[dict]:
    """Fetch all 21 CAI regional groups from the REST API."""
    _HEADERS = {"Origin": "https://www.cai.it", "Referer": "https://www.cai.it/"}
    with httpx.Client(timeout=30.0, headers=_HEADERS) as client:
        logger.info("Fetching CAI regional groups...")
        def _fetch(c: httpx.Client = client) -> Any:
            resp = c.get(_REGIONAL_GROUPS_URL)
            resp.raise_for_status()
            return resp.json()

        data = _with_retry(_fetch)

    if not isinstance(data, list):
        logger.error("Unexpected response type for regional groups: %s", type(data).__name__)
        return []

    now = datetime.now(timezone.utc).isoformat()
    results = []
    for raw in data:
        office_addr = raw.get("officeAddress") or raw.get("office_address")
        postal_addr = raw.get("postalAddress") or raw.get("postal_address")
        results.append({
            "gr_codice": raw.get("code"),
            "gr_nome": raw.get("name") or "",
            "gr_codice_fiscale": raw.get("cf") or None,
            "gr_partita_iva": raw.get("vat") or None,
            "gr_email": raw.get("email") or None,
            "gr_pec": raw.get("pec") or None,
            "gr_telefono_sede": raw.get("officePhone") or None,
            "gr_telefono": raw.get("phone") or None,
            "gr_fax": raw.get("fax") or None,
            "gr_indirizzo_sede": json.dumps(office_addr, ensure_ascii=False) if office_addr else None,
            "gr_indirizzo_postale": json.dumps(postal_addr, ensure_ascii=False) if postal_addr else None,
            "gr_sito_web": raw.get("website") or None,
            "gr_descrizione": raw.get("description") or None,
            "gr_soci_ultimo_anno": raw.get("lastyearMembershipsCount") or None,
            "gr_scraped_at": now,
        })

    logger.info("Totale gruppi regionali recuperati: %d", len(results))
    return results


def fetch_all_sections() -> list[dict]:
    """Fetch all CAI sections from the REST API.

    The endpoint returns all 529 sections regardless of the ?region param,
    so we call it once and use the 'region' field in each record.
    """
    _HEADERS = {"Origin": "https://www.cai.it", "Referer": "https://www.cai.it/"}
    with httpx.Client(timeout=30.0, headers=_HEADERS) as client:
        logger.info("Fetching all CAI sections (single request)...")
        def _fetch(c: httpx.Client = client) -> Any:
            resp = c.get(_SECTIONS_URL, params={"region": "lombardia"})
            resp.raise_for_status()
            return resp.json()

        data = _with_retry(_fetch)

    if not isinstance(data, list):
        logger.error("Unexpected response type: %s", type(data).__name__)
        return []

    results = []
    for raw in data:
        regione = (raw.get("region") or "").upper()
        results.append(_normalize_section(raw, regione))

    logger.info("Totale sezioni recuperate: %d", len(results))
    return results
