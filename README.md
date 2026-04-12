# DST and Crime: A Causal Analysis

**IDS 701 - Problem Solving with Data Science | Duke University | Spring 2026**

Does the switch to Daylight Saving Time change crime rates? This project uses a
difference-in-differences design to estimate the effect of the spring DST transition
across six offense types in California, Florida, and Arizona (2022-2024).

---

## Research Design

**Question:** Does the spring-forward DST transition causally shift daily crime rates?

**Identification strategy:** Difference-in-differences with two-way fixed effects (TWFE).

- **Treated states:** California and Florida (observe DST).
- **Control state:** Arizona (does not observe DST; clocks never change).
- **Excluded from AZ control:** Apache, Navajo, and Coconino counties, which contain
  Navajo Nation territory that observes DST independently — their inclusion would
  contaminate the control group.
- **Outcome variables:** Burglary (220), Motor Vehicle Theft (240), Robbery (120),
  Shoplifting (23C), Theft From Building (23D), and Theft From Motor Vehicle (23F).
- **Primary analysis window:** 2022-2024 (three full DST cycles, three years of post-COVID
  crime patterns; 2021 retained as pre-period for parallel trends checks).
- **Unit of observation:** County x date x crime type.

**DST transition dates (computed by rule, not looked up):**
- Spring forward: second Sunday in March each year.
- Fall back: first Sunday in November each year.
- Arizona counties assigned `America/Phoenix` timezone (no DST); FL panhandle counties
  assigned `America/Chicago`; all other FL counties `America/New_York`; all CA counties
  `America/Los_Angeles`. Rules are deterministic overrides, not geocoder outputs.

---

## Repository Structure

```
IDS701_UDS_Final_Project/
|-- notebooks/
|   `-- dst_crime_analysis.ipynb        Main analysis notebook (all models here)
|-- scripts/
|   |-- download_nibrs_state_files.py   Download raw NIBRS ZIPs from CDE
|   |-- audit_nibrs_zip_quality.py      Check ZIP contents before parsing
|   |-- parse_nibrs_focus_states.py     Optional legacy parser (not required by main pipeline)
|   |-- build_focus_state_panel.py      Build incident-level panel from ZIPs
|   |-- build_model_ready_panel.py      Zero-fill panel + attach all controls
|   |-- load_remaining_controls.py      Fetch timezone, holiday, weather data
|   |-- load_socioeconomic_acs.py       Fetch ACS socioeconomic controls
|   |-- load_population_acs.py          Fetch county population from ACS
|   |-- generate_dst_calendar.py        Compute DST start/end dates 2021-2026
|   |-- analyze_focus_states_dst.py     Legacy descriptive analysis (superseded; do not use)
|   `-- load_crime_open_data.py         Legacy city-level API pulls (superseded; do not use)
|-- data/
|   |-- raw/
|   |   |-- crime/nibrs_state_year/     NIBRS ZIPs: AZ/CA/FL x 2021-2024 (gitignored)
|   |   |-- dst/                        DST calendar CSV
|   |   |-- holidays/                   US public holidays 2021-2024
|   |   |-- population/                 Census Bureau county population estimates
|   |   |-- socioeconomic/              ACS raw controls
|   |   |-- timezone/                   County centroid + timezone table
|   |   `-- weather/                    Open-Meteo daily weather by county
|   `-- processed/
|       |-- crime/                      Daily and hourly county crime aggregates
|       |-- model/                      Model-ready panel + treatment tables (gitignored: large)
|       |-- panel/                      Incident-level panel CSV (gitignored: 123 MB)
|       |-- population/                 Long-format county population 2020-2024
|       `-- socioeconomic/              Derived ACS controls
|-- DATA_SOURCES_AND_LOAD.md            API references and load status log
|-- nibrs_diagram.pdf                   NIBRS data structure diagram
|-- .gitignore
`-- README.md
```

---

## Pipeline: How to Reproduce

Run scripts in order. Each step writes to `data/` and the next step reads from it.

### Step 1 - Download raw NIBRS ZIPs

Add fresh CDE signed URLs (one per line) to `data/raw/crime/nibrs_download_urls.txt`,
then run:

```
python scripts/download_nibrs_state_files.py
```

ZIPs land in `data/raw/crime/nibrs_state_year/` named `{STATE}-{YEAR}.zip`.
CDE download links are temporary signed URLs; they cannot be reconstructed from
state/year alone. Get them from: https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/downloads

### Step 2 - Parse ZIPs into incident-level panel

```
python scripts/build_focus_state_panel.py
```

Reads all `{STATE}-{YEAR}.zip` files for CA, FL, AZ. Joins NIBRS offense table to
incident table + agency metadata. Filters to offense codes 120, 220, 23C, 23D, 23F,
and 240. Applies the AZ county exclusion. Outputs one flat CSV at incident-offense grain.

Output: `data/processed/panel/focus_states_incident_offense_panel.csv`

Note: `scripts/parse_nibrs_focus_states.py` is retained for historical debugging and
exploratory summaries; it is not a required step for the reproducible model pipeline.

### Step 3 - Load control data

```
python scripts/load_remaining_controls.py
```

Fetches from three external APIs:
- Open-Meteo geocoding: county centroid lat/lon + timezone (then overridden by
  deterministic state rules so geocoder errors cannot affect treatment assignment).
- Nager.Date: US federal public holidays 2021-2024.
- Open-Meteo archive: daily weather by county (optional; pass `--include-weather`).

```
python scripts/load_socioeconomic_acs.py
```

Fetches ACS 5-year estimates for median household income, poverty rate, unemployment
rate, and bachelor's degree attainment by county x year.

```
python scripts/load_population_acs.py
```

Fetches ACS county population estimates for 2020-2024.

### Step 4 - Build model-ready panel

```
python scripts/build_model_ready_panel.py
```

This is the core ETL step. It:

1. Builds a full skeleton of every county x date x crime_type cell (1,461 dates x
  all counties x selected offense types) using a cross-product join, so zero-incident days
   are explicit zeros rather than missing rows.
2. Left-joins observed incident counts onto the skeleton.
3. Attaches population, socioeconomic controls, holiday flags, and timezone.
4. Computes DST treatment flags: `treated_state`, `in_dst_window`, `days_from_dst_start`,
   `days_from_dst_end`, `post_dst_start`, `post_dst_end`, `observes_dst_county`.
5. Deduplicates holidays before merging (some dates have two holiday names in the
   source data; without deduplication, a row fan-out multiplies incident counts).

Outputs:
- `data/processed/model/focus_states_daily_county_model_panel_2021_2024.csv` (full)
- `data/processed/model/focus_states_daily_county_model_panel_2022_2024.csv` (primary window)
- `data/processed/model/focus_states_county_date_treatment_2021_2024.csv`
- `data/processed/model/focus_states_county_date_treatment_2022_2024.csv`

These files are gitignored (large generated outputs). Re-run this script to recreate them.

### Step 4.5 - Validate generated outputs (required quality gate)

Run these checks before analysis to verify key panel assumptions:

```python
from pathlib import Path
import pandas as pd

root = Path(".")
model = pd.read_csv(root / "data/processed/model/focus_states_daily_county_model_panel_2022_2024.csv", low_memory=False)
trt = pd.read_csv(root / "data/processed/model/focus_states_county_date_treatment_2022_2024.csv", low_memory=False)

model["incident_date"] = pd.to_datetime(model["incident_date"], errors="coerce")
trt["incident_date"] = pd.to_datetime(trt["incident_date"], errors="coerce")

print("MODEL_KEY_DUP:", int(model.duplicated(["state", "county_fips", "incident_date", "crime_type"]).sum()))
print("TRT_KEY_DUP:", int(trt.duplicated(["state", "county_fips", "incident_date"]).sum()))

allowed = {
  "AZ": {"America/Phoenix", "America/Denver"},
  "CA": {"America/Los_Angeles"},
  "FL": {"America/New_York", "America/Chicago"},
}
for st, ok in allowed.items():
  seen = set(model.loc[model["state"] == st, "timezone"].dropna().unique())
  print(f"UNEXPECTED_TZ_{st}:", sorted(seen - ok))

print("ZERO_SHARE:", float((model["incident_count"] == 0).mean()))
```

Expected pass criteria:
- `MODEL_KEY_DUP = 0`
- `TRT_KEY_DUP = 0`
- `UNEXPECTED_TZ_AZ/CA/FL` are empty lists
- `ZERO_SHARE > 0` (confirms explicit zero-filled panel)

### Step 5 - Run analysis

Open and execute `notebooks/dst_crime_analysis.ipynb`.

Warning: do not use `scripts/analyze_focus_states_dst.py` or
`scripts/load_crime_open_data.py` for final estimation outputs.

---

## Analysis Notebook: dst_crime_analysis.ipynb

The notebook runs end-to-end from the model panel CSV through all model specifications.

### Models implemented

**1. Primary TWFE (Difference-in-Differences)**

Two-way fixed effects: county fixed effects + year-month time fixed effects.
Implemented via the FWL theorem (sequential within-transformation: demean by county,
then demean by time period) rather than dummy variables, which avoids memory blowup
on a panel with 200+ counties x 1,461 dates. Standard errors clustered at county level.

Treatment variable: `in_dst_window x treated_state` — equals 1 for counties in CA/FL
during the DST window (March second Sunday through November first Sunday), 0 otherwise.
Arizona is always 0 (never in DST window).

Controls included: log population, median household income, poverty rate, unemployment
rate, bachelor's degree rate, day-of-week dummies, is_weekend, is_holiday.

**2. Event study (dynamic DiD, spring)**

Week bins computed as `days_from_dst_start // 7`, clipped to [-8, +8] (8 weeks before
and after spring transition). Each bin interacted with `treated_state`. The omitted
reference bin is week -1 (the week just before spring forward). County and year fixed
effects included. Shows the pre-trend and post-transition dynamic pattern.

**3. Event study (dynamic DiD, fall)**

Same structure around the fall-back date using `days_from_dst_end`.

**4. Narrow-window RD check**

Restricts sample to 14 days around the spring-forward date. Estimates a sharp RD
using a post-transition dummy interacted with treated_state. Serves as a robustness
check that the effect concentrates at the transition rather than being a DST-window
seasonal effect.

**5. Robustness specifications**

- Exclude holidays: drop all public holiday dates.
- Weekdays only: drop weekends.
- Placebo: use the standard-time window (November through March) as the "treatment"
  window for treated states, where no DST effect should appear.
- Year FE only: replace year-month FE with year FE to check sensitivity to time
  period granularity.

### Key results (2022-2024 primary window)

Baseline TWFE estimates (county and year-month fixed effects; county-clustered
standard errors) from the latest notebook run:

| Crime Type | TWFE Coefficient | SE (clustered) | p-value |
|---|---|---|---|
| Robbery | +0.0058 | 0.0029 | 0.047 |
| Theft From Motor Vehicle | +0.0160 | 0.0089 | 0.073 |
| Burglary | +0.0171 | 0.0097 | 0.076 |
| Motor Vehicle Theft | -0.0154 | 0.0124 | 0.215 |
| Shoplifting | +0.0142 | 0.0126 | 0.261 |
| Theft From Building | -0.0070 | 0.0074 | 0.350 |

Inference diagnostics in the notebook show:
- Placebo cutoff tests at June 15 (+/-21 days) are null for all six outcomes. (Distinct from the winter standard-time placebo check).
- Joint pre-trend tests are mostly non-rejected, but burglary rejects in the
  pre-period and should be interpreted with additional caution.

Interpretation is offense-specific and should prioritize patterns that remain
stable across baseline, event-study, placebo, and robustness checks.

---

## Data Sources

| Dataset | Source | Coverage |
|---|---|---|
| Crime incidents | FBI NIBRS via CDE Downloads | CA, FL, AZ; 2021-2024 |
| County population | ACS 5-year (Census Bureau) | 2020-2024 |
| Socioeconomic controls | ACS 5-year (Census Bureau) | 2021-2024 |
| Timezone | Open-Meteo geocoding (overridden by rule) | All focus counties |
| Weather | Open-Meteo historical archive | All focus counties; 2021-2024 |
| Public holidays | Nager.Date API | US; 2021-2024 |
| DST dates | Computed from NIST rule | 2021-2024 |

NIBRS data dictionary: `data/raw/crime/nibrs_state_year/NIBRS_DataDictionary.pdf`

---

## Key Design Decisions and Pitfalls

**Why Arizona as control?** Arizona does not observe DST statewide (exception: Navajo
Nation). This gives a clean never-treated control group with similar climate and
demographic diversity to CA/FL. Difference-in-differences relies on the parallel trends
assumption: absent DST, CA/FL and AZ would have moved together.

**Why exclude Apache, Navajo, Coconino counties?** These AZ counties contain Navajo
Nation territory, which independently observes DST. Including them as controls would
bias estimates because they experience the treatment.

**Why FL panhandle counties get Central Time?** Bay, Escambia, Okaloosa, Santa Rosa,
and six other FL panhandle counties are in the Central Time zone. Their DST transition
is at the same calendar date but the sunrise/sunset shift differs. The timezone table
assigns them `America/Chicago` to allow future analyses to use local time correctly.

**Why override geocoder timezones unconditionally?** The Open-Meteo geocoding API
returned incorrect results for many county queries (returning parks, airports, or dams
instead of county seats), which would assign wrong timezones and corrupt the
treatment/control classification. All timezone assignments use deterministic state-level
rules that override whatever the geocoder returned.

**Why zero-fill the panel?** County-days with zero crimes are not reported in NIBRS;
they simply do not appear. Without explicit zeros, a regression model would only see
days with at least one crime, introducing selection bias. The skeleton cross-product
ensures every county x date x crime_type cell exists, with incident_count = 0 for
unobserved cells.

**Why deduplicate holidays before merging?** Some dates appear twice in the Nager.Date
response (e.g., Columbus Day / Indigenous Peoples Day). Without deduplication, a
left join on date would produce two rows per county-date on those days, doubling the
incident count for 8 dates per year.

---

## Environment

Python 3.11+.

Install with pinned dependencies:

```
pip install -r requirements.txt
```

The NIBRS ZIP files are not included in the repository (too large; gitignored). All
other raw reference data and small processed files are committed. The large generated
CSVs under `data/processed/model/` and `data/processed/panel/` are also gitignored and
must be regenerated locally by running the pipeline scripts in order.
