import os
import re
import csv
import requests
from pathlib import Path
from urllib.parse import urlparse

URL_FILE = "data/raw/crime/nibrs_download_urls.txt"
OUT_DIR = "data/raw/crime/nibrs_state_year"
LOG_FILE = "data/raw/crime/nibrs_download_log.csv"
CHUNK_SIZE = 1024 * 1024  # 1 MB
TIMEOUT = 600


def extract_state_year(url):
    path = urlparse(url).path
    fname = os.path.basename(path)
    m = re.search(r'([A-Z]{2})[-_](\d{4})\.zip', fname, re.IGNORECASE)
    if m:
        return m.group(1).upper(), m.group(2)
    return None, None


def download_one(url, out_dir):
    state, year = extract_state_year(url)
    if not state:
        return {
            "url": url, "output_file": "", "status_code": None,
            "ok": False, "message": "Could not parse state/year from URL",
        }

    out_path = Path(out_dir) / f"{state}-{year}.zip"

    try:
        resp = requests.get(url, stream=True, timeout=TIMEOUT)
        status_code = resp.status_code

        if status_code == 403 and "X-Amz-Expires=" in url:
            print(
                f"WARNING: Presigned URL expired for {state}-{year}. "
                "Get a fresh link from the CDE downloads page."
            )
            return {
                "url": url, "output_file": str(out_path), "status_code": 403,
                "ok": False, "message": "Presigned URL expired (HTTP 403)",
            }

        resp.raise_for_status()

        with open(out_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                f.write(chunk)

        print(f"  OK  {state}-{year}.zip")
        return {
            "url": url, "output_file": str(out_path), "status_code": status_code,
            "ok": True, "message": "OK",
        }

    except Exception as exc:
        print(f"  ERR {url}: {exc}")
        return {
            "url": url, "output_file": str(out_path), "status_code": None,
            "ok": False, "message": str(exc),
        }


def main():
    Path(OUT_DIR).mkdir(parents=True, exist_ok=True)

    with open(URL_FILE) as f:
        urls = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]

    print(f"Downloading {len(urls)} file(s)...")
    results = [download_one(url, OUT_DIR) for url in urls]

    with open(LOG_FILE, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["url", "output_file", "status_code", "ok", "message"]
        )
        writer.writeheader()
        writer.writerows(results)

    ok = sum(1 for r in results if r["ok"])
    print(f"\n{ok}/{len(results)} succeeded. Log: {LOG_FILE}")


if __name__ == "__main__":
    main()
