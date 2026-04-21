"""
Aggregate hourly crime data to county-day evening window (17:00–20:00).

Evening is defined as hours 17, 18, 19, 20 (5pm–8pm inclusive).

Output: data/processed/model/evening_crime_panel.csv
  One row per (state, county_fips, incident_date, crime_type)
  Columns: evening_count, total_count, evening_share, population,
           evening_rate_per_100k, total_rate_per_100k,
           log_evening_count, log_total_count,
           in_dst_window, is_holiday, dow, year, mon
"""
from pathlib import Path

import numpy as np
import pandas as pd

HOURLY_FILE = "data/processed/crime/focus_states_hourly_structured.csv"
DAILY_FILE  = "data/processed/model/within_state_panel.csv"
OUT_FILE    = "data/processed/model/evening_crime_panel.csv"

EVENING_HOURS = {17, 18, 19, 20}
FOCUS_STATES  = {"AZ", "CA", "NV"}
FOCUS_CRIMES  = {"burglary", "motor_vehicle_theft"}


def main():
    Path(OUT_FILE).parent.mkdir(parents=True, exist_ok=True)

    hourly = pd.read_csv(HOURLY_FILE, dtype=str, low_memory=False)
    hourly.columns = hourly.columns.str.strip().str.lower()
    hourly["hour"]        = pd.to_numeric(hourly["hour"], errors="coerce")
    hourly["crime_count"] = pd.to_numeric(hourly["crime_count"], errors="coerce").fillna(0)
    hourly["year"]        = pd.to_numeric(hourly["year"], errors="coerce")
    hourly["month"]       = pd.to_numeric(hourly["month"], errors="coerce")
    hourly["day"]         = pd.to_numeric(hourly["day"], errors="coerce")

    hourly = hourly[
        hourly["state"].isin(FOCUS_STATES) &
        hourly["offense_type"].isin(FOCUS_CRIMES) &
        hourly["hour"].notna() &
        (hourly["hour"] != 0)
    ].copy()

    hourly["incident_date"] = pd.to_datetime(
        dict(year=hourly["year"], month=hourly["month"], day=hourly["day"]), errors="coerce"
    )
    hourly["is_evening"] = hourly["hour"].isin(EVENING_HOURS).astype(int)

    # Total daily crime per county
    total = (
        hourly.groupby(["state", "county_fips", "incident_date", "offense_type"])["crime_count"]
        .sum().reset_index(name="total_count")
    )
    # Evening crime per county
    evening = (
        hourly[hourly["is_evening"] == 1]
        .groupby(["state", "county_fips", "incident_date", "offense_type"])["crime_count"]
        .sum().reset_index(name="evening_count")
    )

    panel = total.merge(evening, on=["state", "county_fips", "incident_date", "offense_type"], how="left")
    panel["evening_count"] = panel["evening_count"].fillna(0)
    panel["evening_share"] = panel["evening_count"] / panel["total_count"].replace(0, np.nan)

    # Join controls from the daily panel (population, DST flag, weather, etc.)
    daily = pd.read_csv(DAILY_FILE, low_memory=False)
    daily["county_fips"] = daily["county_fips"].astype(str)
    daily["incident_date"] = pd.to_datetime(daily["incident_date"], errors="coerce")
    daily_key = daily[
        ["state", "county_fips", "incident_date", "crime_type",
         "population", "in_dst_window", "is_holiday", "dow", "year", "mon",
         "temperature", "temperature2"]
    ].rename(columns={"crime_type": "offense_type"})

    panel = panel.merge(daily_key, on=["state", "county_fips", "incident_date", "offense_type"], how="left")

    # For AZ (control, not in within_state_panel), pull population from population file
    # AZ rows will have NaN population — fill from the focus_states population file
    pop_file = "data/processed/population/focus_states_county_population_2020_2024_long.csv"
    pop = pd.read_csv(pop_file, dtype=str)
    pop["population"] = pd.to_numeric(pop["population"], errors="coerce")
    pop["data_year"]  = pd.to_numeric(pop["data_year"], errors="coerce")
    pop["proposal_excluded_az_county"] = pop["proposal_excluded_az_county"].map(
        {"True": True, "False": False}
    ).fillna(False)
    pop = pop[~pop["proposal_excluded_az_county"]]
    pop_map = pop.set_index(["county_fips", "data_year"])["population"].to_dict()

    panel["year_int"] = panel["incident_date"].dt.year
    panel["population"] = panel.apply(
        lambda r: r["population"] if pd.notna(r["population"])
        else pop_map.get((r["county_fips"], r["year_int"]), np.nan),
        axis=1,
    )

    # Fill DST and date parts for AZ rows — load comparison weather directly
    cw = pd.read_csv("data/raw/weather/comparison_states_daily_weather_2021_2024.csv", dtype=str)
    cw["date"] = pd.to_datetime(cw["date"], errors="coerce")
    cw["temperature_2m_mean"] = pd.to_numeric(cw["temperature_2m_mean"], errors="coerce")
    cw_az = cw[cw["state"] == "AZ"][["date", "temperature_2m_mean"]].rename(
        columns={"date": "incident_date", "temperature_2m_mean": "temp_az"}
    )
    panel = panel.merge(cw_az, on="incident_date", how="left")
    panel["temperature"] = panel["temperature"].fillna(panel["temp_az"])
    panel["temperature2"] = panel["temperature"] ** 2

    # DST window for AZ rows (AZ observes no DST so always 0)
    panel["in_dst_window"] = panel["in_dst_window"].fillna(0).astype(int)
    panel["is_holiday"]    = panel["is_holiday"].fillna(0)

    # Date parts for AZ
    panel["dow"] = panel["dow"].fillna(panel["incident_date"].dt.dayofweek.astype(str))
    panel["year"] = panel["year"].fillna(panel["incident_date"].dt.year.astype(str))
    panel["mon"]  = panel["mon"].fillna(panel["incident_date"].dt.month.astype(str))

    # Rates
    panel["total_rate_per_100k"]   = panel["total_count"]   / panel["population"] * 100_000
    panel["evening_rate_per_100k"] = panel["evening_count"] / panel["population"] * 100_000
    panel["log_total_count"]       = np.log1p(panel["total_count"])
    panel["log_evening_count"]     = np.log1p(panel["evening_count"])

    keep = [
        "state", "county_fips", "incident_date", "offense_type",
        "evening_count", "total_count", "evening_share",
        "evening_rate_per_100k", "total_rate_per_100k",
        "log_evening_count", "log_total_count",
        "population", "in_dst_window", "is_holiday", "dow", "year", "mon",
        "temperature", "temperature2",
    ]
    panel = panel[[c for c in keep if c in panel.columns]]
    panel.to_csv(OUT_FILE, index=False)
    print(f"Saved {len(panel):,} rows -> {OUT_FILE}")
    print(f"States: {sorted(panel['state'].unique())}")
    print(f"Evening coverage: {panel['evening_count'].gt(0).mean():.1%} of county-days have evening crime")


if __name__ == "__main__":
    main()
