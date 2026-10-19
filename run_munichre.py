"""Double climate trap for Munich Re, 2026-2030, with real inputs: python run_munichre.py

Asset side:     financed emissions and carrying amounts per sector (Munich Re annual report 2025, pp. 115-117)
Liability side: average net nat-cat large losses 2021-2025 (Munich Re annual reports, restated values)
Scenarios:      NGFS Phase V carbon prices for 2030 and a nat-cat multiplier per scenario
                (sources and status in data/reinsurer/scenarios_2030.csv)
"""

import sys

sys.path.insert(0, "src")

import pandas as pd  # noqa: E402

from climalens.double_trap import double_trap_table  # noqa: E402
from climalens.liability import PhysicalScenario  # noqa: E402
from climalens.sector_stress import load_sector_portfolio, sector_stress_summary, top_sectors  # noqa: E402
from climalens.stress_test import Scenario  # noqa: E402

# US$2010 -> EUR 2025: US consumer prices rose about 47 % from 2010 to 2025, and
# 1 EUR was worth about 1.13 USD on average in 2025. 1.47 / 1.13 = 1.30. To be checked.
USD2010_TO_EUR2025 = 1.30
# NGFS prices are global shadow prices that are close to zero today, so the full 2030
# price is treated as the extra carbon cost.
BASE_PRICE_EUR = 0.0

natcat = pd.read_csv("data/reinsurer/munichre_natcat_losses.csv")
key = pd.read_csv("data/reinsurer/munichre_key_figures.csv")
BASELINE_EUR = natcat["natcat_large_losses_meur"].mean() * 1e6
EQUITY_EUR = key.loc[key["item"] == "group_equity", "value_meur"].iloc[0] * 1e6

# Assumptions, each run as a sensitivity below.
DEFAULTS = dict(pass_through=0.3, ev_ebitda_multiple=8.0, debt_loss_factor=0.3)
TREND = 0.0  # 0 = climate effect only; exposure growth is matched by premium growth
REPRICING = 0.5  # share of extra losses recovered through higher prices at renewal

portfolio = load_sector_portfolio("data/reinsurer/munichre_financed_emissions_2025.csv")
scen = pd.read_csv("data/reinsurer/scenarios_2030.csv")
pairs = [
    (Scenario(r.scenario, r.carbon_price_2030_usd2010 * USD2010_TO_EUR2025),
     PhysicalScenario(r.scenario, r.natcat_multiplier_2030))
    for r in scen.itertuples()
]


def trap(trend=TREND, repricing=REPRICING, **stress):
    return double_trap_table(
        portfolio, pairs, BASE_PRICE_EUR, BASELINE_EUR, trend, repricing, EQUITY_EUR,
        asset_summary=sector_stress_summary, **{**DEFAULTS, **stress},
    )


fe = portfolio["scope1_financed_tco2e"] + portfolio["scope2_financed_tco2e"]
print("Munich Re corporate investments (equity, loans, bonds), 31.12.2025")
print(f"  carrying amount:    EUR {portfolio['carrying_amount_meur'].sum() / 1e3:,.1f} bn")
print(f"  financed emissions: {fe.sum() / 1e6:,.2f} Mt CO2e (Scope 1+2)")
print(f"  nat-cat baseline:   EUR {BASELINE_EUR / 1e9:,.2f} bn per year (average 2021-2025)")
print(f"  equity:             EUR {EQUITY_EUR / 1e9:,.1f} bn")

table = trap()
show = table.assign(
    carbon_price_eur=[p[0].carbon_price_eur for p in pairs],
    asset_loss_eur_bn=table["asset_loss_eur"] / 1e9,
    liability_extra_eur_bn=table["liability_extra_eur"] / 1e9,
)
print("\nDouble climate trap 2026-2030, in % of equity:")
cols = ["scenario", "carbon_price_eur", "asset_loss_eur_bn", "liability_extra_eur_bn",
        "asset_pct_equity", "liability_pct_equity", "net_pct_equity"]
print(show[cols].round(2).to_string(index=False))

nz = pairs[-1][0]
print(f"\nLargest asset losses under {nz.name} (EUR m):")
top = top_sectors(portfolio, nz, BASE_PRICE_EUR, **DEFAULTS)
top["loss_eur_m"] = (top.pop("loss_eur") / 1e6).round(0)
print(top.to_string(index=False))

print("\nSensitivity, net effect in % of equity (Current Policies / NDCs / Net Zero 2050):")
cases = {
    "base case": {},
    "pass-through 0 %": dict(pass_through=0.0),
    "pass-through 60 %": dict(pass_through=0.6),
    "debt loss factor 10 %": dict(debt_loss_factor=0.1),
    "debt loss factor 50 %": dict(debt_loss_factor=0.5),
    "nat-cat trend 5 % p.a.": dict(trend=0.05),
    "no repricing": dict(repricing=0.0),
}
for name, kw in cases.items():
    net = trap(**kw)["net_pct_equity"].round(1).tolist()
    print(f"  {name:<24} {' / '.join(f'{v:5.1f}' for v in net)}")
