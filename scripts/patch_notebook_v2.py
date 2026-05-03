"""
Rewrite all stale interpretation cells in the notebook to match actual results.
Run from project root: python scripts/patch_notebook_v2.py
"""
import json
from pathlib import Path

NB_PATH = Path("notebooks/dst_crime_analysis.ipynb")
nb = json.load(open(NB_PATH, encoding="utf-8"))
cells = nb["cells"]
id_to_idx = {c["id"]: i for i, c in enumerate(cells)}


def set_md(cell_id, new_source):
    idx = id_to_idx[cell_id]
    cells[idx]["source"] = [new_source]


# ── Cell 13 (c9469822): Stage 1 Findings ─────────────────────────────────────
set_md("c9469822", """\
## Stage 1: Findings and Interpretation

**Stage 1A (daily):** California and Arizona show similar summer crime rises, confirming that "DST months = higher crime" comparisons are driven by season, not the clock. The ±15-day window around spring-forward shows no sharp break at day 0, arguing against a large one-day shock.

**Hourly profile — CA + FL (treated), 28-day window around March 10 2024:**

| Zone | Hours | Raw change in treated states |
|---|---|---|
| Morning dark | 5–8h | −1% to −6% (flat to slightly down) |
| Evening light | 18–19h | −10% to −14% |

**What the data show — and what they do not:**

Evening crime (hours 18–19) fell 10–14% in CA+FL after spring-forward. However, AZ (no clock change) also shows a −7% evening decline over the same window, suggesting seasonal drift rather than a DST-specific effect. The triple-difference regression — which directly tests whether the within-day shift in CA+FL is *differential* vs. AZ — is **not statistically significant** for either bucket (morning p = 0.75, evening p = 0.74).

Critically, the morning-dark coefficient in the triple-diff is **negative** (−0.025), the *opposite* of what the displacement hypothesis predicts. The displacement hypothesis (DST rotates crime toward darker morning hours) is **not supported** by this one-year hourly sample.

**Conclusion for Stage 1:** The mechanism diagnostic is inconclusive. The raw evening decline in treated states is consistent with the light-shift story, but it does not survive adjustment for the AZ control. Multi-year hourly data would be needed to confirm or rule out the mechanism.
""")

# ── Cell 28 (6895ca2a): Interpreting Baseline TWFE ───────────────────────────
set_md("6895ca2a", """\
### Interpreting the Baseline TWFE Results

The dot plot above shows the estimated effect of the DST window on daily crime rates for each offense, with 95% confidence intervals. Key points:

- **All confidence intervals cross zero.** No offense is statistically significant at conventional thresholds once we account for multiple testing.
- **Unadjusted**, robbery (p = 0.053) and theft from motor vehicle (p = 0.064) are marginally suggestive. But testing six outcomes simultaneously means we expect roughly one false positive at the 10% level purely by chance — the "Jelly Bean" problem. After **Holm-Bonferroni correction** (see Section 2.10), both corrected p-values rise to ~0.32. No offense reaches significance.
- **The all-crime aggregate** (Section 2.12) is also null: β = +0.013, p = 0.600.
- Standard errors are clustered at the county level. Socioeconomic controls do not change estimates, confirming they are collinear with county fixed effects.
""")

# ── Cell 33 (54884d8f): Interpreting Event Studies ───────────────────────────
set_md("54884d8f", """\
### Interpreting the Event Studies

Each panel plots event-study coefficients in **2-week bins** relative to the DST transition (bin −1 = reference). Flat pre-period bins (bins −4 to −1) support the parallel trends assumption.

- **Robbery, theft from motor vehicle, motor vehicle theft:** pre-periods are flat. Parallel trends hold.
- **Burglary, shoplifting, theft from building:** 1 of 3 pre-period bins is individually significant at 10% for each. The joint pre-trend test for burglary (p = 0.079) and shoplifting (p = 0.076) is borderline. Interpret TWFE estimates for these three offenses with caution — pre-existing differential trends cannot be fully ruled out.
- **Post-period coefficients** are generally close to zero with wide confidence intervals, consistent with the null TWFE result.

The fall-back event study (Section 2.5b) serves as a symmetry check; a symmetric pattern at fall-back would strengthen credibility of any spring-forward effect.
""")

# ── Cell 39 (24b0bade): Interpreting Heterogeneity ───────────────────────────
set_md("24b0bade", """\
### Interpreting Heterogeneity Results

The forest plot breaks the pooled estimate into state-by-state comparisons. The key finding is **heterogeneity in theft from motor vehicle**:

- **CA vs AZ: β = +0.039, p = 0.003 (***)**
- **UT vs AZ: β = +0.045, p = 0.004 (***)**
- FL vs AZ: β = +0.012, p = 0.209 (not significant)

California and Utah individually show strong, statistically significant associations between the DST window and theft from motor vehicle — even before any multiple-testing correction. These are the two states with the most geographic and climatic comparability to Arizona. Florida does not show the same pattern.

**What this means:** The pooled TWFE result (null after FWER) averages over heterogeneous state effects. The CA and UT signal is real in magnitude and precision. This does *not* establish causality on its own — it could reflect state-specific trends not fully absorbed by the fixed effects — but it is the most credible individual finding in this analysis and warrants follow-up.

All other offense types remain null across all state subgroups, consistent with the pooled result.
""")

# ── Cell 43 (0405c389): Interpreting Robustness ──────────────────────────────
set_md("0405c389", """\
### Interpreting Robustness Checks

Four robustness specifications are reported:

1. **Exclude holidays:** Crime on holidays is atypical. Removing them does not change results.
2. **Weekdays only:** Weekend crime patterns differ structurally. Restricting to weekdays does not recover significant effects.
3. **Standard-time placebo:** Uses November–March (non-DST window) as a fake treatment period. Results are null or sign-reversed — reassuring that the baseline estimates are not driven by systematic seasonal differences between treated and control states.
4. **Year FE only:** Replacing year-month with year fixed effects absorbs less seasonality. Some estimates become nominally significant under this looser specification (e.g., motor vehicle theft), but this reflects the year-FE model's susceptibility to seasonal confounding — exactly the problem the baseline design is built to avoid.

**Overall:** The null pattern in the baseline TWFE is robust across the first three checks. The year-FE result is an artefact of under-controlling for seasonality and should not be interpreted as evidence of a real DST effect.
""")

# ── Cell 52 (9530c9d4): 2.11 Interpretation and Conclusion ───────────────────
set_md("9530c9d4", """\
## 2.11 Interpretation and Conclusion

### Summary of findings

**Pooled TWFE (primary specification):**
After applying Holm-Bonferroni correction for six simultaneous tests, no offense type reaches statistical significance. Unadjusted p-values for robbery (0.053) and theft from motor vehicle (0.064) were superficially marginal but correct to ~0.32 after FWER adjustment. The all-crime aggregate is null (β = +0.013, p = 0.600).

**Heterogeneity — the most credible individual finding:**
Theft from motor vehicle shows significant associations in CA vs AZ (β = +0.039, p = 0.003) and UT vs AZ (β = +0.045, p = 0.004), independently. These are the two treated states most comparable to Arizona geographically. Florida does not show the same pattern, suggesting the signal is not universal. This state-level finding does not survive pooled FWER correction across all outcomes, but it is specific, directionally consistent across two independent comparisons, and worth prioritizing in follow-up work.

**Mechanism (Stage 1 hourly):**
No statistically significant displacement of crime across hours of day was detected. The evening decline in raw treated-state data (10–14% at hours 18–19) is not confirmed as differential vs. Arizona by the triple-difference model (p > 0.74 for both buckets). The morning-dark coefficient is negative — opposite to the displacement prediction. The light-shift mechanism remains unconfirmed in this one-year hourly sample.

**Design caveats:**
- 12 AZ control counties vs. 154 treated counties: asymmetric control group limits precision.
- NIBRS coverage varies by state/year; Florida has thin participation in early years.
- Burglary, shoplifting, and theft from building show borderline pre-trend violations; causal claims for these offenses are not warranted here.

### What to take forward

The analysis does **not** support a "DST causes a broad crime wave" narrative. The honest summary is:

1. No universal effect across offenses or in aggregate.
2. Theft from motor vehicle in CA and UT is a specific, credible signal worth investigating further — not a definitive causal finding.
3. The hourly mechanism requires multi-year data to test properly.
4. Before any statutory use of this evidence, commission a multi-year hourly analysis and apply pre-registered FWER thresholds across outcomes.
""")

json.dump(nb, open(NB_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("Notebook interpretation cells updated.")
