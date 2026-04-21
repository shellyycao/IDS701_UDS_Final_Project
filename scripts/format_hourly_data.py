from pathlib import Path

import pandas as pd

HOURLY_FILE = "data/processed/crime/focus_states_hourly_county_counts.csv"
TIMEZONE_FILE = "data/raw/timezone/focus_states_county_centroids_timezone.csv"
OUT_FILE = "data/processed/crime/focus_states_hourly_structured.csv"


def main():
    df = pd.read_csv(HOURLY_FILE, dtype=str)
    df.columns = df.columns.str.strip().str.lower()

    df["incident_date"] = pd.to_datetime(df["incident_date"], errors="coerce")
    df["year"] = df["incident_date"].dt.year.astype(str)
    df["month"] = df["incident_date"].dt.month.astype(str).str.zfill(2)
    df["day"] = df["incident_date"].dt.day.astype(str).str.zfill(2)

    df.rename(columns={"crime_type": "offense_type", "incident_count": "crime_count"}, inplace=True)
    df["county_name"] = df["county_name"].str.strip().str.upper()

    tz = pd.read_csv(TIMEZONE_FILE, dtype=str)
    tz.columns = tz.columns.str.strip().str.lower()
    tz["county_name"] = tz["county_name"].str.strip().str.upper()
    tz["county_fips"] = tz["county_fips"].str.strip().str.zfill(5)

    df = df.merge(
        tz[["state", "county_name", "county_fips"]],
        on=["state", "county_name"],
        how="left",
    )

    out_cols = ["state", "county_fips", "year", "month", "day", "incident_hour",
                "offense_type", "crime_count"]
    df = df.rename(columns={"incident_hour": "hour"})
    out_cols = ["state", "county_fips", "year", "month", "day", "hour",
                "offense_type", "crime_count"]
    df = df[out_cols]

    Path(OUT_FILE).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_FILE, index=False)
    print(f"Saved {len(df):,} rows to {OUT_FILE}")


if __name__ == "__main__":
    main()
