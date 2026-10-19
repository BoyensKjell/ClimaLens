"""Munich Re inputs and the double climate trap with real data, shared by run_munichre.py and the web app.

Asset side:     financed emissions and carrying amounts per sector (Munich Re annual report 2025, pp. 115-117)
Liability side: average net nat-cat large losses 2021-2025 (Munich Re annual reports, restated values)
Scenarios:      NGFS Phase V carbon prices for 2030 and a nat-cat multiplier per scenario
                (sources and status in data/reinsurer/scenarios_2030.csv)
"""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from climalens.double_trap import double_trap_table
from climalens.liability import PhysicalScenario
from climalens.sector_stress import load_sector_portfolio, sector_stress_summary
from climalens.stress_test import Scenario

# US$2010 -> EUR 2025: US consumer prices rose about 47 % from 2010 to 2025, and
# 1 EUR was worth about 1.13 USD on average in 2025. 1.47 / 1.13 = 1.30. To be checked.
USD2010_TO_EUR2025 = 1.30
# NGFS prices are global shadow prices that are close to zero today, so the full 2030
# price is treated as the extra carbon cost.
BASE_PRICE_EUR = 0.0

# Base case assumptions; the web app lets the user change each of them.
STRESS_DEFAULTS = dict(pass_through=0.3, ev_ebitda_multiple=8.0, debt_loss_factor=0.3)
TREND = 0.0  # 0 = climate effect only; exposure growth is matched by premium growth
REPRICING = 0.5  # share of extra losses recovered through higher prices at renewal

DATA = Path(__file__).resolve().parents[2] / "data" / "reinsurer"


@dataclass(frozen=True)
class Inputs:
    portfolio: pd.DataFrame
    scenarios: pd.DataFrame
    pairs: list[tuple[Scenario, PhysicalScenario]]
    natcat: pd.DataFrame
    baseline_eur: float
    equity_eur: float


def load_inputs(data_dir: Path = DATA) -> Inputs:
    natcat = pd.read_csv(data_dir / "munichre_natcat_losses.csv")
    key = pd.read_csv(data_dir / "munichre_key_figures.csv")
    scenarios = pd.read_csv(data_dir / "scenarios_2030.csv")
    pairs = [
        (Scenario(r.scenario, r.carbon_price_2030_usd2010 * USD2010_TO_EUR2025),
         PhysicalScenario(r.scenario, r.natcat_multiplier_2030))
        for r in scenarios.itertuples()
    ]
    return Inputs(
        portfolio=load_sector_portfolio(data_dir / "munichre_financed_emissions_2025.csv"),
        scenarios=scenarios,
        pairs=pairs,
        natcat=natcat,
        baseline_eur=natcat["natcat_large_losses_meur"].mean() * 1e6,
        equity_eur=key.loc[key["item"] == "group_equity", "value_meur"].iloc[0] * 1e6,
    )


def trap(inputs: Inputs, trend: float = TREND, repricing: float = REPRICING, **stress) -> pd.DataFrame:
    """Double climate trap table for Munich Re; any argument left out uses the base case."""
    return double_trap_table(
        inputs.portfolio, inputs.pairs, BASE_PRICE_EUR, inputs.baseline_eur, trend, repricing,
        inputs.equity_eur, asset_summary=sector_stress_summary, **{**STRESS_DEFAULTS, **stress},
    )
