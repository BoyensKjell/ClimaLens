import pandas as pd
import pytest

from climalens.extract import candidate_passages, check_answer, extract_company, gemini_client

REPORT = """Vorwort
Sehr geehrte Aktionärinnen und Aktionäre
Mio. Tonnen CO2e Basisjahr (2022) 2025 2024
Scope-1-THG-Bruttoemissionen 85,74 51,89 53,24
Standortbezogene Scope-2-THG-Bruttoemissionen 0,20 0,22 0,39
Marktbezogene Scope-2-THG-Bruttoemissionen 0,20 0,22 0,39
Gesamte indirekte (Scope-3-)THG-Bruttoemissionen 22,15 19,47 21,77
Konzernabschluss"""
LINES = REPORT.splitlines()
GOLD = pd.Series({"company": "RWE AG", "scope1_tco2e": 51_890_000, "scope2_market_tco2e": 220_000,
                  "scope2_location_tco2e": 220_000, "scope3_tco2e": 19_470_000})


def item(value, number, line, quote, unit="Mt"):
    return {"value": value, "number": number, "unit": unit, "line": line, "quote": quote}


GOOD = {
    "scope1_tco2e": item("51,89", 51.89, 4, "Scope-1-THG-Bruttoemissionen 85,74 51,89 53,24"),
    "scope2_market_tco2e": item("0,22", 0.22, 6, "Marktbezogene Scope-2-THG-Bruttoemissionen 0,20 0,22"),
    "scope2_location_tco2e": item("0,22", 0.22, 5, "Standortbezogene Scope-2-THG-Bruttoemissionen 0,20 0,22 0,39"),
    "scope3_tco2e": item("19,47", 19.47, 7, "Gesamte indirekte (Scope-3-)THG-Bruttoemissionen 22,15 19,47 21,77"),
}


def test_passages_keep_line_numbers_and_the_table_header():
    p = candidate_passages(REPORT)
    assert "L3: Mio. Tonnen CO2e Basisjahr (2022) 2025 2024" in p
    assert "L4: Scope-1-THG-Bruttoemissionen 85,74 51,89 53,24" in p


def test_correct_answers_are_verified():
    out = check_answer("RWE AG", GOOD, LINES, GOLD)
    assert out["verdict"].tolist() == ["correct"] * 4
    assert out["quote_ok"].all() and out["number_ok"].all()


def test_wrong_column_is_wrong_and_invented_quote_is_unverified():
    answer = dict(GOOD)
    answer["scope1_tco2e"] = item("85,74", 85.74, 4, "Scope-1-THG-Bruttoemissionen 85,74")  # base year column
    answer["scope3_tco2e"] = item("19,47", 19.47, 7, "Scope 3 total 19,47")  # not in the report
    out = check_answer("RWE AG", answer, LINES, GOLD).set_index("field")["verdict"]
    assert out["scope1_tco2e"] == "wrong"
    assert out["scope3_tco2e"] == "unverified"


def test_null_answer_is_missed_and_number_must_fit_the_quote():
    answer = dict(GOOD)
    answer["scope1_tco2e"] = item(None, None, None, None, unit=None)
    answer["scope3_tco2e"] = item("19,47", 194.7, 7, GOOD["scope3_tco2e"]["quote"])  # misread the comma
    out = check_answer("RWE AG", answer, LINES, GOLD).set_index("field")
    assert out.loc["scope1_tco2e", "verdict"] == "missed"
    assert not out.loc["scope3_tco2e", "number_ok"]


def test_short_printed_values_count_when_quoted():
    lines = ["GHG Emissions Scope 2 (market-based) 1 kt;"]
    answer = {f: item(None, None, None, None, unit=None) for f in GOOD}
    answer["scope2_market_tco2e"] = item("1", 1, 1, "GHG Emissions Scope 2 (market-based) 1 kt", unit="kt")
    out = check_answer("SAP SE", answer, lines, pd.Series({"scope2_market_tco2e": 1000.0})).set_index("field")
    assert out.loc["scope2_market_tco2e", "verdict"] == "correct"


def test_extract_company_sends_the_passages_to_the_model():
    seen = {}

    def fake(prompt):
        seen["prompt"] = prompt
        return GOOD

    _, out = extract_company("RWE AG", 2025, REPORT, fake, GOLD)
    assert "RWE AG" in seen["prompt"] and "take the 2025 column" in seen["prompt"]
    assert (out["verdict"] == "correct").all()


def test_client_needs_a_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        gemini_client()
