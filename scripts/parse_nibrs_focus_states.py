"""Parse downloaded NIBRS state-year ZIP files into analysis-ready aggregates.

Default focus follows the project proposal:
- California (CA)
- Florida (FL)
- Arizona (AZ)

Outputs:
- data/processed/crime/focus_states_daily_county_counts.csv
- data/processed/crime/focus_states_hourly_county_counts.csv
- data/processed/crime/focus_states_state_year_summary.csv

Notes:
- If focus-state ZIPs are missing, the script prints warnings and exits cleanly.
- Arizona counties Apache, Navajo, and Coconino are excluded per proposal.
"""

from __future__ import annotations

from pathlib import Path
import re
import zipfile

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_ZIP_DIR = ROOT / "data" / "raw" / "crime" / "nibrs_state_year"
OUT_DIR = ROOT / "data" / "processed" / "crime"

FOCUS_STATES = {"CA", "FL", "AZ", "UT"}
FOCUS_CRIME_CODES = {
    "220": "burglary",
    "240": "motor_vehicle_theft",
}
AZ_EXCLUDED_COUNTIES = {"APACHE", "NAVAJO", "COCONINO"}
ZIP_RE = re.compile(r"^(?P<state>[A-Z]{2})-(?P<year>\d{4})\.zip$")


def discover_focus_zips(zip_dir: Path) -> list[tuple[str, int, Path]]:
    found: list[tuple[str, int, Path]] = []
    for p in sorted(zip_dir.glob("*.zip")):
        m = ZIP_RE.match(p.name)
        if not m:
            continue
        state = m.group("state")
        year = int(m.group("year"))
        if state in FOCUS_STATES:
            found.append((state, year, p))
    return found


def read_csv_from_zip(zf: zipfile.ZipFile, member: str, usecols: list[str]) -> pd.DataFrame:
    try:
        with zf.open(member) as f:
            return pd.read_csv(f, usecols=usecols, low_memory=False, encoding="utf-8")
    except UnicodeDecodeError:
        # Some state files include non-UTF8 bytes in agency names/metadata.
        with zf.open(member) as f:
            return pd.read_csv(f, usecols=usecols, low_memory=False, encoding="latin-1")


def process_zip(state: str, year: int, zip_path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path) as zf:
        incident = read_csv_from_zip(
            zf,
            "NIBRS_incident.csv",
            ["incident_id", "agency_id", "incident_date", "incident_hour"],
        )
        offense = read_csv_from_zip(
            zf,
            "NIBRS_OFFENSE.csv",
            ["incident_id", "offense_code"],
        )
        agencies = read_csv_from_zip(
            zf,
            "agencies.csv",
            ["agency_id", "county_name", "state_abbr"],
        )

    offense["offense_code"] = offense["offense_code"].astype(str)
    offense = offense[offense["offense_code"].isin(FOCUS_CRIME_CODES)].copy()
    if offense.empty:
        return pd.DataFrame()

    merged = offense.merge(incident, on="incident_id", how="inner")
    merged = merged.merge(agencies, on="agency_id", how="left")

    merged["crime_type"] = merged["offense_code"].map(FOCUS_CRIME_CODES)
    merged["state"] = state
    merged["year"] = year

    merged["incident_date"] = pd.to_datetime(merged["incident_date"], errors="coerce").dt.date
    merged["incident_hour"] = pd.to_numeric(merged["incident_hour"], errors="coerce")

    merged["county_name"] = (
        merged["county_name"].fillna("UNKNOWN").astype(str).str.upper().str.strip()
    )

    if state == "AZ":
        merged = merged[~merged["county_name"].isin(AZ_EXCLUDED_COUNTIES)].copy()

    merged = merged.dropna(subset=["incident_date", "incident_hour", "crime_type"])
    merged["incident_hour"] = merged["incident_hour"].astype(int)
    merged = merged[(merged["incident_hour"] >= 0) & (merged["incident_hour"] <= 23)]

    # Deduplicate in case of repeated rows within source files.
    merged = merged.drop_duplicates(subset=["incident_id", "offense_code", "incident_hour"])

    return merged[["state", "year", "county_name", "incident_date", "incident_hour", "crime_type"]]


def main() -> None:
    zips = discover_focus_zips(RAW_ZIP_DIR)
    if not zips:
        print("No focus-state ZIPs found.")
        print("Expected files like CA-2024.zip, FL-2024.zip, AZ-2024.zip in:")
        print(f"  {RAW_ZIP_DIR}")
        return

    print(f"Found {len(zips)} focus-state ZIP file(s).")
    all_rows: list[pd.DataFrame] = []

    for state, year, path in zips:
        print(f"Processing {path.name}...")
        df = process_zip(state=state, year=year, zip_path=path)
        if df.empty:
            print(f"  -> No target crimes found in {path.name}")
            continue
        print(f"  -> rows: {len(df):,}")
        all_rows.append(df)

    if not all_rows:
        print("No parsed rows for burglary/motor-vehicle-theft after filtering.")
        return

    full = pd.concat(all_rows, ignore_index=True)

    daily = (
        full.groupby(["state", "year", "county_name", "incident_date", "crime_type"], as_index=False)
        .size()
        .rename(columns={"size": "incident_count"})
        .sort_values(["state", "year", "incident_date", "county_name", "crime_type"])
    )

    hourly = (
        full.groupby(
            ["state", "year", "county_name", "incident_date", "incident_hour", "crime_type"],
            as_index=False,
        )
        .size()
        .rename(columns={"size": "incident_count"})
        .sort_values(["state", "year", "incident_date", "incident_hour", "county_name", "crime_type"])
    )

    summary = (
        full.groupby(["state", "year", "crime_type"], as_index=False)
        .size()
        .rename(columns={"size": "incident_count"})
        .sort_values(["state", "year", "crime_type"])
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    daily_path = OUT_DIR / "focus_states_daily_county_counts.csv"
    hourly_path = OUT_DIR / "focus_states_hourly_county_counts.csv"
    summary_path = OUT_DIR / "focus_states_state_year_summary.csv"

    daily.to_csv(daily_path, index=False)
    hourly.to_csv(hourly_path, index=False)
    summary.to_csv(summary_path, index=False)

    print("\nWrote outputs:")
    print(f"- {daily_path} ({len(daily):,} rows)")
    print(f"- {hourly_path} ({len(hourly):,} rows)")
    print(f"- {summary_path} ({len(summary):,} rows)")


if __name__ == "__main__":
    main()
