from pathlib import Path

import pandas as pd

PANEL_FILE = "data/processed/model/focus_states_daily_county_model_panel_2022_2024.csv"
OUT_FILE = "data/processed/analysis/parallel_trends_monthly.csv"


def main():
    Path(OUT_FILE).parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(PANEL_FILE, low_memory=False)
    df = df[~df["proposal_excluded_az_county"]]
    df["incident_date"] = pd.to_datetime(df["incident_date"])
    df["year"] = df["incident_date"].dt.year
    df["month"] = df["incident_date"].dt.month

    # State total population per year (sum unique county populations)
    state_pop = (
        df.drop_duplicates(["state", "county_fips", "year"])
        .groupby(["state", "year"])["population"].sum()
        .reset_index()
    )

    # Sum all county counts per state-date-crime_type (zero-filled, so all days included)
    daily_state = (
        df.groupby(["state", "year", "month", "incident_date", "crime_type"])["incident_count"]
        .sum()
        .reset_index()
    )
    daily_state = daily_state.merge(state_pop, on=["state", "year"])
    daily_state["crime_rate_per_100k"] = (
        daily_state["incident_count"] / daily_state["population"] * 100_000
    )

    monthly = (
        daily_state.groupby(["state", "year", "month", "crime_type"])["crime_rate_per_100k"]
        .mean()
        .reset_index(name="mean_daily_rate_per_100k")
    )

    monthly.to_csv(OUT_FILE, index=False)
    print(f"Saved {len(monthly)} rows -> {OUT_FILE}")


if __name__ == "__main__":
    main()
