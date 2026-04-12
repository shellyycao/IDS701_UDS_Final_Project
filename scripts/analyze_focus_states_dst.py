"""Create first-pass DST analysis tables from parsed focus-state crime aggregates.

Inputs:
- data/processed/crime/focus_states_daily_county_counts.csv
- data/raw/population/county_population_acs_2021_2023.csv (optional for per-capita rates)

Outputs:
- data/processed/analysis/focus_states_daily_with_dst_flags.csv
- data/processed/analysis/focus_states_dst_period_summary.csv
- data/processed/analysis/focus_states_hour_bucket_summary.csv
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DAILY_INPUT = ROOT / "data" / "processed" / "crime" / "focus_states_daily_county_counts.csv"
HOURLY_INPUT = ROOT / "data" / "processed" / "crime" / "focus_states_hourly_county_counts.csv"
POP_INPUT = ROOT / "data" / "raw" / "population" / "county_population_acs_2021_2023.csv"
OUT_DIR = ROOT / "data" / "processed" / "analysis"

DST_STATES = {"CA", "FL"}
NO_DST_STATES = {"AZ"}


def nth_weekday_of_month(y: int, m: int, weekday: int, n: int) -> date:
    d = date(y, m, 1)
    offset = (weekday - d.weekday()) % 7
    first = d.toordinal() + offset
    target = first + (n - 1) * 7
    return date.fromordinal(target)


def dst_bounds_us(year: int) -> tuple[date, date]:
    # US DST: second Sunday in March to first Sunday in November.
    start = nth_weekday_of_month(year, 3, 6, 2)
    end = nth_weekday_of_month(year, 11, 6, 1)
    return start, end


def add_dst_flags(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["incident_date"] = pd.to_datetime(out["incident_date"])  # date-like string
    out["year"] = out["incident_date"].dt.year

    starts = {}
    ends = {}
    for y in sorted(out["year"].unique()):
        s, e = dst_bounds_us(int(y))
        starts[int(y)] = pd.Timestamp(s)
        ends[int(y)] = pd.Timestamp(e)

    out["dst_start"] = out["year"].map(starts)
    out["dst_end"] = out["year"].map(ends)

    out["in_dst_window"] = (out["incident_date"] >= out["dst_start"]) & (
        out["incident_date"] < out["dst_end"]
    )

    out["dst_observed"] = out["state"].isin(DST_STATES)
    out["is_dst_period"] = out["dst_observed"] & out["in_dst_window"]
    out["is_standard_period"] = out["dst_observed"] & (~out["in_dst_window"])
    out["is_az_counterfactual_dst_window"] = out["state"].isin(NO_DST_STATES) & out[
        "in_dst_window"
    ]

    return out


def attach_population_if_available(df: pd.DataFrame) -> pd.DataFrame:
    if not POP_INPUT.exists():
        return df

    pop = pd.read_csv(POP_INPUT, low_memory=False)
    needed = {"year", "state", "county", "population"}
    if not needed.issubset(set(pop.columns)):
        return df

    pop = pop.rename(columns={"county": "county_name"})
    pop["state"] = pop["state"].astype(str).str.upper()
    pop["county_name"] = pop["county_name"].astype(str).str.upper().str.strip()

    out = df.merge(pop[["year", "state", "county_name", "population"]], on=["year", "state", "county_name"], how="left")
    out["rate_per_100k"] = (out["incident_count"] / out["population"]) * 100000
    return out


def build_hour_bucket_summary(hourly: pd.DataFrame) -> pd.DataFrame:
    h = hourly.copy()
    h["incident_date"] = pd.to_datetime(h["incident_date"])
    h["year"] = h["incident_date"].dt.year
    h = add_dst_flags(h)

    h["hour_bucket"] = "other"
    h.loc[h["incident_hour"].between(17, 20), "hour_bucket"] = "evening_5pm_9pm"
    h.loc[h["incident_hour"].between(5, 8), "hour_bucket"] = "morning_5am_9am"
    h = h[h["hour_bucket"] != "other"].copy()

    out = (
        h.groupby(["state", "year", "crime_type", "hour_bucket", "in_dst_window"], as_index=False)[
            "incident_count"
        ]
        .sum()
        .sort_values(["state", "year", "crime_type", "hour_bucket", "in_dst_window"])
    )
    return out


def main() -> None:
    if not DAILY_INPUT.exists() or not HOURLY_INPUT.exists():
        print("Missing parsed crime inputs. Run scripts/parse_nibrs_focus_states.py first.")
        return

    daily = pd.read_csv(DAILY_INPUT, low_memory=False)
    hourly = pd.read_csv(HOURLY_INPUT, low_memory=False)

    daily = add_dst_flags(daily)
    daily = attach_population_if_available(daily)

    period_summary = (
        daily.groupby(["state", "year", "crime_type", "in_dst_window"], as_index=False)["incident_count"]
        .sum()
        .sort_values(["state", "year", "crime_type", "in_dst_window"])
    )

    hour_bucket_summary = build_hour_bucket_summary(hourly)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    detailed_path = OUT_DIR / "focus_states_daily_with_dst_flags.csv"
    period_path = OUT_DIR / "focus_states_dst_period_summary.csv"
    hour_path = OUT_DIR / "focus_states_hour_bucket_summary.csv"

    daily.to_csv(detailed_path, index=False)
    period_summary.to_csv(period_path, index=False)
    hour_bucket_summary.to_csv(hour_path, index=False)

    print("Wrote analysis outputs:")
    print(f"- {detailed_path} ({len(daily):,} rows)")
    print(f"- {period_path} ({len(period_summary):,} rows)")
    print(f"- {hour_path} ({len(hour_bucket_summary):,} rows)")


if __name__ == "__main__":
    main()
