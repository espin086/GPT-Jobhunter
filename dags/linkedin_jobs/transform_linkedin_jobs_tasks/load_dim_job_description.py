import logging
from google.cloud import storage
from google.cloud import bigquery
import json
import random
from google.api_core.exceptions import Conflict

# Configure logging settings
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    handlers=[logging.StreamHandler()],
)


def check_if_table_exists(client, project_id, dataset_id, table_id):
    try:
        client.get_table(f"{project_id}.{dataset_id}.{table_id}")
        return True
    except Exception as e:
        return False


def create_table(client, dataset_id, table_id):
    table_ref = client.dataset(dataset_id).table(table_id)
    schema = [
        bigquery.SchemaField("linkedin_job_url_cleaned", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("description", "STRING", mode="REQUIRED"),
    ]

    # Check if the table already exists
    if not check_if_table_exists(client, table_ref.project, dataset_id, table_id):
        table = bigquery.Table(table_ref, schema=schema)
        try:
            table = client.create_table(table)  # Create the table
            logging.info(f"Table {table_ref.path} created.")
        except google.api_core.exceptions.Conflict:
            # If the table exists, update the schema instead
            existing_table = client.get_table(table_ref)
            if existing_table.schema != schema:
                existing_table.schema = schema
                client.update_table(existing_table, ["schema"])
                logging.info(f"Schema updated for table {table_ref.path}.")
        except Exception as e:
            logging.error(f"Error creating/updating table {table_ref.path}: {e}")
    else:
        logging.info(f"Table {table_ref.path} already exists.")


def check_if_record_exists(client, project_id, dataset_id, table_id, linkedin_url):
    query = f"""
        SELECT COUNT(*) as count
        FROM `{project_id}.{dataset_id}.{table_id}`
        WHERE linkedin_job_url_cleaned = '{linkedin_url}'
    """
    result = client.query(query).result()
    for row in result:
        return row["count"] > 0
    return False


def upload_single_to_bigquery(
    client, project_id, dataset_id, table_id, linkedin_url, description
):
    schema = [
        bigquery.SchemaField("linkedin_job_url_cleaned", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("description", "STRING", mode="REQUIRED"),
    ]

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
    )

    table_ref = client.dataset(dataset_id).table(table_id)
    table = client.get_table(table_ref)

    if table is None:
        # If the table does not exist, create it
        logging.info(f"Creating BigQuery table: {project_id}.{dataset_id}.{table_id}")
        new_table = bigquery.Table(table_ref, schema=schema)
        table = client.create_table(new_table)
        logging.info(f"Table {table_ref.path} created.")
    else:
        schema_changed = table.schema != schema
        if schema_changed:
            # If the schema has changed, create a new table with the updated schema
            new_table_id = f"{table_id}_new"
            new_table_ref = client.dataset(dataset_id).table(new_table_id)

            # Delete the new table if it exists
            if check_if_table_exists(client, project_id, dataset_id, new_table_id):
                client.delete_table(new_table_ref)

            new_schema = [field for field in table.schema]
            for i, field in enumerate(new_schema):
                if field.name == "description":
                    new_schema[i] = bigquery.SchemaField(
                        field.name, field.field_type, mode="REQUIRED"
                    )
            new_table = bigquery.Table(new_table_ref, schema=new_schema)
            client.create_table(new_table)
            table_ref = new_table_ref

    row = {
        "linkedin_job_url_cleaned": linkedin_url,
        "description": description,
    }

    job = client.load_table_from_json([row], table_ref, job_config=job_config)
    job.result()  # Waits for the job to complete.

    if schema_changed:
        # If a new table was created, copy data to the original table and delete the new table
        logging.info("Copying data to the original table.")
        copy_job_config = bigquery.CopyJobConfig()
        copy_job = client.copy_table(
            table_ref,
            client.dataset(dataset_id).table(table_id),
            job_config=copy_job_config,
        )
        copy_job.result()

        logging.info("Deleting the new table.")
        client.delete_table(new_table_ref)

    logging.info(f"Data for URL '{linkedin_url}' uploaded to BigQuery successfully.")


def upload_to_bigquery(client, project_id, dataset_id, table_id, data):
    schema = [
        bigquery.SchemaField("linkedin_job_url_cleaned", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("description", "STRING", mode="REQUIRED"),
    ]

    try:
        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
        )

        table_ref = client.dataset(dataset_id).table(table_id)
        table = client.get_table(table_ref)

        if table is None:
            # If the table does not exist, create it
            logging.info(
                f"Creating BigQuery table: {project_id}.{dataset_id}.{table_id}"
            )
            new_table = bigquery.Table(table_ref, schema=schema)
            table = client.create_table(new_table)
            logging.info(f"Table {table_ref.path} created.")
        else:
            schema_changed = table.schema != schema
            if schema_changed:
                # If the schema has changed, update the table schema
                table.schema = schema
                client.update_table(table, ["schema"])
                logging.info(f"Schema updated for table {table_ref.path}.")

        job = client.load_table_from_json(data, table_ref, job_config=job_config)
        job.result()  # Waits for the job to complete.

        logging.info("Data uploaded to BigQuery successfully.")
    except Exception as e:
        logging.error(f"Error in upload_to_bigquery: {e}")


def main():
    try:
        # Initialize Cloud Storage and BigQuery clients
        storage_client = storage.Client()
        bigquery_client = bigquery.Client()

        # Replace these with your actual values
        bucket_name = "jobhunter"
        folder_name = "raw-json-job-descriptions/"
        project_id = "ai-solutions-lab-randd"
        dataset_id = "jobhunter"
        table_id = "dim_job_descriptions"

        # Check if the table exists in BigQuery
        table_ref = bigquery_client.dataset(dataset_id).table(table_id)
        table = bigquery_client.get_table(table_ref)

        if table is None:
            # If the table does not exist, create it
            logging.info(
                f"Creating BigQuery table: {project_id}.{dataset_id}.{table_id}"
            )
            schema = [
                bigquery.SchemaField(
                    "linkedin_job_url_cleaned", "STRING", mode="REQUIRED"
                ),
                bigquery.SchemaField("description", "STRING", mode="REQUIRED"),
            ]
            table = bigquery.Table(table_ref, schema=schema)
            bigquery_client.create_table(table)

        # List all blobs (JSON files) in the Cloud Storage bucket
        bucket = storage_client.bucket(bucket_name)
        blobs = list(bucket.list_blobs(prefix=folder_name))
        # to test with a smaller sample
        blobs = random.sample(blobs, 3)

        if not blobs:
            logging.warning("No JSON files found in the Cloud Storage bucket.")
            return

        # Upload each JSON file to BigQuery one by one
        for blob in blobs:
            # Download the JSON data from Cloud Storage
            json_data = blob.download_as_text()
            logging.info(f"Downloading blob: {blob.name}")

            # Skip processing if JSON data is empty
            if not json_data.strip():
                logging.warning(
                    f"JSON data is empty for blob: {blob.name}. Skipping this file."
                )
                continue

            try:
                job_description_dict = json.loads(json_data)
                for linkedin_url, description in job_description_dict.items():
                    # Check if the record already exists in BigQuery
                    if not check_if_record_exists(
                        bigquery_client, project_id, dataset_id, table_id, linkedin_url
                    ):
                        # Upload the data to BigQuery for this JSON file
                        upload_single_to_bigquery(
                            bigquery_client,
                            project_id,
                            dataset_id,
                            table_id,
                            linkedin_url,
                            description,
                        )
            except json.JSONDecodeError as e:
                logging.warning(
                    f"Invalid JSON data in {blob.name}. Skipping this file."
                )

    except Exception as e:
        logging.error(f"Error in main: {e}")


if __name__ == "__main__":
    main()
