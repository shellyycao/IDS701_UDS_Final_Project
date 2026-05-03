# Memo: Does Daylight Saving Time Reduce Property Crime?

**To:** Director of Research, State Office of Justice Programs  
**From:** Criminal justice data analysis team  
**Re:** DST and property crime — CA (treated) vs AZ (control), 2022–2024  
**Date:** May 3, 2026  

**Stakeholder:** The target reader is a Director of Research at a state Office of Justice Programs — a senior policy analyst with graduate-level training in social science research methods. They are comfortable reading coefficient plots / regression tables and the idea of “controlling for” stable differences across counties and seasonality, but they are not expected to debug econometric edge-cases. They advise legislators on public safety proposals and need results framed as actionable guidance.

---

## Executive Summary

Your office may be asked whether DST should be defended (or opposed) on public-safety grounds. The decision-relevant question is whether shifting one hour of daylight from morning to evening measurably changes property crime. The core empirical challenge is that **DST months are also “summer months”**, when crime changes for many reasons unrelated to clocks (weather, school schedules, travel), so simple seasonal comparisons can be misleading.

We evaluate the question using a natural experiment: **California (CA)** observes DST while **Arizona (AZ)** does not change clocks. Using **NIBRS county-by-day data (2022–2024)** for **burglary** and **motor vehicle theft**, we compare how crime changes in CA versus AZ during the DST window while controlling for stable county differences and month-to-month seasonality. We also do a short-run “mechanism check” around the **2024 spring-forward** using hourly counts to see whether crime shifts from evening to morning when ambient light shifts. **Across both analyses, we find no statistically credible evidence that DST meaningfully reduces property crime** in this setting; estimates are small, uncertain, and robust to alternative reasonable choices.

**Causal question:** Does observing DST (CA) versus not observing DST (AZ) change burglary and motor vehicle theft rates?

## Decisions Requested

1. **Policy messaging:** Decide whether to treat “DST reduces property crime” as unsupported for legislative / stakeholder communication in this setting.
2. **Research scope:** Decide whether to invest in a follow-up study focused on (a) more offense types, and/or (b) a longer panel beyond 2022–2024, to detect smaller effects.
3. **Mechanism vs levels:** Decide whether your stakeholder cares more about (a) a short-run transition effect (spring-forward week) or (b) sustained DST-window effects (Mar–Nov). This memo focuses primarily on (b) and uses (a) as a mechanism diagnostic.

---

## Why Arizona is the Control and How We Handle Seasonality

A naive comparison of “DST months vs non-DST months” in California would confound clocks with season. Arizona provides a rare U.S. benchmark: AZ experiences the same seasonal cycle but **does not change clocks**. In addition, we adjust for:

- **Stable county differences:** time-invariant differences in baseline crime levels and reporting.
- **Month-by-month patterns:** shared seasonal patterns and common shocks within the same calendar month.

This isolates whether CA’s daily crime rates shift *differentially* during the DST window relative to AZ.

**Figure 1 — Seasonality and spring-forward window (CA vs AZ)**
*Top row shows seasonal patterns (non-DST months vs DST months). Bottom row shows a ±15-day window around spring-forward (day 0). There is no visible discontinuity at spring-forward in either outcome.*

<img src="../figures/memo_refined/01_section_2_eda_descriptive_trends.png" alt="Figure 1: EDA seasonality and ±15-day window" width="900" />

---

## Stage 1 — Mechanism Check: Time-of-Day Displacement

**Question:** If DST matters through ambient light, does crime shift **away from the newly-lighter evening** and **toward the newly-darker morning**?

**Data:** Hourly crime counts for CA / AZ (and a robustness treated group CA+UT) around the **2024 spring-forward**, within a ±28-day window.

**Design (plain language):** We compare before vs after spring-forward in CA versus AZ, separately for (a) morning hours that become darker after the shift and (b) evening hours that become lighter. This tests whether DST changes the *timing* of property crime within the day.

**Key result:** The identified estimates are small and not statistically significant (p-values > 0.37). Notably, the morning estimate is negative (opposite the displacement hypothesis).

| Model | Time-of-day window | Coef | SE | p-value |
|---|---|---:|---:|---:|
| CA vs AZ (main) | Morning (newly darker) | -0.0443 | 0.0638 | 0.4876 |
| CA+UT vs AZ (robustness) | Morning (newly darker) | -0.0440 | 0.0637 | 0.4895 |
| CA vs AZ (main) | Evening (newly lighter) | -0.0600 | 0.0674 | 0.3729 |
| CA+UT vs AZ (robustness) | Evening (newly lighter) | -0.0554 | 0.0674 | 0.4110 |

**Figure 2 — Stage 1 displacement regression coefficients (identified panel)**
*The identified panel (right) shows no statistically clear shift in morning/evening windows relative to the late-night reference.*

<img src="../figures/memo_refined/06_section_3_stage_1_mechanism_time_of_day_displaceme.png" alt="Figure 2: Stage 1 displacement regression coefficients" width="900" />

---

## Stage 2 — Main Result: Does DST Change Total Daily Crime?

**Question:** Does being in the DST window (Mar–Nov in CA, never in AZ) change the **level** of daily property crime?

**Approach:** We estimate the average difference in daily property crime rates in CA during the DST window (Mar–Nov) compared to the same months in AZ, while accounting for stable county differences and month-to-month seasonality. We report results both in levels (rate per 100k) and in a log-transformed outcome as a robustness check.

**Main estimates (average DST-window effect in CA relative to AZ):**

| Offense | Model | Coef | SE | p-value | 95% CI | N |
|---|---|---:|---:|---:|---|---:|
| Burglary | M1 Baseline (rate per 100k) | 0.01665 | 0.01351 | 0.2178 | [-0.0098, 0.0431] | 76720 |
| Burglary | M2 Log rate (log(1 + rate)) | 0.00439 | 0.00544 | 0.4191 | [-0.0063, 0.0151] | 76720 |
| Motor Vehicle Theft | M1 Baseline (rate per 100k) | -0.00845 | 0.01956 | 0.6659 | [-0.0468, 0.0299] | 76720 |
| Motor Vehicle Theft | M2 Log rate (log(1 + rate)) | 0.00372 | 0.00524 | 0.4777 | [-0.0066, 0.0140] | 76720 |

Interpretation: confidence intervals cross zero for all outcomes/specs; there is no evidence of a meaningful average DST-window effect on daily burglary or motor vehicle theft in CA relative to AZ.

**Figure 3 — Main estimated effects (dot + 95% CI)**
*The main estimates are close to zero and imprecise enough that both small increases and small decreases remain plausible.*

<img src="../figures/memo_refined/09_section_4_stage_2_main_did_results_primary_finding.png" alt="Figure 3: Main estimated effects" width="900" />

**Figure 4 — Event study around spring-forward (parallel-trends diagnostic)**
*Pre-period coefficients are not systematically far from zero, providing partial visual support for parallel trends; post-period shows no consistent shift.*

<img src="../figures/memo_refined/10_section_4_stage_2_main_did_results_primary_finding.png" alt="Figure 4: Spring-forward event study" width="900" />

---

## Robustness Checks

We test whether the null main result is sensitive to alternative samples/specifications (e.g., weekdays only, excluding holidays, excluding ±7 days around transitions, placebo windows, alternative treated definition).

**Figure 5 — Robustness forest plot**
*Across robustness specifications, point estimates remain close to zero and confidence intervals include zero. The CA+UT treated check (green) does not change conclusions.*

<img src="../figures/memo_refined/13_section_5_robustness_checks.png" alt="Figure 5: Robustness forest plot" width="900" />

---

## Limitations

- **Outcomes:** The refined memo focuses on two property-crime types (burglary and motor vehicle theft). DST effects could differ for other offense categories.
- **Time span:** The panel covers 2022–2024; smaller effects may require a longer series to detect.
- **NIBRS coverage:** NIBRS is not a full census of all jurisdictions; reporting coverage changes can affect precision.
- **Assumptions:** Parallel trends cannot be proven; event-study visuals provide partial support but are not definitive.
- **Mechanism sample:** The Stage 1 mechanism test focuses on a single spring-forward (2024) and may miss longer-run adaptation.

## Conclusion

Using Arizona as a no-clock-change control and a CA-versus-AZ comparison that adjusts for stable county differences and seasonality, we find **no reliable evidence that DST reduces daily burglary or motor vehicle theft** in California relative to Arizona. A targeted mechanism test based on hourly data similarly fails to find a statistically credible time-of-day displacement consistent with the “lighter evenings reduce crime” hypothesis.

**Bottom line for stakeholders:** In this setting and time period, DST does not appear to be a meaningful property-crime prevention tool. The best next step, if a decision requires stronger evidence, is to expand scope (more years and/or more offenses) rather than to rely on seasonal comparisons.
