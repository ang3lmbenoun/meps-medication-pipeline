"""
MEPS Prescribed Medicines extractor.

Downloads a given year's Prescribed Medicines public-use file from AHRQ,
parses it, validates the documented row count, tags the source year, and
lands it as raw CSV in data/raw/.

Usage (from the project root):
    python extract/extract_meps.py 2021
"""
import sys
import zipfile
from pathlib import Path

import pandas as pd
import requests

# Each year maps to its MEPS Prescribed Medicines public-use file.
# Adding a year later is just another entry here.
PMED_FILES = {
    2021: {
        "puf": "h229a",
        "url": "https://meps.ahrq.gov/data_files/pufs/h229a/h229adta.zip",
        "dta_file": "h229a.dta",
        "expected_rows": 303394,
    },
}

RAW_DIR = Path("data/raw")


def extract_year(year: int) -> Path:
    if year not in PMED_FILES:
        raise ValueError(f"No config for year {year}. Known years: {list(PMED_FILES)}")

    cfg = PMED_FILES[year]
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    zip_path = RAW_DIR / f"{cfg['puf']}.zip"
    print(f"[{year}] Downloading {cfg['url']}")
    resp = requests.get(cfg["url"], timeout=180)
    resp.raise_for_status()
    zip_path.write_bytes(resp.content)
    print(f"[{year}] Downloaded {zip_path.stat().st_size / 1_000_000:.1f} MB -> {zip_path}")

    print(f"[{year}] Unzipping {cfg['dta_file']}")
    with zipfile.ZipFile(zip_path) as zf:
        zf.extract(cfg["dta_file"], RAW_DIR)
    dta_path = RAW_DIR / cfg["dta_file"]

    print(f"[{year}] Reading Stata file (this takes a few seconds)")
    df = pd.read_stata(dta_path, convert_categoricals=False)
    print(f"[{year}] Parsed shape: {df.shape[0]:,} rows x {df.shape[1]} columns")

    # Validation gate: the row count must match AHRQ's documented figure.
    if df.shape[0] != cfg["expected_rows"]:
        raise ValueError(
            f"[{year}] Row count {df.shape[0]:,} != expected {cfg['expected_rows']:,}"
        )
    print(f"[{year}] Row count matches documented {cfg['expected_rows']:,}")

    # Tag the source year so stacked years stay distinguishable downstream.
    df["source_year"] = year

    out_path = RAW_DIR / f"pmed_{year}.csv"
    df.to_csv(out_path, index=False)
    print(f"[{year}] Wrote raw CSV: {out_path} ({out_path.stat().st_size / 1_000_000:.1f} MB)")
    return out_path


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python extract/extract_meps.py <year>")
        sys.exit(1)
    extract_year(int(sys.argv[1]))