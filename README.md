# IDS701_UDS_Final_Project

This repository contains the final analysis for evaluating whether Daylight Saving Time (DST) reduces property crime using a California vs. Arizona Difference-in-Differences design.

## Branch Overview (`full_analysis`)

This branch contains the clean, finalized version of the project. All exploratory analyses have been removed.

### Final Notebooks
Only the final analysis notebooks are kept in `notebooks/`:
* **`stage1_stage2_ca_az_only.ipynb`**: The original combined Stage 1 and Stage 2 analysis.
* **`dst_crime_ca_az_refined.ipynb`**: The refined version with a clean structure (where triple-difference is used only in Stage 1, Stage 2 acts as the primary finding, and the visuals are simplified).

### Complete Data Pipeline
All data processing and modeling scripts located in the `scripts/` directory have been updated to their final state and are used to generate the required panel datasets.

### Data Files
Essential processed and raw data files have been committed. However, massive intermediate panel files and raw NIBRS ZIPs are intentionally ignored by git to keep the repository lightweight. To reproduce the full dataset from scratch, follow the Data Setup steps below.

---

## Data setup

Raw crime data and large intermediate panels are intentionally not committed to this repo. To reproduce the model-ready datasets from scratch, follow the steps below. 
*(Note: Population, weather, and socioeconomic control data have already been processed and committed to this branch, so you can skip those loaders!)*

To skip reproduction entirely, ask a teammate for the final panel file and place it at:
`data/processed/model/focus_states_daily_county_model_panel_2022_2024.csv`

### Step 1 — Download NIBRS ZIPs
1. Go to https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/downloads
2. Download the following state-year ZIP files and save them to `data/raw/crime/nibrs_state_year/`:
   - AZ-2022.zip, AZ-2023.zip, AZ-2024.zip
   - CA-2022.zip, CA-2023.zip, CA-2024.zip
   - UT-2022.zip, UT-2023.zip, UT-2024.zip
3. Paste the download URLs (one per line) into `data/raw/crime/nibrs_download_urls.txt`
4. Run: `python scripts/download_nibrs_state_files.py`
   - Note: increase `timeout` in that script from 120 to 600 before running — CA files are large

### Step 2 — Build Crime Panels
Since population and socioeconomic data are already committed, you only need to audit the NIBRS zips and build the crime panels:

```bash
python scripts/audit_nibrs_zip_quality.py
python scripts/build_focus_state_panel.py
python scripts/build_model_ready_panel.py
```