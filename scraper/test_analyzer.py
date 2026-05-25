"""Unit tests for scraper/analyzer.py using real PDF fixtures."""
import pytest
from pathlib import Path

from .analyzer import extract_bilancio_pdf, parse_italian_number

FIXTURES = Path(__file__).parent / "test_data" / "bilanci"

PISA_2024_EXPECTED = {
    "oneri_a_interesse_generale":           122929.00,
    "oneri_b_attivita_diverse":               3762.00,
    "oneri_c_raccolta_fondi":                    0.00,
    "oneri_d_finanziarie_patrimoniali":          0.00,
    "oneri_e_supporto_generale":                 0.00,
    "totale_oneri":                          126691.00,
    "proventi_a_interesse_generale":         166860.00,
    "proventi_b_attivita_diverse":             4368.00,
    "proventi_c_raccolta_fondi":                 0.00,
    "proventi_d_finanziarie_patrimoniali":       0.00,
    "proventi_e_supporto_generale":              0.00,
    "totale_proventi":                       171228.00,
    "risultato_ante_imposte":                 44537.00,
    "imposte":                                    0.00,
    "risultato_esercizio":                    44537.00,
}

# Parma 2025 is a Mod.B PDF where financial pages (2-4) are image-based.
# pdfplumber extracts no financial text from these pages (OCR required).
# The test verifies the function completes without error and captures raw_text.
PARMA_2025_EXPECTED = {}


def test_extract_bilancio_pisa_2024():
    path = FIXTURES / "Bilancio_Pisa_2024.pdf"
    assert path.exists(), f"Fixture non trovata: {path}"
    result = extract_bilancio_pdf(str(path))
    for key, expected in PISA_2024_EXPECTED.items():
        actual = result.get(key)
        assert actual is not None, f"{key}: valore non estratto (None)"
        assert abs(actual - expected) < 0.01, f"{key}: atteso {expected}, ottenuto {actual}"


def test_extract_bilancio_parma_2025():
    path = FIXTURES / "Bilancio_Parma_2025.pdf"
    assert path.exists(), f"Fixture non trovata: {path}"
    result = extract_bilancio_pdf(str(path))
    # Image-based PDF: pdfplumber cannot extract financial figures without OCR.
    # Verify the function completes and returns a well-formed result.
    from .analyzer import _PATTERNS
    for key in _PATTERNS:
        assert key in result, f"Campo mancante nel risultato: {key}"
    assert "_raw_text" in result, "_raw_text deve essere presente nel risultato"


@pytest.mark.parametrize("s,expected", [
    ("502.912,98",  502912.98),
    ("502 912,98",  502912.98),
    ("502'912,98",  502912.98),
    ("122929",      122929.00),
    ("122.929",     122929.00),
    ("122.929,00",  122929.00),
    ("0,00",            0.00),
    ("0",               0.00),
])
def test_parse_italian_number(s, expected):
    result = parse_italian_number(s)
    assert result is not None, f"parse_italian_number({s!r}) returned None"
    assert abs(result - expected) < 0.001, f"parse_italian_number({s!r}): atteso {expected}, ottenuto {result}"


def test_parse_italian_number_invalid():
    assert parse_italian_number("") is None
    assert parse_italian_number(None) is None
