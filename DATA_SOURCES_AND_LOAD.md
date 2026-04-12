# DST Crime Project: APIs and Load Status

This document lists the practical APIs/sources for your proposal and what has already been loaded into this repo.

## 1) Crime data (burglary, motor vehicle theft)

- Primary source: FBI Crime Data Explorer (CDE) API and NIBRS downloads
- API base: https://api.usa.gov/crime/fbi/cde/
- Docs page: https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/docApi
- Download page: https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/downloads

Status:
- API call without key returns `403 Forbidden`.
- You need a data.gov API key for direct API pulls.
- Practical fallback is downloading NIBRS state-year files from CDE Downloads and placing them under `data/raw/crime/`.
- Historical public scripts that hardcode older FBI S3 keys currently return `404` on tested files (the structure appears to have changed).

Local bulk-download workflow now added:
- Put current CDE NIBRS state-year ZIP URLs (one per line) in `data/raw/crime/nibrs_download_urls.txt`.
- Run `scripts/download_nibrs_state_files.py` to download all files and write a log.

Run command:
- `C:/Users/LENOVO/miniforge3/python.exe scripts/download_nibrs_state_files.py`

Outputs:
- `data/raw/crime/nibrs_state_year/` (downloaded ZIP files)
- `data/raw/crime/nibrs_download_log.csv` (status by URL)

## 2) Population denominator (county-year)

- Working API: ACS 5-year county population
- Endpoint pattern: `https://api.census.gov/data/{year}/acs/acs5?get=NAME,B01003_001E&for=county:*&in=state:*`

Status:
- Loaded successfully for 2021, 2022, 2023.
- Output file: `data/raw/population/county_population_acs_2021_2023.csv`
- Rows: 9,666 (header + 9,665 county-year records)

Loader script:
- `scripts/load_population_acs.py`

Run command:
- `C:/Users/LENOVO/miniforge3/python.exe scripts/load_population_acs.py`

## 3) DST transition dates

- Rule source: NIST DST rules (second Sunday in March, first Sunday in November)
- Reference: https://www.nist.gov/pml/time-and-frequency-division/popular-links/daylight-saving-time-dst

Status:
- Generated table for 2021 through 2026.
- Output file: `data/raw/dst/dst_calendar_2021_2026.csv`

Generator script:
- `scripts/generate_dst_calendar.py`

Run command:
- `C:/Users/LENOVO/miniforge3/python.exe scripts/generate_dst_calendar.py`

## 4) Daylight/sunset controls

- Working API (no key): Sunrise-Sunset API
- Example endpoint: `https://api.sunrise-sunset.org/json?lat=35.7796&lng=-78.6382&date=2023-03-12&formatted=0`

Status:
- Endpoint verified.
- Not yet bulk-loaded for all counties because county latitude/longitude table still needs to be finalized.

## 5) Time zone by county

- Needed columns: `county_fips`, `tz_name`, `observes_dst`

Status:
- Not loaded yet.
- Recommended approach: use a county centroid file + timezone lookup pipeline, then manually validate known exception states (e.g., IN, KY, TN, FL split areas).

## 6) What is already ready for your team

- `data/raw/population/county_population_acs_2021_2023.csv`
- `data/raw/dst/dst_calendar_2021_2026.csv`
- `data/raw/crime/crime_chicago_year_type_2021_plus.csv`
- `data/raw/crime/crime_nyc_year_type_2021_plus.csv`
- `data/raw/crime/crime_city_year_type_2021_plus.csv`
- Reproducible loaders in `scripts/`

## 6a) Working yearly crime-by-type APIs loaded now

These are fully working and already materialized in this repo.

1. Chicago Open Data (Crimes)
- API dataset: `ijzp-q8t2`
- Query used: grouped by `year` and `primary_type`
- Coverage pulled: 2021+

2. NYC Open Data (NYPD Complaint Data)
- API dataset: `5uac-w243`
- Query used: grouped by `date_extract_y(cmplnt_fr_dt)` and `ofns_desc`
- Coverage pulled: 2021+

Loader script:
- `scripts/load_crime_open_data.py`

Run command:
- `C:/Users/LENOVO/miniforge3/python.exe scripts/load_crime_open_data.py`

## 7) Immediate next inputs needed from team

1. Crime raw files from CDE/NIBRS into `data/raw/crime/`
2. County-timezone table into `data/raw/timezone/`
3. County-date daylight table into `data/raw/daylight/`

## 8) Proposal focus states confirmed

From the proposal document, the analysis focus is:
- California (`CA`)
- Florida (`FL`)
- Arizona (`AZ`) as non-DST comparison state

Special rule from proposal:
- Exclude Arizona counties: Apache, Navajo, and Coconino.

## 9) New parser + analysis scripts added

1. Parse NIBRS ZIPs for focus states
- Script: `scripts/parse_nibrs_focus_states.py`
- Inputs: files like `CA-2024.zip`, `FL-2024.zip`, `AZ-2024.zip` in `data/raw/crime/nibrs_state_year/`
- Outputs:
	- `data/processed/crime/focus_states_daily_county_counts.csv`
	- `data/processed/crime/focus_states_hourly_county_counts.csv`
	- `data/processed/crime/focus_states_state_year_summary.csv`

Run command:
- `C:/Users/LENOVO/miniforge3/python.exe scripts/parse_nibrs_focus_states.py`

2. Build first DST analysis tables
- Script: `scripts/analyze_focus_states_dst.py`
- Outputs:
	- `data/processed/analysis/focus_states_daily_with_dst_flags.csv`
	- `data/processed/analysis/focus_states_dst_period_summary.csv`
	- `data/processed/analysis/focus_states_hour_bucket_summary.csv`

Run command:
- `C:/Users/LENOVO/miniforge3/python.exe scripts/analyze_focus_states_dst.py`

Note on download links:
- CDE state-year ZIP links are temporary signed URLs and cannot be safely reused by changing only the state code.
- Add one fresh signed URL per state-year in `data/raw/crime/nibrs_download_urls.txt`, then run `scripts/download_nibrs_state_files.py`.
