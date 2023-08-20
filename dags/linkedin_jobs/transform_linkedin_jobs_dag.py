from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonVirtualenvOperator
from datetime import timedelta
from transform_linkedin_jobs_tasks.create_dim_date import main as create_dim_date_main
from transform_linkedin_jobs_tasks.create_dim_job_title import (
    main as create_dim_job_title_main,
)
from transform_linkedin_jobs_tasks.create_dim_job_description import (
    main as create_dim_job_description_main,
)
from transform_linkedin_jobs_tasks.load_dim_job_description import (
    main as task_load_dim_job_description,
)

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": "2023-07-28",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# Define the DAG
dag = DAG(
    "transform_linkedin_jobs",
    default_args=default_args,
    description="DAG to create dim and fact tables from LinkedIn jobs data",
    schedule_interval="0 1 * * 5",  # Run daily at 1 AM UTC
    catchup=False,  # Disable catchup to avoid backfilling
)

# Dummy operator to start the DAG
start_operator = DummyOperator(task_id="start", dag=dag)


# Task to execute the first Python script (create_temp_table, create_dim_date_table, delete_temp_table)
task_create_dim_date_table = PythonOperator(
    task_id="create_dim_date_table",
    python_callable=create_dim_date_main,
    dag=dag,
)

# Task to execute the second Python script (main)
task_create_dim_job_title = PythonOperator(
    task_id="create_dim_job_title",
    python_callable=create_dim_job_title_main,
    dag=dag,
)

# Task to execute the second Python script (main)

task_create_dim_job_description = PythonOperator(
    task_id="task_create_dim_job_description",
    python_callable=create_dim_job_description_main,
    dag=dag,
)

task_load_dim_job_description = PythonOperator(
    task_id="task_load_dim_job_description",
    python_callable=task_load_dim_job_description,
    dag=dag,
)


# Dummy operator to end the DAG
end_operator = DummyOperator(task_id="end", dag=dag)

# Set task dependencies
(
    start_operator
    >> [
        task_create_dim_date_table,
        task_create_dim_job_title,
    ]
    >> end_operator
)
(
    start_operator
    >> task_create_dim_job_description
    >> task_load_dim_job_description
    >> end_operator
)
