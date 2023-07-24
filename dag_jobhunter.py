from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from airflow.providers.google.cloud.operators.bigquery import (
    BigQueryExecuteQueryOperator,
    BigQueryCreateEmptyTableOperator,
)
from tasks_jobhunter.get_jobs_linkedin import main
from tasks_jobhunter.load_raw_into_bq import load_raw_into_bq
from tasks_jobhunter.validate_json import main as validate_and_delete_files

import os

dag_file_path = os.path.dirname(os.path.abspath(__file__))
sql_file_path = os.path.join(
    dag_file_path, "tasks_jobhunter/deduplicate_raw_listings.sql"
)

default_args = {
    "owner": "airflow",
    "start_date": datetime.now(),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "schedule_interval": "0 0 * * *",
}

job_locations = {
    "Principal Machine Learning Engineer": "remote",
    "Senior Data Scientist": "remote",
    "AI ML Architect": "remote",
    "Lead Data Scientist": "remote",
    # Add more job titles and their corresponding locations here
}

dag = DAG("jobhunter", default_args=default_args, schedule_interval="0 0 * * *")

start_task = DummyOperator(task_id="start", dag=dag)

get_jobs_tasks = []

for job_title, location in job_locations.items():
    search_term = job_title.replace("_", " ")  # Convert job_title to search_term format

    for page in range(1, 4):  # Iterate through pages 1, 2, and 3

        def run_main(page_num):
            main(search_term, location, page_num)

        get_jobs = PythonOperator(
            task_id=f"get_jobs_{job_title.replace(' ', '_').lower()}_{location.replace(' ', '_').lower()}_page_{page}",
            python_callable=run_main,
            op_kwargs={"page_num": page},
            dag=dag,
        )

        get_jobs_tasks.append(get_jobs)
        start_task >> get_jobs

load_bigquery = PythonOperator(
    task_id="load_into_bigquery",
    python_callable=load_raw_into_bq,
    dag=dag,
)

validate_json = PythonOperator(
    task_id="validate_json",
    python_callable=validate_and_delete_files,
    dag=dag,
)


def execute_create_temp_table_query():
    create_temp_table_task = BigQueryCreateEmptyTableOperator(
        task_id="create_temp_table",
        dataset_id="jobhunter",
        table_id="raw_listings_deduplicated_temp",
        schema_fields=[
            # Define the schema of the temporary table here
            {"name": "posted_date", "type": "DATE"},
            {"name": "job_location", "type": "STRING"},
            {"name": "company_name", "type": "STRING"},
            {"name": "listing_url", "type": "STRING"},
            {"name": "company_url", "type": "STRING"},
            {"name": "job_title", "type": "STRING"},
        ],
        project_id="ai-solutions-lab-randd",
        location="US",
        dag=dag,
    )
    return create_temp_table_task


def delete_destination_table():
    sql_query = """
    -- Delete the destination table if it exists
    DELETE FROM `ai-solutions-lab-randd.jobhunter.raw_listings_deduplicated`
    WHERE TRUE
    """
    delete_destination_table_task = BigQueryExecuteQueryOperator(
        task_id="delete_destination_table",
        sql=sql_query,
        use_legacy_sql=False,  # Use standard SQL
        dag=dag,
    )
    return delete_destination_table_task


def insert_into_destination_table():
    sql_query = """
    -- Insert the data into the destination table
    INSERT INTO `ai-solutions-lab-randd.jobhunter.raw_listings_deduplicated`
    SELECT *
    FROM `ai-solutions-lab-randd.jobhunter.raw_listings_deduplicated_temp`
    """
    insert_into_destination_table_task = BigQueryExecuteQueryOperator(
        task_id="insert_into_destination_table",
        sql=sql_query,
        use_legacy_sql=False,  # Use standard SQL
        dag=dag,
    )
    return insert_into_destination_table_task


def cleanup_temp_table():
    sql_query = """
    -- Clean up the temporary table
    DROP TABLE `ai-solutions-lab-randd.jobhunter.raw_listings_deduplicated_temp`
    """
    cleanup_temp_table_task = BigQueryExecuteQueryOperator(
        task_id="cleanup_temp_table",
        sql=sql_query,
        use_legacy_sql=False,  # Use standard SQL
        dag=dag,
    )
    return cleanup_temp_table_task


create_temp_table_task = execute_create_temp_table_query()
delete_destination_table_task = delete_destination_table()
insert_into_destination_table_task = insert_into_destination_table()
cleanup_temp_table_task = cleanup_temp_table()

# Set the dependencies between tasks
start_task >> get_jobs_tasks >> validate_json >> load_bigquery >> create_temp_table_task
create_temp_table_task >> delete_destination_table_task
delete_destination_table_task >> insert_into_destination_table_task
insert_into_destination_table_task >> cleanup_temp_table_task
