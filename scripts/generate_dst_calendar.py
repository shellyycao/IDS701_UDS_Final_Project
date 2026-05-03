from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd


def nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> date:
    d = date(year, month, 1)
    days_to_weekday = (weekday - d.weekday()) % 7
    d = d + timedelta(days=days_to_weekday)
    d = d + timedelta(weeks=n - 1)
    return d


def build_dst_table(start_year: int, end_year: int) -> pd.DataFrame:
    rows = []
    for y in range(start_year, end_year + 1):
      # US DST rule (since 2007): starts second Sunday in March, ends first Sunday in November.
      start = nth_weekday_of_month(y, 3, 6, 2)
      end = nth_weekday_of_month(y, 11, 6, 1)
      rows.append(
          {
              "year": y,
              "dst_start_local_date": start.isoformat(),
              "dst_end_local_date": end.isoformat(),
          }
      )
    return pd.DataFrame(rows)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out_dir = root / "data" / "raw" / "dst"
    out_dir.mkdir(parents=True, exist_ok=True)

    df = build_dst_table(2021, 2026)
    out_file = out_dir / "dst_calendar_2021_2026.csv"
    df.to_csv(out_file, index=False)
    print(f"Wrote: {out_file}")


if __name__ == "__main__":
    main()