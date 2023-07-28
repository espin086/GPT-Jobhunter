from airflow.models import Variable
import logging
import requests
import json
import os
from google.cloud import storage
import time

RAPID_API_KEY = os.getenv("RAPID_API_KEY") or Variable.get("RAPID_API_KEY")
BUCKET_NAME = os.getenv("GCP_BUCKET_JOBHUNTER") or Variable.get("GCP_BUCKET_JOBHUNTER")
GCS_DIRECTORY = "raw-json-files-jobs/"

logging.basicConfig(level=logging.INFO)


def search_linkedin_jobs(search_term, location, page=1):
    """
    This function takes in a search term, location, and an optional page number as input and uses them to make a request to the LinkedIn jobs API.
    The API returns a JSON object containing job search results that match the search term and location provided.
    The function also sets up logging to log the request and any errors that may occur.

    Args:
    - search_term (str): The job title or position you want to search for.
    - location (str): The location you want to search for jobs in.
    - page (int, optional): The page number of the search results you want to retrieve. Default is 1.

    Returns:
    - json: A JSON object containing the search results without the array.

    Raises:
    - Exception: If an exception is encountered during the API request, it is logged as an error.
    """

    url = "https://linkedin-jobs-search.p.rapidapi.com/"
    payload = {"search_terms": search_term, "location": location, "page": str(page)}
    headers = {
        "content-type": "application/json",
        "X-RapidAPI-Key": RAPID_API_KEY,
        "X-RapidAPI-Host": "linkedin-jobs-search.p.rapidapi.com",
    }

    logging.debug(
        "Making request to LinkedIn jobs API with search term: {}, location: {}".format(
            search_term, location
        )
    )

    try:
        response = requests.request("POST", url, json=payload, headers=headers)
        json_object = json.loads(response.text)
        if "results" in json_object:
            return json_object["results"]
        return json_object

    except Exception as e:
        logging.error("Encountered exception: {}".format(e))


def save_to_cloud_storage(data, filename_prefix):
    """
    This function saves each element in the provided data array as an individual JSON file in Cloud Storage.

    Args:
    - data: The data array to be saved.
    - filename_prefix: The prefix for the filenames of the JSON files to be saved in Cloud Storage.
    """
    client = storage.Client()
    bucket = client.get_bucket(BUCKET_NAME)

    required_keys = ["job_url"]  # Add any other required keys

    for index, element in enumerate(data):
        if all(key in element for key in required_keys):
            filename = f"{GCS_DIRECTORY}{filename_prefix}_{index}.json"
            blob = bucket.blob(filename)
            blob.upload_from_string(
                json.dumps(element), content_type="application/json"
            )
            logging.info(f"Data saved to Cloud Storage: gs://{BUCKET_NAME}/{filename}")
        else:
            logging.warning(
                f"Skipping data element {index} due to missing keys: {required_keys}"
            )


def main(search_term, location, page):
    """
    main() is a function that performs a job search on LinkedIn using the search_linkedin_jobs() function.
    It also saves the resulting JSON data to Cloud Storage.

    Args:
    - search_term (str): The job title or keyword to search for.
    - location (str): The location to search for the job.
    - page (int, optional): The page number of the search results. Default is 1.

    Returns:
    - json: The JSON object returned by the LinkedIn jobs API.
    """
    results = search_linkedin_jobs(
        search_term=search_term, location=location, page=page
    )
    timestamp = str(int(time.time()))
    filename = f"job_search_{timestamp}.json"
    save_to_cloud_storage(results, filename)
    return results


if __name__ == "__main__":
    results = main(search_term="data scientist", location="San Francisco", page=1)
    print(results)
