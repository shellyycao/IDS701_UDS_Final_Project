"""
Compute monthly state-level aggregates for parallel trends DiD visualization.

For each state (AZ control, CA treated, NV treated) × crime type:
  - Total daily crime: avg_daily_count, avg_daily_rate_per_100k
  - Evening (17–20h) crime: avg_evening_count, avg_evening_rate_per_100k

Output: data/processed/model/parallel_trends_monthly.csv
  One row per (state, year_month, crime_type)
"""
from pathlib import Path

import numpy as np
import pandas as pd

EVENING_FILE = "data/processed/model/evening_crime_panel.csv"
OUT_FILE = "data/processed/model/parallel_trends_monthly.csv"


def main():
    Path(OUT_FILE).parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(EVENING_FILE, low_memory=False)
    df["incident_date"] = pd.to_datetime(df["incident_date"], errors="coerce")
    df["year_month"] = df["incident_date"].dt.to_period("M")

    # Monthly aggregate: mean across county-days within each state-month
    # (average at county level first, then average across counties)
    grp = df.groupby(["state", "offense_type", "year_month", "county_fips"]).agg(
        daily_total=("total_count", "mean"),
        daily_evening=("evening_count", "mean"),
        daily_total_rate=("total_rate_per_100k", "mean"),
        daily_evening_rate=("evening_rate_per_100k", "mean"),
    ).reset_index()

    monthly = grp.groupby(["state", "offense_type", "year_month"]).agg(
        avg_daily_count=("daily_total", "mean"),
        avg_evening_count=("daily_evening", "mean"),
        avg_daily_rate=("daily_total_rate", "mean"),
        avg_evening_rate=("daily_evening_rate", "mean"),
        n_counties=("county_fips", "nunique"),
    ).reset_index()

    monthly["year_month"] = monthly["year_month"].astype(str)
    monthly["year"] = monthly["year_month"].str[:4].astype(int)
    monthly["month"] = monthly["year_month"].str[5:].astype(int)

    # DST window flag: March–November (months 3–11) for CA and NV; AZ never observes DST
    monthly["in_dst_window"] = (
        (monthly["state"].isin(["CA", "NV"])) &
        (monthly["month"].between(3, 11))
    ).astype(int)

    monthly = monthly.sort_values(["state", "offense_type", "year_month"]).reset_index(drop=True)
    monthly.to_csv(OUT_FILE, index=False)
    print(f"Saved {len(monthly):,} rows -> {OUT_FILE}")
    print(f"States: {sorted(monthly['state'].unique())}")
    print(f"Date range: {monthly['year_month'].min()} – {monthly['year_month'].max()}")
    print(monthly.groupby(["state", "offense_type"])[["avg_daily_count", "avg_daily_rate"]].mean().round(2))


if __name__ == "__main__":
    main()
