# Munich Re figures for the liability side

Taken by hand from the Munich Re group annual reports 2021 to 2025 (German versions). Values in EUR million, net of retrocession.

**Natural catastrophe losses** (`munichre_natcat_losses.csv`): "Großschäden aus Naturkatastrophen" in property-casualty reinsurance. The series is only partly comparable:

- IFRS 4 until 2021, IFRS 17 from 2022 on.
- Large-loss threshold raised from EUR 10m to EUR 30m per loss on 1 January 2023.
- From the 2025 report on, Global Specialty Insurance is reported separately, so 2024 was restated from 2,644 to 1,915.

`natcat_large_losses_meur` uses the latest restated value for each year, `first_reported_meur` the value in that year's own report. The baseline for the liability model is the five-year average: EUR 2,079m with restated values, EUR 2,287m with first-reported values. Both should be shown as a sensitivity.

**Key figures** (`munichre_key_figures.csv`): group equity at year end, used to express both sides of the balance sheet in % of equity.

**Sector portfolio** (`munichre_financed_emissions_2025.csv`): table "Finanzierte Emissionen, aufgeschlüsselt nach GICS-Industriezweigen", group annual report 2025, pp. 115–117. Financed Scope 1 and 2 emissions (t CO2e) and gross carrying amount (EUR m) per GICS industry for equity, loans and bonds at 31.12.2025. Undrawn loan commitments are left out. Row sums differ from the report totals by at most 2 because the report rounds each row. Sovereign bonds are not in this table; they are not hit directly by a carbon price on companies.

**Scenarios** (`scenarios_2030.csv`): carbon price in 2030 (US$2010/t CO2) and nat-cat loss multiplier for 2030 per NGFS scenario, with source and status. Research notes with all quotes: `quellen/ngfs_werte.md` in the project folder.

**Hotspots** (`hotspots.csv`): the nat-cat side split into Munich Re's five largest climate-related peril regions. `var_low_meur`/`var_high_meur` are the net 1-in-200 Value-at-Risk from the group annual report 2025, p. 103 (one value or a range). `uplift` is the climate-driven rise of insured losses by 2040 at 1.5°C from Swiss Re sigma 4/2021 (pp. 19–20); only the relative size between the regions matters, because the regional factors are calibrated to the global factor of each scenario (`src/climalens/hotspots.py`). Severe convective storms have no peril-specific source and use the middle of the sigma all-peril range as an assumption. The flood value (+200 %) is high compared with RMS (Europe flood +34–75 % by 2050) and should be checked.
