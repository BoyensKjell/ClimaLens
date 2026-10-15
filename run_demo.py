"""Run the stress test on the demo portfolio: python run_demo.py"""

import sys

sys.path.insert(0, "src")

from climalens.portfolio import financed_emissions, load_portfolio, portfolio_summary  # noqa: E402
from climalens.stress_test import PLACEHOLDER_SCENARIOS, stress_summary  # noqa: E402

df = load_portfolio("data/examples/demo_portfolio.csv")

print("Financed emissions per holding (tCO2e):")
print(financed_emissions(df)[["company", "attribution_factor", "financed_tco2e"]].round(5).to_string(index=False))

s = portfolio_summary(df)
print(f"\nInvested: EUR {s['invested_eur'] / 1e6:,.0f} m")
print(f"Financed emissions: {s['financed_tco2e']:,.0f} tCO2e")
print(f"Footprint: {s['footprint_tco2e_per_meur']:,.1f} tCO2e per EUR m invested")
print(f"Data coverage: {s['data_coverage']:.0%} of invested amount")

print("\nStress test (placeholder carbon prices, base EUR 70/t):")
summary = stress_summary(df, PLACEHOLDER_SCENARIOS, base_price_eur=70.0)
summary["loss_eur_m"] = (summary.pop("loss_eur") / 1e6).round(1)
summary["loss_pct"] = summary["loss_pct"].round(1)
print(summary.to_string(index=False))
