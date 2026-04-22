from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://api.census.gov/data/{year}/acs/acs5"
STATES = {"04": "AZ", "06": "CA", "32": "NV"}
YEARS = [2021, 2022, 2023, 2024]

VARS = [
    "NAME",
    "B19013_001E",   # median household income
    "B17001_001E",   # poverty universe
    "B17001_002E",   # below poverty
    "B23025_003E",   # employed
    "B23025_005E",   # unemployed
    "B15003_001E",   # education universe (25+)
    "B15003_022E",   # bachelor's
    "B15003_023E",   # master's
    "B15003_024E",   # professional school
    "B15003_025E",   # doctorate
]

RAW_OUT = "data/raw/socioeconomic/acs_county_controls_raw_2021_2024.csv"
DERIVED_OUT = "data/processed/socioeconomic/acs_county_controls_derived_2021_2024.csv"


def fetch_year_state(year, state_fips):
    url = BASE_URL.format(year=year)
    params = {
        "get": ",".join(VARS),
        "for": "county:*",
        "in": f"state:{state_fips}",
    }
    resp = requests.get(url, params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    cols = data[0]
    rows = data[1:]
    return pd.DataFrame(rows, columns=cols)


def main():
    Path(RAW_OUT).parent.mkdir(parents=True, exist_ok=True)
    Path(DERIVED_OUT).parent.mkdir(parents=True, exist_ok=True)

    all_raw = []
    for year in YEARS:
        for fips, abbr in STATES.items():
            print(f"  Fetching ACS5 {year} {abbr} ...")
            try:
                df = fetch_year_state(year, fips)
                df["data_year"] = year
                df["state"] = abbr
                all_raw.append(df)
            except Exception as exc:
                print(f"    ERROR {year} {abbr}: {exc}")

    raw = pd.concat(all_raw, ignore_index=True)
    raw["county_fips"] = (raw["state_fips"] if "state_fips" in raw.columns
                          else raw["state"]).astype(str).str.zfill(2) + raw["county"].str.zfill(3)

    raw["county_fips"] = raw.apply(
        lambda r: str(r.get("state", "")).zfill(2) + str(r.get("county", "")).zfill(3)
        if len(str(r.get("county_fips", ""))) != 5
        else str(r.get("county_fips", "")).zfill(5),
        axis=1,
    )

    # Build numeric 5-digit FIPS from Census state/county codes (before state is replaced with abbr)
    if "state" in raw.columns and "county" in raw.columns:
        raw["county_fips"] = (
            raw["state"].astype(str).str.zfill(2) + raw["county"].astype(str).str.zfill(3)
        )

    raw.rename(columns={"NAME": "county_name_raw"}, inplace=True)
    raw.to_csv(RAW_OUT, index=False)
    print(f"Raw saved: {len(raw):,} rows -> {RAW_OUT}")

    def to_float(series):
        return pd.to_numeric(series, errors="coerce")

    raw["median_household_income"] = to_float(raw["B19013_001E"])
    raw["poverty_rate"] = to_float(raw["B17001_002E"]) / to_float(raw["B17001_001E"])
    raw["unemployment_rate"] = to_float(raw["B23025_005E"]) / (
        to_float(raw["B23025_003E"]) + to_float(raw["B23025_005E"])
    )
    raw["bachelors_plus_rate"] = (
        to_float(raw["B15003_022E"]) + to_float(raw["B15003_023E"])
        + to_float(raw["B15003_024E"]) + to_float(raw["B15003_025E"])
    ) / to_float(raw["B15003_001E"])

    raw["county_name"] = raw["county_name_raw"].str.replace(r",.*", "", regex=True).str.strip()

    derived = raw[[
        "state", "data_year", "county_fips", "county_name",
        "median_household_income", "poverty_rate", "unemployment_rate", "bachelors_plus_rate",
    ]].copy()
    derived.to_csv(DERIVED_OUT, index=False)
    print(f"Derived saved: {len(derived):,} rows -> {DERIVED_OUT}")


if __name__ == "__main__":
    main()
