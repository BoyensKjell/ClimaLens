# ClimaLens

**The double climate trap of European reinsurers: do transition risk on the asset side and physical risk on the liability side offset each other across NGFS scenarios?**

Reinsurers are hit by climate change twice. Their investments lose value when carbon becomes more expensive (transition risk), and their claims rise when natural catastrophes become more frequent and severe (physical risk). Strict climate policy hurts the first, weak climate policy the second. ClimaLens puts both sides of the balance sheet into one figure per scenario, in % of equity, for Munich Re (benchmark: Hannover Re).

The asset side needs Scope 1 and 2 emissions for every company in the portfolio, which are often buried in long PDF sustainability reports. ClimaLens reads these reports with an LLM, checks the extracted figures the way an auditor would, and tests whether AI-extracted data is good enough for the stress test. The goal is an agent that turns a portfolio into a short ORSA climate brief.

Research project in the course *Sustainability and ESG Data Analytics* (NTPU, Fall 2026).

## Status

| Module | Status |
| --- | --- |
| Financed emissions (PCAF) | first version, tested |
| Carbon price stress test (asset side) | first version, tested, scenario prices are placeholders |
| Natural catastrophe losses (liability side) | first version, tested, scenario multipliers are placeholders |
| Double climate trap table (both sides, % of equity) | first version, tested |
| Hand-checked gold dataset | 5 companies checked (Allianz, BASF, Siemens, SAP, RWE), to be extended to about 40 |
| Tracing gold values back to the report text | first version, tested |
| LLM extraction from PDF reports | planned |
| Verification step for LLM values | planned (reuses the tracing check) |
| Streamlit web app | planned |

## Quick start

```bash
pip install -r requirements.txt
python run_demo.py      # demo portfolio of fictional companies
python run_lab.py       # trace the gold values back to the report texts in data/raw/reports/
python -m pytest        # run the tests
```

## Repository layout

```
src/climalens/portfolio.py    financed emissions and portfolio footprint (PCAF)
src/climalens/stress_test.py  carbon price stress test (asset side)
src/climalens/liability.py    extra natural catastrophe losses (liability side)
src/climalens/double_trap.py  both sides per scenario in % of equity
src/climalens/trace.py        find each emissions value in the report text (audit-style check)
data/gold/                    hand-checked emissions values (the reference)
data/examples/                demo portfolio, fictional companies and numbers
tests/                        unit tests
```

## Method notes

- **Financed emissions:** attribution factor = market value / EVIC; financed emissions = attribution factor × (Scope 1 + Scope 2).
- **Stress test:** extra carbon cost = emissions × price increase × (1 − pass-through); loss in company value = extra cost × EV/EBITDA multiple; the holding loses the same share of its value.
- **Liability side:** loss in year t = baseline × (1 + trend)^(t − 2025) × climate multiplier; extra loss = that minus the baseline, summed up to 2030; only the share not won back through higher premiums counts (× (1 − repricing share)).
- **Net effect:** asset loss + liability extra loss, both in % of equity. High in every scenario = double trap; high on only one side per scenario = natural hedge.
- **Missing data stays missing.** A company that does not report emissions is shown as a data gap, never as zero emissions.
- The scenario carbon prices in `stress_test.py`, the climate multipliers in `liability.py` and the reinsurer figures in `run_demo.py` are placeholders. They will be replaced with NGFS Phase V data and figures from the Munich Re annual reports.
