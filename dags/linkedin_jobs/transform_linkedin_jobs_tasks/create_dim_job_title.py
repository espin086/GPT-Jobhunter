from google.cloud import bigquery


def main():
    # Initialize the BigQuery client
    client = bigquery.Client()

    # Define the SQL query to create the intermediate table
    create_query = """
    CREATE OR REPLACE TABLE `ai-solutions-lab-randd.jobhunter.temp_dim_job_title`
    AS
    WITH job_title_counts AS (
      SELECT
        LOWER(job_title) AS job_title,
        COUNT(*) AS observations
      FROM
        `ai-solutions-lab-randd.jobhunter.raw_listings`
      GROUP BY
        job_title
    ),
    specialty_counts AS (
      SELECT
        job_title,
        observations,
        CASE
          WHEN job_title LIKE '%business intelligence%' THEN 'business intelligence'
          WHEN job_title LIKE '%data architect%' THEN 'data architect'
          WHEN job_title LIKE '%data engineer%' THEN 'data engineer'
          WHEN job_title LIKE '%machine learning%' THEN 'machine learning'
          WHEN job_title LIKE '%data analyst%' OR job_title LIKE '%analyst%' OR job_title LIKE '%data analytics%' OR job_title LIKE '%analytics%' THEN 'data analysis' 
          WHEN job_title LIKE '%data scientist%' OR job_title LIKE '%data science%' OR job_title LIKE '%scientist%' THEN 'data science'
          ELSE 'Other'
        END AS specialty
      FROM
        job_title_counts
    ),
    job_level AS (
      SELECT
        job_title,
        observations,
        specialty, 
        CASE 
          WHEN job_title LIKE "%vice president%" THEN 'vice president'
          WHEN job_title LIKE "%director%" THEN 'director'
          WHEN job_title LIKE "%manager%" THEN 'manager'
          WHEN job_title LIKE "%principal%" THEN 'principal'
          WHEN job_title LIKE "%lead%" THEN 'lead'
          WHEN job_title LIKE "%senior%" OR job_title LIKE '%sr%' THEN 'senior'
          WHEN job_title LIKE "%junior%" THEN 'junior'
          ELSE 'Other'
        END AS level
      FROM
        specialty_counts
      ORDER BY
        observations DESC
    )
    
    SELECT * FROM job_level
    """

    # Start the query job to create the intermediate table
    create_query_job = client.query(create_query)
    create_query_job.result()  # Wait for the job to complete

    print("Intermediate table 'temp_dim_job_title' created.")

    # Define the SQL query to replace the final dim_job_title table
    replace_query = """
    CREATE OR REPLACE TABLE `ai-solutions-lab-randd.jobhunter.dim_job_title`
    AS
    SELECT * FROM `ai-solutions-lab-randd.jobhunter.temp_dim_job_title`
    """

    # Start the query job to replace the final table
    replace_query_job = client.query(replace_query)
    replace_query_job.result()  # Wait for the job to complete

    print("Table 'dim_job_title' replaced with the new results.")

    # Clean up: Delete the intermediate table
    delete_query = """
    DROP TABLE IF EXISTS `ai-solutions-lab-randd.jobhunter.temp_dim_job_title`
    """

    # Start the query job to delete the intermediate table
    delete_query_job = client.query(delete_query)
    delete_query_job.result()  # Wait for the job to complete

    print("Intermediate table 'temp_dim_job_title' deleted.")


if __name__ == "__main__":
    main()
