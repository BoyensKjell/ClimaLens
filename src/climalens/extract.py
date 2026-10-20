"""Read Scope 1, 2 and 3 emissions from a report with an LLM, and check every answer.

1. Find the passages: an annual report has about 20,000 lines, but the emissions tables
   are a few hundred. Lines that name a scope (and words like "gross" or "Brutto") are
   scored, a window of lines around each one is kept (with the table header above it),
   and the best windows are sent to the model. Every line carries its line number.
2. Ask the model: for each field it returns the number as printed, the unit, the line
   number and a quote copied from that line, or null if the report does not give it.
3. Check the answer, without trusting the model:
   - quote_ok: the quote really is in the report on that line (or the next one).
   - number_ok: the number is in the quote and, converted with the unit, gives value_t.
   - Against the gold set: the value is within 0.5 % of the hand-checked value.
   An answer that fails the first two checks is a hallucination, whatever its value.

The model is called through Google's Gemini API (free key from aistudio.google.com),
read from the environment variable GEMINI_API_KEY. The key is never printed or saved.
"""

import json
import os
import re
import time
import urllib.error
import urllib.request

import pandas as pd

from climalens.trace import NUMBER, SPACED_NUMBER, UNIT_FACTORS, match_precision, read_number

DEFAULT_MODEL = "gemini-3.8-flash"
TOLERANCE = 0.005  # an answer is correct if it is within 0.5 % of the hand-checked value
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

SCOPE = re.compile(r"scope[\s-]*[123]", re.IGNORECASE)
STRONG_WORDS = ["brutto", "gross", "gesamt", "total", "summe", "marktbezogen", "standortbezogen",
                "market-based", "location-based", "marktbasiert", "standortbasiert"]

FIELDS = {
    "scope1_tco2e": "Scope 1 gross GHG emissions",
    "scope2_market_tco2e": "Scope 2 gross GHG emissions, market-based",
    "scope2_location_tco2e": "Scope 2 gross GHG emissions, location-based",
    "scope3_tco2e": "Scope 3 total gross GHG emissions (market-based if both are given)",
}

PROMPT = """You read the sustainability statement (ESRS E1) of {company}, report year {year}.
Below are passages of the report. Every line starts with its line number, like "L123: ".

For each field, find the value for the report year {year} for the whole group:
{fields}

Rules:
- Use the ESRS gross values for the whole group ("Brutto", "gross", "Gesamt"), not a subset
  such as only production sites or one segment, and not values after offsets or removals.
- Tables often have several year columns (base year, {year}, {prev}, targets). Read the column
  headers above the row and take the {year} column.
- value: the number exactly as printed in the report, e.g. "15,369" or "30 761,4".
- number: the same number as a plain decimal in that unit, with a dot as decimal point
  (German reports use "," as decimal point: "15,369" Mt is 15.369; "30 761,4" t is 30761.4).
- unit: the unit the table or text uses for that number: "t", "kt" or "Mt" (Mio. t = Mt, Tsd. t = kt).
- line: the line number where the number is printed.
- quote: copy the words of that line that name the row and contain the number, character for character.
- If the report does not give a field, return null for all of value, number, unit, line and quote.

Passages:
{passages}
"""


def _schema() -> dict:
    item = {
        "type": "OBJECT",
        "properties": {
            "value": {"type": "STRING", "nullable": True},
            "number": {"type": "NUMBER", "nullable": True},
            "unit": {"type": "STRING", "enum": list(UNIT_FACTORS), "nullable": True},
            "line": {"type": "INTEGER", "nullable": True},
            "quote": {"type": "STRING", "nullable": True},
        },
        "required": ["value", "number", "unit", "line", "quote"],
    }
    return {"type": "OBJECT", "properties": {f: item for f in FIELDS}, "required": list(FIELDS)}


def line_score(line: str) -> int:
    lower = line.lower()
    if not SCOPE.search(line):
        return 0
    return 1 + sum(word in lower for word in STRONG_WORDS) + bool(NUMBER.search(line))


def candidate_passages(text: str, max_chars: int = 60_000, before: int = 14, after: int = 8) -> str:
    """The best-scoring windows of the report, each line prefixed with its number, in report order."""
    lines = text.splitlines()
    scores = [line_score(line) for line in lines]
    windows = []
    for i, s in enumerate(scores):
        if s:
            lo, hi = max(0, i - before), min(len(lines), i + after + 1)
            if windows and lo <= windows[-1][1]:
                windows[-1] = [windows[-1][0], hi, windows[-1][2] + s]
            else:
                windows.append([lo, hi, s])
    chosen, used = [], 0
    for lo, hi, _ in sorted(windows, key=lambda w: -w[2] / (w[1] - w[0]) ** 0.5):
        block = "\n".join(f"L{n + 1}: {lines[n].strip()}" for n in range(lo, hi) if lines[n].strip())
        if used + len(block) > max_chars:
            continue
        chosen.append((lo, block))
        used += len(block)
    return "\n...\n".join(block for _, block in sorted(chosen))


def build_prompt(company: str, year: int, passages: str) -> str:
    fields = "\n".join(f"- {key}: {label}" for key, label in FIELDS.items())
    return PROMPT.format(company=company, year=year, prev=year - 1, fields=fields, passages=passages)


def gemini_client(model: str | None = None, api_key: str | None = None, retries: int = 4):
    """A function prompt -> parsed JSON answer, calling the Gemini API."""
    model = model or os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
    key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("No API key: set the environment variable GEMINI_API_KEY.")

    def ask(prompt: str) -> dict:
        body = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json",
                                 "responseSchema": _schema()},
        }
        request = urllib.request.Request(
            API_URL.format(model=model), data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "x-goog-api-key": key})
        for attempt in range(retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=180) as response:
                    answer = json.load(response)
                break
            except urllib.error.HTTPError as err:
                # 429: free-tier rate limit, 503: model busy. Wait and try again.
                if err.code in (429, 500, 503) and attempt < retries:
                    time.sleep(15 * 2 ** attempt)
                    continue
                detail = err.read().decode(errors="replace")[:500]
                raise RuntimeError(f"Gemini API error {err.code} for model {model}: {detail}") from None
        return json.loads(answer["candidates"][0]["content"]["parts"][0]["text"])

    ask.model = model
    return ask


def _normalise(s: str) -> str:
    return " ".join(str(s).replace(" ", " ").replace(" ", " ").split()).lower()


def _numbers(text: str) -> list[str]:
    return NUMBER.findall(text) + SPACED_NUMBER.findall(text)


def check_answer(company: str, answer: dict, lines: list[str], gold_row: pd.Series | None = None) -> pd.DataFrame:
    """One row per field: what the model said, whether its quote and number hold up, and whether it matches gold."""
    rows = []
    for field in FIELDS:
        a = answer.get(field) or {}
        value, number, unit, line, quote = (a.get(k) for k in ("value", "number", "unit", "line", "quote"))
        value_t = float(number) * UNIT_FACTORS[unit] if number is not None and unit in UNIT_FACTORS else None
        near = " ".join(lines[n - 1] for n in (line, line + 1) if 1 <= n <= len(lines)) if isinstance(line, int) else ""
        quote_ok = bool(quote) and _normalise(quote) in _normalise(near)
        # The printed number must be in the quote and mean value_t; "1" (kt) is too short for
        # match_precision, so a quote that contains the printed value itself also counts.
        number_ok = bool(quote) and value_t is not None and (
            any(match_precision(t, value_t) is not None for t in _numbers(quote))
            or (bool(value) and _normalise(value) in _normalise(quote) and float(number) in [r for r, _ in read_number(str(value).replace(" ", ""))]))
        gold = None if gold_row is None or pd.isna(gold_row.get(field)) else float(gold_row[field])
        if gold is None:
            verdict = "no gold value" if value_t is not None else "both empty"
        elif value_t is None:
            verdict = "missed"
        elif not (quote_ok and number_ok):
            verdict = "unverified"
        elif abs(value_t - gold) <= TOLERANCE * gold:
            verdict = "correct"
        else:
            verdict = "wrong"
        rows.append({"company": company, "field": field, "llm_value": value, "llm_unit": unit,
                     "llm_tco2e": value_t, "gold_tco2e": gold, "line": line, "quote": quote,
                     "quote_ok": quote_ok, "number_ok": number_ok, "verdict": verdict})
    out = pd.DataFrame(rows)
    out["line"] = out["line"].astype("Int64")
    return out


def extract_company(company: str, year: int, text: str, ask, gold_row: pd.Series | None = None) -> tuple[dict, pd.DataFrame]:
    answer = ask(build_prompt(company, year, candidate_passages(text)))
    return answer, check_answer(company, answer, text.splitlines(), gold_row)
