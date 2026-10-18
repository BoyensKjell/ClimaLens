"""Physical climate risk on the liability side of a reinsurer.

Simple, transparent factor model (no catastrophe model):

1. Start from the reinsurer's average yearly natural catastrophe losses today (baseline).
2. Grow them with the observed loss trend and a climate multiplier per scenario:
       loss in year t = baseline * (1 + trend)^(t - start_year) * multiplier(t)
   The multiplier rises in a straight line from 1.0 in the start year to the
   scenario's value in the end year.
3. Extra loss = loss in year t - baseline, summed over all years up to the end year.
4. Only the part the reinsurer cannot win back through higher premiums counts:
       extra loss after repricing = extra loss * (1 - repricing_share)
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PhysicalScenario:
    name: str
    climate_multiplier_end: float  # loss multiplier in the end year on top of the trend, 1.0 = no climate effect


# PLACEHOLDER multipliers for development only. Replace with values derived from the
# physical damages in NGFS Phase V before using any result in the report.
PLACEHOLDER_PHYSICAL_SCENARIOS = [
    PhysicalScenario("Current policies (placeholder)", 1.15),
    PhysicalScenario("Delayed transition (placeholder)", 1.10),
    PhysicalScenario("Net zero 2050 (placeholder)", 1.05),
]


def climate_multiplier(scenario: PhysicalScenario, year: int, start_year: int, end_year: int) -> float:
    """Multiplier in one year: 1.0 in the start year, rising in a straight line to the scenario value."""
    progress = (year - start_year) / (end_year - start_year)
    return 1.0 + (scenario.climate_multiplier_end - 1.0) * progress


def extra_physical_losses(
    baseline_eur: float,
    scenario: PhysicalScenario,
    trend: float,
    repricing_share: float,
    start_year: int = 2025,
    end_year: int = 2030,
) -> float:
    """Extra natural catastrophe losses in EUR, summed over the years after start_year up to end_year."""
    if baseline_eur < 0:
        raise ValueError("baseline_eur cannot be negative")
    if not 0 <= repricing_share <= 1:
        raise ValueError("repricing_share must be between 0 and 1")
    if end_year <= start_year:
        raise ValueError("end_year must be after start_year")
    total = 0.0
    for year in range(start_year + 1, end_year + 1):
        loss = baseline_eur * (1 + trend) ** (year - start_year) * climate_multiplier(scenario, year, start_year, end_year)
        total += loss - baseline_eur
    return total * (1 - repricing_share)
