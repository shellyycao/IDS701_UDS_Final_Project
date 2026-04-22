# Memo: Does Daylight Saving Time Drive Crime? Evidence from NIBRS County Panels

**To:** Director of Research, state Office of Justice Programs  
**From:** Criminal justice data analysis team  
**Re:** DST and crime — NIBRS county panel, CA/FL/UT vs. AZ  
**Date:** April 2026

---

**Stakeholder:** The target reader is a Director of Research at a state Office of Justice Programs — a senior policy analyst with graduate-level training in social science research methods, comfortable reading regression tables and understanding concepts like fixed effects and parallel trends, but not a specialist in econometrics. They advise legislators on public safety proposals and need results framed in terms of what action the evidence supports, not just what the model estimates.

---

## Executive Summary

Every spring, DST shifts clocks forward one hour, bringing more evening daylight but also compressing morning light. Policymakers and advocates routinely assert that this light shift either increases or decreases crime — but **nearly every seasonal comparison that supports such claims confounds the clock change with summer**, when crime rises for many reasons that have nothing to do with DST. The problem this memo addresses is: **can we distinguish the effect of DST on crime from the effect of summer, and if so, which crimes — if any — are affected?**

To answer this question, we analyze a **county-day panel** for California, Florida, and Utah (states that observe DST) versus Arizona (which does not), using **three years of NIBRS data (2022–2024)** and **two-way fixed effects** that absorb county-specific baselines and shared month-by-year seasonality. This design lets us ask: relative to Arizona's counties, how does crime in DST-observing counties shift during the DST calendar window — over and above what shared seasonality explains?

**The headline finding is that DST does not produce a broad, uniform crime wave.** Four of six offense types — burglary, motor vehicle theft, theft from building, and shoplifting — show no statistically distinguishable association with the DST window in the baseline model. Two offenses consistent with outdoor, opportunistic crime — **robbery** (+0.005 incidents/100k/day, p = 0.053) and **theft from motor vehicle** (+0.016 incidents/100k/day, p = 0.064) — show suggestive positive associations, supported by null results when we run the same test on a non-DST calendar cutoff (placebo). **Burglary** shows marginal significance in some specifications but fails diagnostic checks for pre-existing trends and should not be given causal weight here.

**Recommended action:** Brief legislative and public audiences with the finding that no general "DST crime effect" is supported; focus monitoring resources on robbery and vehicle-related theft; and commission multi-year hourly analysis before drawing any statutory conclusions.

---

## Decisions Requested

1. **What to say publicly.** The evidence supports leading with "no uniform crime spike" — not silence or hedging on all results. Robbery and theft from motor vehicle are the two outcomes where the association is positive and passes basic design checks; those warrant targeted attention, not a blanket DST-causes-crime narrative.

2. **How to frame the policy scope.** The primary model captures months-long DST exposure (mid-March through early November) relative to Arizona — not just the spring-forward weekend. Any legislative briefing should distinguish these two very different claims: "the clock-change weekend disrupts sleep and spikes crime briefly" versus "DST-season crime is structurally higher in states that observe DST."

3. **What additional evidence is needed before acting.** Robust causal claims — sufficient to support or oppose DST legislation — require multi-year hourly data to confirm the light-driven mechanism, count models suited to the sparsity in rural county data, and subsamples that exclude states or years with thin NIBRS coverage. This analysis supports scoping that follow-on work, not replacing it.

---

## Why Arizona Provides the Right Benchmark

The core challenge in estimating a DST effect is that **DST months are summer months**. Any comparison of "DST season vs. winter" in a single state conflates warmer weather, longer natural days, school schedules, and the clock change itself. Arizona provides a rare within-U.S. benchmark: most of its counties do not observe DST, yet they share regional characteristics — climate zones, border economies, demographic composition — with parts of California and Utah. By comparing crime trends in DST-observing counties against Arizona counties **within the same calendar month and year**, the fixed-effects design removes shared seasonal and macroeconomic shocks and isolates differential exposure to the clock change.

Three Arizona counties in the Navajo Nation territory do observe DST and are excluded from the control group, preserving the clean "no-DST" status of Arizona's contribution.

---

## What the Evidence Shows

### The main result: two offenses flag, four do not

The figure below shows the primary estimates — **coefficients on DST-window exposure** for each of six offense types, after absorbing county fixed effects and year-month fixed effects, with standard errors clustered at the county level.

**Figure 1 — Baseline TWFE: DST window effect on daily crime rates (CA, FL, UT vs. AZ)**
*Robbery and theft from motor vehicle are the only offenses where the DST-window coefficient is positive and marginally distinguishable from zero; the other four offenses are not statistically significant.*

<img src="./figures/memo/07_24_two_way_fixed_effects_did.png" alt="Figure 1: Baseline TWFE coefficients for six offense types" width="900" />

The two flagged offenses follow a coherent pattern. Robbery and theft from motor vehicle are inherently outdoor and time-of-day sensitive — a shift in when it is light versus dark plausibly changes the opportunity structure. The null results for burglary, motor vehicle theft, shoplifting, and theft from building are also coherent: those crimes depend heavily on factors (residential occupancy, commercial traffic, parking exposure) less directly tied to ambient light.

| Offense | DST-window effect | p-value | Design check |
|---|---|---|---|
| Robbery | +0.005 per 100k/day | 0.053 | Pre-trends pass; placebo null |
| Theft from motor vehicle | +0.016 per 100k/day | 0.064 | Pre-trends pass; placebo null |
| Motor vehicle theft | −0.016 per 100k/day | 0.161 | Not significant |
| Theft from building | −0.008 per 100k/day | 0.255 | Not significant |
| Burglary | +0.010 per 100k/day | 0.287 | Pre-trends **fail**; discard for causal use |
| Shoplifting | +0.006 per 100k/day | 0.607 | Not significant |

### The placebo test supports design validity

A key concern is that the DST window simply proxies for warmer months when crime is higher regardless of the clock. To test this, we run the same regression using a fictitious "treatment" cutoff in June — a date well within DST where no clock change occurs. **All six placebo estimates are null** (all p > 0.20), which means the signal for robbery and theft from motor vehicle is not just a generic summer pattern detectable at any calendar breakpoint.

### Burglary fails the parallel trends check

Before the DST window begins, treated states (CA, FL, UT) and Arizona should be trending similarly in crime rates — the "parallel trends" assumption that makes the design interpretable. For burglary, **5 of 7 pre-treatment weekly bins are individually significant at the 10% level**, and the joint pre-trend test p-value is 0.079. This indicates that treated and control counties were already diverging before DST, which means any DST-window estimate for burglary could reflect a pre-existing gap rather than an effect of the clock change.

### Event studies confirm the pattern

**Figure 2 — Event studies around spring-forward (left) and fall-back (right)**
*Flat pre-period coefficients for robbery and theft from motor vehicle support the parallel trends assumption; burglary pre-periods diverge, reinforcing our caution about that offense.*

<img src="./figures/memo/08_25_event_study.png" alt="Figure 2a: Event study around spring-forward" width="900" />

<img src="./figures/memo/09_25_event_study.png" alt="Figure 2b: Event study around fall-back" width="900" />

### A light-shift mechanism is plausible but not confirmed

As a mechanism diagnostic, we examined **hourly crime profiles in California and Florida versus Arizona** in the 28-day window around the 2024 spring-forward transition. The displacement hypothesis predicts that DST should rotate the hourly crime profile: more crime in early mornings (now dark) and less in evenings (now light). The data show a 10–14% decline in evening-light crime (hours 18–20) in treated states after spring-forward, consistent with the mechanism — but the within-state regression and triple-difference model do not reach statistical significance with one year of hourly data. These diagnostics motivate, rather than confirm, the light-shift story.

**Figure 3 — Seasonal patterns and the spring-forward window (California vs. Arizona)**
*Both states show a similar summer crime rise, demonstrating why raw seasonal comparisons overstate any DST effect; the narrow ±15-day window around spring-forward shows no sharp spike at day zero.*

<img src="./figures/memo/01_stage_1a_daily_data_seasonality_ca_vs_az_and_sprin.png" alt="Figure 3: Stage 1A daily CA vs AZ" width="900" />

---

## Limitations

Three limitations materially affect how much confidence to attach to these results:

- **Arizona contributes only 12 control counties** against 154 treated counties (58 CA, 67 FL, 29 UT). The control group is small, and while county-clustering adjusts standard errors accordingly, the asymmetry limits the precision of the design.
- **NIBRS coverage varies by state and year**, particularly for Florida in earlier years. Estimates that change materially when thin-coverage years are dropped would warrant additional scrutiny.
- **Six simultaneous tests** increase the probability of at least one false positive at conventional significance thresholds. The consistency of results — two positives that share a theoretical mechanism, four nulls — is more credible than any single p-value.

---

## Conclusion

The goal of this analysis was to determine whether DST drives crime — or whether what looks like a "DST effect" in seasonal comparisons is simply summer. Using Arizona as a non-DST benchmark with two-way fixed effects, we find **no basis for claiming DST produces across-the-board increases in the six studied offense types.** Four offenses show no association with the DST calendar window. Two offenses — robbery and theft from motor vehicle — show suggestive positive associations that survive placebo testing and parallel trends checks, consistent with the theoretical mechanism of shifting outdoor crime opportunity by changing the light environment.

These findings are sufficient to recommend **against broad DST-causes-crime framing** and in favor of **targeted monitoring** of robbery and vehicle-related theft during DST-transition periods. They are not sufficient to support statutory recommendations on DST policy. That step requires the follow-on hourly mechanism analysis, count models suited to sparse county data, and coverage-robust subsamples described above.

---

## Appendix: Additional Figures

*Regenerate all figures: `python scripts/export_notebook_figures.py` from the project root.*

### Descriptive statistics

<img src="./figures/memo/05_23_descriptive_statistics.png" alt="Descriptive statistics 1" width="900" />

<img src="./figures/memo/06_23_descriptive_statistics.png" alt="Descriptive statistics 2" width="900" />

### Hourly mechanism diagnostics (Stage 1B–1D)

<img src="./figures/memo/02_stage_1b_hourly_crime_profile_before_vs_after_spri.png" alt="Hourly crime profile before vs. after spring-forward" width="900" />

<img src="./figures/memo/03_stage_1c_bucket_level_summary.png" alt="Time bucket summary" width="900" />

<img src="./figures/memo/04_stage_1d_displacement_regression.png" alt="Displacement regression coefficients" width="900" />

### Heterogeneity by state

<img src="./figures/memo/10_27_heterogeneity.png" alt="DST effect heterogeneity across CA, FL, UT subgroups" width="900" />

### Robustness checks

<img src="./figures/memo/11_28_robustness.png" alt="Robustness: exclude holidays, weekdays only, placebo, year FE" width="900" />
