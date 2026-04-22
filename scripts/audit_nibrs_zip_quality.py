import re
import zipfile
from pathlib import Path

import pandas as pd

ZIP_DIR = "data/raw/crime/nibrs_state_year"
SUSPICIOUS_THRESHOLD = 0.20  # < 20 % of state median
MIN_FILE_MB = 1.0


def count_rows(zf, name):
    candidates = [n for n in zf.namelist() if n.upper().split("/")[-1] == name.upper()]
    if not candidates:
        return None
    with zf.open(candidates[0]) as f:
        return sum(1 for _ in f) - 1  # subtract header


def audit_zip(path):
    size_mb = path.stat().st_size / 1e6
    m = re.search(r'([A-Z]{2})-(\d{4})\.zip', path.name, re.IGNORECASE)
    state = m.group(1).upper() if m else "??"
    year = int(m.group(2)) if m else 0

    try:
        with zipfile.ZipFile(path) as zf:
            incidents = count_rows(zf, "NIBRS_incident.csv")
            offenses = count_rows(zf, "NIBRS_OFFENSE.csv")
            agencies = count_rows(zf, "agencies.csv")
    except Exception as exc:
        return {
            "state": state, "year": year, "size_mb": round(size_mb, 2),
            "incidents": None, "offenses": None, "agencies": None,
            "error": str(exc),
        }

    return {
        "state": state, "year": year, "size_mb": round(size_mb, 2),
        "incidents": incidents, "offenses": offenses, "agencies": agencies,
        "error": None,
    }


def main():
    zips = sorted(Path(ZIP_DIR).glob("*-*.zip"))
    if not zips:
        print(f"No ZIP files found in {ZIP_DIR}")
        return

    print(f"Auditing {len(zips)} ZIP file(s)...\n")
    rows = [audit_zip(p) for p in zips]
    df = pd.DataFrame(rows)

    # Compute per-state medians
    medians = df.groupby("state")[["incidents", "agencies"]].median()

    suspicious = []
    for _, row in df.iterrows():
        flags = []
        if row["size_mb"] < MIN_FILE_MB:
            flags.append(f"size {row['size_mb']} MB < {MIN_FILE_MB}")
        if row["error"]:
            flags.append(f"read error: {row['error']}")
        else:
            med_inc = medians.loc[row["state"], "incidents"]
            med_age = medians.loc[row["state"], "agencies"]
            if row["incidents"] is not None and med_inc and row["incidents"] < SUSPICIOUS_THRESHOLD * med_inc:
                flags.append(f"incidents {row['incidents']} < 20% of state median {med_inc:.0f}")
            if row["agencies"] is not None and med_age and row["agencies"] < SUSPICIOUS_THRESHOLD * med_age:
                flags.append(f"agencies {row['agencies']} < 20% of state median {med_age:.0f}")
        if flags:
            suspicious.append({"file": f"{row['state']}-{row['year']}.zip", "flags": "; ".join(flags)})

    print(df[["state", "year", "size_mb", "incidents", "offenses", "agencies"]].to_string(index=False))

    print(f"\n{len(suspicious)} suspicious file(s):")
    if suspicious:
        for s in suspicious:
            print(f"  {s['file']}: {s['flags']}")
    else:
        print("  None")


if __name__ == "__main__":
    main()
