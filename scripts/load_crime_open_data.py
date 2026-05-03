from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests


def fetch_csv(url: str) -> pd.DataFrame:
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    return pd.read_csv(pd.io.common.StringIO(response.text))


def load_chicago_year_type(start_year: int = 2021) -> pd.DataFrame:
    # Chicago Crimes (2001-present) grouped by year and primary crime type.
    url = (
        "https://data.cityofchicago.org/resource/ijzp-q8t2.csv"
        f"?%24select=year%2Cprimary_type%2Ccount(*)&%24where=year%3E%3D{start_year}"
        "&%24group=year%2Cprimary_type&%24order=year%2Cprimary_type"
    )
    df = fetch_csv(url)
    df = df.rename(columns={"primary_type": "crime_type", "count": "incident_count"})
    df["source"] = "chicago_open_data"
    df["geo_unit"] = "city"
    df["geo_name"] = "Chicago"
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["incident_count"] = pd.to_numeric(df["incident_count"], errors="coerce")
    return df[["source", "geo_unit", "geo_name", "year", "crime_type", "incident_count"]]


def load_nyc_year_type(start_year: int = 2021) -> pd.DataFrame:
    # NYC NYPD Complaint Data grouped by complaint year and offense description.
    url = (
        "https://data.cityofnewyork.us/resource/5uac-w243.csv"
        "?%24select=date_extract_y(cmplnt_fr_dt)%20as%20year%2Cofns_desc%2Ccount(*)&"
        f"%24where=cmplnt_fr_dt%20%3E=%20%22{start_year}-01-01T00:00:00%22"
        "&%24group=year%2Cofns_desc&%24order=year%2Cofns_desc&%24limit=50000"
    )
    df = fetch_csv(url)
    df = df.rename(columns={"ofns_desc": "crime_type", "count": "incident_count"})
    df["source"] = "nyc_open_data"
    df["geo_unit"] = "city"
    df["geo_name"] = "New York City"
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["incident_count"] = pd.to_numeric(df["incident_count"], errors="coerce")
    return df[["source", "geo_unit", "geo_name", "year", "crime_type", "incident_count"]]


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out_dir = root / "data" / "raw" / "crime"
    out_dir.mkdir(parents=True, exist_ok=True)

    chicago = load_chicago_year_type(start_year=2021)
    nyc = load_nyc_year_type(start_year=2021)
    combined = pd.concat([chicago, nyc], ignore_index=True)

    chicago_file = out_dir / "crime_chicago_year_type_2021_plus.csv"
    nyc_file = out_dir / "crime_nyc_year_type_2021_plus.csv"
    combined_file = out_dir / "crime_city_year_type_2021_plus.csv"

    chicago.to_csv(chicago_file, index=False)
    nyc.to_csv(nyc_file, index=False)
    combined.to_csv(combined_file, index=False)

    print(f"Wrote: {chicago_file} ({len(chicago)} rows)")
    print(f"Wrote: {nyc_file} ({len(nyc)} rows)")
    print(f"Wrote: {combined_file} ({len(combined)} rows)")


if __name__ == "__main__":
    main()