from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 3, 8),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'linkedin_bot_jobhunter_pipeline',
    default_args=default_args,
    schedule=timedelta(days=1),
)

run_linkedin_bot_script = BashOperator(
    task_id="run_linkedin_bot_script",
    bash_command="python3 ../jobhunter/linkedin_bot.py 'director of data science' 'los angeles' 0 0",
    dag=dag,
)

run_database_script = BashOperator(
    task_id="run_database_script",
    bash_command="python3 ../jobhunter/utils/database.py",
    dag=dag,
)

run_clean_data_loader_script = BashOperator(
    task_id="run_clean_data_loader_script",
    bash_command="python3 ../jobhunter/utils/clean_data_loader.py",
    dag=dag,
)

#set up dependencies
run_linkedin_bot_script >> run_database_script >> run_clean_data_loader_script