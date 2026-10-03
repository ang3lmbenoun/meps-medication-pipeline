"""
Load a raw MEPS CSV into Snowflake (RAW schema).

Builds an all-VARCHAR landing table from the CSV header, stages the file,
and COPYs it in. Raw landing keeps every column as text, faithful to the
source; typing and filtering happen later in dbt. Verifies the loaded row
count against the local file.

Usage (from the project root):
    python load/load_to_snowflake.py 2021
"""
import csv
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import snowflake.connector

load_dotenv()

RAW_DIR = Path("data/raw")


def load_year(year: int) -> None:
    csv_path = RAW_DIR / f"pmed_{year}.csv"
    if not csv_path.exists():
        print(f"File not found: {csv_path}. Run the extractor first.")
        sys.exit(1)

    table = f"PMED_{year}"

    # Read only the header to build the table definition.
    with open(csv_path, newline="", encoding="utf-8") as f:
        header = next(csv.reader(f))
    columns_ddl = ",\n    ".join(f'"{col.upper()}" VARCHAR' for col in header)

    # Count local data rows (excluding the header) for the verification gate.
    with open(csv_path, encoding="utf-8") as f:
        local_rows = sum(1 for _ in f) - 1

    database = os.getenv("SNOWFLAKE_DATABASE")
    schema = os.getenv("SNOWFLAKE_SCHEMA")

    conn = snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        role=os.getenv("SNOWFLAKE_ROLE") or None,
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=database,
        schema=schema,
    )
    cur = conn.cursor()
    try:
        print(f"Creating table {database}.{schema}.{table} ...")
        cur.execute(f'CREATE OR REPLACE TABLE "{table}" (\n    {columns_ddl}\n)')

        # CSV file format matching what pandas.to_csv wrote.
        cur.execute(
            """
            CREATE OR REPLACE FILE FORMAT meps_csv_format
                TYPE = CSV
                FIELD_OPTIONALLY_ENCLOSED_BY = '"'
                SKIP_HEADER = 1
                EMPTY_FIELD_AS_NULL = TRUE
            """
        )
        cur.execute("CREATE OR REPLACE STAGE meps_stage FILE_FORMAT = meps_csv_format")

        local_posix = csv_path.resolve().as_posix()
        print("Uploading file to the Snowflake stage (can take a minute) ...")
        cur.execute(f"PUT file://{local_posix} @meps_stage OVERWRITE = TRUE")

        print("Copying staged file into the table ...")
        cur.execute(f'COPY INTO "{table}" FROM @meps_stage')

        cur.execute(f'SELECT COUNT(*) FROM "{table}"')
        loaded = cur.fetchone()[0]
        print(f"Loaded rows in Snowflake: {loaded:,}")
        print(f"Local data rows:          {local_rows:,}")
        if loaded != local_rows:
            raise ValueError("Row count mismatch between local file and Snowflake!")
        print(f"\nSUCCESS - {database}.{schema}.{table} loaded and verified.")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python load/load_to_snowflake.py <year>")
        sys.exit(1)
    load_year(int(sys.argv[1]))