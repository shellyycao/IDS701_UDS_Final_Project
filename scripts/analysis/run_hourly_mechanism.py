"""
Stage 1 hourly mechanism test.

Estimates whether DST shifts crime across hours of the day by interacting
the DST indicator with each hour dummy (Section 7 of the analysis plan).

Model per (state × crime_type):
  log(count+1) ~ Σ_h β_h*(DST × I(hour=h)) + temperature + FEs

Fixed effects absorbed: county, day-of-week, year, month.
SE clustered by county.

Input:  data/processed/crime/focus_states_hourly_structured.csv
        data/processed/model/within_state_panel.csv  (for weather + controls)
Output: data/processed/model/hourly_dst_effects.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd
from linearmodels.iv.absorbing import AbsorbingLS

HOURLY_FILE  = "data/processed/crime/focus_states_hourly_structured.csv"
PANEL_FILE   = "data/processed/model/within_state_panel.csv"
WEATHER_FILE = "data/raw/weather/comparison_states_daily_weather_2021_2024.csv"
OUT_FILE     = "data/processed/model/hourly_dst_effects.csv"

FOCUS_STATES = {"CA", "NV"}
FOCUS_CRIMES = {"burglary", "motor_vehicle_theft"}


def load_state_weather():
    cw = pd.read_csv(WEATHER_FILE, dtype=str)
    cw["date"] = pd.to_datetime(cw["date"], errors="coerce")
    cw["temperature_2m_mean"] = pd.to_numeric(cw["temperature_2m_mean"], errors="coerce")
    return cw[cw["state"].isin(FOCUS_STATES)][["state", "date", "temperature_2m_mean"]].rename(
        columns={"temperature_2m_mean": "temperature"}
    )


def main():
    Path(OUT_FILE).parent.mkdir(parents=True, exist_ok=True)

    # Load hourly crime
    hourly = pd.read_csv(HOURLY_FILE, dtype=str, low_memory=False)
    hourly.columns = hourly.columns.str.strip().str.lower()
    hourly["hour"]          = pd.to_numeric(hourly["hour"], errors="coerce")
    hourly["crime_count"]   = pd.to_numeric(hourly["crime_count"], errors="coerce").fillna(0)
    hourly["year"]          = pd.to_numeric(hourly["year"], errors="coerce")
    hourly["month"]         = pd.to_numeric(hourly["month"], errors="coerce")
    hourly["day"]           = pd.to_numeric(hourly["day"], errors="coerce")
    hourly = hourly[
        hourly["state"].isin(FOCUS_STATES) &
        hourly["offense_type"].isin(FOCUS_CRIMES) &
        hourly["hour"].notna() &
        (hourly["hour"] != 0)            # drop NIBRS "time unknown" placeholder
    ].copy()

    hourly["incident_date"] = pd.to_datetime(
        dict(year=hourly["year"], month=hourly["month"], day=hourly["day"]), errors="coerce"
    )
    hourly["log_count"] = np.log1p(hourly["crime_count"])
    hourly["dow"] = hourly["incident_date"].dt.dayofweek.astype(str)
    hourly["yr"]  = hourly["year"].astype(int).astype(str)
    hourly["mon"] = hourly["month"].astype(int).astype(str)

    # Attach DST indicator and weather from daily panel
    daily = pd.read_csv(PANEL_FILE, dtype=str, low_memory=False)
    daily["incident_date"] = pd.to_datetime(daily["incident_date"], errors="coerce")
    daily["in_dst_window"] = pd.to_numeric(daily["in_dst_window"], errors="coerce").fillna(0)
    daily["temperature"]   = pd.to_numeric(daily["temperature"],   errors="coerce")
    daily_key = (
        daily[["state", "county_fips", "incident_date", "crime_type", "in_dst_window", "temperature", "is_holiday"]]
        .rename(columns={"crime_type": "offense_type"})
        .drop_duplicates(subset=["state", "county_fips", "incident_date", "offense_type"])
    )
    daily_key["is_holiday"] = pd.to_numeric(daily_key["is_holiday"], errors="coerce").fillna(0)

    hourly = hourly.merge(daily_key, on=["state", "county_fips", "incident_date", "offense_type"], how="left")

    # Fill any still-missing temperature from state-level ERA5
    wx = load_state_weather()
    hourly = hourly.merge(wx, left_on=["state", "incident_date"], right_on=["state", "date"], how="left", suffixes=("", "_state"))
    hourly["temperature"] = hourly["temperature"].fillna(hourly["temperature_state"])
    hourly = hourly.dropna(subset=["temperature", "in_dst_window"])

    all_rows = []

    for state in FOCUS_STATES:
        for crime in FOCUS_CRIMES:
            print(f"\n{state} | {crime}")
            sub = hourly[(hourly["state"] == state) & (hourly["offense_type"] == crime)].copy()

            # Create DST × hour interaction dummies (hours 1–23; hour 0 dropped)
            hour_vals = sorted(sub["hour"].dropna().unique().astype(int).tolist())
            for h in hour_vals:
                sub[f"dst_h{h}"] = (sub["in_dst_window"] * (sub["hour"] == h)).astype(float)

            dst_cols = [f"dst_h{h}" for h in hour_vals]
            exog_cols = dst_cols + ["temperature"]

            absorb_cols = ["county_fips", "dow", "yr", "mon"]
            reg_df = sub[exog_cols + absorb_cols + ["log_count", "is_holiday"]].dropna().copy()
            absorb = reg_df[absorb_cols].astype("category")
            exog   = reg_df[exog_cols + ["is_holiday"]].copy()
            exog.insert(0, "const", 1.0)
            dep    = reg_df["log_count"]

            try:
                mod = AbsorbingLS(dep, exog, absorb=absorb)
                res = mod.fit(cov_type="clustered", clusters=sub.loc[reg_df.index, "county_fips"])
                print(f"  n={int(res.nobs):,}  R²={res.rsquared:.3f}")
                for h in hour_vals:
                    col = f"dst_h{h}"
                    all_rows.append({
                        "state":    state,
                        "crime":    crime,
                        "hour":     h,
                        "coef":     res.params[col],
                        "se":       res.std_errors[col],
                        "t_stat":   res.tstats[col],
                        "p_value":  res.pvalues[col],
                        "ci_low":   res.conf_int().loc[col, "lower"],
                        "ci_high":  res.conf_int().loc[col, "upper"],
                        "n_obs":    int(res.nobs),
                    })
            except Exception as exc:
                print(f"  ERROR: {exc}")

    out = pd.DataFrame(all_rows).round(6)
    out.to_csv(OUT_FILE, index=False)
    print(f"\nSaved {len(out)} rows -> {OUT_FILE}")
    print(out[out["p_value"] < 0.1][["state","crime","hour","coef","se","p_value"]].to_string(index=False))


if __name__ == "__main__":
    main()
