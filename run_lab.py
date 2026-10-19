"""Lab 21.10: trace every hand-checked value back to its report.

Put the report texts in data/raw/reports/ as <first word of company>_<year>.txt,
e.g. siemens_2025.txt (data/raw/ is not uploaded to GitHub). Then run:

    python run_lab.py
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, "src")

from climalens.trace import trace_company  # noqa: E402

REPORTS = Path("data/raw/reports")

gold = pd.read_csv("data/gold/gold_template.csv")
results = []
for _, row in gold.dropna(subset=["scope1_tco2e"]).iterrows():
    path = REPORTS / f"{row['company'].split()[0].lower()}_{row['report_year']}.txt"
    if not path.exists():
        print(f"No report text for {row['company']} ({path})")
        continue
    results.append(trace_company(row, path.read_text(encoding="utf-8")))

table = pd.concat(results, ignore_index=True)
pd.set_option("display.width", 200)
print(table.to_string(index=False))
print(f"\n{table['found'].sum()} of {len(table)} hand-checked values found in the reports.")
