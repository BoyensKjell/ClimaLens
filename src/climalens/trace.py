"""Trace hand-checked emissions values back to the report text (an audit-style check).

For every value in the gold dataset we ask: can we find this number in the report,
on a line that talks about emissions? If not, either the value was typed or
converted wrongly, or it was put together from several numbers in the report.

Reports print the same value in many ways: 288,300 t can appear as "288,3" (kt,
German), "288.3" (kt, English) or "288 300" (t). So every number on a line is read
in German and English format and in t, kt and Mt, and it counts as a match if it
equals the gold value within the rounding of the printed number. Very rough numbers
("5", "13 %") would match almost anything, so a match needs at least two significant
digits, a rounding step of at most 5 % of the value, and no "%" right after it.
The most precise match is reported first.

This step needs no AI. The same check will later verify what the LLM extracts.
"""

import re

import pandas as pd

EMISSION_WORDS = ["scope", "thg", "ghg", "co2", "emission", "treibhausgas"]
UNIT_FACTORS = {"t": 1, "kt": 1_000, "Mt": 1_000_000}
VALUE_COLUMNS = ["scope1_tco2e", "scope2_market_tco2e", "scope2_location_tco2e", "scope3_tco2e"]

# Plain numbers ("288,3", "14,224", "2025") and numbers with spaces between thousands ("30 761,4").
NUMBER = re.compile(r"(?<![\d.,])\d+(?:[.,]\d+)*(?![\d]|\s?%)")
SPACED_NUMBER = re.compile(r"(?<![\d.,])\d{1,3}(?:[ \u00a0\u202f]\d{3})+(?:,\d+)?(?![\d]|\s?%)")
MAX_ROUNDING = 0.05  # rounding step of the printed number, as a share of the value


def read_number(token: str) -> list[tuple[float, float]]:
    """All plausible readings of a printed number as (value, rounding step).

    "14,224" can be 14.224 (German) or 14224 (English), so both are returned.
    """
    token = token.replace(" ", "").replace(" ", "").replace(" ", "")
    readings = []
    for thousands, decimal in [(".", ","), (",", ".")]:
        parts = token.split(decimal)
        if len(parts) > 2:
            continue
        whole = parts[0]
        groups = whole.split(thousands)
        if len(groups) > 1 and not all(len(g) == 3 for g in groups[1:]):
            continue
        digits = "".join(groups)
        decimals = parts[1] if len(parts) == 2 else ""
        if not digits.isdigit() or (decimals and not decimals.isdigit()):
            continue
        value = float(digits + ("." + decimals if decimals else ""))
        readings.append((value, 10 ** -len(decimals)))
    return list(set(readings))


def match_precision(token: str, value_t: float) -> float | None:
    """How precisely the printed number matches value_t (rounding step / value), or None if it does not.

    The number may be printed in t, kt or Mt; it matches if it equals value_t within its rounding.
    """
    best = None
    significant = len(token.replace(" ", "").replace(".", "").replace(",", "").lstrip("0"))
    if significant < 2 or value_t <= 0:
        return None
    for number, step in read_number(token):
        for factor in UNIT_FACTORS.values():
            precision = step * factor / value_t
            if precision <= MAX_ROUNDING and abs(number * factor - value_t) <= step * factor / 2 + 1e-6:
                best = precision if best is None else min(best, precision)
    return best


def matches(token: str, value_t: float) -> bool:
    return match_precision(token, value_t) is not None


def find_value(lines: list[str], value_t: float) -> list[int]:
    """Line numbers (1-based) of emissions lines that contain value_t, most precise match first."""
    hits = []
    for i, line in enumerate(lines):
        context = (lines[i - 1] + " " + line).lower() if i else line.lower()
        if not any(word in context for word in EMISSION_WORDS):
            continue
        precisions = [match_precision(t, value_t) for t in NUMBER.findall(line) + SPACED_NUMBER.findall(line)]
        precisions = [p for p in precisions if p is not None]
        if precisions:
            hits.append((min(precisions), i + 1))
    return [line_no for _, line_no in sorted(hits)]


def trace_company(gold_row: pd.Series, report_text: str) -> pd.DataFrame:
    """One row per gold value: was it found in the report, and on which line."""
    lines = report_text.splitlines()
    rows = []
    for col in VALUE_COLUMNS:
        value = gold_row[col]
        if pd.isna(value):
            continue
        hits = find_value(lines, float(value))
        rows.append({
            "company": gold_row["company"],
            "field": col,
            "gold_tco2e": value,
            "found": bool(hits),
            "first_line": hits[0] if hits else None,
            "report_text": lines[hits[0] - 1].strip()[:90] if hits else "",
        })
    out = pd.DataFrame(rows)
    out["first_line"] = out["first_line"].astype("Int64")
    return out
