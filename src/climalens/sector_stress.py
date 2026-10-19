"""Carbon price stress test on a portfolio reported by sector, as insurers publish it.

Munich Re does not publish its single holdings, but it does publish the financed
Scope 1 and 2 emissions and the carrying amount per GICS industry and asset class
(equity, loans, bonds). That is enough for the cost-shock model of stress_test.py,
because the attribution factor cancels out:

    loss on holding = market value * extra cost * ev_ebitda_multiple / EVIC
                    = financed emissions * price shock * (1 - pass_through) * ev_ebitda_multiple

Debt is hurt less than equity: lenders only lose when a company's value falls far
enough. debt_loss_factor is the share of the equity-style loss that hits loans and
bonds. It is an assumption, so run it as a sensitivity.

Each loss is capped at the carrying amount of that sector and asset class.
"""

import pandas as pd

from climalens.stress_test import Scenario

REQUIRED_COLUMNS = ["asset_class", "sector_en", "scope1_financed_tco2e", "scope2_financed_tco2e", "carrying_amount_meur"]
ASSET_CLASSES = {"equity", "loans", "bonds"}


def load_sector_portfolio(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    validate_sector_portfolio(df)
    return df


def validate_sector_portfolio(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Sector portfolio is missing columns: {missing}")
    unknown = set(df["asset_class"]) - ASSET_CLASSES
    if unknown:
        raise ValueError(f"Unknown asset classes: {sorted(unknown)}")
    for col in ["scope1_financed_tco2e", "scope2_financed_tco2e", "carrying_amount_meur"]:
        if (df[col] < 0).any():
            raise ValueError(f"Negative values in {col}")


def run_sector_stress(
    df: pd.DataFrame,
    scenario: Scenario,
    base_price_eur: float,
    pass_through: float = 0.3,
    ev_ebitda_multiple: float = 8.0,
    debt_loss_factor: float = 0.3,
) -> pd.DataFrame:
    """Loss per sector and asset class (EUR) under one carbon price scenario."""
    if not 0 <= pass_through <= 1:
        raise ValueError("pass_through must be between 0 and 1")
    if not 0 <= debt_loss_factor <= 1:
        raise ValueError("debt_loss_factor must be between 0 and 1")
    out = df.copy()
    price_shock = scenario.carbon_price_eur - base_price_eur
    emissions = out["scope1_financed_tco2e"] + out["scope2_financed_tco2e"]
    equity_style_loss = emissions * price_shock * (1 - pass_through) * ev_ebitda_multiple
    factor = out["asset_class"].map(lambda a: 1.0 if a == "equity" else debt_loss_factor)
    carrying_eur = out["carrying_amount_meur"] * 1e6
    out["loss_eur"] = (equity_style_loss * factor).clip(lower=0, upper=carrying_eur)
    out["loss_pct"] = (out["loss_eur"] / carrying_eur * 100).where(carrying_eur > 0, 0.0)
    out["scenario"] = scenario.name
    return out


def sector_stress_summary(df: pd.DataFrame, scenarios: list[Scenario], base_price_eur: float, **kwargs) -> pd.DataFrame:
    """One row per scenario: total loss in EUR and in % of the carrying amount."""
    rows = []
    for sc in scenarios:
        res = run_sector_stress(df, sc, base_price_eur, **kwargs)
        rows.append({
            "scenario": sc.name,
            "carbon_price_eur": sc.carbon_price_eur,
            "loss_eur": res["loss_eur"].sum(),
            "loss_pct": res["loss_eur"].sum() / (res["carrying_amount_meur"].sum() * 1e6) * 100,
            # The interface of double_trap_table expects this column; sector data has no missing holdings.
            "holdings_without_data": 0,
        })
    return pd.DataFrame(rows)


def top_sectors(df: pd.DataFrame, scenario: Scenario, base_price_eur: float, n: int = 5, **kwargs) -> pd.DataFrame:
    """The sectors (all asset classes together) with the largest losses."""
    res = run_sector_stress(df, scenario, base_price_eur, **kwargs)
    grouped = res.groupby("sector_en")[["loss_eur", "carrying_amount_meur"]].sum()
    return grouped.sort_values("loss_eur", ascending=False).head(n).reset_index()
