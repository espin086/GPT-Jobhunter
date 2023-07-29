from google.cloud import storage
import json
import os


def validate_and_delete_files(
    bucket_name, source_directory, destination_directory, required_key
):
    # Create a storage client
    client = storage.Client()

    # Get the bucket
    bucket = client.get_bucket(bucket_name)

    # List the files in the source directory
    blobs = bucket.list_blobs(prefix=source_directory)

    # Iterate over the files
    for blob in blobs:
        try:
            # Download the file to a local directory
            local_filename = f"/tmp/{os.path.basename(blob.name)}"
            blob.download_to_filename(local_filename)

            # Read the file as a JSON object
            with open(local_filename) as file:
                json_data = json.load(file)

            # Check if the required key is present in the JSON object
            if required_key not in json_data:
                # Move the file to the destination directory
                destination_blob_name = f"{destination_directory}/{blob.name}"
                bucket.rename_blob(blob, destination_blob_name)
                print(f"File '{blob.name}' moved to '{destination_blob_name}'")

                # Delete the local file
                os.remove(local_filename)
                print(f"File '{local_filename}' deleted from local storage")
            else:
                print(f"File '{blob.name}' has the required key")
        except json.JSONDecodeError as e:
            # Move the file to the destination directory
            destination_blob_name = f"{destination_directory}/{blob.name}"
            bucket.rename_blob(blob, destination_blob_name)
            print(
                f"File '{blob.name}' moved to '{destination_blob_name}' due to JSON decoding error: {e}"
            )


# Usage example


def main():
    bucket_name = "jobhunter"
    source_directory = "raw-json-files-jobs"
    destination_directory = "bad-schema-json-files"
    required_key = "job_url"

    validate_and_delete_files(
        bucket_name, source_directory, destination_directory, required_key
    )


if __name__ == "__main__":
    main()
