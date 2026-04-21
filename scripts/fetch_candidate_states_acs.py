"""
Fetch ACS5 socioeconomic data for 8 candidate comparison states (NM, NV, TX, CO, ID, WY, OR, MT)
and append to the existing derived CSV. Also extracts their population from the raw Census file.
Run AFTER load_socioeconomic_acs.py has already produced the 4-state baseline files.
"""
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://api.census.gov/data/{year}/acs/acs5"

CANDIDATE_STATES = {
    "35": "NM",
    "32": "NV",
    "48": "TX",
    "08": "CO",
    "16": "ID",
    "56": "WY",
    "41": "OR",
    "30": "MT",
}
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

RAW_OUT     = "data/raw/socioeconomic/acs_county_controls_raw_2021_2024.csv"
DERIVED_OUT = "data/processed/socioeconomic/acs_county_controls_derived_2021_2024.csv"

POP_RAW  = "data/raw/population/co-est2024-alldata.csv"
POP_OUT  = "data/processed/population/focus_states_county_population_2020_2024_long.csv"

STATE_FIPS_TO_ABBR = {v: k for k, v in CANDIDATE_STATES.items()}  # abbr -> fips (inverted below)
FIPS_TO_ABBR = CANDIDATE_STATES


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
    return pd.DataFrame(data[1:], columns=data[0])


def to_float(series):
    return pd.to_numeric(series, errors="coerce")


# ── ACS fetch ──────────────────────────────────────────────────────────────────
def fetch_acs():
    all_raw = []
    for year in YEARS:
        for fips, abbr in CANDIDATE_STATES.items():
            print(f"  Fetching ACS5 {year} {abbr} ...")
            try:
                df = fetch_year_state(year, fips)
                df["data_year"] = year
                # Build FIPS before renaming Census 'state' column
                df["county_fips"] = (
                    df["state"].astype(str).str.zfill(2) + df["county"].astype(str).str.zfill(3)
                )
                # Drop Census numeric state/county to avoid duplicate columns on concat
                df.drop(columns=["state", "county"], inplace=True)
                df["state"] = abbr
                all_raw.append(df)
                print(f"    {len(df)} counties OK")
            except Exception as exc:
                print(f"    ERROR {year} {abbr}: {exc}")

    if not all_raw:
        print("No ACS data fetched.")
        return

    raw = pd.concat(all_raw, ignore_index=True)
    raw.rename(columns={"NAME": "county_name_raw"}, inplace=True)

    # Append to raw CSV
    existing_raw = pd.read_csv(RAW_OUT, dtype=str)
    # Align columns before concat to avoid duplicate-index error
    all_cols = list(dict.fromkeys(list(existing_raw.columns) + list(raw.columns)))
    combined_raw = pd.concat(
        [existing_raw.reindex(columns=all_cols), raw.reindex(columns=all_cols)],
        ignore_index=True,
    )
    combined_raw.to_csv(RAW_OUT, index=False)
    print(f"Raw appended: {len(raw):,} new rows -> {RAW_OUT} (total {len(combined_raw):,})")

    # Derive rates
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

    new_derived = raw[[
        "state", "data_year", "county_fips", "county_name",
        "median_household_income", "poverty_rate", "unemployment_rate", "bachelors_plus_rate",
    ]].copy()

    existing_derived = pd.read_csv(DERIVED_OUT, dtype=str)
    already_there = set(existing_derived["state"].unique())
    new_abbrs = set(CANDIDATE_STATES.values()) - already_there
    if not new_abbrs:
        print("Derived already contains all candidate states — skipping.")
        return
    new_derived = new_derived[new_derived["state"].isin(new_abbrs)]

    for col in ["median_household_income", "poverty_rate", "unemployment_rate", "bachelors_plus_rate"]:
        new_derived[col] = new_derived[col].astype(str)

    combined_derived = pd.concat([existing_derived, new_derived], ignore_index=True)
    combined_derived.to_csv(DERIVED_OUT, index=False)
    print(f"Derived appended: {len(new_derived):,} new rows -> {DERIVED_OUT} (total {len(combined_derived):,})")


# ── Population extract ─────────────────────────────────────────────────────────
def extract_population():
    pop_raw = pd.read_csv(POP_RAW, encoding="latin-1")
    pop_raw = pop_raw[pop_raw["SUMLEV"] == 50].copy()

    candidate_fips = set(CANDIDATE_STATES.keys())
    pop_raw["state_fips"] = pop_raw["STATE"].astype(str).str.zfill(2)
    subset = pop_raw[pop_raw["state_fips"].isin(candidate_fips)].copy()

    subset["state"] = subset["state_fips"].map(CANDIDATE_STATES)
    subset["county_fips"] = subset["state_fips"] + subset["COUNTY"].astype(str).str.zfill(3)
    subset["county_name"] = subset["CTYNAME"].str.upper()

    year_cols = {
        2020: "POPESTIMATE2020",
        2021: "POPESTIMATE2021",
        2022: "POPESTIMATE2022",
        2023: "POPESTIMATE2023",
        2024: "POPESTIMATE2024",
    }

    frames = []
    for year, col in year_cols.items():
        tmp = subset[["state", "county_fips", "county_name", col]].copy()
        tmp.rename(columns={col: "population"}, inplace=True)
        tmp["data_year"] = year
        tmp["proposal_excluded_az_county"] = False
        frames.append(tmp)

    new_pop = pd.concat(frames, ignore_index=True)
    new_pop = new_pop[["state", "data_year", "county_fips", "county_name", "population", "proposal_excluded_az_county"]]

    existing_pop = pd.read_csv(POP_OUT, dtype=str)
    new_pop["population"] = new_pop["population"].astype(str)
    new_pop["data_year"] = new_pop["data_year"].astype(str)
    new_pop["proposal_excluded_az_county"] = new_pop["proposal_excluded_az_county"].astype(str)

    existing_pop = pd.read_csv(POP_OUT, dtype=str)
    already_there = set(existing_pop["state"].unique())
    new_states = set(CANDIDATE_STATES.values()) - already_there
    if not new_states:
        print("Population already contains all candidate states — skipping.")
        return
    new_pop = new_pop[new_pop["state"].isin(new_states)]
    combined_pop = pd.concat([existing_pop, new_pop], ignore_index=True)
    combined_pop.to_csv(POP_OUT, index=False)
    print(f"Population appended: {len(new_pop):,} new rows -> {POP_OUT} (total {len(combined_pop):,})")


if __name__ == "__main__":
    Path(RAW_OUT).parent.mkdir(parents=True, exist_ok=True)
    Path(DERIVED_OUT).parent.mkdir(parents=True, exist_ok=True)

    print("=== Extracting population for candidate states ===")
    extract_population()

    print("\n=== Fetching ACS5 for candidate states ===")
    fetch_acs()

    print("\nDone.")
