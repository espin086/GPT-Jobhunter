from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator

from extract_linkedin_jobs_tasks.get_jobs_linkedin import main
from extract_linkedin_jobs_tasks.load_raw_into_bq import load_raw_into_bq
from extract_linkedin_jobs_tasks.validate_json import main as validate_and_delete_files

import os

dag_file_path = os.path.dirname(os.path.abspath(__file__))


default_args = {
    "owner": "airflow",
    "start_date": "2023-07-27",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "schedule_interval": "0 0 * * 5",
}

job_locations = {
    "Principal Machine Learning Engineer": "remote",
    "Senior Data Scientist": "remote",
    "AI ML Architect": "remote",
    "Lead Data Scientist": "remote",
    "Senior Machine Learning Engineer": "remote",
    "Senior Data Engineer": "remote",
    "Senior Data Analyst": "remote",
    "Data Engineer": "remote",
    "Data Scientist": "remote",
    "Machine Learning Engineer": "remote",
    "Data Analyst": "remote",
    # Add more job titles and their corresponding locations here
}

dag = DAG(
    "extract_linked_jobs", default_args=default_args, schedule_interval="0 0 * * 5"
)

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


validate_json = PythonOperator(
    task_id="validate_json",
    python_callable=validate_and_delete_files,
    dag=dag,
)

load_bigquery = PythonOperator(
    task_id="load_into_bigquery",
    python_callable=load_raw_into_bq,
    dag=dag,
)

# Set the dependencies between tasks
start_task >> get_jobs_tasks >> validate_json >> load_bigquery
