"""Both sides of the balance sheet per climate scenario: is there a 'double climate trap'?

Asset side:     loss on the investment portfolio from a higher carbon price (stress_test.py)
Liability side: extra natural catastrophe losses up to the end year (liability.py)

Both are shown in % of the reinsurer's equity, so they can be added up:

    net effect = asset loss + liability extra loss

Double trap:   the net effect is high in every scenario.
Natural hedge: in each scenario only one side is high, so the net effect stays similar.
"""

import pandas as pd

from climalens.liability import PhysicalScenario, extra_physical_losses
from climalens.stress_test import Scenario, stress_summary


def double_trap_table(
    portfolio: pd.DataFrame,
    scenarios: list[tuple[Scenario, PhysicalScenario]],
    base_price_eur: float,
    baseline_losses_eur: float,
    trend: float,
    repricing_share: float,
    equity_eur: float,
    start_year: int = 2025,
    end_year: int = 2030,
    **stress_kwargs,
) -> pd.DataFrame:
    """One row per scenario pair: asset loss, liability extra loss and net effect in EUR and % of equity."""
    if equity_eur <= 0:
        raise ValueError("equity_eur must be positive")
    rows = []
    for transition, physical in scenarios:
        asset = stress_summary(portfolio, [transition], base_price_eur, **stress_kwargs).iloc[0]
        liability = extra_physical_losses(
            baseline_losses_eur, physical, trend, repricing_share, start_year, end_year
        )
        rows.append({
            "scenario": transition.name,
            "asset_loss_eur": asset["loss_eur"],
            "liability_extra_eur": liability,
            "asset_pct_equity": asset["loss_eur"] / equity_eur * 100,
            "liability_pct_equity": liability / equity_eur * 100,
            "net_pct_equity": (asset["loss_eur"] + liability) / equity_eur * 100,
            "holdings_without_data": asset["holdings_without_data"],
        })
    return pd.DataFrame(rows)
