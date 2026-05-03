"""Rebuild the focus-states population panel from co-est2024-alldata.csv.

Reads the Census Bureau county population estimates and filters to
focus states (AZ, CA, FL, UT), producing a long-format panel with
one row per state × county × year (2020-2024).

This script replaces manual creation of:
    data/processed/population/focus_states_county_population_2020_2024_long.csv
"""

from __future__ import annotations
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_IN = ROOT / "data" / "raw" / "population" / "co-est2024-alldata.csv"
OUT = ROOT / "data" / "processed" / "population" / "focus_states_county_population_2020_2024_long.csv"

# STATE FIPS codes for focus states.
STATE_FIPS = {"04": "AZ", "06": "CA", "12": "FL", "49": "UT"}

# AZ counties excluded per proposal (Navajo Nation territory).
AZ_EXCLUDED_COUNTIES = {"APACHE", "NAVAJO", "COCONINO"}

POP_YEAR_COLS = {
    2020: "POPESTIMATE2020",
    2021: "POPESTIMATE2021",
    2022: "POPESTIMATE2022",
    2023: "POPESTIMATE2023",
    2024: "POPESTIMATE2024",
}


def main() -> None:
    if not RAW_IN.exists():
        raise FileNotFoundError(f"Missing raw population file: {RAW_IN}")

    raw = pd.read_csv(RAW_IN, low_memory=False, encoding="latin-1")

    # Keep county-level records only (SUMLEV == 050).
    raw = raw[raw["SUMLEV"] == 50].copy()

    # Filter to focus states.
    raw["STATE"] = raw["STATE"].astype(str).str.zfill(2)
    raw = raw[raw["STATE"].isin(STATE_FIPS)].copy()
    raw["state"] = raw["STATE"].map(STATE_FIPS)

    # Build county FIPS.
    raw["county_fips"] = raw["STATE"] + raw["COUNTY"].astype(str).str.zfill(3)

    # Parse county name: "Autauga County" -> "AUTAUGA"
    raw["county_name"] = (
        raw["CTYNAME"]
        .astype(str)
        .str.replace(" County", "", regex=False)
        .str.replace(" Parish", "", regex=False)
        .str.upper()
        .str.strip()
    )

    # Mark AZ excluded counties.
    raw["proposal_excluded_az_county"] = (
        raw["state"].eq("AZ") & raw["county_name"].isin(AZ_EXCLUDED_COUNTIES)
    )

    # Melt to long format (one row per county × year).
    rows = []
    for year, col in POP_YEAR_COLS.items():
        subset = raw[["state", "county_fips", "county_name", "proposal_excluded_az_county", col]].copy()
        subset = subset.rename(columns={col: "population"})
        subset["data_year"] = year
        subset["population"] = pd.to_numeric(subset["population"], errors="coerce").astype("Int64")
        rows.append(subset)

    long = pd.concat(rows, ignore_index=True)
    long = long[["state", "data_year", "county_fips", "county_name", "population", "proposal_excluded_az_county"]]
    long = long.sort_values(["state", "data_year", "county_fips"]).reset_index(drop=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    long.to_csv(OUT, index=False)

    print(f"Wrote: {OUT} ({len(long):,} rows)")
    print("Coverage by state:")
    print(long.groupby("state")["county_fips"].nunique())


if __name__ == "__main__":
    main()
