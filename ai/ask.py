"""
Natural-language query layer over the MEPS star schema.

Ask a question in plain English; Groq (an LLM) writes a Snowflake SQL query
against the star schema, we validate it is read-only, run it, and print the
result.

Usage:
    python ai/ask.py "How many mental-health prescriptions by sex?"
    python ai/ask.py "Weighted mental-health fills per year"
"""
import os
import re
import sys

from dotenv import load_dotenv
import snowflake.connector
from groq import Groq

load_dotenv()

SCHEMA_CONTEXT = """
You write SQL for Snowflake. There are two tables in MEPS_PIPELINE.ANALYTICS,
a star schema built from the U.S. MEPS survey (2017-2021).

DIM_PERSON (one row per person per survey year):
  PERSON_YEAR_ID   text, primary key
  DUPERSID         text, person id
  SOURCE_YEAR      int, survey year (2017-2021)
  SEX              text, 'Male' or 'Female'
  RACE_ETHNICITY   text, e.g. 'White, non-Hispanic'
  AGE              int
  AGE_GROUP        text, '0-17','18-34','35-49','50-64','65+'
  POVERTY_CATEGORY int
  CENSUS_REGION    int
  INSURANCE_COVERAGE int
  PERSON_WEIGHT    float, survey weight for national estimates

FCT_PRESCRIPTIONS (one row per prescription-fill event):
  PERSON_YEAR_ID      text, foreign key to DIM_PERSON
  SOURCE_YEAR         int
  DRUG_NAME           text, generic drug name
  THERAPEUTIC_CLASS_1 int
  IS_MENTAL_HEALTH    boolean, true for psychotherapeutic drugs
  DAYS_SUPPLY         int
  QUANTITY            float
  TOTAL_EXPENDITURE   float
  PERSON_WEIGHT       float

Guidance:
- Join the tables on PERSON_YEAR_ID.
- Mental-health prescriptions: WHERE IS_MENTAL_HEALTH = TRUE.
- Raw counts use COUNT(*); national estimates use SUM(PERSON_WEIGHT).
"""

SYSTEM_PROMPT = SCHEMA_CONTEXT + """
Rules:
- Return ONLY one SQL SELECT query. No prose, no explanation, no markdown fences.
- Read-only: use only SELECT / WITH. Never INSERT, UPDATE, DELETE, DROP,
  CREATE, ALTER, MERGE, TRUNCATE, GRANT or REVOKE.
- Fully qualify tables as MEPS_PIPELINE.ANALYTICS.<table>.
"""

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|create|alter|merge|truncate|grant|revoke)\b",
    re.IGNORECASE,
)


def generate_sql(question: str) -> str:
    client = Groq(api_key=os.getenv("LLM_API_KEY"))
    resp = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
    )
    sql = resp.choices[0].message.content.strip()
    fenced = re.search(r"```(?:sql)?\s*(.*?)```", sql, re.S | re.I)
    if fenced:
        sql = fenced.group(1)
    return sql.strip().rstrip(";").strip()


def is_safe(sql: str) -> bool:
    low = sql.lower().lstrip()
    if not (low.startswith("select") or low.startswith("with")):
        return False
    if FORBIDDEN.search(sql):
        return False
    if ";" in sql:  # single statement only (trailing ; already stripped)
        return False
    return True


def run_sql(sql: str):
    conn = snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        role=os.getenv("SNOWFLAKE_ROLE") or None,
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
    )
    try:
        cur = conn.cursor()
        cur.execute(sql)
        cols = [c[0] for c in cur.description]
        rows = cur.fetchall()
        return cols, rows
    finally:
        cur.close()
        conn.close()


def main():
    if len(sys.argv) < 2:
        print('Usage: python ai/ask.py "your question"')
        sys.exit(1)
    question = " ".join(sys.argv[1:])
    print(f"Q: {question}\n")

    sql = generate_sql(question)
    print("Generated SQL:\n" + sql + "\n")

    if not is_safe(sql):
        print("REFUSED: the generated query is not a safe read-only SELECT.")
        sys.exit(1)

    cols, rows = run_sql(sql)
    print(" | ".join(cols))
    print("-" * 50)
    for r in rows[:50]:
        print(" | ".join("" if v is None else str(v) for v in r))
    if len(rows) > 50:
        print(f"... ({len(rows):,} rows total)")


if __name__ == "__main__":
    main()