"""Audit quality of focus-state NIBRS ZIP files.

Flags suspiciously small state-year files by comparing incident and agency counts.
"""

from __future__ import annotations

from pathlib import Path
import re
import zipfile

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ZIP_DIR = ROOT / "data" / "raw" / "crime" / "nibrs_state_year"
ZIP_RE = re.compile(r"^(CA|FL|AZ)-(\d{4})\.zip$")


def pick_member(names: list[str], target: str) -> str | None:
    t = target.lower()
    for n in names:
        if n.lower() == t or n.lower().endswith("/" + t) or Path(n).name.lower() == t:
            return n
    return None


def read_count(z: zipfile.ZipFile, member: str, usecols: list[str]) -> int:
    try:
        return len(pd.read_csv(z.open(member), usecols=usecols, low_memory=False, encoding="utf-8"))
    except UnicodeDecodeError:
        return len(pd.read_csv(z.open(member), usecols=usecols, low_memory=False, encoding="latin-1"))


def audit_one(path: Path) -> dict[str, object]:
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        inc_name = pick_member(names, "NIBRS_incident.csv")
        off_name = pick_member(names, "NIBRS_OFFENSE.csv")
        ag_name = pick_member(names, "agencies.csv")

        incidents = -1
        offenses = -1
        agencies = -1

        if inc_name:
            incidents = read_count(z, inc_name, ["incident_id"])
        if off_name:
            offenses = read_count(z, off_name, ["offense_id", "offense_code"])
        if ag_name:
            agencies = read_count(z, ag_name, ["agency_id"])

    m = ZIP_RE.match(path.name)
    state = m.group(1) if m else "??"
    year = int(m.group(2)) if m else -1

    return {
        "file": path.name,
        "state": state,
        "year": year,
        "size_mb": round(path.stat().st_size / 1024 / 1024, 3),
        "incident_rows": incidents,
        "offense_rows": offenses,
        "agency_rows": agencies,
    }


def main() -> None:
    rows = []
    for p in sorted(ZIP_DIR.glob("*.zip")):
        if ZIP_RE.match(p.name):
            rows.append(audit_one(p))

    if not rows:
        print("No focus-state ZIP files found.")
        return

    df = pd.DataFrame(rows).sort_values(["state", "year"])

    # Simple anomaly rule: very low agencies or incidents relative to neighboring years.
    df["flag_suspicious"] = False
    for st, g in df.groupby("state"):
        g = g.sort_values("year")
        med_inc = g["incident_rows"].median()
        med_ag = g["agency_rows"].median()
        idx = g.index[
            (g["incident_rows"] < 0.2 * med_inc)
            | (g["agency_rows"] < 0.2 * med_ag)
            | (g["size_mb"] < 1.0)
        ]
        df.loc[idx, "flag_suspicious"] = True

    print(df.to_string(index=False))

    bad = df[df["flag_suspicious"]]
    if not bad.empty:
        print("\nSuspicious files:")
        for _, r in bad.iterrows():
            print(f"- {r['file']} (size_mb={r['size_mb']}, incidents={r['incident_rows']}, agencies={r['agency_rows']})")


if __name__ == "__main__":
    main()
