"""Download NIBRS state-year ZIP files from a list of CDE URLs.

Why this script exists:
- Historical community scripts hardcode older S3 keys that now return 404.
- The CDE downloads page still provides valid links, but they can change over time.
- This script lets you paste current links once and bulk-download reliably.

Input file format (one URL per line):
- Blank lines and lines starting with '#' are ignored.
- Example:
  https://.../AL-2021.zip
  https://.../TX-2022.zip

Outputs:
- ZIP files under data/raw/crime/nibrs_state_year/
- Download log CSV: data/raw/crime/nibrs_download_log.csv
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote, urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_URL_FILE = ROOT / "data" / "raw" / "crime" / "nibrs_download_urls.txt"
OUT_DIR = ROOT / "data" / "raw" / "crime" / "nibrs_state_year"
LOG_FILE = ROOT / "data" / "raw" / "crime" / "nibrs_download_log.csv"

STATE_YEAR_RE = re.compile(r"([A-Z]{2})[-_](\d{4})\.zip$", re.IGNORECASE)


@dataclass
class DownloadResult:
    url: str
    output_file: str
    status_code: int
    ok: bool
    message: str


def load_urls(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(
            f"URL file not found: {path}. Create it with one URL per line."
        )

    urls: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(line)

    if not urls:
        raise ValueError(f"No URLs found in {path}. Add at least one URL.")

    return urls


def derive_filename_from_url(url: str) -> str:
    parsed = urlparse(url)
    tail = Path(parsed.path).name
    tail = unquote(tail)
    if tail.lower().endswith(".zip"):
        return tail
    return "downloaded_file.zip"


def canonical_filename(filename: str) -> str:
    match = STATE_YEAR_RE.search(filename)
    if not match:
        return filename
    state, year = match.group(1).upper(), match.group(2)
    return f"{state}-{year}.zip"


def download_one(url: str, out_dir: Path, timeout: int = 120) -> DownloadResult:
    out_dir.mkdir(parents=True, exist_ok=True)

    filename = canonical_filename(derive_filename_from_url(url))
    out_path = out_dir / filename

    try:
        with requests.get(url, stream=True, timeout=timeout) as resp:
            if resp.status_code != 200:
                message = f"HTTP {resp.status_code}"
                if resp.status_code == 403 and "X-Amz-Expires=" in url:
                    message += " (signed URL likely expired; refresh link from CDE downloads page)"
                return DownloadResult(
                    url=url,
                    output_file=str(out_path),
                    status_code=resp.status_code,
                    ok=False,
                    message=message,
                )

            with out_path.open("wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)

            return DownloadResult(
                url=url,
                output_file=str(out_path),
                status_code=resp.status_code,
                ok=True,
                message="downloaded",
            )
    except Exception as exc:  # noqa: BLE001
        return DownloadResult(
            url=url,
            output_file=str(out_path),
            status_code=-1,
            ok=False,
            message=str(exc),
        )


def write_log(results: Iterable[DownloadResult], log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["url", "output_file", "status_code", "ok", "message"],
        )
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "url": result.url,
                    "output_file": result.output_file,
                    "status_code": result.status_code,
                    "ok": result.ok,
                    "message": result.message,
                }
            )


def main() -> None:
    urls = load_urls(DEFAULT_URL_FILE)

    print(f"Loaded {len(urls)} URL(s) from {DEFAULT_URL_FILE}")
    print(f"Downloading to: {OUT_DIR}")

    results: list[DownloadResult] = []
    for idx, url in enumerate(urls, start=1):
        print(f"[{idx}/{len(urls)}] {url}")
        result = download_one(url=url, out_dir=OUT_DIR)
        results.append(result)
        print(f"  -> {result.message}")

    write_log(results, LOG_FILE)

    success_count = sum(1 for r in results if r.ok)
    fail_count = len(results) - success_count

    print("\nDone.")
    print(f"Successful downloads: {success_count}")
    print(f"Failed downloads: {fail_count}")
    print(f"Log file: {LOG_FILE}")


if __name__ == "__main__":
    main()
