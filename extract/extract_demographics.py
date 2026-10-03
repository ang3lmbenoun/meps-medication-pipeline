"""
MEPS Full Year Consolidated (demographics) extractor.

Downloads a year's Full Year Consolidated public-use file from AHRQ, keeps
only the demographic / linking / survey-design columns we need, validates
the documented person count, tags the year, and lands it as raw CSV.

The consolidated file has ~1,488 columns; we deliberately select the dozen
we need rather than land all of them -- the rest are irrelevant to this
project and would bloat the raw layer.

Usage (from the project root):
    python extract/extract_demographics.py 2021
"""
import sys
import zipfile
from pathlib import Path

import pandas as pd
import requests

DEMOG_FILES = {
    2021: {
        "puf": "h233",
        "url": "https://meps.ahrq.gov/data_files/pufs/h233/h233dta.zip",
        "dta_file": "h233.dta",
        "expected_rows": 28336,
    },
}

# Columns we keep from the consolidated file.
KEEP_COLUMNS = {
    2021: [
        "DUPERSID",   # person id -- join key to the prescription file
        "PANEL",      # survey panel
        "AGELAST",    # age last eligible (0-85)
        "AGE21X",     # age as of 12/31/2021
        "SEX",        # 1=male, 2=female
        "RACETHX",    # race/ethnicity (1-5)
        "HISPANX",    # hispanic ethnicity
        "POVCAT21",   # poverty category (1-5)
        "REGION21",   # census region
        "INSCOV21",   # insurance coverage
        "PERWT21F",   # person weight -- required for national estimates
        "VARSTR",     # variance stratum (survey design)
        "VARPSU",     # variance PSU (survey design)
    ],
}

RAW_DIR = Path("data/raw")


def extract_year(year: int) -> Path:
    if year not in DEMOG_FILES:
        raise ValueError(f"No config for year {year}. Known years: {list(DEMOG_FILES)}")

    cfg = DEMOG_FILES[year]
    keep = KEEP_COLUMNS[year]
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    zip_path = RAW_DIR / f"{cfg['puf']}.zip"
    print(f"[{year}] Downloading {cfg['url']}")
    resp = requests.get(cfg["url"], timeout=180)
    resp.raise_for_status()
    zip_path.write_bytes(resp.content)
    print(f"[{year}] Downloaded {zip_path.stat().st_size / 1_000_000:.1f} MB")

    print(f"[{year}] Unzipping {cfg['dta_file']}")
    with zipfile.ZipFile(zip_path) as zf:
        zf.extract(cfg["dta_file"], RAW_DIR)
    dta_path = RAW_DIR / cfg["dta_file"]

    print(f"[{year}] Reading Stata file and selecting {len(keep)} columns")
    df = pd.read_stata(dta_path, convert_categoricals=False, columns=keep)
    print(f"[{year}] Parsed shape: {df.shape[0]:,} rows x {df.shape[1]} columns")

    if df.shape[0] != cfg["expected_rows"]:
        raise ValueError(
            f"[{year}] Row count {df.shape[0]:,} != expected {cfg['expected_rows']:,}"
        )
    print(f"[{year}] Row count matches documented {cfg['expected_rows']:,}")

    df["source_year"] = year

    out_path = RAW_DIR / f"demographics_{year}.csv"
    df.to_csv(out_path, index=False)
    print(f"[{year}] Wrote raw CSV: {out_path} ({out_path.stat().st_size / 1_000_000:.2f} MB)")
    return out_path


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python extract/extract_demographics.py <year>")
        sys.exit(1)
    extract_year(int(sys.argv[1]))