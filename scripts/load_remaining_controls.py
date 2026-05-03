"""Load remaining control datasets for DST-crime analysis.

Creates:
- data/raw/timezone/focus_states_county_centroids_timezone.csv
- data/raw/holidays/us_public_holidays_2021_2024.csv
- data/raw/weather/focus_states_daily_weather_2021_2024.csv

Data sources:
- Open-Meteo geocoding (county centroid-like coords + timezone)
- Open-Meteo archive (daily weather)
- Nager.Date public holidays API (US holidays)
"""

from __future__ import annotations

import argparse
from pathlib import Path
import time
from typing import Any

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
POP_INPUT = ROOT / "data" / "processed" / "population" / "focus_states_county_population_2020_2024_long.csv"

TZ_OUT = ROOT / "data" / "raw" / "timezone" / "focus_states_county_centroids_timezone.csv"
HOLIDAY_OUT = ROOT / "data" / "raw" / "holidays" / "us_public_holidays_2021_2024.csv"
WEATHER_OUT = ROOT / "data" / "raw" / "weather" / "focus_states_daily_weather_2021_2024.csv"

STATE_NAME = {"AZ": "Arizona", "CA": "California", "FL": "Florida", "UT": "Utah"}
YEARS = [2021, 2022, 2023, 2024]

# Florida counties that observe Central Time at county-level aggregation.
FL_CENTRAL_COUNTIES = {
    "BAY",
    "CALHOUN",
    "ESCAMBIA",
    "GULF",
    "HOLMES",
    "JACKSON",
    "OKALOOSA",
    "SANTA ROSA",
    "WALTON",
    "WASHINGTON",
}

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "ids701-dst-crime-loader/1.0"})


def get_county_list() -> pd.DataFrame:
    if not POP_INPUT.exists():
        raise FileNotFoundError(f"Missing input population file: {POP_INPUT}")

    pop = pd.read_csv(POP_INPUT, low_memory=False)
    keep = ["state", "county_fips", "county_name", "proposal_excluded_az_county"]
    for c in keep:
        if c not in pop.columns:
            raise ValueError(f"Missing column {c} in {POP_INPUT}")

    counties = pop[keep].drop_duplicates().copy()
    counties = counties.sort_values(["state", "county_fips"])
    return counties


def pick_best_geocode(results: list[dict[str, Any]], state_name: str) -> dict[str, Any] | None:
    if not results:
        return None

    # Prefer county-like features in requested state.
    for r in results:
        if r.get("feature_code") == "ADM2" and str(r.get("admin1", "")).lower() == state_name.lower():
            return r

    # Then any result in requested state.
    for r in results:
        if str(r.get("admin1", "")).lower() == state_name.lower():
            return r

    return results[0]


def geocode_county(county_name: str, state_abbr: str) -> dict[str, Any] | None:
    state_name = STATE_NAME[state_abbr]
    query = f"{county_name.title()} County"
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": query,
        "country": "US",
        "count": 10,
        "language": "en",
        "format": "json",
    }

    resp = SESSION.get(url, params=params, timeout=60)
    resp.raise_for_status()
    payload = resp.json()
    best = pick_best_geocode(payload.get("results", []), state_name)
    return best


def build_timezone_centroid_table(counties: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for _, r in counties.iterrows():
        county_name = str(r["county_name"])
        state = str(r["state"])

        geo = None
        err = None
        try:
            geo = geocode_county(county_name, state)
        except Exception as exc:  # noqa: BLE001
            err = str(exc)

        row = {
            "state": state,
            "county_fips": str(r["county_fips"]).zfill(5),
            "county_name": county_name,
            "proposal_excluded_az_county": bool(r["proposal_excluded_az_county"]),
            "latitude": geo.get("latitude") if geo else pd.NA,
            "longitude": geo.get("longitude") if geo else pd.NA,
            "timezone": geo.get("timezone") if geo else pd.NA,
            "geo_name": geo.get("name") if geo else pd.NA,
            "geo_admin1": geo.get("admin1") if geo else pd.NA,
            "geo_feature_code": geo.get("feature_code") if geo else pd.NA,
            "geo_error": err,
        }
        rows.append(row)

        # Be gentle with free API.
        time.sleep(0.05)

    out = pd.DataFrame(rows)
    return out


def apply_timezone_rules(tz_table: pd.DataFrame) -> pd.DataFrame:
    """Override timezones with deterministic county/state canonical rules.

    Geocoder results are unreliable at county granularity (e.g. parks, airports,
    dams returned instead of county seats).  Rules always override geocoder values
    so that treatment/control assignment is never driven by a wrong API hit.

    Rules:
    - CA counties -> America/Los_Angeles (all CA observes Pacific DST)
    - FL Panhandle counties -> America/Chicago, all others -> America/New_York
    - AZ counties -> America/Phoenix (no DST), except excluded Navajo-territory
      proxy counties -> America/Denver
    """

    out = tz_table.copy()
    out["county_name"] = out["county_name"].astype(str).str.upper().str.strip()

    # California: always Pacific Time.
    ca_mask = out["state"].eq("CA")
    out.loc[ca_mask, "timezone"] = "America/Los_Angeles"
    out.loc[ca_mask, "geo_feature_code"] = "RULE_CA"

    # Florida: Panhandle counties Central Time, all others Eastern.
    fl_mask = out["state"].eq("FL")
    fl_central_mask = fl_mask & out["county_name"].isin(FL_CENTRAL_COUNTIES)
    fl_eastern_mask = fl_mask & (~out["county_name"].isin(FL_CENTRAL_COUNTIES))
    out.loc[fl_central_mask, "timezone"] = "America/Chicago"
    out.loc[fl_central_mask, "geo_feature_code"] = "RULE_FL_CENTRAL"
    out.loc[fl_eastern_mask, "timezone"] = "America/New_York"
    out.loc[fl_eastern_mask, "geo_feature_code"] = "RULE_FL_EASTERN"

    # Arizona: excluded Navajo-territory proxy counties use Denver, rest Phoenix.
    az_mask = out["state"].eq("AZ")
    az_excluded = az_mask & out["proposal_excluded_az_county"].fillna(False)
    az_default = az_mask & (~out["proposal_excluded_az_county"].fillna(False))
    out.loc[az_default, "timezone"] = "America/Phoenix"
    out.loc[az_default, "geo_feature_code"] = "RULE_AZ_PHOENIX"
    out.loc[az_excluded, "timezone"] = "America/Denver"
    out.loc[az_excluded, "geo_feature_code"] = "RULE_AZ_EXCLUDED"

    # Utah: all counties observe Mountain Time (with DST).
    ut_mask = out["state"].eq("UT")
    out.loc[ut_mask, "timezone"] = "America/Denver"
    out.loc[ut_mask, "geo_feature_code"] = "RULE_UT"

    out.loc[out["timezone"].notna(), "geo_error"] = pd.NA

    return out


def load_us_holidays(years: list[int]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for y in years:
        url = f"https://date.nager.at/api/v3/PublicHolidays/{y}/US"
        resp = SESSION.get(url, timeout=60)
        resp.raise_for_status()

        for x in resp.json():
            rows.append(
                {
                    "date": x.get("date"),
                    "year": y,
                    "local_name": x.get("localName"),
                    "name": x.get("name"),
                    "country_code": x.get("countryCode"),
                    "global": x.get("global"),
                    "fixed": x.get("fixed"),
                    "launch_year": x.get("launchYear"),
                    "types": ",".join(x.get("types", [])),
                }
            )

    out = pd.DataFrame(rows)
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.date
    out = out.sort_values(["date", "name"]).reset_index(drop=True)
    return out


def load_weather_for_county(row: pd.Series, start_date: str, end_date: str) -> pd.DataFrame:
    lat = row["latitude"]
    lon = row["longitude"]
    if pd.isna(lat) or pd.isna(lon):
        return pd.DataFrame()

    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": float(lat),
        "longitude": float(lon),
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_mean,temperature_2m_min,temperature_2m_max,precipitation_sum",
        "timezone": "auto",
    }

    resp = SESSION.get(url, params=params, timeout=120)
    resp.raise_for_status()
    payload = resp.json()
    daily = payload.get("daily", {})

    if not daily or "time" not in daily:
        return pd.DataFrame()

    out = pd.DataFrame(
        {
            "date": daily.get("time", []),
            "temperature_2m_mean": daily.get("temperature_2m_mean", []),
            "temperature_2m_min": daily.get("temperature_2m_min", []),
            "temperature_2m_max": daily.get("temperature_2m_max", []),
            "precipitation_sum": daily.get("precipitation_sum", []),
        }
    )

    out["state"] = row["state"]
    out["county_fips"] = str(row["county_fips"]).zfill(5)
    out["county_name"] = row["county_name"]
    out["timezone"] = row.get("timezone", pd.NA)
    out["proposal_excluded_az_county"] = bool(row["proposal_excluded_az_county"])
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.date
    return out


def load_weather(tz_table: pd.DataFrame) -> pd.DataFrame:
    start_date = "2021-01-01"
    end_date = "2024-12-31"

    rows = []
    for _, r in tz_table.iterrows():
        try:
            w = load_weather_for_county(r, start_date, end_date)
            if not w.empty:
                rows.append(w)
        except Exception:
            continue
        time.sleep(0.02)

    if not rows:
        return pd.DataFrame()

    out = pd.concat(rows, ignore_index=True)
    out = out.sort_values(["state", "county_fips", "date"]).reset_index(drop=True)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Load remaining control datasets.")
    parser.add_argument(
        "--include-weather",
        action="store_true",
        help="Also download weather controls. Disabled by default.",
    )
    args = parser.parse_args()

    counties = get_county_list()

    TZ_OUT.parent.mkdir(parents=True, exist_ok=True)
    HOLIDAY_OUT.parent.mkdir(parents=True, exist_ok=True)

    tz_table = build_timezone_centroid_table(counties)
    tz_table = apply_timezone_rules(tz_table)
    tz_table.to_csv(TZ_OUT, index=False)

    holidays = load_us_holidays(YEARS)
    holidays.to_csv(HOLIDAY_OUT, index=False)

    print(f"Wrote: {TZ_OUT} rows={len(tz_table):,}")
    print(f"Wrote: {HOLIDAY_OUT} rows={len(holidays):,}")

    if args.include_weather:
        WEATHER_OUT.parent.mkdir(parents=True, exist_ok=True)
        weather = load_weather(tz_table)
        weather.to_csv(WEATHER_OUT, index=False)
        print(f"Wrote: {WEATHER_OUT} rows={len(weather):,}")
    else:
        print("Skipped weather download. Use --include-weather to enable it.")


if __name__ == "__main__":
    main()
