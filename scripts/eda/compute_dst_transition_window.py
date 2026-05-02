from pathlib import Path

import pandas as pd

PANEL_FILE = "data/processed/model/focus_states_daily_county_model_panel_2022_2024.csv"
OUT_FILE = "data/processed/analysis/dst_transition_window.csv"

WINDOW_DAYS = 14  # ±14 days around spring-forward (days_from_dst_start = 0)


def main():
    Path(OUT_FILE).parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(PANEL_FILE, low_memory=False)
    df = df[~df["proposal_excluded_az_county"]]
    df["incident_date"] = pd.to_datetime(df["incident_date"])
    df["year"] = df["incident_date"].dt.year

    window = df[
        (df["days_from_dst_start"] >= -WINDOW_DAYS) &
        (df["days_from_dst_start"] <= WINDOW_DAYS)
    ].copy()

    # State total population per year
    state_pop = (
        window.drop_duplicates(["state", "county_fips", "year"])
        .groupby(["state", "year"])["population"].sum()
        .reset_index()
    )

    # Sum all county counts per state-date-crime_type
    daily_state = (
        window.groupby(["state", "year", "incident_date", "crime_type", "days_from_dst_start"])
        ["incident_count"].sum()
        .reset_index()
    )
    daily_state = daily_state.merge(state_pop, on=["state", "year"])
    daily_state["avg_daily_rate_per_100k"] = (
        daily_state["incident_count"] / daily_state["population"] * 100_000
    )
    daily_state = daily_state.rename(columns={
        "incident_count": "avg_daily_count",
        "days_from_dst_start": "days_from_transition",
    })
    daily_state["incident_date"] = daily_state["incident_date"].dt.strftime("%Y-%m-%d")

    result = daily_state[[
        "year", "state", "incident_date", "days_from_transition", "crime_type",
        "avg_daily_count", "avg_daily_rate_per_100k",
    ]]

    result.to_csv(OUT_FILE, index=False)
    print(f"Saved {len(result)} rows ({result['year'].nunique()} years) -> {OUT_FILE}")


if __name__ == "__main__":
    main()
