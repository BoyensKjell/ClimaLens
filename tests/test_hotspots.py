import pandas as pd
import pytest

from climalens.hotspots import hotspot_losses, regional_factors
from climalens.liability import PhysicalScenario, extra_physical_losses
from climalens.munichre import load_inputs


def toy():
    return pd.DataFrame({"weight": [0.75, 0.25], "uplift": [0.2, 1.0]})


def test_weighted_mean_of_regional_factors_is_the_global_factor():
    f = regional_factors(toy(), 1.16)
    assert (toy()["weight"] * f).sum() == pytest.approx(1.16)
    assert f[1] > f[0]  # the region with the larger uplift gets the larger factor


def test_hotspots_add_up_to_the_nat_cat_result():
    inp = load_inputs()
    for _, physical in inp.pairs:
        for trend, repricing in [(0.0, 0.5), (0.05, 0.2)]:
            h = hotspot_losses(inp.hotspots, physical, inp.baseline_eur, 2030, trend, repricing)
            total = extra_physical_losses(inp.baseline_eur, physical, trend, repricing)
            assert h["extra_horizon_eur"].sum() == pytest.approx(total)


def test_weights_sum_to_one_and_years_after_2030_continue_the_line():
    inp = load_inputs()
    assert inp.hotspots["weight"].sum() == pytest.approx(1.0)
    sc = PhysicalScenario("x", 1.1)
    h2030 = hotspot_losses(inp.hotspots, sc, 1e9, 2030, 0.0, 0.0)
    h2035 = hotspot_losses(inp.hotspots, sc, 1e9, 2035, 0.0, 0.0)
    assert (h2035["factor_year"] - 1).to_numpy() == pytest.approx(2 * (h2030["factor_year"] - 1).to_numpy())
