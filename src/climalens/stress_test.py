"""Carbon price stress test for an insurer's investment portfolio.

Simple, transparent cost-shock approach:

1. A higher carbon price raises each company's costs:
       extra cost = (Scope 1 + Scope 2) * (scenario price - base price) * (1 - pass_through)
   pass_through = share of the extra cost the company can pass on to its customers.
2. Lower earnings lower the company's value:
       loss in enterprise value = extra cost * ev_ebitda_multiple
3. The holding loses the same share of its value as the company:
       loss share = loss in enterprise value / EVIC   (capped at 100 %)
       loss on holding = market value * loss share

Companies without emissions data are reported separately, never treated as zero emissions.
"""

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Scenario:
    name: str
    carbon_price_eur: float  # EUR per tCO2e in the stress year


# PLACEHOLDER prices for development only. Replace with the carbon prices of the
# NGFS scenarios (e.g. Current Policies, Delayed Transition, Net Zero 2050) before
# using any result in the report.
PLACEHOLDER_SCENARIOS = [
    Scenario("Current policies (placeholder)", 80.0),
    Scenario("Delayed transition (placeholder)", 150.0),
    Scenario("Net zero 2050 (placeholder)", 250.0),
]


def run_stress_test(
    df: pd.DataFrame,
    scenario: Scenario,
    base_price_eur: float,
    pass_through: float = 0.3,
    ev_ebitda_multiple: float = 8.0,
) -> pd.DataFrame:
    """Loss per holding (EUR and share of market value) under one carbon price scenario."""
    if not 0 <= pass_through <= 1:
        raise ValueError("pass_through must be between 0 and 1")
    out = df.copy()
    price_shock = scenario.carbon_price_eur - base_price_eur
    emissions = out["scope1_tco2e"] + out["scope2_tco2e"]
    out["extra_cost_eur"] = emissions * price_shock * (1 - pass_through)
    out["loss_share"] = (out["extra_cost_eur"] * ev_ebitda_multiple / out["evic_eur"]).clip(upper=1.0)
    out["loss_eur"] = out["market_value_eur"] * out["loss_share"]
    out["scenario"] = scenario.name
    return out


def stress_summary(
    df: pd.DataFrame,
    scenarios: list[Scenario],
    base_price_eur: float,
    **kwargs,
) -> pd.DataFrame:
    """One row per scenario: total loss in EUR and in % of the invested amount."""
    rows = []
    for sc in scenarios:
        res = run_stress_test(df, sc, base_price_eur, **kwargs)
        covered = res["loss_eur"].notna()
        rows.append({
            "scenario": sc.name,
            "carbon_price_eur": sc.carbon_price_eur,
            "loss_eur": res.loc[covered, "loss_eur"].sum(),
            "loss_pct": res.loc[covered, "loss_eur"].sum() / res["market_value_eur"].sum() * 100,
            "holdings_without_data": int((~covered).sum()),
        })
    return pd.DataFrame(rows)
