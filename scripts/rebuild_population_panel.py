from pathlib import Path

import pandas as pd

POP_FILE = "data/raw/population/co-est2024-alldata.csv"
OUT_FILE = "data/processed/population/focus_states_county_population_2020_2024_long.csv"

STATE_FIPS = {"04": "AZ", "06": "CA", "32": "NV"}
EXCLUDED_AZ = {"APACHE", "NAVAJO", "COCONINO"}
POP_COLS = {yr: f"POPESTIMATE{yr}" for yr in range(2020, 2025)}


def main():
    Path(OUT_FILE).parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(POP_FILE, encoding="latin-1", dtype=str, low_memory=False)
    df.columns = df.columns.str.strip()

    df = df[df["SUMLEV"] == "050"].copy()
    df = df[df["STATE"].isin(STATE_FIPS.keys())].copy()

    df["state"] = df["STATE"].map(STATE_FIPS)
    df["county_fips"] = (df["STATE"].str.zfill(2) + df["COUNTY"].str.zfill(3)).str.zfill(5)

    df["county_name"] = (
        df["CTYNAME"]
        .str.replace(r"\s+County$", "", regex=True)
        .str.replace(r"\s+Parish$", "", regex=True)
        .str.strip()
        .str.upper()
    )

    df["proposal_excluded_az_county"] = (
        (df["state"] == "AZ") & (df["county_name"].isin(EXCLUDED_AZ))
    )

    rows = []
    for year, col in POP_COLS.items():
        if col not in df.columns:
            print(f"  WARNING: column {col} not found, skipping year {year}")
            continue
        subset = df[["state", "county_fips", "county_name", "proposal_excluded_az_county", col]].copy()
        subset.rename(columns={col: "population"}, inplace=True)
        subset["data_year"] = year
        subset["population"] = pd.to_numeric(subset["population"], errors="coerce")
        rows.append(subset)

    panel = pd.concat(rows, ignore_index=True)
    panel = panel[["state", "data_year", "county_fips", "county_name",
                   "population", "proposal_excluded_az_county"]]
    panel.to_csv(OUT_FILE, index=False)

    print(f"Saved {len(panel):,} rows ({panel['county_fips'].nunique()} counties) to {OUT_FILE}")


if __name__ == "__main__":
    main()
