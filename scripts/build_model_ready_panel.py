import re
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

PANEL_FILE = "data/processed/panel/focus_states_incident_offense_panel.csv"
TZ_FILE = "data/raw/timezone/focus_states_county_centroids_timezone.csv"
POP_FILE = "data/processed/population/focus_states_county_population_2020_2024_long.csv"
HOLIDAYS_FILE = "data/raw/holidays/us_public_holidays_2021_2024.csv"
ACS_FILE = "data/processed/socioeconomic/acs_county_controls_derived_2021_2024.csv"
WEATHER_FILE = "data/raw/weather/focus_states_daily_weather_2021_2024.csv"

OUT_FULL = "data/processed/model/focus_states_daily_county_model_panel_2021_2024.csv"
OUT_2022 = "data/processed/model/focus_states_daily_county_model_panel_2022_2024.csv"

CRIME_TYPES = ["robbery", "burglary", "shoplifting",
               "theft_from_building", "theft_from_motor_vehicle", "motor_vehicle_theft"]
TREATED_STATES = {"CA", "NV", "UT"}
START_DATE = date(2021, 1, 1)
END_DATE = date(2024, 12, 31)


def nth_weekday(year, month, weekday, n):
    first = date(year, month, 1)
    delta = (weekday - first.weekday()) % 7
    return first + timedelta(days=delta) + timedelta(weeks=n - 1)


def dst_bounds(year):
    return nth_weekday(year, 3, 6, 2), nth_weekday(year, 11, 6, 1)


def normalize_county_name(name):
    name = str(name).upper()
    name = re.sub(r"\s+COUNTY$", "", name)
    name = re.sub(r"\s+PARISH$", "", name)
    name = re.sub(r"[^A-Z0-9 ]", "", name)
    return name.strip()


def main():
    Path(OUT_FULL).parent.mkdir(parents=True, exist_ok=True)

    print("Loading timezone file...")
    tz = pd.read_csv(TZ_FILE, dtype=str)
    tz.columns = tz.columns.str.strip().str.lower()
    tz["county_fips"] = tz["county_fips"].str.zfill(5)

    print("Building skeleton (county × date × crime_type)...")
    dates = pd.date_range(START_DATE.isoformat(), END_DATE.isoformat(), freq="D")
    counties = tz[["state", "county_fips", "timezone"]].drop_duplicates()

    skel_parts = []
    for ct in CRIME_TYPES:
        tmp = counties.copy()
        tmp["crime_type"] = ct
        skel_parts.append(tmp)
    skeleton = pd.concat(skel_parts, ignore_index=True)

    date_df = pd.DataFrame({"incident_date": dates})
    skeleton = skeleton.merge(date_df, how="cross")
    skeleton["incident_date"] = pd.to_datetime(skeleton["incident_date"])
    print(f"  Skeleton: {len(skeleton):,} rows")

    print("Loading incident panel...")
    panel = pd.read_csv(PANEL_FILE, dtype=str, low_memory=False)
    panel.columns = panel.columns.str.strip().str.lower()
    panel["incident_date"] = pd.to_datetime(panel["incident_date"], errors="coerce")

    # county_fips may not be in the panel — join from timezone lookup via county_name
    if "county_fips" not in panel.columns or panel.get("county_fips", pd.Series(dtype=str)).isna().all():
        tz_lookup = tz[["state", "county_name", "county_fips"]].copy()
        tz_lookup["county_name"] = tz_lookup["county_name"].str.upper()
        panel["county_name"] = panel["county_name"].str.upper()
        panel = panel.merge(tz_lookup, on=["state", "county_name"], how="left")

    panel["county_fips"] = panel["county_fips"].astype(str).str.zfill(5)
    panel = panel.dropna(subset=["incident_date", "county_fips", "crime_type"])

    counts = (
        panel.groupby(["state", "county_fips", "incident_date", "crime_type"])
        .size()
        .reset_index(name="incident_count")
    )

    print("Merging counts onto skeleton...")
    full = skeleton.merge(counts, on=["state", "county_fips", "incident_date", "crime_type"], how="left")
    full["incident_count"] = full["incident_count"].fillna(0).astype(int)

    print("Joining population...")
    pop = pd.read_csv(POP_FILE, dtype=str)
    pop.columns = pop.columns.str.strip().str.lower()
    pop["county_fips"] = pop["county_fips"].str.zfill(5)
    pop["data_year"] = pop["data_year"].astype(int)
    pop["population"] = pd.to_numeric(pop["population"], errors="coerce")

    full["data_year"] = full["incident_date"].dt.year
    full = full.merge(
        pop[["state", "county_fips", "data_year", "population", "proposal_excluded_az_county"]],
        on=["state", "county_fips", "data_year"],
        how="left",
    )

    print("Joining socioeconomic controls...")
    acs = pd.read_csv(ACS_FILE, dtype=str)
    acs.columns = acs.columns.str.strip().str.lower()
    acs["county_fips"] = acs["county_fips"].str.zfill(5)
    acs["data_year"] = acs["data_year"].astype(int)
    for col in ["median_household_income", "poverty_rate", "unemployment_rate", "bachelors_plus_rate"]:
        acs[col] = pd.to_numeric(acs[col], errors="coerce")

    full = full.merge(
        acs[["state", "county_fips", "data_year",
             "median_household_income", "poverty_rate", "unemployment_rate", "bachelors_plus_rate"]],
        on=["state", "county_fips", "data_year"],
        how="left",
    )

    print("Joining holidays...")
    holidays = pd.read_csv(HOLIDAYS_FILE, dtype=str)
    holidays.columns = holidays.columns.str.strip().str.lower()
    holidays["date"] = pd.to_datetime(holidays["date"], errors="coerce")
    holidays = holidays.drop_duplicates(subset=["date"])[["date", "name"]].rename(
        columns={"name": "holiday_name"}
    )
    full = full.merge(holidays, left_on="incident_date", right_on="date", how="left")
    full.drop(columns=["date"], errors="ignore", inplace=True)
    full["is_holiday"] = full["holiday_name"].notna().astype(int)

    if Path(WEATHER_FILE).exists():
        print("Joining weather...")
        weather = pd.read_csv(WEATHER_FILE, dtype=str)
        weather.columns = weather.columns.str.strip().str.lower()
        weather["date"] = pd.to_datetime(weather["date"], errors="coerce")
        weather["county_fips"] = weather["county_fips"].str.zfill(5)
        for col in ["temperature_2m_mean", "temperature_2m_min", "temperature_2m_max", "precipitation_sum"]:
            if col in weather.columns:
                weather[col] = pd.to_numeric(weather[col], errors="coerce")
        full = full.merge(
            weather[["state", "county_fips", "date",
                      "temperature_2m_mean", "temperature_2m_min",
                      "temperature_2m_max", "precipitation_sum"]],
            left_on=["state", "county_fips", "incident_date"],
            right_on=["state", "county_fips", "date"],
            how="left",
        )
        full.drop(columns=["date"], errors="ignore", inplace=True)
    else:
        print("  Weather file not found — skipping.")
        for col in ["temperature_2m_mean", "temperature_2m_min", "temperature_2m_max", "precipitation_sum"]:
            full[col] = np.nan

    print("Computing derived variables...")
    full["population"] = pd.to_numeric(full["population"], errors="coerce")
    full["crime_rate_per_100k"] = np.where(
        full["population"] > 0,
        full["incident_count"] / full["population"] * 100_000,
        np.nan,
    )
    full["log_rate"] = np.log1p(full["crime_rate_per_100k"])
    full["day_of_week"] = full["incident_date"].dt.dayofweek
    full["is_weekend"] = (full["day_of_week"] >= 5).astype(int)
    full["month"] = full["incident_date"].dt.month

    dst_bounds_by_year = {yr: dst_bounds(yr) for yr in range(2021, 2025)}
    full["observes_dst_county"] = (full["timezone"] != "America/Phoenix").astype(int)
    full["treated_state"] = full["state"].isin(TREATED_STATES).astype(int)
    full["is_az_control"] = (full["state"] == "AZ").astype(int)

    def compute_dst_flags(row):
        yr = row["incident_date"].year
        if yr not in dst_bounds_by_year:
            return pd.Series({"in_dst_window": 0, "days_from_dst_start": np.nan,
                              "days_from_dst_end": np.nan})
        dst_start, dst_end = dst_bounds_by_year[yr]
        d = row["incident_date"].date()
        observes = row["observes_dst_county"] == 1
        in_window = int(observes and dst_start <= d <= dst_end)
        days_start = (d - dst_start).days
        days_end = (d - dst_end).days
        return pd.Series({"in_dst_window": in_window,
                          "days_from_dst_start": days_start,
                          "days_from_dst_end": days_end})

    dst_cols = full.apply(compute_dst_flags, axis=1)
    full = pd.concat([full, dst_cols], axis=1)

    full["county_fips"] = full["county_fips"].str.zfill(5)

    dup_count = full.duplicated(subset=["state", "county_fips", "incident_date", "crime_type"]).sum()
    missing_pop_share = full["population"].isna().mean()
    missing_tz = full["timezone"].isna().sum()
    zero_share = (full["incident_count"] == 0).mean()

    print("\n=== INTEGRITY SUMMARY ===")
    print(f"  Total rows:             {len(full):,}")
    print(f"  Duplicate keys:         {dup_count}")
    print(f"  Missing population:     {missing_pop_share:.1%}")
    print(f"  Missing timezone:       {missing_tz}")
    print(f"  Zero incident share:    {zero_share:.3f}")
    print("=========================\n")

    out_cols = [
        "state", "county_fips", "incident_date", "crime_type", "data_year", "month",
        "day_of_week", "is_weekend", "is_holiday", "holiday_name",
        "timezone", "observes_dst_county", "treated_state", "is_az_control",
        "in_dst_window", "days_from_dst_start", "days_from_dst_end",
        "incident_count", "population", "crime_rate_per_100k", "log_rate",
        "median_household_income", "poverty_rate", "unemployment_rate", "bachelors_plus_rate",
        "temperature_2m_mean", "temperature_2m_min", "temperature_2m_max", "precipitation_sum",
        "proposal_excluded_az_county",
    ]
    out_cols = [c for c in out_cols if c in full.columns]
    full = full[out_cols]

    full.to_csv(OUT_FULL, index=False)
    print(f"Full panel saved: {len(full):,} rows -> {OUT_FULL}")

    subset = full[full["data_year"].isin([2022, 2023, 2024])]
    subset.to_csv(OUT_2022, index=False)
    print(f"2022-2024 subset saved: {len(subset):,} rows -> {OUT_2022}")


if __name__ == "__main__":
    main()
