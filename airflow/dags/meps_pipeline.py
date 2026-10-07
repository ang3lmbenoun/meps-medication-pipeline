"""
MEPS pipeline DAG — runs the dbt transform + tests on a schedule.
Transforms the raw MEPS tables in Snowflake into the tested star schema.
"""
from airflow.decorators import dag
from airflow.providers.standard.operators.bash import BashOperator
import pendulum

# Call the dbt binary in its venv directly, and run from the project dir.
DBT_BIN = "/usr/local/airflow/dbt_venv/bin/dbt"
PROJECT_DIR = "/usr/local/airflow/include/meps_analytics"


@dag(
    schedule="@daily",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    tags=["meps", "dbt"],
)
def meps_pipeline():

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"cd {PROJECT_DIR} && {DBT_BIN} run --profiles-dir .",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {PROJECT_DIR} && {DBT_BIN} test --profiles-dir .",
    )

    dbt_run >> dbt_test


meps_pipeline()