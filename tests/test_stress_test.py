import pandas as pd
import pytest

from climalens.stress_test import Scenario, run_stress_test, stress_summary


def make_df():
    return pd.DataFrame({
        "company": ["A", "B"],
        "market_value_eur": [1_000.0, 1_000.0],
        "evic_eur": [100_000.0, 100_000.0],
        "scope1_tco2e": [100.0, None],
        "scope2_tco2e": [0.0, 0.0],
    })


def test_loss_follows_cost_shock_formula():
    res = run_stress_test(make_df(), Scenario("x", 150.0), base_price_eur=100.0,
                          pass_through=0.5, ev_ebitda_multiple=8.0)
    # extra cost = 100 t * 50 EUR * 0.5 = 2,500; loss share = 2,500 * 8 / 100,000 = 20 %
    assert res.loc[0, "loss_share"] == pytest.approx(0.20)
    assert res.loc[0, "loss_eur"] == pytest.approx(200.0)


def test_loss_is_capped_at_full_value():
    res = run_stress_test(make_df(), Scenario("x", 10_000.0), base_price_eur=0.0, pass_through=0.0)
    assert res.loc[0, "loss_share"] == 1.0


def test_summary_reports_holdings_without_data():
    summary = stress_summary(make_df(), [Scenario("x", 150.0)], base_price_eur=100.0)
    assert summary.loc[0, "holdings_without_data"] == 1


def test_pass_through_must_be_a_share():
    with pytest.raises(ValueError):
        run_stress_test(make_df(), Scenario("x", 150.0), base_price_eur=100.0, pass_through=1.5)
