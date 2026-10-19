# Munich Re figures for the liability side

Taken by hand from the Munich Re group annual reports 2021 to 2025 (German versions). Values in EUR million, net of retrocession.

**Natural catastrophe losses** (`munichre_natcat_losses.csv`): "Großschäden aus Naturkatastrophen" in property-casualty reinsurance. The series is only partly comparable:

- IFRS 4 until 2021, IFRS 17 from 2022 on.
- Large-loss threshold raised from EUR 10m to EUR 30m per loss on 1 January 2023.
- From the 2025 report on, Global Specialty Insurance is reported separately, so 2024 was restated from 2,644 to 1,915.

`natcat_large_losses_meur` uses the latest restated value for each year, `first_reported_meur` the value in that year's own report. The baseline for the liability model is the five-year average: EUR 2,079m with restated values, EUR 2,287m with first-reported values. Both should be shown as a sensitivity.

**Key figures** (`munichre_key_figures.csv`): group equity at year end, used to express both sides of the balance sheet in % of equity.
