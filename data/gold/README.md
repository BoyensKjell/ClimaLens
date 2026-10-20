# Gold standard (hand-checked values)

`gold_template.csv` is the hand-checked reference the AI extraction is measured against.

- One row per company and report year. The company list is a starting point: check that each company is still in its index and extend it to about 40.
- Take values from the ESRS E1 section (climate change) of the sustainability statement, usually the table "Gross Scopes 1, 2, 3 and Total GHG emissions".
- Always convert to **tonnes CO2e** and note the unit used in the report in `unit_in_report` (t, kt, Mt).
- `source_page` and `source_quote` (the exact words or table row) let anyone repeat the check.
- Leave a cell **empty** if the report does not give the value. Never write 0 for "not reported".

## AI extraction (`python run_extract.py`)

The LLM gets the emissions passages of each report (with line numbers) and returns value, unit, line and quote for each field. Each answer is checked without trusting the model:

- `quote_ok`: the quote is really on the cited line of the report.
- `number_ok`: the number is in the quote and means the value in tonnes.
- `verdict`: `correct` (within 0.5 % of the gold value), `wrong`, `unverified` (quote or number does not hold up, so a possible hallucination), `missed` (model returned nothing).

Results go to `llm_results.csv` and the raw answers to `llm_answers.json`. The gold values are never shown to the model.

