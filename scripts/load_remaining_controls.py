import argparse
import time
from pathlib import Path

import pandas as pd
import requests

POP_FILE = "data/processed/population/focus_states_county_population_2020_2024_long.csv"
TZ_OUT = "data/raw/timezone/focus_states_county_centroids_timezone.csv"
HOLIDAYS_OUT = "data/raw/holidays/us_public_holidays_2021_2024.csv"
WEATHER_OUT = "data/raw/weather/focus_states_daily_weather_2021_2024.csv"

EXCLUDED_AZ = {"APACHE", "NAVAJO", "COCONINO"}
def assign_timezone(state, county_name, excluded):
    if state == "CA":
        return "America/Los_Angeles"
    if state == "AZ":
        return "America/Denver" if excluded else "America/Phoenix"
    if state == "NV":
        return "America/Los_Angeles"
    return "America/Los_Angeles"


def build_timezone_table(pop):
    counties = (
        pop[["state", "county_fips", "county_name", "proposal_excluded_az_county"]]
        .drop_duplicates()
        .copy()
    )
    counties["county_name_upper"] = counties["county_name"].str.upper()
    counties["timezone"] = counties.apply(
        lambda r: assign_timezone(r["state"], r["county_name_upper"], r["proposal_excluded_az_county"]),
        axis=1,
    )
    tz = counties[["state", "county_fips", "county_name", "timezone", "proposal_excluded_az_county"]].copy()
    tz.to_csv(TZ_OUT, index=False)
    print(f"Timezone table saved: {len(tz):,} rows -> {TZ_OUT}")
    return tz


def fetch_holidays():
    all_rows = []
    for year in range(2021, 2025):
        url = f"https://date.nager.at/api/v3/PublicHolidays/{year}/US"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        for h in resp.json():
            all_rows.append({
                "date": h["date"],
                "name": h["localName"],
                "year": year,
            })
    df = pd.DataFrame(all_rows)
    df.to_csv(HOLIDAYS_OUT, index=False)
    print(f"Holidays saved: {len(df):,} rows -> {HOLIDAYS_OUT}")


def fetch_county_centroids():
    """Download county centroids from Census Bureau gazetteer (FIPS → lat/lon)."""
    import io
    url = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2023_Gazetteer/2023_Gaz_counties_national.zip"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    import zipfile
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        name = [n for n in zf.namelist() if n.endswith(".txt")][0]
        with zf.open(name) as f:
            gaz = pd.read_csv(f, sep="\t", dtype=str, encoding="latin-1")
    gaz.columns = gaz.columns.str.strip()
    # GEOID is 5-digit FIPS; INTPTLAT/INTPTLONG are internal point coordinates
    lat_col = next(c for c in gaz.columns if "INTPTLAT" in c.upper())
    lon_col = next(c for c in gaz.columns if "INTPTLONG" in c.upper())
    geoid_col = next(c for c in gaz.columns if "GEOID" in c.upper())
    gaz = gaz[[geoid_col, lat_col, lon_col]].rename(
        columns={geoid_col: "county_fips", lat_col: "latitude", lon_col: "longitude"}
    )
    gaz["county_fips"] = gaz["county_fips"].str.strip().str.zfill(5)
    gaz["latitude"] = pd.to_numeric(gaz["latitude"], errors="coerce")
    gaz["longitude"] = pd.to_numeric(gaz["longitude"], errors="coerce")
    return gaz.set_index("county_fips")[["latitude", "longitude"]].to_dict("index")


def fetch_weather_for_county(lat, lon, county_fips, county_name, state):
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": "2021-01-01",
        "end_date": "2024-12-31",
        "daily": "temperature_2m_mean,temperature_2m_min,temperature_2m_max,precipitation_sum",
        "timezone": "auto",
    }
    resp = requests.get(url, params=params, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    daily = data.get("daily", {})
    dates = daily.get("time", [])
    df = pd.DataFrame({
        "date": dates,
        "temperature_2m_mean": daily.get("temperature_2m_mean", [None] * len(dates)),
        "temperature_2m_min": daily.get("temperature_2m_min", [None] * len(dates)),
        "temperature_2m_max": daily.get("temperature_2m_max", [None] * len(dates)),
        "precipitation_sum": daily.get("precipitation_sum", [None] * len(dates)),
    })
    df["county_fips"] = county_fips
    df["county_name"] = county_name
    df["state"] = state
    return df


def fetch_weather(tz):
    print("Fetching county centroids from Census Bureau gazetteer...")
    centroids = fetch_county_centroids()

    print(f"Fetching weather for {len(tz)} counties (one API call each)...")
    weather_frames = []
    for _, row in tz.iterrows():
        fips = str(row["county_fips"]).zfill(5)
        coord = centroids.get(fips)
        if coord is None:
            print(f"  No centroid for {row['county_name']}, {row['state']} ({fips})")
            continue
        lat, lon = coord["latitude"], coord["longitude"]
        try:
            df = fetch_weather_for_county(lat, lon, fips, row["county_name"], row["state"])
            weather_frames.append(df)
            time.sleep(0.15)
        except Exception as exc:
            print(f"  Weather error {row['county_name']}, {row['state']}: {exc}")

    if weather_frames:
        weather = pd.concat(weather_frames, ignore_index=True)
        weather.to_csv(WEATHER_OUT, index=False)
        print(f"Weather saved: {len(weather):,} rows -> {WEATHER_OUT}")
    else:
        print("No weather data collected.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-weather", action="store_true")
    args = parser.parse_args()

    Path(TZ_OUT).parent.mkdir(parents=True, exist_ok=True)
    Path(HOLIDAYS_OUT).parent.mkdir(parents=True, exist_ok=True)

    pop = pd.read_csv(POP_FILE, dtype=str)
    pop["proposal_excluded_az_county"] = pop["proposal_excluded_az_county"].map(
        {"True": True, "False": False, True: True, False: False}
    ).fillna(False)

    tz = build_timezone_table(pop)

    print("Fetching US public holidays 2021-2024 ...")
    fetch_holidays()

    if args.include_weather:
        Path(WEATHER_OUT).parent.mkdir(parents=True, exist_ok=True)
        fetch_weather(tz)
    else:
        print("Skipping weather (pass --include-weather to fetch).")


if __name__ == "__main__":
    main()
