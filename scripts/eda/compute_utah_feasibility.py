from pathlib import Path

import pandas as pd
from scipy import stats

IN_FILE = "data/processed/socioeconomic/acs_county_controls_derived_2021_2024.csv"
OUT_DIST = "data/processed/analysis/acs_distributions_2023.csv"
OUT_MW = "data/processed/analysis/nv_mannwhitney.csv"

VARIABLES = ["median_household_income", "poverty_rate", "unemployment_rate", "bachelors_plus_rate"]
FOCUS_STATES = ["AZ", "CA", "NV"]


def main():
    Path(OUT_DIST).parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(IN_FILE, dtype=str)
    df.columns = df.columns.str.strip().str.lower()
    df["data_year"] = pd.to_numeric(df["data_year"], errors="coerce")
    for v in VARIABLES:
        df[v] = pd.to_numeric(df[v], errors="coerce")
    # Census sentinel for missing values
    df["median_household_income"] = df["median_household_income"].where(
        df["median_household_income"] > 0
    )

    df2023 = df[df["data_year"] == 2023].copy()

    dist = df2023[df2023["state"].isin(FOCUS_STATES)][["state", "county_name"] + VARIABLES].copy()
    dist.to_csv(OUT_DIST, index=False)
    print(f"Saved {len(dist)} rows -> {OUT_DIST}")

    nv = df2023[df2023["state"] == "NV"]
    rows = []
    for var in VARIABLES:
        nv_vals = nv[var].dropna().values
        for state in [s for s in FOCUS_STATES if s != "NV"]:
            other_vals = df2023[df2023["state"] == state][var].dropna().values
            u_stat, p_val = stats.mannwhitneyu(nv_vals, other_vals, alternative="two-sided")
            rows.append({
                "variable": var,
                "state_compared": state,
                "u_statistic": round(u_stat, 2),
                "p_value": round(p_val, 4),
            })

    mw = pd.DataFrame(rows)
    mw.to_csv(OUT_MW, index=False)
    print(f"Saved {len(mw)} rows -> {OUT_MW}")
    print(mw.to_string(index=False))


if __name__ == "__main__":
    main()
