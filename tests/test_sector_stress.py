import pandas as pd
import pytest

from climalens.portfolio import financed_emissions
from climalens.sector_stress import run_sector_stress, sector_stress_summary, validate_sector_portfolio
from climalens.stress_test import Scenario, run_stress_test


def sector_df():
    return pd.DataFrame({
        "asset_class": ["equity", "bonds"],
        "sector_en": ["Utilities", "Utilities"],
        "scope1_financed_tco2e": [1000.0, 1000.0],
        "scope2_financed_tco2e": [0.0, 0.0],
        "carrying_amount_meur": [10.0, 10.0],
    })


def test_matches_holding_level_model_for_equity():
    # One holding: 1 % of a company with 100,000 t emissions -> 1,000 t financed.
    holding = pd.DataFrame({"company": ["A"], "market_value_eur": [10e6], "evic_eur": [1e9],
                            "scope1_tco2e": [100_000.0], "scope2_tco2e": [0.0]})
    sc = Scenario("test", 170.0)
    expected = run_stress_test(holding, sc, 70.0)["loss_eur"].iloc[0]
    sector = sector_df().iloc[[0]].assign(scope1_financed_tco2e=financed_emissions(holding)["financed_tco2e"].iloc[0])
    assert run_sector_stress(sector, sc, 70.0)["loss_eur"].iloc[0] == pytest.approx(expected)


def test_debt_loses_less_than_equity():
    res = run_sector_stress(sector_df(), Scenario("test", 170.0), 70.0, debt_loss_factor=0.3)
    equity, bonds = res["loss_eur"]
    assert bonds == pytest.approx(0.3 * equity)


def test_loss_capped_at_carrying_amount():
    res = run_sector_stress(sector_df(), Scenario("extreme", 1e6), 0.0)
    assert (res["loss_eur"] <= 10e6).all()


def test_no_gain_when_price_falls():
    res = run_sector_stress(sector_df(), Scenario("lower", 10.0), 70.0)
    assert (res["loss_eur"] == 0).all()


def test_summary_percent_of_carrying_amount():
    s = sector_stress_summary(sector_df(), [Scenario("test", 170.0)], 70.0, debt_loss_factor=0.0)
    # equity loss = 1000 t * 100 EUR * 0.7 * 8 = 560,000 EUR on 20 m carrying amount
    assert s["loss_eur"].iloc[0] == pytest.approx(560_000)
    assert s["loss_pct"].iloc[0] == pytest.approx(2.8)


def test_rejects_unknown_asset_class():
    with pytest.raises(ValueError):
        validate_sector_portfolio(sector_df().assign(asset_class=["equity", "cash"]))
