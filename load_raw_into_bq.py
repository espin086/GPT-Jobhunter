from google.cloud import bigquery
from google.cloud.bigquery import SourceFormat
from google.cloud import storage
import re
import time


def load_raw_into_bq():
    # Create a BigQuery client
    client = bigquery.Client()

    # Set the project ID and dataset ID
    project_id = "ai-solutions-lab-randd"
    dataset_id = "jobhunter"

    # Set the table ID
    table_id = "raw_listings"

    # Define the path to the directory containing the JSON files in Google Cloud Storage
    gcs_bucket_name = "jobhunter"
    gcs_directory = "raw-json-files-jobs"

    # Create the dataset if it doesn't exist
    dataset_ref = client.dataset(dataset_id, project=project_id)
    try:
        dataset = client.create_dataset(dataset_ref)
        print("Created dataset:", dataset_id)
    except:
        print("Dataset already exists:", dataset_id)

    # Define the table reference
    table_ref = dataset_ref.table(table_id)

    # Configure the table schema
    schema = [
        bigquery.SchemaField(
            "filename", "STRING", mode="NULLABLE"
        ),  # Add a new column to store the filename
        bigquery.SchemaField("job_url", "STRING"),
        bigquery.SchemaField("linkedin_job_url_cleaned", "STRING"),
        bigquery.SchemaField("company_name", "STRING"),
        bigquery.SchemaField("company_url", "STRING"),
        bigquery.SchemaField("linkedin_company_url_cleaned", "STRING"),
        bigquery.SchemaField("job_title", "STRING"),
        bigquery.SchemaField("job_location", "STRING"),
        bigquery.SchemaField("posted_date", "DATE"),
        bigquery.SchemaField("normalized_company_name", "STRING"),
    ]

    # Create the table if it doesn't exist
    table = bigquery.Table(table_ref, schema=schema)
    try:
        table = client.create_table(table)
        print("Created table:", table_id)
    except:
        print("Table already exists:", table_id)

    # Get the list of files in the Cloud Storage directory
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(gcs_bucket_name)
    blobs = bucket.list_blobs(prefix=gcs_directory)

    # Check if the table is empty
    table_empty = True
    for row in client.list_rows(table_ref, max_results=1):
        table_empty = False
        break

    if table_empty:
        new_files = [
            f"gs://{gcs_bucket_name}/{blob.name}"
            for blob in blobs
            if blob.name.startswith(gcs_directory)
        ]
        print("Loading all files into the table...")
    else:
        # Filter out files that have already been loaded
        loaded_files = set()

        query = f"""
            SELECT DISTINCT filename
            FROM `{project_id}.{dataset_id}.{table_id}`
        """

        loaded_files_query_job = client.query(query)
        for row in loaded_files_query_job:
            loaded_files.add(row["filename"])

        new_files = [
            f"gs://{gcs_bucket_name}/{blob.name}"
            for blob in blobs
            if blob.name.startswith(gcs_directory) and blob.name not in loaded_files
        ]

        if not new_files:
            print("No new files to load.")
        else:
            print("Loading new files into the table...")

    # Configure the job options
    job_config = bigquery.LoadJobConfig(
        autodetect=True,  # Automatically detect the schema from the JSON files
        source_format=SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,  # Append the data to the table
    )

    if new_files:
        print("New files to load:", new_files)
        load_job = client.load_table_from_uri(
            new_files, table_ref, job_config=job_config
        )

        # Wait for the load job to complete
        load_job.result()

        # Check the load job status
        if load_job.state == "DONE":
            print("Data loaded successfully.")
        else:
            print("Error loading data.")

    else:
        print("No new files to load.")


if __name__ == "__main__":
    load_raw_into_bq()
