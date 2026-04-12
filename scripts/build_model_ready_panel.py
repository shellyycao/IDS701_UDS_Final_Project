"""Build model-ready daily county panel for DST-crime analysis.

Inputs:
- data/processed/panel/focus_states_incident_offense_panel.csv
- data/raw/timezone/focus_states_county_centroids_timezone.csv
- data/processed/population/focus_states_county_population_2020_2024_long.csv
- data/raw/holidays/us_public_holidays_2021_2024.csv
- data/processed/socioeconomic/acs_county_controls_derived_2021_2024.csv

Outputs:
- data/processed/model/focus_states_daily_county_model_panel_2021_2024.csv
- data/processed/model/focus_states_county_date_treatment_2021_2024.csv
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
import re

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

PANEL_IN = ROOT / "data" / "processed" / "panel" / "focus_states_incident_offense_panel.csv"
TZ_IN = ROOT / "data" / "raw" / "timezone" / "focus_states_county_centroids_timezone.csv"
POP_IN = ROOT / "data" / "processed" / "population" / "focus_states_county_population_2020_2024_long.csv"
HOLIDAY_IN = ROOT / "data" / "raw" / "holidays" / "us_public_holidays_2021_2024.csv"
SOCIO_IN = ROOT / "data" / "processed" / "socioeconomic" / "acs_county_controls_derived_2021_2024.csv"

MODEL_OUT = ROOT / "data" / "processed" / "model" / "focus_states_daily_county_model_panel_2021_2024.csv"
MODEL_OUT_2022 = ROOT / "data" / "processed" / "model" / "focus_states_daily_county_model_panel_2022_2024.csv"
TREATMENT_OUT = ROOT / "data" / "processed" / "model" / "focus_states_county_date_treatment_2021_2024.csv"
TREATMENT_OUT_2022 = ROOT / "data" / "processed" / "model" / "focus_states_county_date_treatment_2022_2024.csv"


def norm_county(s: pd.Series) -> pd.Series:
    return (
        s.astype(str)
        .str.upper()
        .str.replace(" COUNTY", "", regex=False)
        .str.replace(r"[^A-Z0-9]", "", regex=True)
        .str.strip()
    )


def nth_weekday_of_month(y: int, m: int, weekday: int, n: int) -> date:
    d = date(y, m, 1)
    offset = (weekday - d.weekday()) % 7
    first = d.toordinal() + offset
    target = first + (n - 1) * 7
    return date.fromordinal(target)


def build_dst_bounds(years: list[int]) -> pd.DataFrame:
    rows = []
    for y in years:
        start = nth_weekday_of_month(y, 3, 6, 2)  # 2nd Sunday March
        end = nth_weekday_of_month(y, 11, 6, 1)   # 1st Sunday Nov
        rows.append({"data_year": y, "dst_start_date": start, "dst_end_date": end})
    return pd.DataFrame(rows)


def build_treatment_table(base_daily: pd.DataFrame) -> pd.DataFrame:
    years = sorted(base_daily["data_year"].unique().tolist())
    bounds = build_dst_bounds(years)

    out = base_daily[["state", "county_fips", "county_name", "incident_date", "data_year", "timezone", "proposal_excluded_az_county"]].drop_duplicates().copy()
    out = out.merge(bounds, on="data_year", how="left")

    out["incident_date"] = pd.to_datetime(out["incident_date"], errors="coerce").dt.date
    out["dst_start_date"] = pd.to_datetime(out["dst_start_date"], errors="coerce").dt.date
    out["dst_end_date"] = pd.to_datetime(out["dst_end_date"], errors="coerce").dt.date

    out["treated_state"] = out["state"].isin(["CA", "FL"]) 
    out["is_az_control"] = out["state"].eq("AZ")

    # County-level DST observance flag from timezone assignment.
    out["observes_dst_county"] = ~out["timezone"].isin(["America/Phoenix"])

    out["in_dst_window"] = (
        out["observes_dst_county"]
        & (out["incident_date"] >= out["dst_start_date"])
        & (out["incident_date"] < out["dst_end_date"])
    )

    out["days_from_dst_start"] = (
        pd.to_datetime(out["incident_date"]) - pd.to_datetime(out["dst_start_date"])
    ).dt.days
    out["days_from_dst_end"] = (
        pd.to_datetime(out["incident_date"]) - pd.to_datetime(out["dst_end_date"])
    ).dt.days

    out["post_dst_start"] = out["days_from_dst_start"] >= 0
    out["post_dst_end"] = out["days_from_dst_end"] >= 0

    return out.sort_values(["state", "county_fips", "incident_date"]).reset_index(drop=True)


def main() -> None:
    panel = pd.read_csv(PANEL_IN, low_memory=False)
    tz = pd.read_csv(TZ_IN, low_memory=False)
    pop = pd.read_csv(POP_IN, low_memory=False)
    hol = pd.read_csv(HOLIDAY_IN, low_memory=False)
    socio = pd.read_csv(SOCIO_IN, low_memory=False)

    for df in (tz, pop, socio):
        if "county_fips" in df.columns:
            df["county_fips"] = df["county_fips"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(5)

    # Normalize county keys for robust joins.
    panel["county_key"] = norm_county(panel["county_name"])
    tz["county_key"] = norm_county(tz["county_name"])
    pop["county_key"] = norm_county(pop["county_name"])
    socio["county_key"] = norm_county(socio["county_name"])

    panel["incident_date"] = pd.to_datetime(panel["incident_date"], errors="coerce").dt.date
    panel = panel.dropna(subset=["incident_date"]).copy()

    # Attach county_fips + timezone.
    panel = panel.merge(
        tz[["state", "county_key", "county_fips", "timezone", "proposal_excluded_az_county"]],
        on=["state", "county_key"],
        how="left",
    )

    # Build full county × date × crime_type skeleton (zero-filled).
    # Using the tz table as the canonical county list ensures every county appears
    # even on days with no reported incidents.
    date_range = pd.date_range("2021-01-01", "2024-12-31", freq="D")
    dates_df = pd.DataFrame({
        "incident_date": date_range.date,
        "data_year": date_range.year,
    })
    crime_types = sorted(panel["crime_type"].dropna().unique().tolist())
    crime_df = pd.DataFrame({"crime_type": crime_types})

    county_meta = (
        tz[["state", "county_key", "county_fips", "county_name", "timezone", "proposal_excluded_az_county"]]
        .drop_duplicates(subset=["state", "county_fips"])
        .copy()
    )

    skeleton = (
        county_meta.assign(_k=1)
        .merge(dates_df.assign(_k=1), on="_k")
        .merge(crime_df.assign(_k=1), on="_k")
        .drop(columns="_k")
    )

    # Aggregate observed incident counts by county + date + crime_type.
    observed = (
        panel.groupby(["state", "county_fips", "incident_date", "crime_type"], as_index=False)
        .size()
        .rename(columns={"size": "incident_count"})
    )
    observed["incident_date"] = pd.to_datetime(observed["incident_date"], errors="coerce").dt.date

    # Left-join observed onto skeleton; unmatched cells get explicit zero.
    daily = skeleton.merge(observed, on=["state", "county_fips", "incident_date", "crime_type"], how="left")
    daily["incident_count"] = daily["incident_count"].fillna(0).astype(int)

    # Merge population by state + county_fips + year.
    pop_yr = pop[["state", "county_fips", "data_year", "population"]].drop_duplicates(subset=["state", "county_fips", "data_year"])
    daily = daily.merge(pop_yr, on=["state", "county_fips", "data_year"], how="left")

    daily = daily.merge(
        socio[["state", "data_year", "county_key", "county_fips", "median_household_income", "poverty_rate", "unemployment_rate", "bachelors_plus_rate"]],
        on=["state", "data_year", "county_key", "county_fips"],
        how="left",
    )

    # Merge holiday flags.
    # Deduplicate to one row per date before merging to prevent fan-out from
    # multi-name dates (e.g. Columbus Day / Indigenous Peoples' Day, duplicate
    # Good Friday entries).  Collapse multiple names with "; ".
    hol["date"] = pd.to_datetime(hol["date"], errors="coerce").dt.date
    hol_deduped = (
        hol.groupby("date", as_index=False)
        .agg(holiday_name=("name", lambda x: "; ".join(sorted(set(x)))))
    )
    hol_deduped["is_holiday"] = True
    daily = daily.merge(
        hol_deduped.rename(columns={"date": "incident_date"}),
        on="incident_date",
        how="left",
    )
    daily["is_holiday"] = daily["is_holiday"].fillna(False)

    # Calendar features.
    dt = pd.to_datetime(daily["incident_date"]) 
    daily["month"] = dt.dt.month
    daily["day_of_week"] = dt.dt.dayofweek
    daily["is_weekend"] = daily["day_of_week"] >= 5

    # Treatment flags (DST design).
    treatment = build_treatment_table(daily)
    daily = daily.merge(
        treatment[
            [
                "state",
                "county_fips",
                "incident_date",
                "treated_state",
                "is_az_control",
                "observes_dst_county",
                "in_dst_window",
                "days_from_dst_start",
                "days_from_dst_end",
                "post_dst_start",
                "post_dst_end",
            ]
        ],
        on=["state", "county_fips", "incident_date"],
        how="left",
    )

    # Per-capita outcome.
    daily["crime_rate_per_100k"] = (daily["incident_count"] / daily["population"]) * 100000.0

    # Keep tidy ordering.
    cols = [
        "state",
        "data_year",
        "county_fips",
        "county_name",
        "incident_date",
        "crime_type",
        "incident_count",
        "population",
        "crime_rate_per_100k",
        "timezone",
        "proposal_excluded_az_county",
        "treated_state",
        "is_az_control",
        "observes_dst_county",
        "in_dst_window",
        "days_from_dst_start",
        "days_from_dst_end",
        "post_dst_start",
        "post_dst_end",
        "is_holiday",
        "holiday_name",
        "month",
        "day_of_week",
        "is_weekend",
        "median_household_income",
        "poverty_rate",
        "unemployment_rate",
        "bachelors_plus_rate",
    ]

    for c in cols:
        if c not in daily.columns:
            daily[c] = pd.NA

    daily = daily[cols].sort_values(["state", "county_fips", "incident_date", "crime_type"]).reset_index(drop=True)

    daily["county_fips"] = daily["county_fips"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(5)
    treatment["county_fips"] = treatment["county_fips"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(5)

    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    daily.to_csv(MODEL_OUT, index=False)
    treatment.to_csv(TREATMENT_OUT, index=False)

    # 2022-2024 primary analysis window subset.
    daily_2022 = daily[daily["data_year"] >= 2022].reset_index(drop=True)
    treatment_2022 = treatment[treatment["data_year"] >= 2022].reset_index(drop=True)
    daily_2022.to_csv(MODEL_OUT_2022, index=False)
    treatment_2022.to_csv(TREATMENT_OUT_2022, index=False)

    print(f"Wrote: {MODEL_OUT} rows={len(daily):,}")
    print(f"Wrote: {MODEL_OUT_2022} rows={len(daily_2022):,}")
    print(f"Wrote: {TREATMENT_OUT} rows={len(treatment):,}")
    print(f"Wrote: {TREATMENT_OUT_2022} rows={len(treatment_2022):,}")

    dup_keys = daily.duplicated(subset=["state", "county_fips", "incident_date", "crime_type"]).sum()
    zero_share = (daily["incident_count"] == 0).mean()
    print("Integrity summary:")
    print(
        {
            "missing_county_fips": int(daily["county_fips"].isna().sum()),
            "missing_population": int(daily["population"].isna().sum()),
            "missing_timezone": int(daily["timezone"].isna().sum()),
            "missing_income": int(daily["median_household_income"].isna().sum()),
            "duplicate_keys": int(dup_keys),
            "zero_incident_share": round(float(zero_share), 4),
        }
    )


if __name__ == "__main__":
    main()
