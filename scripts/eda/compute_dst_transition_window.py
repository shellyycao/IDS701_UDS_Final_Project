from pathlib import Path

import pandas as pd

IN_FILE = "data/processed/crime/focus_states_daily_county_counts.csv"
POP_FILE = "data/processed/population/focus_states_county_population_2020_2024_long.csv"
OUT_FILE = "data/processed/analysis/dst_transition_window.csv"

# Spring-forward date per year (2nd Sunday in March)
TRANSITIONS = {
    2022: pd.Timestamp("2022-03-13"),
    2023: pd.Timestamp("2023-03-12"),
    2024: pd.Timestamp("2024-03-10"),
}
WINDOW_DAYS = 14  # ±14 days around transition


def main():
    Path(OUT_FILE).parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(IN_FILE, dtype=str)
    df.columns = df.columns.str.strip().str.lower()
    df["incident_date"] = pd.to_datetime(df["incident_date"], errors="coerce")
    df["incident_count"] = pd.to_numeric(df["incident_count"], errors="coerce").fillna(0)

    frames = []
    for year, transition in TRANSITIONS.items():
        start = transition - pd.Timedelta(days=WINDOW_DAYS)
        end = transition + pd.Timedelta(days=WINDOW_DAYS)
        window = df[(df["incident_date"] >= start) & (df["incident_date"] <= end)].copy()
        avg = (
            window.groupby(["state", "incident_date", "crime_type"])["incident_count"]
            .mean()
            .reset_index(name="avg_daily_count")
        )
        avg["year"] = year
        avg["days_from_transition"] = (avg["incident_date"] - transition).dt.days
        frames.append(avg)

    result = pd.concat(frames, ignore_index=True)
    result["incident_date"] = result["incident_date"].dt.strftime("%Y-%m-%d")

    pop = pd.read_csv(POP_FILE, dtype=str)
    pop["population"] = pd.to_numeric(pop["population"], errors="coerce")
    pop["data_year"] = pd.to_numeric(pop["data_year"], errors="coerce")
    pop["proposal_excluded_az_county"] = pop["proposal_excluded_az_county"].map(
        {"True": True, "False": False}
    ).fillna(False)
    pop = pop[~pop["proposal_excluded_az_county"]]
    pop_state = pop.groupby(["state", "data_year"])["population"].sum().reset_index()

    result = result.merge(pop_state, left_on=["state", "year"], right_on=["state", "data_year"], how="left")
    result["avg_daily_rate_per_100k"] = result["avg_daily_count"] / result["population"] * 100_000
    result = result[["year", "state", "incident_date", "days_from_transition", "crime_type",
                     "avg_daily_count", "avg_daily_rate_per_100k"]]

    result.to_csv(OUT_FILE, index=False)
    print(f"Saved {len(result)} rows ({result['year'].nunique()} years) -> {OUT_FILE}")


if __name__ == "__main__":
    main()
