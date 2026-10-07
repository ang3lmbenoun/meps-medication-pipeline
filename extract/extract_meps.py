"""
MEPS Prescribed Medicines extractor -- multi-year.

Downloads a year's Prescribed Medicines file, selects the columns we need,
normalizes year-stamped names (RXXP21X -> RXXP_X, PERWT21F -> PERWT_F) to a
stable schema, validates the documented row count, tags the year, and lands
it as raw CSV.

Usage:  python extract/extract_meps.py 2019
"""
import sys, zipfile
from pathlib import Path
import pandas as pd
import requests

PMED_FILES = {
    2017: {"puf": "h197a", "expected_rows": 310487},
    2018: {"puf": "h206a", "expected_rows": 319666},
    2019: {"puf": "h213a", "expected_rows": 293125},
    2020: {"puf": "h220a", "expected_rows": 279755},
    2021: {"puf": "h229a", "expected_rows": 303394},
}
STABLE = ["DUPERSID", "RXDRGNAM", "TC1", "RXDAYSUP", "RXQUANTY"]
YEAR_STAMPED = {"RXXP{yy}X": "RXXP_X", "PERWT{yy}F": "PERWT_F"}
OUTPUT_ORDER = ["DUPERSID","RXDRGNAM","TC1","RXDAYSUP","RXQUANTY","RXXP_X","PERWT_F"]
RAW_DIR = Path("data/raw")


def extract_year(year: int) -> Path:
    if year not in PMED_FILES:
        raise ValueError(f"No config for year {year}. Known: {list(PMED_FILES)}")
    cfg = PMED_FILES[year]; yy = str(year)[2:]
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
    out = RAW_DIR / f"pmed_{year}.csv"
    df.to_csv(out, index=False)
    print(f"[{year}] Wrote {out} ({out.stat().st_size/1_000_000:.1f} MB)")
    return out


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python extract/extract_meps.py <year>"); sys.exit(1)
    extract_year(int(sys.argv[1]))