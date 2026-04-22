# Memo: Daylight Saving Time and Crime in NIBRS Data (California, Florida, Utah vs. Arizona)

**Layout:** Main memo is **text-only**; **figures** are in the **Appendix** below (for page limits). Preview this file so images resolve (`./` = this folder). Regenerate PNGs: `python scripts/export_notebook_figures.py` from the project root.

**To:** Director of Research, state Office of Justice Programs  
**From:** Criminal justice data analysis team  
**Re:** DST and crime — NIBRS county panel (CA, FL, UT vs. AZ)  
**Date:** April 2026

---

## Executive Summary

Policymakers often ask whether **Daylight Saving Time (DST)** increases crime—either by shifting crime across hours of day or by lining up “DST months” with **summer**, when crime rises for many reasons unrelated to the clock. Simple before–after or summer–winter comparisons **confound seasonality with DST**.

We analyze **NIBRS-based county–day panels** for **California, Florida, and Utah** (DST-observing) and **Arizona** (most counties do not observe DST; Navajo Nation counties that observe DST are excluded from the control group). We estimate **two-way fixed effects** models with **county** and **year–month** fixed effects. The estimand is the association of the **calendar DST window** (roughly March through early November) with daily crime **in treated states relative to Arizona**, controlling for county-specific levels and shared month-by-year shocks, for **six offense types**: burglary, motor vehicle theft, robbery, shoplifting, theft from building, and theft from motor vehicle. Supporting diagnostics contrast **daily** seasonal patterns and a **narrow window around spring-forward** with **hourly** profiles (DST states vs. Arizona). We also report **event studies**, **narrow-window** checks, **heterogeneity by state**, and **placebo** tests using a non-DST calendar cutoff.

**Main findings.** The results **do not** support a **universal DST “crime wave”** across all six offenses. Several outcomes are **not** statistically distinguishable from zero in the baseline specification. There is **suggestive evidence** of **higher DST-window rates** for offenses consistent with **outdoor, opportunistic** crime—especially **robbery** and **theft from motor vehicle**—with **null placebo** results at an arbitrary non-DST date that lend credibility to the design. **Burglary** appears sensitive to specification and **fails joint pre-trend tests**; we **do not** treat burglary as a secure causal conclusion. Confidence is **moderate**: Arizona contributes **twelve** control counties, **NIBRS reporting** varies by state and year, and **six outcomes** warrant caution on **multiple testing**.

---

## Decisions requested

1. **Messaging:** Lead public or legislative briefings with **no evidence of a uniform spike across all studied crimes**, explicit **uncertainty on burglary**, and **targeted attention** to **robbery** and **vehicle-related theft** for monitoring and follow-up research—not as standalone proof that DST “causes” those crimes.
2. **Policy framing:** DST rules are largely statutory; the primary model captures **months-long DST exposure** relative to Arizona, **not** only the **spring-forward weekend**. Distinguish **clock-change weekend** narratives from **season-long** associations.
3. **Follow-up evidence:** Before strong policy claims, prioritize **multi-year hourly** analysis (mechanism), **count models** for sparse daily events, and **reporting-coverage** sensitivity (especially states or years with thin NIBRS participation).

---

## Motivation

Decision-makers need to know whether higher crime in **warmer months** in DST states reflects **the clock** or **summer conditions** that would appear even without DST. **Arizona** provides a **within-U.S. comparison** where most counties **do not** spring forward, while sharing regional comparability with parts of the treated states. A **difference-style** design with **Arizona** as a benchmark and **flexible time controls** helps separate **shared seasonality** from **differential DST exposure** in a way that raw seasonal comparisons do not.

---

## Evidence (summary; figures in Appendix)

**Figure 1** — Daily state-level rates (CA vs. AZ) for burglary and motor vehicle theft: monthly seasonality and a ±15-day window around spring-forward. Supports interpreting “DST months” patterns alongside **shared summer seasonality**. *(Appendix.)*

**Figures 2a–2c** — Hourly profiles, four time-bucket summaries, and displacement-style regression (Stage 1B–1D); exploratory mechanism context for the **daily** TWFE. *(Appendix.)*

**Figure 3** — Baseline TWFE: DST calendar-window coefficients for CA, FL, UT vs. Arizona (six offense types), county and year–month FE, county-clustered SEs. *(Appendix.)*

**Figures 4a–4b** — Event studies around spring-forward and fall-back; pre-periods inform parallel trends (burglary interpreted cautiously). *(Appendix.)*

**Additional** — Descriptive plots, heterogeneity, and robustness exports (see Appendix; files `05`, `06`, `10`, `11` in this folder).

---

## Methods (summary)

- **Units:** County × day × offense type (aggregated to rates per 100,000 using county population).  
- **Treated:** Counties in **CA, FL, UT** that observe DST per project rules.  
- **Control:** **Arizona** counties on **America/Phoenix**; **Apache, Navajo, and Coconino** excluded (Navajo Nation observes DST).  
- **Primary specification:** Linear TWFE; **weekend** and **holiday** controls; **county-clustered** inference.  
- **Estimand note:** The coefficient describes **DST-window months vs. not** in treated states **relative to Arizona**, not a single **spring-forward weekend** effect for every county.

---

## Results (concise)

<table style="width:100%;border-collapse:collapse;margin:0.75em 0;line-height:1.45;">
<thead>
<tr>
<th scope="col" style="text-align:left;border-bottom:2px solid #333;padding:0.45em 0.75em 0.45em 0;vertical-align:top;width:32%;">Question</th>
<th scope="col" style="text-align:left;border-bottom:2px solid #333;padding:0.45em 0 0.45em 0.75em;vertical-align:top;">Answer</th>
</tr>
</thead>
<tbody>
<tr>
<td style="border-bottom:1px solid #ccc;padding:0.5em 0.75em 0.5em 0;vertical-align:top;">Universal increase across all six crimes?</td>
<td style="border-bottom:1px solid #ccc;padding:0.5em 0 0.5em 0.75em;vertical-align:top;"><strong>No</strong> — several offenses are <strong>not</strong> significant in baseline TWFE.</td>
</tr>
<tr>
<td style="border-bottom:1px solid #ccc;padding:0.5em 0.75em 0.5em 0;vertical-align:top;">Outdoor / opportunistic patterns?</td>
<td style="border-bottom:1px solid #ccc;padding:0.5em 0 0.5em 0.75em;vertical-align:top;"><strong>Suggestive</strong> positives for <strong>robbery</strong> and <strong>theft from motor vehicle</strong>; interpret as <strong>associational</strong> under this design.</td>
</tr>
<tr>
<td style="border-bottom:1px solid #ccc;padding:0.5em 0.75em 0.5em 0;vertical-align:top;">Burglary?</td>
<td style="border-bottom:1px solid #ccc;padding:0.5em 0 0.5em 0.75em;vertical-align:top;"><strong>Unreliable</strong> for causal claims here — <strong>pre-trend</strong> diagnostics fail.</td>
</tr>
<tr>
<td style="border-bottom:1px solid #ccc;padding:0.5em 0.75em 0.5em 0;vertical-align:top;">Placebo (non-DST date)?</td>
<td style="border-bottom:1px solid #ccc;padding:0.5em 0 0.5em 0.75em;vertical-align:top;"><strong>Null</strong> across outcomes in the documented run — supports that signals are not generic calendar noise.</td>
</tr>
<tr>
<td style="border-bottom:1px solid #ccc;padding:0.5em 0.75em 0.5em 0;vertical-align:top;">Stage 1 + Stage 2 together?</td>
<td style="border-bottom:1px solid #ccc;padding:0.5em 0 0.5em 0.75em;vertical-align:top;">Daily diagnostics warn against <strong>season vs. DST</strong> confusion; Stage 2 targets <strong>DST window vs. Arizona</strong> with fixed effects.</td>
</tr>
</tbody>
</table>

---

## Limitations

- **Precision:** Few **Arizona** control counties vs. many treated counties.  
- **Data:** **NIBRS** coverage varies; **Florida** participation is weak in some early years.  
- **Inference:** **Six outcomes** imply **multiple testing** — emphasize **consistent patterns**, not one **p-value**.  
- **Causal language:** Results support **policy-relevant monitoring and further research** more than a single definitive **DST** causal effect for every offense.

---

## Conclusion

Without a **non-DST benchmark**, seasonal crime is easy to misread as “DST effects.” This analysis uses **Arizona** and **two-way fixed effects** to isolate **differential DST-window exposure** for six offense types, with **supporting** daily and hourly diagnostics. We find **no** basis for claiming DST drives **across-the-board** increases in the studied crimes. **Robbery** and **theft from motor vehicle** show **suggestive** associations warranting **follow-up**; **burglary** does **not** clear **pre-trend** scrutiny. Next steps: **multi-year hourly** mechanism work, **count** models, and **coverage-robust** subsamples before any broad statutory conclusion.

---

## Appendix: Figures

*Full-resolution plots for submission or printing after the main memo. PNGs in this folder; regenerate from project root:* `python scripts/export_notebook_figures.py`

### Figure 1 — Daily rates: California vs. Arizona (seasonality and spring-forward window)

State-level daily crime rates per 100,000 residents for **burglary** and **motor vehicle theft**: (top) average daily rate by **calendar month**; (bottom) **±15 days** from the **second Sunday in March** (spring-forward).

<img src="./01_stage_1a_daily_data_seasonality_ca_vs_az_and_sprin.png" alt="Figure 1: Stage 1A daily CA vs AZ" width="920" />

### Figures 2a–2c — Hourly profiles, time buckets, displacement (Stage 1B–1D)

Mechanism diagnostics: **hourly** pre/post spring-forward, **four time buckets**, and **regression coefficients** (HC3 in notebook). Exploratory; primary estimate is Figure 3.

<img src="./02_stage_1b_hourly_crime_profile_before_vs_after_spri.png" alt="Figure 2a: hourly profile" width="920" />

<img src="./03_stage_1c_bucket_level_summary.png" alt="Figure 2b: time buckets" width="920" />

<img src="./04_stage_1d_displacement_regression.png" alt="Figure 2c: displacement regression" width="920" />

### Figure 3 — Baseline two-way fixed effects: DST window vs. Arizona (six offense types)

Coefficients on **DST calendar-window exposure** for **CA, FL, and UT** relative to **Arizona**, with **county** and **year–month** fixed effects and **county-clustered** standard errors.

<img src="./07_24_two_way_fixed_effects_did.png" alt="Figure 3: TWFE baseline" width="920" />

### Figures 4a–4b — Event studies (spring and fall)

Event-study coefficients around **spring-forward** and **fall-back**. **Flat pre-periods** support **parallel trends** where applicable; **burglary** discussed cautiously where pre-trend tests fail.

<img src="./08_25_event_study.png" alt="Figure 4a: event study spring-forward" width="920" />

<img src="./09_25_event_study.png" alt="Figure 4b: event study fall-back" width="920" />

### Additional outputs

Descriptive and robustness figures.

<img src="./05_23_descriptive_statistics.png" alt="Figure: descriptive 05" width="920" />

<img src="./06_23_descriptive_statistics.png" alt="Figure: descriptive 06" width="920" />

<img src="./10_27_heterogeneity.png" alt="Figure: heterogeneity" width="920" />

<img src="./11_28_robustness.png" alt="Figure: robustness" width="920" />
