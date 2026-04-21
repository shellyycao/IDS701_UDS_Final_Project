"""
Stage 1 within-state regressions for CA and NV separately.

Runs 4 model specifications per (state × crime_type):
  M1  Baseline:   log_count ~ DST + temp + county_FE + dow_FE + year_FE
  M2  Extended:   M1 + temp² + month_FE + holiday
  M3  Window±30:  M2 on ±30-day transition window only
  M4  Robustness: M2 with log_rate as outcome

Standard errors clustered by county_fips.

Outputs:
  data/processed/model/within_state_results.csv   — full coefficient table
  data/processed/model/within_state_summary.csv   — DST coefficient only
"""
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

IN_FILE     = "data/processed/model/within_state_panel.csv"
OUT_RESULTS = "data/processed/model/within_state_results.csv"
OUT_SUMMARY = "data/processed/model/within_state_summary.csv"

STATES  = ["CA", "NV"]
CRIMES  = ["burglary", "motor_vehicle_theft"]


def fit_ols(df, formula, cluster_col="county_fips"):
    """Fit OLS with county-clustered SEs; return tidy params DataFrame."""
    mod = smf.ols(formula, data=df).fit(
        cov_type="cluster", cov_kwds={"groups": df[cluster_col]}
    )
    params = mod.params.reset_index()
    params.columns = ["variable", "coef"]
    params["se"]      = mod.bse.values
    params["t_stat"]  = mod.tvalues.values
    params["p_value"] = mod.pvalues.values
    ci = mod.conf_int()
    params["ci_low"]  = ci.iloc[:, 0].values
    params["ci_high"] = ci.iloc[:, 1].values
    params["n_obs"]   = int(mod.nobs)
    params["r2"]      = mod.rsquared
    params["r2_adj"]  = mod.rsquared_adj
    return params


def main():
    Path(OUT_RESULTS).parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(IN_FILE, low_memory=False)
    df["incident_date"]  = pd.to_datetime(df["incident_date"], errors="coerce")
    df["in_dst_window"]  = pd.to_numeric(df["in_dst_window"],  errors="coerce").fillna(0)
    df["is_holiday"]     = pd.to_numeric(df["is_holiday"],     errors="coerce").fillna(0)
    df["temperature"]    = pd.to_numeric(df["temperature"],    errors="coerce")
    df["temperature2"]   = pd.to_numeric(df["temperature2"],   errors="coerce")
    df["log_count"]      = pd.to_numeric(df["log_count"],      errors="coerce")
    df["log_rate"]       = pd.to_numeric(df["log_rate"],       errors="coerce")
    df["in_window_30"]   = pd.to_numeric(df["in_window_30"],   errors="coerce").fillna(0)

    # Treat FE columns as strings for C() syntax
    df["county_fips"] = df["county_fips"].astype(str)
    df["dow"]         = df["dow"].astype(str)
    df["year"]        = df["year"].astype(str)
    df["mon"]         = df["mon"].astype(str)

    all_results = []

    # Formulas
    FE_BASE = "C(county_fips) + C(dow) + C(year)"
    FE_EXT  = "C(county_fips) + C(dow) + C(year) + C(mon)"

    F1 = f"log_count ~ in_dst_window + temperature + {FE_BASE}"
    F2 = f"log_count ~ in_dst_window + temperature + temperature2 + is_holiday + {FE_EXT}"
    F3 = F2   # same formula, restricted sample
    F4 = f"log_rate  ~ in_dst_window + temperature + temperature2 + is_holiday + {FE_EXT}"

    SPECS = [
        ("M1_baseline", F1, "log_count", False),
        ("M2_extended", F2, "log_count", False),
        ("M3_window30", F3, "log_count", True),
        ("M4_lograte",  F4, "log_rate",  False),
    ]

    for state in STATES:
        for crime in CRIMES:
            print(f"\n{'='*50}\n  {state} | {crime}\n{'='*50}")
            base = df[(df["state"] == state) & (df["crime_type"] == crime)].copy()

            for model_name, formula, outcome, window_only in SPECS:
                sub = base[base["in_window_30"] == 1].copy() if window_only else base.copy()
                sub = sub.dropna(subset=["temperature", outcome])
                print(f"  {model_name}: n={len(sub):,}")
                try:
                    params = fit_ols(sub, formula)
                    params["state"]  = state
                    params["crime"]  = crime
                    params["model"]  = model_name
                    params["outcome"] = outcome
                    all_results.append(params)
                except Exception as exc:
                    print(f"    ERROR: {exc}")

    results = pd.concat(all_results, ignore_index=True)
    results = results[[
        "state", "crime", "model", "outcome", "variable",
        "coef", "se", "t_stat", "p_value", "ci_low", "ci_high",
        "n_obs", "r2", "r2_adj",
    ]].round(6)
    results.to_csv(OUT_RESULTS, index=False)
    print(f"\nFull results saved: {len(results)} rows -> {OUT_RESULTS}")

    # Summary: DST coefficient only
    summary = results[results["variable"] == "in_dst_window"].copy()
    summary["sig"] = summary["p_value"].apply(
        lambda p: "***" if p < 0.01 else ("**" if p < 0.05 else ("*" if p < 0.1 else ""))
    )
    print("\n── DST coefficient (in_dst_window) ──")
    print(summary[["state","crime","model","coef","se","p_value","sig","n_obs"]].to_string(index=False))
    summary.to_csv(OUT_SUMMARY, index=False)
    print(f"\nSummary saved -> {OUT_SUMMARY}")


if __name__ == "__main__":
    main()
