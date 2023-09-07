import datetime
import json
import logging
import os
import pprint
import requests
import time

from dotenv import load_dotenv
import app.config as config
from tqdm import tqdm

# Get the API key from the environment variable
RAPID_API_KEY = os.environ.get("RAPID_API_KEY")

# Load the .env file
load_dotenv("../.env")

# Initialize pretty printer and logging
pp = pprint.PrettyPrinter(indent=4)
logging.basicConfig(
    level=config.LOGGING_LEVEL, format="%(asctime)s - %(levelname)s - %(message)s"
)


# Get the API URL from the config file
JOB_SEARCH_URL = config.JOB_SEARCH_URL


def search_linkedin_jobs(search_term, location, page):
    """
    This function takes in a search term, location and an optional page number as input and uses them to make a request to the LinkedIn jobs API. The API returns a json object containing job search results that match the search term and location provided. The function also sets up logging to log the request and any errors that may occur.

    Args:
    search_term (str): The job title or position you want to search for.
    location (str): The location you want to search for jobs in.
    page (int, optional): The page number of the search results you want to retrieve. Default is 1.

    Returns:
    json: A json object containing the search results.

    Raises:
    Exception: If an exception is encountered during the API request, it is logged as an error.
    """

    url = JOB_SEARCH_URL
    payload = {"search_terms": search_term, "location": location, "page": page}
    headers = {
        "content-type": "application/json",
        "X-RapidAPI-Key": RAPID_API_KEY,
        "X-RapidAPI-Host": config.JOB_SEARCH_X_RAPIDAPI_HOST,
    }

    logging.debug(
        "Making request to LinkedIn jobs API with search term: {}, location: {}".format(
            search_term, location
        )
    )

    try:
        response = requests.request("POST", url, json=payload, headers=headers)
        json_object = json.loads(response.text)
        return json_object

    except Exception as e:
        logging.error("Encountered exception: {}".format(e))


def save_raw_data(data, source):
    """
    Saves a dictionary to a JSON file locally in the ../data/raw directory.
    """
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
        # Note: You might want to add a unique identifier for each job to the file name
        file_path = os.path.join("temp", "data", "raw", f"{source}-{timestamp}.json")

        with open(file_path, "w") as f:
            json.dump(data, f)

        logging.info("Saved job successfully.")
        logging.debug("Saved data to %s", file_path)

    except Exception as e:
        logging.error("An error occurred while saving data: %s", str(e))


def get_all_jobs(search_term, location, pages):
    all_jobs = []
    for page in range(0, pages):
        try:
            time.sleep(0.5)
            jobs = search_linkedin_jobs(
                search_term=search_term, location=location, page=page
            )
            if jobs:
                all_jobs.extend(jobs)  # change this line to extend instead of append

                logging.debug(f"Appended {len(jobs)} jobs for page {page}")
                for job in jobs:
                    save_raw_data(
                        job, source="linkedinjobs"
                    )  # save each job as it's found
            else:
                logging.warning("No jobs found for page %d", page)

        except Exception as e:
            logging.error(
                "An error occurred while fetching jobs for page %d: %s", page, str(e)
            )

    return all_jobs


def save_jobs(search_term, location, pages):
    try:
        jobs = get_all_jobs(search_term=search_term, location=location, pages=pages)
        if jobs:
            logging.info(
                f"Found {len(jobs)} jobs. Jobs saved."
            )  # No need to save again here, already saved in get_all_jobs
        else:
            logging.warning("No jobs found.")

    except Exception as e:
        logging.error("An error occurred while saving jobs: %s", str(e))


def extract():
    try:
        positions = config.POSITIONS
        locations = config.LOCATIONS

        logging.info(
            "Starting extraction process for positions: %s, locations: %s",
            positions,
            locations,
        )

        for position in tqdm(positions):
            for location in locations:
                save_jobs(search_term=position, location=location, pages=config.PAGES)

        logging.info("Extraction process completed.")

    except Exception as e:
        logging.error("An error occurred in the extract function: %s", str(e))


if __name__ == "__main__":
    logging.info("Application started.")
    extract()
    logging.info("Application finished.")
