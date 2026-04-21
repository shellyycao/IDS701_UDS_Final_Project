import csv
from datetime import date, timedelta

OUT_FILE = "data/raw/dst/dst_calendar_2021_2026.csv"


def nth_weekday(year, month, weekday, n):
    """Return the date of the nth occurrence (1-based) of weekday in month/year."""
    first = date(year, month, 1)
    delta = (weekday - first.weekday()) % 7
    first_occurrence = first + timedelta(days=delta)
    return first_occurrence + timedelta(weeks=n - 1)


def dst_start(year):
    return nth_weekday(year, 3, 6, 2)  # 2nd Sunday in March


def dst_end(year):
    return nth_weekday(year, 11, 6, 1)  # 1st Sunday in November


def main():
    rows = []
    for year in range(2021, 2027):
        rows.append({
            "year": year,
            "dst_start_local_date": dst_start(year).isoformat(),
            "dst_end_local_date": dst_end(year).isoformat(),
        })

    with open(OUT_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["year", "dst_start_local_date", "dst_end_local_date"])
        writer.writeheader()
        writer.writerows(rows)

    for r in rows:
        print(f"{r['year']}: start={r['dst_start_local_date']}  end={r['dst_end_local_date']}")
    print(f"\nSaved to {OUT_FILE}")


if __name__ == "__main__":
    main()
