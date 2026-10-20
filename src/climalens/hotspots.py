"""Where the extra nat-cat losses come from: the liability side split into peril regions (hotspots).

Munich Re does not publish its exposure by country. Its annual report 2025 (p. 103) does list the
net 1-in-200 Value-at-Risk of its largest climate-related nat-cat exposures, for example tropical
cyclones in North America or floods in Germany. These peril regions are the hotspots, and their
share of the total VaR is their weight (the middle of the range where the report gives a range):

    w_r = VaR_r / sum of VaR

Climate change does not raise every peril by the same amount. uplift_r is the expected rise of the
insured losses of one peril region (data/reinsurer/hotspots.csv, with sources). The regional factors
keep the global factor M of each scenario, so the hotspots add up exactly to the nat-cat result of
the stress test:

    M_r = 1 + (M - 1) * uplift_r / sum(w * uplift)

Like the global factor, each M_r rises in a straight line from 1.0 in the start year to its value in
the end year. Later years continue that line; this is an outlook, not a forecast.

Earthquakes are not driven by the climate and are not part of this model.
"""

import pandas as pd

from climalens.liability import PhysicalScenario

REQUIRED_COLUMNS = ["hotspot", "peril", "region", "lat", "lon", "var_low_meur", "var_high_meur", "uplift"]


def load_hotspots(path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Hotspot file is missing columns: {missing}")
    if (df["uplift"] < 0).any() or (df["var_low_meur"] > df["var_high_meur"]).any():
        raise ValueError("Uplifts must be positive and var_low_meur <= var_high_meur")
    df["var_mid_meur"] = (df["var_low_meur"] + df["var_high_meur"]) / 2
    df["weight"] = df["var_mid_meur"] / df["var_mid_meur"].sum()
    return df


def regional_factors(hotspots: pd.DataFrame, multiplier_end: float) -> pd.Series:
    """Loss factor of each hotspot in the end year; their weighted mean equals multiplier_end."""
    mean_uplift = (hotspots["weight"] * hotspots["uplift"]).sum()
    return 1 + (multiplier_end - 1) * hotspots["uplift"] / mean_uplift


def factor_in_year(factor_end: pd.Series, year: int, start_year: int = 2025, end_year: int = 2030) -> pd.Series:
    return 1 + (factor_end - 1) * (year - start_year) / (end_year - start_year)


def hotspot_losses(
    hotspots: pd.DataFrame,
    scenario: PhysicalScenario,
    baseline_eur: float,
    year: int,
    trend: float,
    repricing_share: float,
    start_year: int = 2025,
    end_year: int = 2030,
) -> pd.DataFrame:
    """Extra nat-cat losses per hotspot after repricing: in the chosen year and summed over the stress test horizon."""
    if year <= start_year:
        raise ValueError("year must be after start_year")
    out = hotspots.copy()
    out["factor_end"] = regional_factors(hotspots, scenario.climate_multiplier_end)

    def extra(t: int) -> pd.Series:
        loss = baseline_eur * out["weight"] * (1 + trend) ** (t - start_year) * factor_in_year(out["factor_end"], t, start_year, end_year)
        return (loss - baseline_eur * out["weight"]) * (1 - repricing_share)

    out["factor_year"] = factor_in_year(out["factor_end"], year, start_year, end_year)
    out["extra_year_eur"] = extra(year)
    out["extra_horizon_eur"] = sum(extra(t) for t in range(start_year + 1, end_year + 1))
    out["scenario"] = scenario.name
    out["year"] = year
    return out
