from pathlib import Path

import pandas as pd

DAILY_FILE = "data/processed/crime/focus_states_daily_county_counts.csv"
POP_FILE = "data/processed/population/focus_states_county_population_2020_2024_long.csv"
OUT_FILE = "data/processed/analysis/parallel_trends_monthly.csv"

EXCLUDED_AZ = {"APACHE", "NAVAJO", "COCONINO"}


def main():
    Path(OUT_FILE).parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(DAILY_FILE, dtype=str)
    df.columns = df.columns.str.strip().str.lower()
    df["incident_date"] = pd.to_datetime(df["incident_date"], errors="coerce")
    df["incident_count"] = pd.to_numeric(df["incident_count"], errors="coerce").fillna(0)
    df["county_name"] = df["county_name"].str.strip().str.upper()

    # Exclude AZ control-group contaminated counties
    df = df[~((df["state"] == "AZ") & (df["county_name"].isin(EXCLUDED_AZ)))]

    df["year"] = df["incident_date"].dt.year
    df["month"] = df["incident_date"].dt.month

    pop = pd.read_csv(POP_FILE, dtype=str)
    pop.columns = pop.columns.str.strip().str.lower()
    pop["county_name"] = pop["county_name"].str.strip().str.upper()
    pop["data_year"] = pd.to_numeric(pop["data_year"], errors="coerce")
    pop["population"] = pd.to_numeric(pop["population"], errors="coerce")

    df = df.merge(
        pop[["state", "county_name", "data_year", "population"]],
        left_on=["state", "county_name", "year"],
        right_on=["state", "county_name", "data_year"],
        how="left",
    )

    df["crime_rate_per_100k"] = df["incident_count"] / df["population"] * 100_000

    monthly = (
        df.groupby(["state", "year", "month", "crime_type"])["crime_rate_per_100k"]
        .mean()
        .reset_index(name="mean_daily_rate_per_100k")
    )

    monthly.to_csv(OUT_FILE, index=False)
    print(f"Saved {len(monthly)} rows -> {OUT_FILE}")


if __name__ == "__main__":
    main()
