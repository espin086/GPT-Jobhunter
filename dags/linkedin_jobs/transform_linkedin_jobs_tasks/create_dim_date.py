from google.cloud import bigquery


def create_temp_table():
    # Initialize the BigQuery client
    client = bigquery.Client()

    # Define the SQL query to create the temporary table
    query = """
    DECLARE start_date DATE;
    SET start_date = '2023-01-01';

    CREATE OR REPLACE TABLE `ai-solutions-lab-randd.jobhunter.temp_table`
    AS
    SELECT
      date,
      EXTRACT(DAYOFWEEK FROM date) AS day_of_week,
      EXTRACT(MONTH FROM date) AS month,
      EXTRACT(YEAR FROM date) AS year,
      EXTRACT(QUARTER FROM date) AS quarter,
      EXTRACT(DAY FROM date) AS day_of_month,
      EXTRACT(WEEK FROM date) AS week_of_year,
      EXTRACT(DAYOFYEAR FROM date) AS day_of_year,
      CASE WHEN EXTRACT(DAYOFWEEK FROM date) IN (1, 7) THEN TRUE ELSE FALSE END AS is_weekend,
      CASE WHEN EXTRACT(DAYOFWEEK FROM date) BETWEEN 2 AND 6 THEN TRUE ELSE FALSE END AS is_weekday,
      CASE WHEN EXTRACT(DAY FROM date) = EXTRACT(DAY FROM start_date) THEN TRUE ELSE FALSE END AS is_first_day_of_month,
      CASE WHEN EXTRACT(DAY FROM date) = EXTRACT(DAY FROM LAST_DAY(date)) THEN TRUE ELSE FALSE END AS is_last_day_of_month
    FROM
      UNNEST(GENERATE_DATE_ARRAY(start_date, CURRENT_DATE())) AS date;
    """

    # Start the query job to create the temporary table
    query_job = client.query(query)
    query_job.result()  # Wait for the job to complete

    print("Temporary table 'temp_table' created.")


def create_dim_date_table():
    # Initialize the BigQuery client
    client = bigquery.Client()

    # Define the SQL query to create the final dim_date table
    query = """
    CREATE OR REPLACE TABLE `ai-solutions-lab-randd.jobhunter.dim_date`
    AS
    SELECT *
    FROM `ai-solutions-lab-randd.jobhunter.temp_table`;
    """

    # Start the query job to create the dim_date table
    query_job = client.query(query)
    query_job.result()  # Wait for the job to complete

    print("Final table 'dim_date' created with the query results.")


def delete_temp_table():
    # Initialize the BigQuery client
    client = bigquery.Client()

    # Define the SQL query to delete the temporary table
    query = """
    DROP TABLE IF EXISTS `ai-solutions-lab-randd.jobhunter.temp_table`;
    """

    # Start the query job to delete the temporary table
    query_job = client.query(query)
    query_job.result()  # Wait for the job to complete

    print("Temporary table 'temp_table' deleted.")


def main():
    create_temp_table()
    create_dim_date_table()
    delete_temp_table()


if __name__ == "__main__":
    main()
