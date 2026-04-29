"""
Patch the dst_crime_analysis notebook with all professor-requested changes.
Run from the project root: python scripts/patch_notebook.py
"""
import json
from pathlib import Path

NB_PATH = Path("notebooks/dst_crime_analysis.ipynb")
nb = json.load(open(NB_PATH, encoding="utf-8"))
cells = nb["cells"]
id_to_idx = {c["id"]: i for i, c in enumerate(cells)}


def set_cell(cell_id, new_source):
    idx = id_to_idx[cell_id]
    cells[idx]["source"] = [new_source]
    cells[idx]["outputs"] = []
    cells[idx]["execution_count"] = None


def insert_after(after_id, new_id, cell_type, new_source):
    idx = id_to_idx[after_id]
    new_cell = {
        "cell_type": cell_type,
        "id": new_id,
        "metadata": {},
        "source": [new_source],
    }
    if cell_type == "code":
        new_cell["outputs"] = []
        new_cell["execution_count"] = None
    cells.insert(idx + 1, new_cell)
    for i, c in enumerate(cells):
        id_to_idx[c["id"]] = i


# ============================================================
# CELL 27 (3ca21024): TWFE dot plot — baseline only, no bars
# ============================================================
set_cell("3ca21024", """\
# Coefficient plot: baseline rate only — point estimate + 95% CI (dot plot)
colors_cycle = ['#0077BB', '#EE7733', '#009988', '#CC3311', '#33BBEE', '#EE3377']

coefs, ses, labels, pt_colors = [], [], [], []
for idx, ct in enumerate(crime_types):
    key = f'{ct} | rate | baseline'
    if key not in results:
        continue
    r = results[key]
    coefs.append(r.params['in_dst_window'])
    ses.append(r.bse['in_dst_window'])
    labels.append(titles.get(ct, ct.replace('_', ' ').title()))
    pt_colors.append(colors_cycle[idx % len(colors_cycle)])

coefs  = np.array(coefs)
ses    = np.array(ses)
ci95   = 1.96 * ses
y_pos  = np.arange(len(labels))

fig, ax = plt.subplots(figsize=(8, max(3, 0.65 * len(labels))))
ax.scatter(coefs, y_pos, color=pt_colors, s=90, zorder=3)
ax.errorbar(coefs, y_pos, xerr=ci95, fmt='none',
            color='black', elinewidth=1.4, capsize=5)
ax.axvline(0, color='black', lw=0.9, ls='--')
ax.set_yticks(y_pos)
ax.set_yticklabels(labels, fontsize=10)
ax.set_xlabel('Estimated DST-window effect on daily crime rate per 100k (95% CI)', fontsize=9)
ax.set_title(
    'Baseline TWFE: DST-window effect on daily crime rates\\n'
    '(CA, FL, UT vs. AZ  |  county + year-month FE  |  county-clustered SE)',
    fontsize=10
)
ax.grid(axis='x', alpha=0.3)
plt.tight_layout()
plt.show()
""")

# ============================================================
# CELL 30 (d95531a5): Event study function — 2-week bins
# ============================================================
set_cell("d95531a5", """\
def run_event_study(df, outcome, entity='county_fips', time='data_year',
                    cluster='county_fips', clip=(-4, 4), ref_bin=-1):
    \"\"\"
    Dynamic DiD event study around DST spring-forward.
    Bins observations into 2-week periods: bin = floor(days / 14).
    clip=(-4, 4) covers +/-8 weeks (4 two-week bins each side).
    ref_bin=-1 = the 2-week period immediately before spring-forward.
    \"\"\"
    d = df.copy()
    d['week_rel'] = (d['days_from_dst_start'] // 14).clip(*clip)
    bins = [b for b in sorted(d['week_rel'].unique()) if b != ref_bin]

    dum_cols = []
    for b in bins:
        col = f'tw_{b:+d}'
        d[col] = d['treated_state'].astype(float) * (d['week_rel'] == b).astype(float)
        dum_cols.append(col)

    regressors = dum_cols + ['is_weekend', 'is_holiday']
    cols = list(dict.fromkeys([outcome] + regressors + [entity, time, cluster]))
    d2 = d[cols].dropna(subset=[outcome]).copy()

    for c in [outcome] + regressors:
        d2[c] = d2[c].astype(float)

    em = d2.groupby(entity)[[outcome] + regressors].transform('mean')
    d2[[outcome] + regressors] = d2[[outcome] + regressors] - em
    tm = d2.groupby(time)[[outcome] + regressors].transform('mean')
    d2[[outcome] + regressors] = d2[[outcome] + regressors] - tm

    X = sm.add_constant(d2[regressors])
    groups = d.loc[d2.index, cluster].values
    res = sm.OLS(d2[outcome], X).fit(
        cov_type='cluster', cov_kwds={'groups': groups}
    )

    rows = []
    for b, col in zip(bins, dum_cols):
        if col in res.params.index:
            ci = res.conf_int().loc[col]
            rows.append({'week': b, 'coef': res.params[col],
                         'se': res.bse[col], 'pval': res.pvalues[col],
                         'ci_lo': ci[0], 'ci_hi': ci[1]})
    rows.append({'week': ref_bin, 'coef': 0, 'se': 0, 'pval': 1, 'ci_lo': 0, 'ci_hi': 0})
    return pd.DataFrame(rows).sort_values('week').reset_index(drop=True)


def plot_event_study(es_df, title, ax=None):
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 5))
    ax.fill_between(es_df['week'], es_df['ci_lo'], es_df['ci_hi'],
                    alpha=0.18, color='steelblue')
    ax.plot(es_df['week'], es_df['coef'], 'o-', color='steelblue', ms=5, lw=1.8)
    ax.axhline(0, color='black', lw=0.8)
    ax.axvline(-0.5, color='crimson', ls='--', lw=1.2, label='DST spring-forward')
    ax.axvspan(-4, -0.5, alpha=0.04, color='green', label='Pre-period')
    ax.axvspan(-0.5, 4, alpha=0.04, color='gold', label='Post (DST active)')
    ax.set_xlabel('2-week bins relative to DST spring-forward (bin -1 = 2 weeks before; bin 0 = weeks 1-2 after)')
    ax.set_ylabel('Coef relative to 2-week period before spring-forward')
    ax.set_title(title, fontweight='bold')
    ax.legend(fontsize=8)
    ax.xaxis.set_major_locator(mticker.MultipleLocator(1))
    return ax

print('Event study functions defined (2-week bins).')
""")

# ============================================================
# CELL 32 (8db8dfa4): Fall-back event study — 2-week bins
# ============================================================
set_cell("8db8dfa4", """\
# Event study: fall-back (around DST end) — 2-week bins
def run_event_study_end(df, outcome, entity='county_fips', time='data_year',
                        cluster='county_fips', clip=(-4, 4), ref_bin=-1):
    d = df.copy()
    d['week_rel'] = (d['days_from_dst_end'] // 14).clip(*clip)
    bins = [b for b in sorted(d['week_rel'].unique()) if b != ref_bin]

    dum_cols = []
    for b in bins:
        col = f'twe_{b:+d}'
        d[col] = d['treated_state'].astype(float) * (d['week_rel'] == b).astype(float)
        dum_cols.append(col)

    regressors = dum_cols + ['is_weekend', 'is_holiday']
    cols = list(dict.fromkeys([outcome] + regressors + [entity, time, cluster]))
    d2 = d[cols].dropna(subset=[outcome]).copy()
    for c in [outcome] + regressors:
        d2[c] = d2[c].astype(float)

    em = d2.groupby(entity)[[outcome] + regressors].transform('mean')
    d2[[outcome] + regressors] = d2[[outcome] + regressors] - em
    tm = d2.groupby(time)[[outcome] + regressors].transform('mean')
    d2[[outcome] + regressors] = d2[[outcome] + regressors] - tm

    X = sm.add_constant(d2[regressors])
    groups = d.loc[d2.index, cluster].values
    res = sm.OLS(d2[outcome], X).fit(
        cov_type='cluster', cov_kwds={'groups': groups}
    )

    rows = []
    for b, col in zip(bins, dum_cols):
        if col in res.params.index:
            ci = res.conf_int().loc[col]
            rows.append({'week': b, 'coef': res.params[col],
                         'se': res.bse[col], 'pval': res.pvalues[col],
                         'ci_lo': ci[0], 'ci_hi': ci[1]})
    rows.append({'week': ref_bin, 'coef': 0, 'se': 0, 'pval': 1, 'ci_lo': 0, 'ci_hi': 0})
    return pd.DataFrame(rows).sort_values('week').reset_index(drop=True)


es_end_results = {}
for ct in crime_types:
    es_end_results[ct] = run_event_study_end(
        sample[sample['crime_type'] == ct], 'crime_rate_per_100k'
    )

n = len(crime_types)
ncols = 2
nrows = int(np.ceil(n / ncols))
fig, axes = plt.subplots(nrows, ncols, figsize=(15, 4.8 * nrows))
axes = np.atleast_1d(axes).ravel()

for i, ct in enumerate(crime_types):
    ax = axes[i]
    es_df = es_end_results[ct]
    ax.fill_between(es_df['week'], es_df['ci_lo'], es_df['ci_hi'], alpha=0.18, color='darkorange')
    ax.plot(es_df['week'], es_df['coef'], 'o-', color='darkorange', ms=5, lw=1.8)
    ax.axhline(0, color='black', lw=0.8)
    ax.axvline(-0.5, color='crimson', ls='--', lw=1.2, label='DST fall-back')
    ax.set_xlabel('2-week bins relative to DST fall-back')
    ax.set_ylabel('Coef (treated vs AZ, relative to bin -1)')
    ax.set_title(
        f"{titles.get(ct, ct.replace('_',' ').title())}: Event Study around DST Fall-Back",
        fontweight='bold'
    )
    ax.legend(fontsize=8)
    ax.xaxis.set_major_locator(mticker.MultipleLocator(1))

for j in range(i + 1, len(axes)):
    axes[j].axis('off')

plt.tight_layout()
plt.show()
""")

# ============================================================
# CELL 47 (8fdcbf2c): FWER (Holm-Bonferroni) correction
# ============================================================
set_cell("8fdcbf2c", """\
from statsmodels.stats.multitest import multipletests

# Baseline table ranked by p-value
baseline_rows = []
for ct in crime_types:
    key = f'{ct} | rate | baseline'
    if key not in results:
        continue
    r = results[key]
    p = float(r.pvalues.get('in_dst_window', np.nan))
    baseline_rows.append({
        'crime_type': ct,
        'label': titles.get(ct, ct.replace('_', ' ').title()),
        'beta': float(r.params.get('in_dst_window', np.nan)),
        'se': float(r.bse.get('in_dst_window', np.nan)),
        'p_value': p,
    })

baseline_df = pd.DataFrame(baseline_rows).sort_values('p_value').reset_index(drop=True)

# Holm-Bonferroni FWER correction (controls family-wise error rate across m=6 tests)
pvals = baseline_df['p_value'].values
_, pvals_holm, _, _ = multipletests(pvals, method='holm')
baseline_df['p_holm'] = pvals_holm

def stars(p):
    return '***' if p < 0.01 else '**' if p < 0.05 else '*' if p < 0.10 else ''

baseline_df['sig_raw']  = baseline_df['p_value'].apply(stars)
baseline_df['sig_holm'] = baseline_df['p_holm'].apply(stars)

print('Baseline TWFE: unadjusted vs. Holm-Bonferroni FWER-adjusted p-values (m=6 tests):')
print(baseline_df[['label','beta','se','p_value','sig_raw','p_holm','sig_holm']].to_string(index=False))
print()
print('Significance legend: *** p<0.01  ** p<0.05  * p<0.10')
print()
print('After Holm correction: no offense reaches significance at alpha=0.10.')
print('Unadjusted p-values for robbery (~0.053) and theft-from-MV (~0.064) were')
print('suggestive; the corrected p-values (~0.32 each) reflect the Jelly Bean problem')
print('inherent in testing 6 outcomes simultaneously.')
""")

# ============================================================
# NEW CELLS after Cell 49 (5fee3773): All-crimes aggregate
# ============================================================
insert_after("5fee3773", "allcrime_md", "markdown", """\
## 2.12 All-Crime Aggregate

The memo references outcomes "across all studied crimes." Here we aggregate all six offense types to a county-day total rate and run the same baseline TWFE, providing the "all-crime" reference the memo implies.
""")

insert_after("allcrime_md", "allcrime_code", "code", """\
# Aggregate all crime types to county-day total rate
all_crime_daily = (
    sample
    .groupby(
        ['county_fips', 'incident_date', 'state', 'data_year', 'year_month',
         'in_dst_window', 'is_weekend', 'is_holiday', 'treated_state', 'group'],
        as_index=False
    )
    .agg(total_rate=('crime_rate_per_100k', 'sum'))
)

print(f'All-crime aggregate rows: {len(all_crime_daily):,}')
print(f'Mean total rate — treated: {all_crime_daily[all_crime_daily["treated_state"]==1]["total_rate"].mean():.3f}')
print(f'Mean total rate — control: {all_crime_daily[all_crime_daily["treated_state"]==0]["total_rate"].mean():.3f}')

# TWFE on total rate
r_all  = run_twfe(all_crime_daily, 'total_rate', ['in_dst_window', 'is_weekend', 'is_holiday'])
b_all  = r_all.params['in_dst_window']
se_all = r_all.bse['in_dst_window']
p_all  = r_all.pvalues['in_dst_window']
ci_lo  = b_all - 1.96 * se_all
ci_hi  = b_all + 1.96 * se_all

print(f'\\nAll-crime aggregate TWFE:')
print(f'  beta = {b_all:.4f}  SE = {se_all:.4f}  p = {p_all:.4f}')
print(f'  95% CI: [{ci_lo:.4f}, {ci_hi:.4f}]')

# ---- Monthly trend + point-estimate panel ----
monthly_all = (
    all_crime_daily
    .groupby(['group', 'year_month'], as_index=False)
    .agg(mean_total=('total_rate', 'mean'))
)
monthly_all['date'] = pd.to_datetime(monthly_all['year_month'])

colors_g = {
    'California (treated)': '#0077BB',
    'Florida (treated)':    '#EE7733',
    'Utah (treated)':       '#CC3311',
    'Arizona (control)':    '#009988',
}

fig, axes = plt.subplots(1, 2, figsize=(14, 4.5))

# Left: monthly trend
ax = axes[0]
for grp, gdf in monthly_all.groupby('group'):
    ax.plot(gdf['date'], gdf['mean_total'], label=grp,
            color=colors_g.get(grp, 'gray'), lw=1.8, alpha=0.85)
for yr in [2022, 2023, 2024]:
    ax.axvspan(pd.Timestamp(f'{yr}-03-01'), pd.Timestamp(f'{yr}-11-01'),
               alpha=0.06, color='gold', zorder=0)
ax.set_title('Total crime rate (all 6 offenses) — monthly trends\\n(gold shading = DST window)', fontweight='bold')
ax.set_ylabel('Mean daily total rate per 100k')
ax.legend(fontsize=8)
ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%Y-%m'))
plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha='right')

# Right: TWFE point estimate
ax2 = axes[1]
ax2.scatter([b_all], [0], color='#0077BB', s=100, zorder=3)
ax2.errorbar([b_all], [0],
             xerr=[[b_all - ci_lo], [ci_hi - b_all]],
             fmt='none', color='black', elinewidth=1.6, capsize=6)
ax2.axvline(0, color='black', lw=0.9, ls='--')
sig_txt = f'p = {p_all:.3f}' + (' *' if p_all < 0.10 else ' (n.s.)')
ax2.set_yticks([0])
ax2.set_yticklabels(['All 6 offenses\\ncombined'], fontsize=10)
ax2.set_xlabel('DST-window effect on total daily crime rate per 100k (95% CI)', fontsize=9)
ax2.set_title(f'All-crime aggregate TWFE ({sig_txt})', fontweight='bold')
ax2.grid(axis='x', alpha=0.3)

plt.suptitle('All-Crime Aggregate: DST-window analysis (CA, FL, UT vs. AZ)', fontsize=11, y=1.02)
plt.tight_layout()
plt.show()
""")

# ============================================================
# CELL 2 (4d5a6577): Fix Stage 1A — clearer axes, better seasonality
# ============================================================
set_cell("4d5a6577", """\
from pathlib import Path
from datetime import date, timedelta

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker

ROOT = Path("..").resolve()
DAILY_PATH = ROOT / "data/processed/crime/focus_states_daily_county_counts.csv"
POP_PATH = ROOT / "data/processed/population/focus_states_county_population_2020_2024_long.csv"

CRIMES_1A = ["burglary", "motor_vehicle_theft"]
CRIME_TITLES = {"burglary": "Burglary", "motor_vehicle_theft": "Motor vehicle theft"}
MONTH_LABELS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

def spring_forward_sunday(y: int) -> date:
    d0 = date(y, 3, 1)
    first_sun = d0 + timedelta(days=(6 - d0.weekday()) % 7)
    return first_sun + timedelta(days=7)   # second Sunday in March


if not DAILY_PATH.exists() or not POP_PATH.exists():
    print("Skip 1A: missing data file")
else:
    daily = pd.read_csv(DAILY_PATH, parse_dates=["incident_date"])
    pop   = pd.read_csv(POP_PATH)
    pop["data_year"] = pop["data_year"].astype(int)
    excl   = pop["proposal_excluded_az_county"].fillna(False)
    pop_az = pop[(pop["state"] == "AZ") & (~excl)]
    pop_use = pd.concat([pop[pop["state"] != "AZ"], pop_az], ignore_index=True)
    st_pop  = pop_use.groupby(["state", "data_year"], as_index=False)["population"].sum()

    d = daily[daily["crime_type"].isin(CRIMES_1A)].copy()
    d["year"] = d["year"].astype(int)
    st_day = (
        d.groupby(["state", "year", "incident_date", "crime_type"], as_index=False)["incident_count"].sum()
         .merge(st_pop.rename(columns={"data_year": "year"}), on=["state", "year"], how="left")
    )
    st_day["rate_per_100k"] = st_day["incident_count"] / st_day["population"] * 100_000.0

    years = sorted(st_day["year"].unique())
    sf_dates = {y: pd.Timestamp(spring_forward_sunday(y)) for y in years}
    print(f"Stage 1A daily: years = {years}")
    print(f"Spring-forward dates: {sf_dates}")

    fig, axes = plt.subplots(2, len(CRIMES_1A), figsize=(12, 7), sharex="col")
    fig.suptitle(
        "Stage 1A: Monthly seasonality (CA vs AZ) and \\u00b115-day window around spring-forward",
        fontsize=11, y=1.02,
    )

    for j, ct in enumerate(CRIMES_1A):
        sub = st_day[st_day["crime_type"] == ct].copy()
        sub["month"] = sub["incident_date"].dt.month

        # --- TOP ROW: avg daily rate by calendar month ---
        mo = (
            sub[sub["state"].isin(["CA", "AZ"])]
            .groupby(["state", "month"], as_index=False)["rate_per_100k"].mean()
        )
        ax_m = axes[0, j]
        for st_code, c, lbl in [
            ("CA", "#1f77b4", "California (observes DST)"),
            ("AZ", "#d62728", "Arizona (no DST)"),
        ]:
            m = mo[mo["state"] == st_code].sort_values("month")
            ax_m.plot(m["month"], m["rate_per_100k"], marker="o", label=lbl, color=c, lw=2)
        ax_m.axvspan(3, 11, alpha=0.10, color="#ff7f0e", label="DST window (approx)")
        ax_m.set_xticks(range(1, 13))
        ax_m.set_xticklabels(MONTH_LABELS, fontsize=8)
        ax_m.set_ylabel("Avg daily rate per 100k")
        ax_m.set_title(f"{CRIME_TITLES[ct]}: average daily rate by month", fontsize=10)
        ax_m.legend(fontsize=8)

        # --- BOTTOM ROW: +-15 calendar days relative to spring-forward date ---
        WIN = 15
        rows = []
        for y in years:
            sf_ts = sf_dates[y]
            for st_code in ["CA", "AZ"]:
                tmp = sub[sub["state"] == st_code].copy()
                tmp["days_from_sf"] = (tmp["incident_date"] - sf_ts).dt.days
                win = tmp[tmp["days_from_sf"].between(-WIN, WIN)]
                for _, row in win.iterrows():
                    rows.append({"state": st_code, "days_from_sf": int(row["days_from_sf"]),
                                 "rate": row["rate_per_100k"]})

        if rows:
            wdf = pd.DataFrame(rows)
            wdf_avg = wdf.groupby(["state", "days_from_sf"], as_index=False)["rate"].mean()
            ax_w = axes[1, j]
            for st_code, c, lbl in [
                ("CA", "#1f77b4", "California (observes DST)"),
                ("AZ", "#d62728", "Arizona (no DST)"),
            ]:
                wd = wdf_avg[wdf_avg["state"] == st_code].sort_values("days_from_sf")
                ax_w.plot(wd["days_from_sf"], wd["rate"], marker=".", ms=4, lw=1.5,
                          label=lbl, color=c)
            ax_w.axvline(0, color="black", ls="--", lw=1.2, label="Day 0 = spring-forward")
            ax_w.set_xlabel("Calendar days relative to spring-forward date\\n"
                            "(negative = before clocks change; positive = after)")
            ax_w.set_ylabel("Avg daily rate per 100k")
            ax_w.set_title(f"{CRIME_TITLES[ct]}: \\u00b1{WIN} days around spring-forward date", fontsize=10)
            ax_w.legend(fontsize=8)
            ax_w.set_xlim(-WIN - 1, WIN + 1)

    plt.tight_layout()
    plt.show()

    print("\\nNote: the \\u00b115-day panel shows the AVERAGE daily rate across all years in the data,")
    print("centered on each year's spring-forward date (second Sunday in March).")
    print("A sharp jump at day 0 would suggest a clock-change shock; a smooth trend suggests season.")
""")

# ============================================================
# CELL 7 (fae68cac): Fix Stage 1B — exclude hour 0, improve labels
# ============================================================
set_cell("fae68cac", """\
# Stage 1B hourly profile — exclude hour 0 (midnight-imputed records)
#
# Many agencies assign crimes with unknown time-of-day to 00:00, creating an
# artificial spike at hour 0 that is not meaningful for the displacement analysis.
# Hour 0 is excluded from the plot.

EXCLUDE_HOURS = {0}
hours_plot = [h for h in range(1, 24)]

fig, axes = plt.subplots(1, 2, figsize=(14, 4.5), sharey=False)

for ax, (label, prof) in zip(axes,
        [('Treated: CA + FL  (103 counties)', prof_tr),
         ('Control: AZ  (no DST change)',      prof_az)]):
    sub_pre  = prof.loc[hours_plot, 'pre']
    sub_post = prof.loc[hours_plot, 'post']
    ax.plot(hours_plot, sub_pre.values,  color='steelblue', lw=2,
            marker='o', ms=4, label='Pre-DST  (days -28 to -1)')
    ax.plot(hours_plot, sub_post.values, color='tomato',    lw=2,
            marker='s', ms=4, label='Post-DST (days  0 to +28)')
    ax.axvspan(4.5,  8.5, alpha=0.12, color='navy', label='Morning dark (5-8h)')
    ax.axvspan(17.5, 21.5, alpha=0.12, color='gold', label='Evening light (18-21h)')
    ax.set_title(label, fontsize=11)
    ax.set_xlabel('Hour of day (local clock time; hour 0 excluded — midnight imputation artifact)')
    ax.set_ylabel('Avg crimes per county per day')
    ax.set_xticks(range(1, 24, 2))
    ax.legend(fontsize=8, ncol=2, loc='upper left')

fig.suptitle(
    'Stage 1B: Hourly Crime Profile — 28 days before vs. after spring-forward (March 2024)\\n'
    'Displacement hypothesis: CA+FL evening (18-21h) falls post-DST; AZ stays flat',
    fontsize=11, y=1.03
)
plt.tight_layout()
plt.show()

print('Key hourly findings (CA + FL, excluding hour 0):')
for h in [6, 7, 8, 18, 19, 20]:
    if h in prof_tr.index:
        r = prof_tr.loc[h]
        print(f'  Hour {h:02d}: {r.pct:+.1f}%')
""")

# ============================================================
# CELL 9 (1c59f6a0): Fix Stage 1C — add 95% CI error bars
# ============================================================
set_cell("1c59f6a0", """\
# Stage 1C: Bucket-level summary with 95% CI error bars (SEM across county-days)
BUCKET_ORDER  = ['morning_dark', 'daytime', 'evening_light', 'late_night']
BUCKET_LABELS = {
    'morning_dark':  'Morning\\n(5-8h)',
    'daytime':       'Daytime\\n(9-17h)',
    'evening_light': 'Evening\\n(18-21h)',
    'late_night':    'Late night\\n(22-4h)',
}

def bucket_stats(df, treated, post):
    \"\"\"Mean and SEM per bucket, averaged to county-day level first to avoid pseudo-replication.\"\"\"
    sub = df[(df['treated_state'] == treated) & (df['post_dst'] == post)].copy()
    # Collapse to county-date-bucket (averaging over offense types within bucket)
    cd = sub.groupby(['county_fips', 'date', 'time_bucket'])['crime_count'].mean().reset_index()
    grp = cd.groupby('time_bucket')['crime_count']
    return grp.mean(), grp.sem()

x, w = np.arange(len(BUCKET_ORDER)), 0.20
fig, ax = plt.subplots(figsize=(10, 4.5))
specs = [
    (-1.5*w, 1, 0, '#1f77b4', 'CA+FL  pre-DST'),
    (-0.5*w, 1, 1, '#aec7e8', 'CA+FL post-DST'),
    ( 0.5*w, 0, 0, '#d62728', 'AZ     pre-DST'),
    ( 1.5*w, 0, 1, '#f7a3a3', 'AZ    post-DST'),
]
for offset, trt, post, color, lbl in specs:
    means, sems = bucket_stats(win, trt, post)
    vals = means.reindex(BUCKET_ORDER, fill_value=0)
    errs = sems.reindex(BUCKET_ORDER, fill_value=0)
    ax.bar(x + offset, vals.values, w, label=lbl, color=color)
    ax.errorbar(x + offset, vals.values, yerr=1.96 * errs.values,
                fmt='none', color='black', elinewidth=1.0, capsize=3, zorder=5)

ax.set_xticks(x)
ax.set_xticklabels([BUCKET_LABELS[b] for b in BUCKET_ORDER])
ax.set_ylabel('Avg crimes per county-day  (bars = mean, whiskers = 95% CI)')
ax.set_title(
    'Stage 1C: Crime by time bucket — pre vs. post spring-forward (2024, 28-day window)\\n'
    'Displacement predicts CA+FL evening falls and morning stays flat; AZ should be unchanged',
    fontsize=10
)
ax.legend(fontsize=8, ncol=2)
plt.tight_layout()
plt.show()

# Print table
bucket_tbl = (
    win.groupby(['state', 'time_bucket', 'post_dst'])['crime_count']
    .sum().unstack(fill_value=0)
    .rename(columns={0: 'pre', 1: 'post'})
)
bucket_tbl['pct_change'] = (
    (bucket_tbl['post'] - bucket_tbl['pre'])
    / bucket_tbl['pre'].replace(0, np.nan) * 100
).round(1)
print('Crime counts by state / bucket (pre | post | % change):')
print(bucket_tbl.to_string())
""")

# ============================================================
# CELL 12 (cbfc29db): Improve Stage 1D — clearer triple-diff
# ============================================================
set_cell("cbfc29db", """\
# Stage 1D: Displacement regression — focus on the triple-difference result
#
# The three panels answer a hierarchy of questions:
#   Panel 1 (CA+FL): Did within-day crime shift in TREATED states after DST?
#   Panel 2 (AZ):    Did the same shift happen in the NO-DST control? (Should be flat)
#   Panel 3 (DiD):   Is the treated shift DIFFERENTIAL vs. AZ? This is the DST mechanism test.
#
# If DST causes a light-shift effect:
#   morning_dark should RISE in treated but not in AZ  ->  triple-diff > 0
#   evening_light should FALL in treated but not in AZ ->  triple-diff < 0
#
# All models include county, day-of-week, and offense-type fixed effects.
# Reference group: late_night bucket in pre-DST period.

BUCKET_XLABELS = ['Morning dark\\n(5-8h)', 'Evening light\\n(18-21h)']
BUCKET_KEYS    = ['morning_dark', 'evening_light']

def get_coef_ci(res, bucket_key):
    matches = [k for k in res.params.index if 'post_dst' in k and bucket_key in k]
    if not matches:
        return 0.0, 0.0
    t = matches[0]
    return res.params[t], 1.96 * res.bse[t]

def get_triple_ci(res, bucket_key):
    matches = [k for k in res.params.index
               if all(x in k for x in ['treated_state', 'post_dst', bucket_key])]
    if not matches:
        return 0.0, 0.0
    t = matches[0]
    return res.params[t], 1.96 * res.bse[t]


panel_specs = [
    ('CA + FL (treated)\\nWithin-state shift after DST',           res_tr, get_coef_ci,    'steelblue'),
    ('AZ (no clock change)\\nShould be flat — placebo check',      res_az, get_coef_ci,    '#d62728'),
    ('Triple-diff: treated − AZ\\nDirect DST mechanism test',      res3,   get_triple_ci,  'seagreen'),
]

fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), sharey=False)

for ax, (title, res, fn, color) in zip(axes, panel_specs):
    coefs_p, cis_p = [], []
    for bk in BUCKET_KEYS:
        c, ci = fn(res, bk)
        coefs_p.append(c); cis_p.append(ci)

    ax.scatter([0, 1], coefs_p, color=color, s=100, zorder=3)
    ax.errorbar([0, 1], coefs_p, yerr=cis_p, fmt='none',
                color='black', capsize=7, lw=1.5)
    ax.axhline(0, color='black', lw=0.8, ls='--')
    ax.set_xticks([0, 1])
    ax.set_xticklabels(BUCKET_XLABELS, fontsize=9)
    ax.set_title(title, fontsize=9, fontweight='bold')
    ax.set_ylabel('Coef vs. late-night / pre-DST (crime counts)')
    ax.grid(axis='y', alpha=0.3)

fig.suptitle(
    'Stage 1D: Displacement Regression Coefficients (HC3 SE, 95% CI)\\n'
    'Panel 3 (triple-diff) is the key DST mechanism test: positive morning + negative evening = light-shift effect',
    fontsize=10, y=1.04
)
plt.tight_layout()
plt.show()

print('Triple-diff key interactions (DST mechanism test):')
print('  Positive morning_dark + negative evening_light in treated vs. AZ = light-shift confirmed')
print()
for bk, lbl in zip(BUCKET_KEYS, ['Morning dark (5-8h)', 'Evening light (18-21h)']):
    c, ci = get_triple_ci(res3, bk)
    matches = [k for k in res3.params.index if all(x in k for x in ['treated_state','post_dst',bk])]
    p = res3.pvalues[matches[0]] if matches else float('nan')
    direction = '+' if c > 0 else '-'
    sig = '(sig)' if p < 0.10 else '(n.s.)'
    print(f'  {lbl:30s}: coef = {c:+.4f}  p = {p:.3f}  {sig}')
""")

# Save
json.dump(nb, open(NB_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("Notebook patched and saved successfully.")
print(f"Total cells now: {len(nb['cells'])}")
