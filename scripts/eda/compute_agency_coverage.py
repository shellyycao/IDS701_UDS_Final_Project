from pathlib import Path

import pandas as pd

IN_FILE = "data/processed/crime/focus_states_daily_county_counts.csv"
OUT_FILE = "data/processed/analysis/agency_coverage.csv"


def main():
    Path(OUT_FILE).parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(IN_FILE, dtype=str)
    df.columns = df.columns.str.strip().str.lower()
    df["incident_date"] = pd.to_datetime(df["incident_date"], errors="coerce")
    df["incident_count"] = pd.to_numeric(df["incident_count"], errors="coerce").fillna(0)

    # 2024 only (leap year = 366 days)
    df2024 = df[df["incident_date"].dt.year == 2024].copy()

    active = df2024[df2024["incident_count"] > 0].copy()
    days_reported = (
        active.groupby(["state", "county_name"])["incident_date"]
        .nunique()
        .reset_index(name="days_reported")
    )

    # All unique state-county combos seen in the data
    all_counties = df2024[["state", "county_name"]].drop_duplicates()
    result = all_counties.merge(days_reported, on=["state", "county_name"], how="left")
    result["days_reported"] = result["days_reported"].fillna(0).astype(int)
    result["reporting_rate"] = result["days_reported"] / 366
    result["below_80pct"] = result["reporting_rate"] < 0.80

    result.sort_values(["state", "reporting_rate"], ascending=[True, False], inplace=True)
    result.to_csv(OUT_FILE, index=False)
    print(f"Saved {len(result)} rows -> {OUT_FILE}")
    print(f"Counties below 80%: {result['below_80pct'].sum()}")


if __name__ == "__main__":
    main()
