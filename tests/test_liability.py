import pytest

from climalens.liability import PhysicalScenario, climate_multiplier, extra_physical_losses


def test_no_trend_and_no_climate_effect_means_no_extra_loss():
    assert extra_physical_losses(1_000.0, PhysicalScenario("x", 1.0), trend=0.0, repricing_share=0.0) == 0.0


def test_multiplier_rises_in_a_straight_line():
    sc = PhysicalScenario("x", 1.2)
    assert climate_multiplier(sc, 2025, 2025, 2030) == pytest.approx(1.0)
    assert climate_multiplier(sc, 2030, 2025, 2030) == pytest.approx(1.2)
    assert climate_multiplier(sc, 2027, 2025, 2029) == pytest.approx(1.1)


def test_extra_loss_follows_formula():
    # two years, no trend: multipliers 1.05 and 1.10 -> extra 50 + 100 = 150, half won back by repricing
    res = extra_physical_losses(1_000.0, PhysicalScenario("x", 1.10), trend=0.0, repricing_share=0.5,
                                start_year=2025, end_year=2027)
    assert res == pytest.approx(75.0)


def test_trend_alone_raises_losses():
    # one year, 10 % trend, no climate effect -> extra 100
    res = extra_physical_losses(1_000.0, PhysicalScenario("x", 1.0), trend=0.1, repricing_share=0.0,
                                start_year=2025, end_year=2026)
    assert res == pytest.approx(100.0)


def test_repricing_share_must_be_a_share():
    with pytest.raises(ValueError):
        extra_physical_losses(1_000.0, PhysicalScenario("x", 1.1), trend=0.0, repricing_share=1.5)
