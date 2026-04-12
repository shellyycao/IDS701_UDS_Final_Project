from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests


YEARS = [2021, 2022, 2023]


def fetch_acs_county_population(year: int) -> pd.DataFrame:
    url = f"https://api.census.gov/data/{year}/acs/acs5"
    params = {
        "get": "NAME,B01003_001E",
        "for": "county:*",
        "in": "state:*",
    }
    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    data = r.json()

    if not isinstance(data, list) or len(data) < 2:
        raise ValueError(f"Unexpected ACS response for {year}: {data}")

    df = pd.DataFrame(data[1:], columns=data[0])
    df = df.rename(columns={"NAME": "county_name", "B01003_001E": "population_total"})
    df["county_fips"] = df["state"].astype(str).str.zfill(2) + df["county"].astype(str).str.zfill(3)
    df["year"] = year
    df["population_total"] = pd.to_numeric(df["population_total"], errors="coerce")
    return df[["county_fips", "year", "population_total", "county_name"]]


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out_dir = root / "data" / "raw" / "population"
    out_dir.mkdir(parents=True, exist_ok=True)

    dfs = []
    for y in YEARS:
        print(f"Downloading ACS county population for {y}...")
        try:
            dfs.append(fetch_acs_county_population(y))
        except Exception as exc:
            print(f"Skipping {y}: {exc}")

    if not dfs:
        raise RuntimeError("No ACS population data downloaded.")

    out = pd.concat(dfs, ignore_index=True)
    out_file = out_dir / "county_population_acs_2021_2023.csv"
    out.to_csv(out_file, index=False)
    print(f"Wrote: {out_file}")
    print(out.head())


if __name__ == "__main__":
    main()