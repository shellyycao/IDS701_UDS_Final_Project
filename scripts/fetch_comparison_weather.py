"""
Fetch ERA5 daily weather for representative points in candidate US states.
Used for feasibility analysis: which states have climate most similar to AZ?
One point per state (state geographic center) keeps API calls manageable.
Output: data/raw/weather/comparison_states_daily_weather_2021_2024.csv
"""
import time
from pathlib import Path

import pandas as pd
import requests

OUT_FILE = "data/raw/weather/comparison_states_daily_weather_2021_2024.csv"
ERA5_URL = "https://archive-api.open-meteo.com/v1/era5"

# Representative lat/lon per state (geographic center or major metro)
# Focus on western/dry states that could plausibly resemble AZ
STATES = {
    # Study states
    "AZ": (33.45, -112.07, "Phoenix, AZ"),
    "CA": (36.78, -119.42, "Central Valley, CA"),
    "FL": (27.99,  -81.73, "Central FL"),
    "UT": (40.76, -111.89, "Salt Lake City, UT"),
    # Candidate comparison states
    "NM": (35.10, -106.65, "Albuquerque, NM"),
    "NV": (36.17, -115.14, "Las Vegas, NV"),
    "TX": (30.27,  -97.74, "Austin, TX"),
    "CO": (39.74, -104.98, "Denver, CO"),
    "ID": (43.62, -116.20, "Boise, ID"),
    "WY": (41.14, -104.82, "Cheyenne, WY"),
    "OR": (44.94, -123.03, "Salem, OR"),
    "MT": (46.60, -112.02, "Helena, MT"),
}

DAILY_VARS = "temperature_2m_mean,temperature_2m_min,temperature_2m_max,precipitation_sum"


def fetch_state(abbr, lat, lon, label):
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": "2021-01-01",
        "end_date": "2024-12-31",
        "daily": DAILY_VARS,
        "timezone": "America/Denver",
    }
    resp = requests.get(ERA5_URL, params=params, timeout=120)
    resp.raise_for_status()
    data = resp.json().get("daily", {})
    dates = data.get("time", [])
    df = pd.DataFrame({
        "date": dates,
        "temperature_2m_mean": data.get("temperature_2m_mean", []),
        "temperature_2m_min":  data.get("temperature_2m_min",  []),
        "temperature_2m_max":  data.get("temperature_2m_max",  []),
        "precipitation_sum":   data.get("precipitation_sum",   []),
    })
    df["state"] = abbr
    df["label"] = label
    df["latitude"] = lat
    df["longitude"] = lon
    return df


def main():
    Path(OUT_FILE).parent.mkdir(parents=True, exist_ok=True)
    frames = []
    for abbr, (lat, lon, label) in STATES.items():
        print(f"  Fetching {abbr} ({label}) ...")
        try:
            df = fetch_state(abbr, lat, lon, label)
            frames.append(df)
            print(f"    {len(df)} days OK")
        except Exception as exc:
            print(f"    ERROR: {exc}")
        time.sleep(1.0)   # ERA5 is generous but 1 s gap is polite

    if frames:
        out = pd.concat(frames, ignore_index=True)
        out.to_csv(OUT_FILE, index=False)
        print(f"\nSaved {len(out):,} rows ({out['state'].nunique()} states) -> {OUT_FILE}")
    else:
        print("No data fetched.")


if __name__ == "__main__":
    main()
