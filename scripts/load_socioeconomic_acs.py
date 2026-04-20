"""Load county-level socioeconomic controls from Census ACS API.

Focus states: AZ, CA, FL
Years: 2021-2024

Outputs:
- data/raw/socioeconomic/acs_county_controls_raw_2021_2024.csv
- data/processed/socioeconomic/acs_county_controls_derived_2021_2024.csv

Variables pulled (ACS5 detailed tables):
- B19013_001E: Median household income
- B17001_001E: Poverty universe
- B17001_002E: Population below poverty
- B23025_003E: Civilian labor force
- B23025_005E: Unemployed
- B15003_001E: Educational attainment universe (25+)
- B15003_022E: Bachelor's
- B15003_023E: Master's
- B15003_024E: Professional school
- B15003_025E: Doctorate
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW_OUT = ROOT / "data" / "raw" / "socioeconomic" / "acs_county_controls_raw_2021_2024.csv"
DERIVED_OUT = ROOT / "data" / "processed" / "socioeconomic" / "acs_county_controls_derived_2021_2024.csv"

YEARS = [2021, 2022, 2023, 2024]
STATE_CODE_TO_ABBR = {"04": "AZ", "06": "CA", "12": "FL", "49": "UT"}
STATE_ABBR_TO_CODE = {v: k for k, v in STATE_CODE_TO_ABBR.items()}

ACS_VARS = [
    "NAME",
    "B19013_001E",
    "B17001_001E",
    "B17001_002E",
    "B23025_003E",
    "B23025_005E",
    "B15003_001E",
    "B15003_022E",
    "B15003_023E",
    "B15003_024E",
    "B15003_025E",
]


def fetch_year(year: int) -> pd.DataFrame:
    url = f"https://api.census.gov/data/{year}/acs/acs5"
    params = {
        "get": ",".join(ACS_VARS),
        "for": "county:*",
        "in": "state:*",
    }
    r = requests.get(url, params=params, timeout=120)
    r.raise_for_status()

    payload = r.json()
    header = payload[0]
    rows = payload[1:]
    df = pd.DataFrame(rows, columns=header)
    df["data_year"] = year

    # Keep only focus states.
    df["state"] = df["state"].astype(str).str.zfill(2)
    df = df[df["state"].isin(STATE_CODE_TO_ABBR)].copy()

    return df


def to_numeric_safe(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    return out


def build_derived(raw_df: pd.DataFrame) -> pd.DataFrame:
    d = raw_df.copy()

    d = to_numeric_safe(
        d,
        [
            "B19013_001E",
            "B17001_001E",
            "B17001_002E",
            "B23025_003E",
            "B23025_005E",
            "B15003_001E",
            "B15003_022E",
            "B15003_023E",
            "B15003_024E",
            "B15003_025E",
        ],
    )

    d["state"] = d["state"].map(STATE_CODE_TO_ABBR)
    d["county_fips"] = d["state"].map(STATE_ABBR_TO_CODE) + d["county"].astype(str).str.zfill(3)

    # Parse county name from NAME like: "Autauga County, Alabama"
    d["county_name"] = (
        d["NAME"].astype(str).str.split(",", n=1).str[0].str.replace(" County", "", regex=False).str.upper().str.strip()
    )

    d["median_household_income"] = d["B19013_001E"]
    d["poverty_rate"] = d["B17001_002E"] / d["B17001_001E"]
    d["unemployment_rate"] = d["B23025_005E"] / d["B23025_003E"]

    d["bachelors_plus_count"] = (
        d["B15003_022E"].fillna(0)
        + d["B15003_023E"].fillna(0)
        + d["B15003_024E"].fillna(0)
        + d["B15003_025E"].fillna(0)
    )
    d["bachelors_plus_rate"] = d["bachelors_plus_count"] / d["B15003_001E"]

    keep = [
        "state",
        "data_year",
        "county_fips",
        "county_name",
        "median_household_income",
        "poverty_rate",
        "unemployment_rate",
        "bachelors_plus_rate",
        "B17001_001E",
        "B23025_003E",
        "B15003_001E",
    ]

    out = d[keep].sort_values(["state", "data_year", "county_fips"]).reset_index(drop=True)
    return out


def main() -> None:
    frames = [fetch_year(y) for y in YEARS]
    raw = pd.concat(frames, ignore_index=True)

    RAW_OUT.parent.mkdir(parents=True, exist_ok=True)
    DERIVED_OUT.parent.mkdir(parents=True, exist_ok=True)

    raw.to_csv(RAW_OUT, index=False)

    derived = build_derived(raw)
    derived.to_csv(DERIVED_OUT, index=False)

    print(f"Wrote: {RAW_OUT} rows={len(raw):,}")
    print(f"Wrote: {DERIVED_OUT} rows={len(derived):,}")
    print("Coverage by state-year:")
    print(derived.groupby(["state", "data_year"]).size())


if __name__ == "__main__":
    main()
