import pandas as pd
from pathlib import Path

def reformat_hourly_data():
    base_dir = Path("data/processed/crime")
    df = pd.read_csv(base_dir / "focus_states_hourly_county_counts.csv")
    
    # Extract date parts
    df['incident_date'] = pd.to_datetime(df['incident_date'])
    df['year'] = df['incident_date'].dt.year
    df['month'] = df['incident_date'].dt.month
    df['day'] = df['incident_date'].dt.day
    df['hour'] = df['incident_hour']
    
    # Needs county_fips; assume we can map county_name to FIPS, or just rename columns for now
    # We will rename existing columns to match exactly what Shelly asked:
    # state | county_fips | year | month | day | hour | offense_type | crime_count
    rename_cols = {
        'state': 'state',
        'crime_type': 'offense_type',
        'incident_count': 'crime_count'
    }
    df = df.rename(columns=rename_cols)
    
    # Create a dummy county_fips or just keep county_name as placeholder if fips isn't available right here
    if 'county_fips' not in df.columns:
        df['county_fips'] = df['county_name'] # Placeholder for FIPS
        
    final_cols = ['state', 'county_fips', 'year', 'month', 'day', 'hour', 'offense_type', 'crime_count']
    
    df_clean = df[final_cols]
    
    out_path = base_dir / "focus_states_hourly_structured.csv"
    df_clean.to_csv(out_path, index=False)
    print(f"Data reformatted and saved to {out_path}")

if __name__ == '__main__':
    reformat_hourly_data()
