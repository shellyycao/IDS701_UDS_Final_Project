from pathlib import Path

import pandas as pd

IN_FILE = "data/processed/crime/focus_states_hourly_structured.csv"
POP_FILE = "data/processed/population/focus_states_county_population_2020_2024_long.csv"
OUT_HOURLY = "data/processed/analysis/hourly_by_state.csv"
OUT_HOURLY_YEAR = "data/processed/analysis/hourly_by_state_by_year.csv"
OUT_PERIOD = "data/processed/analysis/hourly_by_dst_period.csv"
OUT_PERIOD_YEAR = "data/processed/analysis/hourly_by_dst_period_year.csv"
OUT_SHARES = "data/processed/analysis/evening_morning_share.csv"


def state_avg_pop(pop_file, years):
    pop = pd.read_csv(pop_file, dtype=str)
    pop["population"] = pd.to_numeric(pop["population"], errors="coerce")
    pop["data_year"] = pd.to_numeric(pop["data_year"], errors="coerce")
    pop["proposal_excluded_az_county"] = pop["proposal_excluded_az_county"].map(
        {"True": True, "False": False}
    ).fillna(False)
    pop = pop[pop["data_year"].isin(years) & ~pop["proposal_excluded_az_county"]]
    return pop.groupby("state")["population"].mean().reset_index(name="avg_population")

# DST windows for all available years
DST_WINDOWS = [
    (pd.Timestamp("2022-03-13"), pd.Timestamp("2022-11-06")),
    (pd.Timestamp("2023-03-12"), pd.Timestamp("2023-11-05")),
    (pd.Timestamp("2024-03-10"), pd.Timestamp("2024-11-03")),
]


def is_dst(d):
    if pd.isna(d):
        return False
    return any(start <= d <= end for start, end in DST_WINDOWS)


def main():
    Path(OUT_HOURLY).parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(IN_FILE, dtype=str)
    df.columns = df.columns.str.strip().str.lower()
    df["hour"] = pd.to_numeric(df["hour"], errors="coerce")
    # Drop hour=0: NIBRS agencies code unknown time as 00:00, creating a false spike
    df = df[df["hour"] != 0]
    df["crime_count"] = pd.to_numeric(df["crime_count"], errors="coerce").fillna(0)
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["month"] = pd.to_numeric(df["month"], errors="coerce")
    df["day"] = pd.to_numeric(df["day"], errors="coerce")
    df["date"] = pd.to_datetime(
        dict(year=df["year"], month=df["month"], day=df["day"]), errors="coerce"
    )

    years = df["year"].dropna().unique()
    pop = state_avg_pop(POP_FILE, years)

    # Hourly totals by state (all-year aggregate)
    hourly = (
        df.groupby(["state", "hour", "offense_type"])["crime_count"]
        .sum()
        .reset_index()
    )
    hourly = hourly.merge(pop, on="state", how="left")
    hourly["crime_rate_per_100k"] = hourly["crime_count"] / hourly["avg_population"] * 100_000
    hourly.to_csv(OUT_HOURLY, index=False)
    print(f"Saved {len(hourly)} rows -> {OUT_HOURLY}")

    # Hourly totals by state × year
    pop_annual = pd.read_csv(POP_FILE, dtype=str)
    pop_annual["population"] = pd.to_numeric(pop_annual["population"], errors="coerce")
    pop_annual["data_year"] = pd.to_numeric(pop_annual["data_year"], errors="coerce")
    pop_annual["proposal_excluded_az_county"] = pop_annual["proposal_excluded_az_county"].map(
        {"True": True, "False": False}
    ).fillna(False)
    pop_annual = pop_annual[~pop_annual["proposal_excluded_az_county"]]
    pop_annual = pop_annual.groupby(["state", "data_year"])["population"].sum().reset_index()

    hourly_yr = (
        df.groupby(["state", "year", "hour", "offense_type"])["crime_count"]
        .sum()
        .reset_index()
    )
    hourly_yr = hourly_yr.merge(
        pop_annual, left_on=["state", "year"], right_on=["state", "data_year"], how="left"
    )
    hourly_yr["crime_rate_per_100k"] = hourly_yr["crime_count"] / hourly_yr["population"] * 100_000
    hourly_yr.to_csv(OUT_HOURLY_YEAR, index=False)
    print(f"Saved {len(hourly_yr)} rows -> {OUT_HOURLY_YEAR}")

    # DST period split — all years (2022–2024)
    df["period"] = df["date"].apply(lambda d: "DST" if is_dst(d) else "standard")
    period = (
        df.groupby(["state", "hour", "offense_type", "period"])["crime_count"]
        .sum()
        .reset_index()
    )
    period = period.merge(pop, on="state", how="left")
    period["crime_rate_per_100k"] = period["crime_count"] / period["avg_population"] * 100_000
    period.to_csv(OUT_PERIOD, index=False)
    print(f"Saved {len(period)} rows -> {OUT_PERIOD}")

    # Per-year breakdown — join year-specific population
    pop_annual = pd.read_csv(POP_FILE, dtype=str)
    pop_annual["population"] = pd.to_numeric(pop_annual["population"], errors="coerce")
    pop_annual["data_year"] = pd.to_numeric(pop_annual["data_year"], errors="coerce")
    pop_annual["proposal_excluded_az_county"] = pop_annual["proposal_excluded_az_county"].map(
        {"True": True, "False": False}
    ).fillna(False)
    pop_annual = pop_annual[~pop_annual["proposal_excluded_az_county"]]
    pop_annual = pop_annual.groupby(["state", "data_year"])["population"].sum().reset_index()

    period_year = (
        df.groupby(["state", "year", "hour", "offense_type", "period"])["crime_count"]
        .sum()
        .reset_index()
    )
    period_year = period_year.merge(
        pop_annual, left_on=["state", "year"], right_on=["state", "data_year"], how="left"
    )
    period_year["crime_rate_per_100k"] = period_year["crime_count"] / period_year["population"] * 100_000
    period_year.to_csv(OUT_PERIOD_YEAR, index=False)
    print(f"Saved {len(period_year)} rows -> {OUT_PERIOD_YEAR}")

    # Evening (17-21) and morning (5-9) shares
    EVENING = set(range(17, 22))
    MORNING = set(range(5, 10))

    total = period.groupby(["state", "offense_type", "period"])["crime_count"].sum().reset_index(name="total")
    eve = (
        period[period["hour"].isin(EVENING)]
        .groupby(["state", "offense_type", "period"])["crime_count"]
        .sum()
        .reset_index(name="evening_count")
    )
    morn = (
        period[period["hour"].isin(MORNING)]
        .groupby(["state", "offense_type", "period"])["crime_count"]
        .sum()
        .reset_index(name="morning_count")
    )
    shares = total.merge(eve, on=["state", "offense_type", "period"], how="left")
    shares = shares.merge(morn, on=["state", "offense_type", "period"], how="left")
    shares["evening_share"] = shares["evening_count"] / shares["total"]
    shares["morning_share"] = shares["morning_count"] / shares["total"]
    shares = shares[["state", "offense_type", "period", "evening_share", "morning_share"]]
    shares.to_csv(OUT_SHARES, index=False)
    print(f"Saved {len(shares)} rows -> {OUT_SHARES}")


if __name__ == "__main__":
    main()
