"""Let the LLM read the emissions from every report and measure it against the gold set.

Needs a free Gemini API key in the environment variable GEMINI_API_KEY
(aistudio.google.com -> Get API key). The report texts are the same as for run_lab.py
(data/raw/reports/<first word of company>_<year>.txt). Then run:

    python run_extract.py

The checked answers are saved to data/gold/llm_results.csv and the raw model answers
to data/gold/llm_answers.json, so the web app can show them without calling the model.
"""

import json
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, "src")

from climalens.extract import extract_company, gemini_client  # noqa: E402

REPORTS = Path("data/raw/reports")

ask = gemini_client()
gold = pd.read_csv("data/gold/gold_template.csv")
answers, results = {}, []
for _, row in gold.iterrows():
    path = REPORTS / f"{row['company'].split()[0].lower()}_{row['report_year']}.txt"
    if not path.exists():
        continue
    start = time.time()
    answer, checked = extract_company(row["company"], int(row["report_year"]), path.read_text(encoding="utf-8"), ask, row)
    answers[row["company"]] = answer
    results.append(checked)
    print(f"{row['company']}: {(checked['verdict'] == 'correct').sum()} of {checked['gold_tco2e'].notna().sum()} correct "
          f"({time.time() - start:.0f} s)")

table = pd.concat(results, ignore_index=True)
pd.set_option("display.width", 220)
pd.set_option("display.max_colwidth", 70)
print()
print(table[["company", "field", "llm_value", "llm_unit", "gold_tco2e", "line", "quote_ok", "number_ok", "verdict"]].to_string(index=False))
scored = table[table["gold_tco2e"].notna()]
print(f"\nModel: {ask.model}")
print(f"{(scored['verdict'] == 'correct').sum()} of {len(scored)} hand-checked values read correctly by the AI.")
for verdict in ["wrong", "unverified", "missed"]:
    print(f"  {verdict}: {(scored['verdict'] == verdict).sum()}")
print(f"Quotes found in the report: {table['quote_ok'].sum()} of {table['quote'].notna().sum()}")
table.to_csv("data/gold/llm_results.csv", index=False)
Path("data/gold/llm_answers.json").write_text(json.dumps({"model": ask.model, "answers": answers}, indent=2, ensure_ascii=False))
