import zipfile
from pathlib import Path

import pandas as pd

ZIP_DIR = "data/raw/crime/nibrs_state_year"
OUT_DIR = "data/processed/crime"

FOCUS_STATES = {"CA", "NV", "AZ"}
OFFENSE_MAP = {"220": "burglary", "240": "motor_vehicle_theft"}
EXCLUDED_AZ_COUNTIES = {"APACHE", "NAVAJO", "COCONINO"}


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
    m_name = path.stem.upper()
    state = m_name.split("-")[0]
    if state not in FOCUS_STATES:
        return None

    print(f"  Processing {path.name} ...")
    with zipfile.ZipFile(path) as zf:
        incidents = read_csv_from_zip(zf, "NIBRS_incident.csv",
                                       ["incident_id", "agency_id", "incident_date", "incident_hour"])
        offenses = read_csv_from_zip(zf, "NIBRS_OFFENSE.csv",
                                      ["incident_id", "offense_code"])
        agencies = read_csv_from_zip(zf, "agencies.csv",
                                      ["agency_id", "county_name", "state_abbr"])

    if incidents is None or offenses is None or agencies is None:
        print(f"    Missing required CSV in {path.name}")
        return None

    offenses = offenses[offenses["offense_code"].isin(OFFENSE_MAP.keys())].copy()
    offenses["crime_type"] = offenses["offense_code"].map(OFFENSE_MAP)

    merged = offenses.merge(incidents, on="incident_id", how="inner")
    merged = merged.merge(agencies, on="agency_id", how="inner")

    merged["county_name"] = merged["county_name"].str.strip().str.upper()
    merged["state_abbr"] = merged["state_abbr"].str.strip().str.upper()

    if state == "AZ":
        merged = merged[~merged["county_name"].isin(EXCLUDED_AZ_COUNTIES)]

    merged = merged.dropna(subset=["incident_date", "incident_hour", "crime_type"])
    merged = merged.drop_duplicates(subset=["incident_id", "offense_code", "incident_hour"])

    return merged


def main():
    Path(OUT_DIR).mkdir(parents=True, exist_ok=True)
    zips = sorted(Path(ZIP_DIR).glob("*-*.zip"))

    all_frames = []
    for path in zips:
        df = process_zip(path)
        if df is not None:
            all_frames.append(df)

    if not all_frames:
        print("No data processed.")
        return

    combined = pd.concat(all_frames, ignore_index=True)
    combined["incident_date"] = pd.to_datetime(combined["incident_date"], errors="coerce")
    combined["year"] = combined["incident_date"].dt.year

    daily = (
        combined.groupby(["state_abbr", "year", "county_name", "incident_date", "crime_type"])
        .size()
        .reset_index(name="incident_count")
    )
    daily.rename(columns={"state_abbr": "state"}, inplace=True)
    daily["incident_date"] = daily["incident_date"].dt.strftime("%Y-%m-%d")

    hourly = (
        combined.groupby(
            ["state_abbr", "year", "county_name", "incident_date", "incident_hour", "crime_type"]
        )
        .size()
        .reset_index(name="incident_count")
    )
    hourly.rename(columns={"state_abbr": "state"}, inplace=True)
    hourly["incident_date"] = hourly["incident_date"].dt.strftime("%Y-%m-%d")

    summary = (
        combined.groupby(["state_abbr", "year", "crime_type"])
        .size()
        .reset_index(name="incident_count")
    )
    summary.rename(columns={"state_abbr": "state"}, inplace=True)

    daily.to_csv(f"{OUT_DIR}/focus_states_daily_county_counts.csv", index=False)
    hourly.to_csv(f"{OUT_DIR}/focus_states_hourly_county_counts.csv", index=False)
    summary.to_csv(f"{OUT_DIR}/focus_states_state_year_summary.csv", index=False)

    print(f"\nDaily rows:  {len(daily):,}")
    print(f"Hourly rows: {len(hourly):,}")
    print(f"Summary rows: {len(summary):,}")
    print(f"Outputs saved to {OUT_DIR}/")


if __name__ == "__main__":
    main()
