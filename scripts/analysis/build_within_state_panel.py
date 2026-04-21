"""
Build the analysis panel for Stage 1 within-state analysis (CA and NV only).

Adds:
  - log(crime_count + 1) outcome
  - crime_rate_per_100k and log_rate (log of rate per 100k + 0.01)
  - temperature filled from state-level ERA5 where county-level is missing
  - temperature² term
  - hour-of-day dummies removed (daily panel only here)

Output: data/processed/model/within_state_panel.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd

PANEL_FILE   = "data/processed/model/focus_states_daily_county_model_panel_2022_2024.csv"
WEATHER_FILE = "data/raw/weather/comparison_states_daily_weather_2021_2024.csv"
OUT_FILE     = "data/processed/model/within_state_panel.csv"

FOCUS_STATES  = {"CA", "NV"}
FOCUS_CRIMES  = {"burglary", "motor_vehicle_theft"}


def load_state_weather():
    """ERA5 state-level daily weather as fallback for missing county data."""
    cw = pd.read_csv(WEATHER_FILE, dtype=str)
    cw["date"] = pd.to_datetime(cw["date"], errors="coerce")
    for col in ["temperature_2m_mean", "temperature_2m_min", "temperature_2m_max", "precipitation_sum"]:
        cw[col] = pd.to_numeric(cw[col], errors="coerce")
    return (
        cw[cw["state"].isin(FOCUS_STATES)]
        .rename(columns={
            "temperature_2m_mean": "temp_state",
            "temperature_2m_min":  "temp_min_state",
            "temperature_2m_max":  "temp_max_state",
            "precipitation_sum":   "precip_state",
        })
        [["state", "date", "temp_state", "temp_min_state", "temp_max_state", "precip_state"]]
    )


def main():
    Path(OUT_FILE).parent.mkdir(parents=True, exist_ok=True)

    panel = pd.read_csv(PANEL_FILE, dtype=str, low_memory=False)
    panel.columns = panel.columns.str.strip().str.lower()

    # Filter to CA and NV, focus crime types
    panel = panel[
        panel["state"].isin(FOCUS_STATES) &
        panel["crime_type"].isin(FOCUS_CRIMES)
    ].copy()

    # Numeric conversions
    panel["incident_date"] = pd.to_datetime(panel["incident_date"], errors="coerce")
    for col in ["incident_count", "population", "data_year", "month", "day_of_week",
                "is_holiday", "in_dst_window", "temperature_2m_mean",
                "temperature_2m_min", "temperature_2m_max", "precipitation_sum",
                "median_household_income", "poverty_rate", "unemployment_rate",
                "bachelors_plus_rate"]:
        panel[col] = pd.to_numeric(panel[col], errors="coerce")

    panel["treated_state"]      = panel["treated_state"].map({"True": 1, "False": 0, True: 1, False: 0}).fillna(0).astype(int)
    panel["observes_dst_county"] = panel["observes_dst_county"].map({"True": 1, "False": 0, True: 1, False: 0}).fillna(0).astype(int)
    panel["is_holiday"]          = panel["is_holiday"].fillna(0).astype(int)

    # Fill missing county weather from state-level ERA5
    state_wx = load_state_weather()
    panel = panel.merge(state_wx, left_on=["state", "incident_date"], right_on=["state", "date"], how="left")

    panel["temperature"] = panel["temperature_2m_mean"].fillna(panel["temp_state"])
    panel["temp_min"]    = panel["temperature_2m_min"].fillna(panel["temp_min_state"])
    panel["temp_max"]    = panel["temperature_2m_max"].fillna(panel["temp_max_state"])
    panel["precip"]      = panel["precipitation_sum"].fillna(panel["precip_state"])

    # Drop rows still missing temperature (shouldn't happen with state fallback)
    missing_temp = panel["temperature"].isna().sum()
    if missing_temp > 0:
        print(f"WARNING: {missing_temp} rows still missing temperature — dropping.")
        panel = panel.dropna(subset=["temperature"])

    # Outcome variables
    panel["log_count"]   = np.log1p(panel["incident_count"])
    panel["log_rate"]    = np.log(panel["incident_count"] / panel["population"] * 100_000 + 0.01)

    # Temperature squared
    panel["temperature2"] = panel["temperature"] ** 2

    # Day-of-week and year as string categories for fixed effects
    panel["dow"]  = panel["day_of_week"].astype(int).astype(str)
    panel["year"] = panel["data_year"].astype(int).astype(str)
    panel["mon"]  = panel["month"].astype(int).astype(str)

    # Transition window flag (±30 days around spring-forward)
    panel["in_window_30"] = (panel["days_from_dst_start"].apply(
        lambda x: pd.to_numeric(x, errors="coerce")
    ).abs() <= 30).astype(int)

    keep = [
        "state", "county_fips", "incident_date", "crime_type",
        "incident_count", "population", "log_count", "log_rate",
        "in_dst_window", "in_window_30",
        "temperature", "temperature2", "temp_min", "temp_max", "precip",
        "is_holiday", "dow", "year", "mon",
        "median_household_income", "poverty_rate", "unemployment_rate", "bachelors_plus_rate",
        "observes_dst_county", "treated_state",
    ]
    panel = panel[[c for c in keep if c in panel.columns]]
    panel.to_csv(OUT_FILE, index=False)
    print(f"Saved {len(panel):,} rows -> {OUT_FILE}")
    print(f"States: {sorted(panel['state'].unique())}")
    print(f"Crimes: {sorted(panel['crime_type'].unique())}")
    print(f"Date range: {panel['incident_date'].min()} – {panel['incident_date'].max()}")
    print(f"Temperature missing: {panel['temperature'].isna().sum()}")
    print(f"Rows in ±30d window: {panel['in_window_30'].sum():,}")


if __name__ == "__main__":
    main()
