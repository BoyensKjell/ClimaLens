# ClimaLens

**The double climate trap of European reinsurers: do transition risk on the asset side and physical risk on the liability side offset each other across NGFS scenarios?**

Reinsurers are hit by climate change twice. Their investments lose value when carbon becomes more expensive (transition risk), and their claims rise when natural catastrophes become more frequent and severe (physical risk). Strict climate policy hurts the first, weak climate policy the second. ClimaLens puts both sides of the balance sheet into one figure per scenario, in % of equity, for Munich Re (benchmark: Hannover Re).

The asset side needs Scope 1 and 2 emissions for every company in the portfolio, which are often buried in long PDF sustainability reports. ClimaLens reads these reports with an LLM, checks the extracted figures the way an auditor would, and tests whether AI-extracted data is good enough for the stress test. The goal is an agent that turns a portfolio into a short ORSA climate brief.

Research project in the course *Sustainability and ESG Data Analytics* (NTPU, Fall 2026).

## Status

| Module | Status |
| --- | --- |
| Financed emissions (PCAF) | first version, tested |
| Carbon price stress test (asset side) | first version, tested; runs on Munich Re's real sector portfolio with NGFS Phase V 2030 prices |
| Natural catastrophe losses (liability side) | first version, tested; Munich Re baseline is real, scenario multipliers derived from Swiss Re sigma 4/2021 (to be refined) |
| Double climate trap table (both sides, % of equity) | first version, tested |
| Hand-checked gold dataset | 5 companies checked (Allianz, BASF, Siemens, SAP, RWE), 15 more in progress (20 before the midterm), about 40 later |
| Tracing gold values back to the report text | first version, tested |
| LLM extraction from report texts (Gemini API) | first version, tested without the model; first real run waits for an API key |
| Verification step for LLM values | first version, tested: quote must be on the cited line, number must fit the quote, value is compared with the gold set |
| Streamlit web app | first version: welcome, results, industries, data check, ORSA brief, how it works |
| Gradio app | second, smaller front end on the same model (results, industries, data check, AI reading test, ORSA brief), ready for Hugging Face Spaces |

## Quick start

```bash
pip install -r requirements.txt
streamlit run app.py    # the web app in the browser
python gradio_app.py    # the same results as a small Gradio app (pip install gradio first)
python run_munichre.py  # double climate trap for Munich Re with real inputs
python plot_munichre.py # the same results as two slide charts in output/
python run_demo.py      # demo portfolio of fictional companies
python run_lab.py       # trace the gold values back to the report texts in data/raw/reports/
python run_extract.py   # let the LLM read the same reports and score it (needs GEMINI_API_KEY)
python -m pytest        # run the tests
```

## Repository layout

```
src/climalens/portfolio.py    financed emissions and portfolio footprint (PCAF)
src/climalens/extract.py      LLM reads Scope 1-3 from a report, every answer checked against the text and the gold set
src/climalens/stress_test.py  carbon price stress test (asset side)
src/climalens/sector_stress.py the same stress test for a portfolio reported by sector (Munich Re)
src/climalens/liability.py    extra natural catastrophe losses (liability side)
src/climalens/double_trap.py  both sides per scenario in % of equity
src/climalens/munichre.py     Munich Re inputs and base-case assumptions (shared by scripts and app)
app.py                        Streamlit web app
gradio_app.py                 Gradio app (same model, for Hugging Face Spaces)
src/climalens/trace.py        find each emissions value in the report text (audit-style check)
data/gold/                    hand-checked emissions values (the reference)
data/reinsurer/               Munich Re nat-cat losses, equity, sector portfolio and 2030 scenarios
data/examples/                demo portfolio, fictional companies and numbers
tests/                        unit tests
```

## Method notes

- **Financed emissions:** attribution factor = market value / EVIC; financed emissions = attribution factor × (Scope 1 + Scope 2).
- **Stress test:** extra carbon cost = emissions × price increase × (1 − pass-through); loss in company value = extra cost × EV/EBITDA multiple; the holding loses the same share of its value.
- **Liability side:** loss in year t = baseline × (1 + trend)^(t − 2025) × climate multiplier; extra loss = that minus the baseline, summed up to 2030; only the share not won back through higher premiums counts (× (1 − repricing share)).
- **Net effect:** asset loss + liability extra loss, both in % of equity. High in every scenario = double trap; high on only one side per scenario = natural hedge.
- **Missing data stays missing.** A company that does not report emissions is shown as a data gap, never as zero emissions.
- **Sector portfolio:** Munich Re publishes financed emissions and carrying amounts per GICS industry, not single holdings. The attribution factor cancels out, so loss = financed emissions × price increase × (1 − pass-through) × EV/EBITDA multiple. Loans and bonds take only a share of that loss (debt loss factor), and no loss can exceed the carrying amount.
- **Scenarios 2030** (`data/reinsurer/scenarios_2030.csv`): carbon prices from NGFS Phase V (US$2010, converted to EUR 2025 with factor 1.30); nat-cat multipliers derived from Swiss Re sigma 4/2021 (+30–63 % weather-related insured losses by 2040). Each row states its source and what is still to be checked.
- `run_demo.py` still uses fictional numbers and the placeholder scenarios; `run_munichre.py` uses the real inputs.

## Web app online

The app runs on Streamlit Community Cloud straight from this repository: sign in at share.streamlit.io with GitHub, choose *Create app*, repository `BoyensKjell/ClimaLens`, branch `main`, main file `app.py`. Every merge to `main` updates the app. The data check page reads `data/gold/trace_results.csv`, which `python run_lab.py` writes, so the report texts never need to be online.
