"""
Snowflake connection test for the MEPS medication pipeline.
Reads credentials from .env, confirms the connection works, and creates
the target database + schema if they do not exist yet.
Run from the project root:  python load/test_connection.py
"""
import os
import sys

from dotenv import load_dotenv
import snowflake.connector

load_dotenv()  # reads .env from the current working directory

required = [
    "SNOWFLAKE_ACCOUNT",
    "SNOWFLAKE_USER",
    "SNOWFLAKE_PASSWORD",
    "SNOWFLAKE_WAREHOUSE",
    "SNOWFLAKE_DATABASE",
    "SNOWFLAKE_SCHEMA",
]
missing = [name for name in required if not os.getenv(name)]
if missing:
    print("Missing values in .env: " + ", ".join(missing))
    sys.exit(1)

account = os.getenv("SNOWFLAKE_ACCOUNT")
database = os.getenv("SNOWFLAKE_DATABASE")
schema = os.getenv("SNOWFLAKE_SCHEMA")

print(f"Connecting to Snowflake account: {account} ...")

try:
    conn = snowflake.connector.connect(
        account=account,
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        role=os.getenv("SNOWFLAKE_ROLE") or None,
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
    )
except Exception as e:
    print("CONNECTION FAILED:")
    print(e)
    sys.exit(1)

try:
    cur = conn.cursor()
    cur.execute(
        "SELECT CURRENT_VERSION(), CURRENT_ACCOUNT(), "
        "CURRENT_USER(), CURRENT_WAREHOUSE()"
    )
    version, acct, user, warehouse = cur.fetchone()
    print("Connected.")
    print(f"  Snowflake version: {version}")
    print(f"  Account:           {acct}")
    print(f"  User:              {user}")
    print(f"  Warehouse:         {warehouse}")

    if not warehouse:
        print("  WARNING: no active warehouse. Check SNOWFLAKE_WAREHOUSE in .env.")

    # Infrastructure as code: create the landing DB + schema, idempotently.
    cur.execute(f"CREATE DATABASE IF NOT EXISTS {database}")
    cur.execute(f"CREATE SCHEMA IF NOT EXISTS {database}.{schema}")
    print(f"  Database/schema ready: {database}.{schema}")

    print("\nSUCCESS - Snowflake is set up and reachable.")
finally:
    cur.close()
    conn.close()