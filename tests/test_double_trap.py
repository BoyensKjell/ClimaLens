import pandas as pd
import pytest

from climalens.double_trap import double_trap_table
from climalens.liability import PhysicalScenario
from climalens.stress_test import Scenario


def make_df():
    return pd.DataFrame({
        "company": ["A"],
        "market_value_eur": [1_000.0],
        "evic_eur": [100_000.0],
        "scope1_tco2e": [100.0],
        "scope2_tco2e": [0.0],
    })


def test_net_effect_adds_both_sides_in_pct_of_equity():
    table = double_trap_table(
        make_df(),
        [(Scenario("x", 150.0), PhysicalScenario("x", 1.10))],
        base_price_eur=100.0,
        baseline_losses_eur=1_000.0,
        trend=0.0,
        repricing_share=0.5,
        equity_eur=1_000.0,
        start_year=2025,
        end_year=2027,
        pass_through=0.5,
        ev_ebitda_multiple=8.0,
    )
    row = table.iloc[0]
    # asset loss 200 (see test_stress_test), liability extra 75 (see test_liability)
    assert row["asset_pct_equity"] == pytest.approx(20.0)
    assert row["liability_pct_equity"] == pytest.approx(7.5)
    assert row["net_pct_equity"] == pytest.approx(27.5)


def test_equity_must_be_positive():
    with pytest.raises(ValueError):
        double_trap_table(make_df(), [], 100.0, 1_000.0, 0.0, 0.0, equity_eur=0.0)
