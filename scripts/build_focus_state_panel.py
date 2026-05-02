import zipfile
from pathlib import Path

import pandas as pd

ZIP_DIR = "data/raw/crime/nibrs_state_year"
OUT_DIR = "data/processed/panel"

FOCUS_STATES = {"CA", "NV", "AZ", "UT"}
OFFENSE_MAP = {
    "120": "robbery",
    "220": "burglary",
    "23C": "shoplifting",
    "23D": "theft_from_building",
    "23F": "theft_from_motor_vehicle",
    "240": "motor_vehicle_theft",
}
EXCLUDED_AZ = {"APACHE", "NAVAJO", "COCONINO"}


def read_csv_from_zip(zf, name, usecols=None):
    candidates = [n for n in zf.namelist() if n.upper().split("/")[-1] == name.upper()]
    if not candidates:
        return None
    for encoding in ("utf-8", "latin-1"):
        try:
            with zf.open(candidates[0]) as f:
                df = pd.read_csv(f, dtype=str, low_memory=False, encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        return None
    df.columns = df.columns.str.strip().str.lower()
    if usecols:
        present = [c for c in usecols if c in df.columns]
        df = df[present]
    return df


def process_zip(path):
    stem = path.stem.upper()
    parts = stem.split("-")
    state = parts[0]
    year = int(parts[1]) if len(parts) > 1 else None
    if state not in FOCUS_STATES:
        return None

    print(f"  {path.name} ...")
    with zipfile.ZipFile(path) as zf:
        incidents = read_csv_from_zip(
            zf, "NIBRS_incident.csv",
            ["incident_id", "agency_id", "incident_date", "incident_hour"],
        )
        offenses = read_csv_from_zip(
            zf, "NIBRS_OFFENSE.csv",
            ["incident_id", "offense_id", "offense_code"],
        )
        agencies = read_csv_from_zip(
            zf, "agencies.csv",
            ["agency_id", "county_name", "state_abbr"],
        )
        offense_types = read_csv_from_zip(
            zf, "NIBRS_OFFENSE_TYPE.csv",
            ["offense_code", "offense_name"],
        )

    if incidents is None or offenses is None or agencies is None:
        print(f"    Missing required CSV — skipping {path.name}")
        return None

    offenses = offenses[offenses["offense_code"].isin(OFFENSE_MAP.keys())].copy()
    offenses["crime_type"] = offenses["offense_code"].map(OFFENSE_MAP)

    merged = offenses.merge(incidents, on="incident_id", how="inner")
    merged = merged.merge(agencies, on="agency_id", how="inner")
    if offense_types is not None:
        merged = merged.merge(offense_types, on="offense_code", how="left")

    merged["county_name"] = merged["county_name"].str.strip().str.upper()
    merged["state_abbr"] = merged["state_abbr"].str.strip().str.upper()

    if state == "AZ":
        merged = merged[~merged["county_name"].isin(EXCLUDED_AZ)]

    merged = merged.dropna(subset=["incident_date", "incident_hour"])
    merged = merged.drop_duplicates(
        subset=["incident_id", "offense_id", "offense_code"]
        if "offense_id" in merged.columns
        else ["incident_id", "offense_code"],
    )

    merged["incident_date"] = pd.to_datetime(merged["incident_date"], errors="coerce")
    merged["data_year"] = year if year else merged["incident_date"].dt.year
    merged["month"] = merged["incident_date"].dt.month
    merged["day_of_week"] = merged["incident_date"].dt.dayofweek
    merged["is_weekend"] = merged["day_of_week"] >= 5
    merged["state"] = state

    return merged


def main():
    Path(OUT_DIR).mkdir(parents=True, exist_ok=True)
    zips = sorted(Path(ZIP_DIR).glob("*-*.zip"))

    frames = []
    for path in zips:
        df = process_zip(path)
        if df is not None:
            frames.append(df)

    if not frames:
        print("No data processed.")
        return

    panel = pd.concat(frames, ignore_index=True)
    panel["incident_date"] = panel["incident_date"].dt.strftime("%Y-%m-%d")

    out_csv = f"{OUT_DIR}/focus_states_incident_offense_panel.csv"
    panel.to_csv(out_csv, index=False)
    print(f"\nSaved {len(panel):,} rows -> {out_csv}")

    try:
        panel.to_parquet(out_csv.replace(".csv", ".parquet"), index=False)
        print(f"Parquet also saved.")
    except ImportError:
        print("pyarrow not available — parquet skipped.")


if __name__ == "__main__":
    main()
