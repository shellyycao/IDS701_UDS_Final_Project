"""Build non-aggregated panel data for focus states (CA, FL, AZ).

This script keeps data granular at the incident-offense row level.
No county/day/hour aggregation is performed.

Input:
- data/raw/crime/nibrs_state_year/{STATE}-{YEAR}.zip

Output:
- data/processed/panel/focus_states_incident_offense_panel.csv
- data/processed/panel/focus_states_incident_offense_panel.parquet (if pyarrow/fastparquet available)

Panel grain:
- one row per offense record (offense_id) joined to incident + agency metadata

Filters:
- States: CA, FL, AZ
- Crime types: Burglary (220), Motor Vehicle Theft (240), Theft From Motor Vehicle (23F),
  Robbery (120), Theft From Building (23D), Shoplifting (23C)
- Arizona counties excluded per proposal: Apache, Navajo, Coconino
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import zipfile

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_ZIP_DIR = ROOT / "data" / "raw" / "crime" / "nibrs_state_year"
OUT_DIR = ROOT / "data" / "processed" / "panel"

FOCUS_STATES = {"CA", "FL", "AZ", "UT"}
FOCUS_CRIME_CODES = {"120", "220", "23C", "23D", "23F", "240"}
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


def find_member_name(zf: zipfile.ZipFile, member: str) -> str:
    target = member.lower()
    for name in zf.namelist():
        if name.lower() == target:
            return name
    for name in zf.namelist():
        if Path(name).name.lower() == target:
            return name
    raise KeyError(f"Could not find {member} in archive")


def read_csv_from_zip(zf: zipfile.ZipFile, member: str, usecols: list[str]) -> pd.DataFrame:
    real_member = find_member_name(zf, member)
    try:
        with zf.open(real_member) as f:
            return pd.read_csv(f, usecols=usecols, low_memory=False, encoding="utf-8")
    except UnicodeDecodeError:
        with zf.open(real_member) as f:
            return pd.read_csv(f, usecols=usecols, low_memory=False, encoding="latin-1")


def read_csv_optional(zf: zipfile.ZipFile, member: str, usecols: list[str]) -> pd.DataFrame:
    try:
        return read_csv_from_zip(zf, member, usecols)
    except Exception:
        return pd.DataFrame(columns=usecols)


def process_zip(state: str, year: int, zip_path: Path, enrich: bool) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path) as zf:
        incident = read_csv_from_zip(
            zf,
            "NIBRS_incident.csv",
            [
                "incident_id",
                "agency_id",
                "nibrs_month_id",
                "incident_date",
                "incident_hour",
                "submission_date",
                "report_date_flag",
                "cargo_theft_flag",
            ],
        )
        offense = read_csv_from_zip(
            zf,
            "NIBRS_OFFENSE.csv",
            ["offense_id", "incident_id", "offense_code", "attempt_complete_flag", "location_id"],
        )
        agencies = read_csv_from_zip(
            zf,
            "agencies.csv",
            ["agency_id", "ori", "ucr_agency_name", "state_abbr", "county_name"],
        )
        offense_type = read_csv_from_zip(
            zf,
            "NIBRS_OFFENSE_TYPE.csv",
            ["offense_code", "offense_name", "crime_against"],
        )
        nibrs_month = pd.DataFrame(columns=["nibrs_month_id", "reported_status", "report_date", "update_flag"])
        victim = pd.DataFrame(columns=["incident_id", "victim_id"])
        offender = pd.DataFrame(columns=["incident_id", "offender_id"])
        arrestee = pd.DataFrame(columns=["incident_id", "arrestee_id"])
        prop = pd.DataFrame(columns=["incident_id", "property_id"])
        if enrich:
            nibrs_month = read_csv_optional(
                zf,
                "NIBRS_month.csv",
                ["nibrs_month_id", "reported_status", "report_date", "update_flag"],
            )
            victim = read_csv_optional(zf, "NIBRS_VICTIM.csv", ["incident_id", "victim_id"])
            offender = read_csv_optional(zf, "NIBRS_OFFENDER.csv", ["incident_id", "offender_id"])
            arrestee = read_csv_optional(zf, "NIBRS_ARRESTEE.csv", ["incident_id", "arrestee_id"])
            prop = read_csv_optional(zf, "NIBRS_PROPERTY.csv", ["incident_id", "property_id"])

    for df in (incident, offense, agencies, offense_type, nibrs_month, victim, offender, arrestee, prop):
        df.columns = [c.lower() for c in df.columns]

    offense["offense_code"] = offense["offense_code"].astype(str).str.strip().str.upper()
    offense = offense[offense["offense_code"].isin(FOCUS_CRIME_CODES)].copy()
    if offense.empty:
        return pd.DataFrame()

    merged = offense.merge(incident, on="incident_id", how="inner")
    merged = merged.merge(agencies, on="agency_id", how="left")
    merged = merged.merge(offense_type, on="offense_code", how="left")
    if not nibrs_month.empty and "nibrs_month_id" in merged.columns:
        merged = merged.merge(nibrs_month, on="nibrs_month_id", how="left")

    if not victim.empty:
        victim_counts = (
            victim.groupby("incident_id", as_index=False)["victim_id"].nunique().rename(columns={"victim_id": "victim_count"})
        )
        merged = merged.merge(victim_counts, on="incident_id", how="left")
    if not offender.empty:
        offender_counts = (
            offender.groupby("incident_id", as_index=False)["offender_id"].nunique().rename(columns={"offender_id": "offender_count"})
        )
        merged = merged.merge(offender_counts, on="incident_id", how="left")
    if not arrestee.empty:
        arrestee_counts = (
            arrestee.groupby("incident_id", as_index=False)["arrestee_id"].nunique().rename(columns={"arrestee_id": "arrestee_count"})
        )
        merged = merged.merge(arrestee_counts, on="incident_id", how="left")
    if not prop.empty:
        prop_counts = (
            prop.groupby("incident_id", as_index=False)["property_id"].nunique().rename(columns={"property_id": "property_record_count"})
        )
        merged = merged.merge(prop_counts, on="incident_id", how="left")

    merged["state"] = state
    merged["data_year"] = year
    merged["county_name"] = merged["county_name"].fillna("UNKNOWN").astype(str).str.upper().str.strip()

    if state == "AZ":
        merged = merged[~merged["county_name"].isin(AZ_EXCLUDED_COUNTIES)].copy()

    merged["incident_date"] = pd.to_datetime(merged["incident_date"], errors="coerce").dt.date
    merged["incident_hour"] = pd.to_numeric(merged["incident_hour"], errors="coerce")
    merged = merged.dropna(subset=["incident_date", "incident_hour"])
    merged["incident_hour"] = merged["incident_hour"].astype(int)
    merged = merged[(merged["incident_hour"] >= 0) & (merged["incident_hour"] <= 23)]

    merged["incident_datetime"] = pd.to_datetime(
        merged["incident_date"].astype(str)
        + " "
        + merged["incident_hour"].astype(str).str.zfill(2)
        + ":00:00",
        format="%Y-%m-%d %H:%M:%S",
        errors="coerce",
    )

    merged["crime_type"] = merged["offense_code"].map(
        {
            "120": "robbery",
            "220": "burglary",
            "23C": "shoplifting",
            "23D": "theft_from_building",
            "23F": "theft_from_motor_vehicle",
            "240": "motor_vehicle_theft",
        }
    )

    merged["is_weekend"] = pd.to_datetime(merged["incident_date"]).dt.dayofweek >= 5
    merged["month"] = pd.to_datetime(merged["incident_date"]).dt.month
    merged["day_of_week"] = pd.to_datetime(merged["incident_date"]).dt.dayofweek

    # Deduplicate repeated offense rows if present.
    merged = merged.drop_duplicates(subset=["data_year", "incident_id", "offense_id", "offense_code"])

    for c in ["victim_count", "offender_count", "arrestee_count", "property_record_count"]:
        if c in merged.columns:
            merged[c] = merged[c].fillna(0).astype(int)

    keep_cols = [
        "state",
        "data_year",
        "county_name",
        "agency_id",
        "ori",
        "ucr_agency_name",
        "incident_id",
        "nibrs_month_id",
        "offense_id",
        "offense_code",
        "offense_name",
        "crime_type",
        "crime_against",
        "cargo_theft_flag",
        "report_date_flag",
        "attempt_complete_flag",
        "location_id",
        "incident_date",
        "incident_hour",
        "incident_datetime",
        "submission_date",
        "reported_status",
        "report_date",
        "update_flag",
        "victim_count",
        "offender_count",
        "arrestee_count",
        "property_record_count",
        "month",
        "day_of_week",
        "is_weekend",
    ]

    for col in keep_cols:
        if col not in merged.columns:
            merged[col] = pd.NA

    return merged[keep_cols]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build focus-state NIBRS panel.")
    parser.add_argument(
        "--enrich",
        action="store_true",
        help="Include heavier incident-level enrichments (victim/offender/arrestee/property/month tables).",
    )
    parser.add_argument(
        "--skip-parquet",
        action="store_true",
        help="Skip writing parquet output to reduce runtime.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    zips = discover_focus_zips(RAW_ZIP_DIR)
    if not zips:
        print("No focus-state ZIPs found in data/raw/crime/nibrs_state_year/")
        return

    print(f"Found {len(zips)} focus-state ZIP file(s).")
    parts: list[pd.DataFrame] = []

    for state, year, path in zips:
        print(f"Processing {path.name}...")
        part = process_zip(state=state, year=year, zip_path=path, enrich=args.enrich)
        if part.empty:
            print("  -> no rows after filters")
            continue
        print(f"  -> rows: {len(part):,}")
        parts.append(part)

    if not parts:
        print("No rows produced.")
        return

    panel = pd.concat(parts, ignore_index=True)
    panel = panel.sort_values(["state", "data_year", "incident_date", "incident_hour", "county_name"]) 

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / "focus_states_incident_offense_panel.csv"
    parquet_path = OUT_DIR / "focus_states_incident_offense_panel.parquet"

    panel.to_csv(csv_path, index=False)

    if args.skip_parquet:
        parquet_status = "skipped (--skip-parquet)"
    else:
        try:
            panel.to_parquet(parquet_path, index=False)
            parquet_status = "written"
        except Exception as exc:  # noqa: BLE001
            parquet_status = f"skipped ({exc})"

    print("\nPanel output:")
    print(f"- {csv_path} ({len(panel):,} rows)")
    print(f"- {parquet_path} ({parquet_status})")


if __name__ == "__main__":
    main()
