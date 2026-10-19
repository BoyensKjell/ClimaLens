import pandas as pd

from climalens.trace import find_value, matches, read_number, trace_company


def test_german_and_english_readings():
    assert (14.224, 0.001) in read_number("14,224")
    assert (14224.0, 1) in read_number("14,224")
    assert read_number("30 761,4") == [(30761.4, 0.1)]


def test_value_matches_in_kt_and_mt():
    assert matches("288,3", 288_300)        # kt, German
    assert matches("93,97", 93_970_000)     # Mt, German
    assert matches("6,239", 6_239_000)      # kt, English
    assert matches("71", 70_700)            # rounded table value
    assert not matches("12,503", 6_239_000)


def test_rough_numbers_do_not_match():
    assert not matches("5", 4_882.4)        # one digit, could be almost anything
    assert not matches("13", 12_503_000)    # rounding step too large

def test_only_emission_lines_count():
    lines = ["Umsatz 288,3", "Gesamte Scope 1 THG-Bruttoemissionen 288,3"]
    assert find_value(lines, 288_300) == [2]


def test_percentages_are_ignored():
    assert find_value(["Scope 3 reduction –13%1"], 13_000_000) == []


def test_most_precise_line_comes_first():
    lines = ["Scope 1 rund 52 Mio. t CO2e", "Scope-1-THG-Bruttoemissionen 51,89"]
    assert find_value(lines, 51_890_000) == [2, 1]


def test_spaced_thousands_are_read():
    lines = ["Scope-1-THG-Bruttoemissionen 30 761,4 36 160,9 -14,9"]
    assert find_value(lines, 30_761.4) == [1]


def test_trace_company_flags_missing_value():
    gold = pd.Series({"company": "X", "scope1_tco2e": 288_300, "scope2_market_tco2e": None,
                      "scope2_location_tco2e": None, "scope3_tco2e": 12_503_000})
    text = "Scope 1 emissions 288,3\nScope 3 location 6,264\nScope 3 market 6,239"
    result = trace_company(gold, text).set_index("field")
    assert result.loc["scope1_tco2e", "found"]
    assert not result.loc["scope3_tco2e", "found"]
