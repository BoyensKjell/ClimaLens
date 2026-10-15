# ClimaLens

**Can AI-extracted emissions data support climate stress tests of European insurers' investment portfolios?**

European insurers have to measure the climate risk in their investments (Solvency II ORSA, SFDR, CSRD/ESRS E1). That needs Scope 1–3 emissions for every company in the portfolio, which are often buried in long PDF sustainability reports. ClimaLens reads these reports with an LLM, checks the extracted figures the way an auditor would, and runs a carbon price stress test on the portfolio.

Research project in the course *Sustainability and ESG Data Analytics* (NTPU, Fall 2026).

## Status

| Module | Status |
| --- | --- |
| Financed emissions (PCAF) | first version, tested |
| Carbon price stress test | first version, tested, scenario prices are placeholders |
| Hand-checked gold dataset | template ready, values to be filled |
| LLM extraction from PDF reports | planned |
| Verification step | planned |
| Streamlit web app | planned |

## Quick start

```bash
pip install -r requirements.txt
python run_demo.py      # demo portfolio of fictional companies
python -m pytest        # run the tests
```

## Repository layout

```
src/climalens/portfolio.py    financed emissions and portfolio footprint (PCAF)
src/climalens/stress_test.py  carbon price stress test
data/gold/                    hand-checked emissions values (the reference)
data/examples/                demo portfolio, fictional companies and numbers
tests/                        unit tests
```

## Method notes

- **Financed emissions:** attribution factor = market value / EVIC; financed emissions = attribution factor × (Scope 1 + Scope 2).
- **Stress test:** extra carbon cost = emissions × price increase × (1 − pass-through); loss in company value = extra cost × EV/EBITDA multiple; the holding loses the same share of its value.
- **Missing data stays missing.** A company that does not report emissions is shown as a data gap, never as zero emissions.
- The scenario carbon prices in `stress_test.py` are placeholders and will be replaced with NGFS scenario data.
