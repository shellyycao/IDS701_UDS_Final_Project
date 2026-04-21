import importlib
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

SCRIPTS = [
    ("compute_agency_coverage",    "Agency reporting coverage"),
    ("compute_seasonality",        "Monthly and day-of-week seasonality"),
    ("compute_hourly_distribution","Hourly crime distribution + DST/standard split"),
    ("compute_dst_transition_window", "DST transition fatigue window"),
    ("compute_parallel_trends",    "Raw parallel trends (state-month crime rates)"),
    ("compute_utah_feasibility",   "Utah feasibility (ACS distributions + Mann-Whitney)"),
]


def main():
    errors = []
    for module_name, description in SCRIPTS:
        print(f"\n{'='*60}")
        print(f"Running: {description}")
        print(f"  ({module_name}.py)")
        print("="*60)
        t0 = time.time()
        try:
            mod = importlib.import_module(module_name)
            mod.main()
            print(f"  Done in {time.time() - t0:.1f}s")
        except Exception as exc:
            print(f"  ERROR: {exc}")
            errors.append((module_name, str(exc)))

    print(f"\n{'='*60}")
    if errors:
        print(f"Finished with {len(errors)} error(s):")
        for name, msg in errors:
            print(f"  {name}: {msg}")
    else:
        print("All EDA scripts completed successfully.")
    print("Outputs in: data/processed/analysis/")


if __name__ == "__main__":
    main()
