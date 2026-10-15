"""Financed emissions of a portfolio, following the PCAF standard for listed equity and corporate bonds.

PCAF attributes a company's emissions to an investor in proportion to how much of the
company the investor finances:

    attribution factor = market value of the holding / EVIC
    financed emissions = attribution factor * (Scope 1 + Scope 2)

EVIC = enterprise value including cash (market capitalisation + debt), in EUR.
"""

import pandas as pd

REQUIRED_COLUMNS = ["company", "market_value_eur", "evic_eur", "scope1_tco2e", "scope2_tco2e"]


def load_portfolio(path: str) -> pd.DataFrame:
    """Read a portfolio CSV and check that every required column is present and usable."""
    df = pd.read_csv(path)
    validate_portfolio(df)
    return df


def validate_portfolio(df: pd.DataFrame) -> None:
    """Raise a ValueError that says exactly what is wrong, instead of silently computing nonsense."""
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Portfolio is missing columns: {missing}")
    if df["company"].duplicated().any():
        dupes = df.loc[df["company"].duplicated(), "company"].tolist()
        raise ValueError(f"Companies listed more than once: {dupes}")
    if (df["evic_eur"] <= 0).any():
        raise ValueError("EVIC must be positive for every company")
    if (df["market_value_eur"] > df["evic_eur"]).any():
        raise ValueError("A holding cannot be worth more than the whole company (market value > EVIC)")
    # Missing emissions stay missing: 'not reported' is not the same as zero.
    for col in ["scope1_tco2e", "scope2_tco2e"]:
        if (df[col] < 0).any():
            raise ValueError(f"Negative values in {col}")


def financed_emissions(df: pd.DataFrame) -> pd.DataFrame:
    """Add attribution factor and financed emissions (tCO2e) per holding."""
    out = df.copy()
    out["attribution_factor"] = out["market_value_eur"] / out["evic_eur"]
    out["financed_tco2e"] = out["attribution_factor"] * (out["scope1_tco2e"] + out["scope2_tco2e"])
    return out


def portfolio_summary(df: pd.DataFrame) -> dict:
    """Headline numbers for the whole portfolio.

    Carbon footprint = financed emissions per EUR 1 million invested, the usual way
    insurers compare portfolios of different sizes.
    """
    fe = financed_emissions(df)
    covered = fe["financed_tco2e"].notna()
    invested = fe["market_value_eur"].sum()
    invested_covered = fe.loc[covered, "market_value_eur"].sum()
    total = fe.loc[covered, "financed_tco2e"].sum()
    return {
        "invested_eur": invested,
        "financed_tco2e": total,
        "footprint_tco2e_per_meur": total / (invested_covered / 1e6) if invested_covered else float("nan"),
        "data_coverage": invested_covered / invested if invested else float("nan"),
    }
