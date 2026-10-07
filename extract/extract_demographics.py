"""
MEPS Full Year Consolidated (demographics) extractor -- multi-year.

Downloads a year's file, selects the demographic/design columns we need,
normalizes the year-stamped names (e.g. PERWT21F -> PERWT_F) to a stable
schema so every year stacks identically, validates the documented person
count, tags the year, and lands it as raw CSV.

Usage:  python extract/extract_demographics.py 2019
"""
import sys, zipfile
from pathlib import Path
import pandas as pd
import requests

DEMOG_FILES = {
    2017: {"puf": "h201", "expected_rows": 31880},
    2018: {"puf": "h209", "expected_rows": 30461},
    2019: {"puf": "h216", "expected_rows": 28512},
    2020: {"puf": "h224", "expected_rows": 27805},
    2021: {"puf": "h233", "expected_rows": 28336},
}
STABLE = ["DUPERSID", "PANEL", "AGELAST", "SEX", "RACETHX", "HISPANX", "VARSTR", "VARPSU"]
YEAR_STAMPED = {"AGE{yy}X": "AGE_X", "POVCAT{yy}": "POVCAT", "REGION{yy}": "REGION",
                "INSCOV{yy}": "INSCOV", "PERWT{yy}F": "PERWT_F"}
OUTPUT_ORDER = ["DUPERSID","PANEL","AGELAST","AGE_X","SEX","RACETHX","HISPANX",
                "POVCAT","REGION","INSCOV","PERWT_F","VARSTR","VARPSU"]
RAW_DIR = Path("data/raw")


def extract_year(year: int) -> Path:
    if year not in DEMOG_FILES:
        raise ValueError(f"No config for year {year}. Known: {list(DEMOG_FILES)}")
    cfg = DEMOG_FILES[year]; yy = str(year)[2:]
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    url = f"https://meps.ahrq.gov/data_files/pufs/{cfg['puf']}/{cfg['puf']}dta.zip"
    zip_path = RAW_DIR / f"{cfg['puf']}.zip"
    print(f"[{year}] Downloading {url}")
    r = requests.get(url, timeout=180); r.raise_for_status(); zip_path.write_bytes(r.content)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extract(f"{cfg['puf']}.dta", RAW_DIR)
    dta = RAW_DIR / f"{cfg['puf']}.dta"

    rename = {c: c for c in STABLE}
    for tpl, out in YEAR_STAMPED.items():
        rename[tpl.format(yy=yy)] = out
    print(f"[{year}] Reading and selecting {len(rename)} columns")
    df = pd.read_stata(dta, convert_categoricals=False, columns=list(rename))
    if df.shape[0] != cfg["expected_rows"]:
        raise ValueError(f"[{year}] rows {df.shape[0]:,} != expected {cfg['expected_rows']:,}")
    print(f"[{year}] Row count matches documented {cfg['expected_rows']:,}")
    df = df.rename(columns=rename)[OUTPUT_ORDER]
    df["source_year"] = year
    out = RAW_DIR / f"demographics_{year}.csv"
    df.to_csv(out, index=False)
    print(f"[{year}] Wrote {out} ({out.stat().st_size/1_000_000:.2f} MB)")
    return out


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python extract/extract_demographics.py <year>"); sys.exit(1)
    extract_year(int(sys.argv[1]))