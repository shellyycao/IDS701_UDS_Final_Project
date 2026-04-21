from pathlib import Path

import pandas as pd

IN_FILE = "data/processed/crime/focus_states_daily_county_counts.csv"
POP_FILE = "data/processed/population/focus_states_county_population_2020_2024_long.csv"
OUT_MONTHLY = "data/processed/analysis/monthly_seasonality.csv"
OUT_MONTHLY_YEAR = "data/processed/analysis/monthly_seasonality_by_year.csv"
OUT_DOW = "data/processed/analysis/dow_pattern.csv"
OUT_DOW_YEAR = "data/processed/analysis/dow_pattern_by_year.csv"


def state_pop(pop_file):
    """State-level annual population (sum of non-excluded counties)."""
    pop = pd.read_csv(pop_file, dtype=str)
    pop["population"] = pd.to_numeric(pop["population"], errors="coerce")
    pop["data_year"] = pd.to_numeric(pop["data_year"], errors="coerce")
    pop["proposal_excluded_az_county"] = pop["proposal_excluded_az_county"].map(
        {"True": True, "False": False}
    ).fillna(False)
    pop = pop[~pop["proposal_excluded_az_county"]]
    return pop.groupby(["state", "data_year"])["population"].sum().reset_index()


def main():
    Path(OUT_MONTHLY).parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(IN_FILE, dtype=str)
    df.columns = df.columns.str.strip().str.lower()
    df["incident_date"] = pd.to_datetime(df["incident_date"], errors="coerce")
    df["incident_count"] = pd.to_numeric(df["incident_count"], errors="coerce").fillna(0)
    df["month"] = df["incident_date"].dt.month
    df["year"] = df["incident_date"].dt.year
    df["day_of_week"] = df["incident_date"].dt.dayofweek

    pop = state_pop(POP_FILE)

    monthly_yr = (
        df.groupby(["state", "year", "month", "crime_type"])["incident_count"]
        .mean()
        .reset_index(name="avg_daily_count")
    )
    monthly_yr = monthly_yr.merge(pop, left_on=["state", "year"], right_on=["state", "data_year"], how="left")
    monthly_yr["avg_daily_rate_per_100k"] = monthly_yr["avg_daily_count"] / monthly_yr["population"] * 100_000
    monthly_yr.to_csv(OUT_MONTHLY_YEAR, index=False)
    print(f"Saved {len(monthly_yr)} rows -> {OUT_MONTHLY_YEAR}")

    monthly = monthly_yr.groupby(["state", "month", "crime_type"])[
        ["avg_daily_count", "avg_daily_rate_per_100k"]
    ].mean().reset_index()
    monthly.to_csv(OUT_MONTHLY, index=False)
    print(f"Saved {len(monthly)} rows -> {OUT_MONTHLY}")

    dow_yr = (
        df.groupby(["state", "year", "day_of_week", "crime_type"])["incident_count"]
        .mean()
        .reset_index(name="avg_daily_count")
    )
    dow_yr = dow_yr.merge(pop, left_on=["state", "year"], right_on=["state", "data_year"], how="left")
    dow_yr["avg_daily_rate_per_100k"] = dow_yr["avg_daily_count"] / dow_yr["population"] * 100_000
    dow_yr.to_csv(OUT_DOW_YEAR, index=False)
    print(f"Saved {len(dow_yr)} rows -> {OUT_DOW_YEAR}")

    dow = dow_yr.groupby(["state", "day_of_week", "crime_type"])[
        ["avg_daily_count", "avg_daily_rate_per_100k"]
    ].mean().reset_index()
    dow.to_csv(OUT_DOW, index=False)
    print(f"Saved {len(dow)} rows -> {OUT_DOW}")


if __name__ == "__main__":
    main()
