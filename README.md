# IDS701_UDS_Final_Project

## Data setup

Raw data is not committed to this repo. To reproduce from scratch, follow the steps below.
To skip reproduction, ask a teammate for the final panel file and place it at:
`data/processed/model/focus_states_daily_county_model_panel_2022_2024.csv`

### Step 1 — NIBRS ZIPs
1. Go to https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/downloads
2. Download the following state-year ZIP files and save them to `data/raw/crime/nibrs_state_year/`:
   - AZ-2022.zip, AZ-2023.zip, AZ-2024.zip
   - CA-2022.zip, CA-2023.zip, CA-2024.zip
   - FL-2022.zip, FL-2023.zip, FL-2024.zip
   - UT-2022.zip, UT-2023.zip, UT-2024.zip
3. Paste the download URLs (one per line) into `data/raw/crime/nibrs_download_urls.txt`
4. Run: `python scripts/download_nibrs_state_files.py`
   - Note: increase `timeout` in that script from 120 to 600 before running — CA files are large

### Step 2 — Census population file
1. Go to https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/counties/totals/
2. Download `co-est2024-alldata.csv`
3. Save it to `data/raw/population/co-est2024-alldata.csv`

### Step 3 — Run loaders
```bash
python scripts/load_socioeconomic_acs.py
python scripts/load_remaining_controls.py --include-weather
```

### Step 4 — Run the pipeline in order
```bash
python scripts/audit_nibrs_zip_quality.py
python scripts/rebuild_population_panel.py
python scripts/build_focus_state_panel.py
python scripts/build_model_ready_panel.py
```