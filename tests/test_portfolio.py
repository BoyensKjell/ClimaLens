import math

import pandas as pd
import pytest

from climalens.portfolio import financed_emissions, portfolio_summary, validate_portfolio


def make_df(**overrides):
    data = {
        "company": ["A", "B"],
        "market_value_eur": [10.0, 30.0],
        "evic_eur": [100.0, 300.0],
        "scope1_tco2e": [50.0, 10.0],
        "scope2_tco2e": [50.0, 20.0],
    }
    data.update(overrides)
    return pd.DataFrame(data)


def test_financed_emissions_use_attribution_factor():
    fe = financed_emissions(make_df())
    # A: 10/100 * 100 = 10; B: 30/300 * 30 = 3
    assert fe["financed_tco2e"].tolist() == pytest.approx([10.0, 3.0])


def test_missing_emissions_are_not_counted_as_zero():
    s = portfolio_summary(make_df(scope1_tco2e=[50.0, None]))
    assert s["data_coverage"] == pytest.approx(10 / 40)
    assert s["financed_tco2e"] == pytest.approx(10.0)
    assert s["footprint_tco2e_per_meur"] == pytest.approx(10.0 / (10 / 1e6))


def test_rejects_duplicate_companies():
    with pytest.raises(ValueError, match="more than once"):
        validate_portfolio(make_df(company=["A", "A"]))


def test_rejects_holding_larger_than_company():
    with pytest.raises(ValueError, match="EVIC"):
        validate_portfolio(make_df(market_value_eur=[200.0, 30.0]))
