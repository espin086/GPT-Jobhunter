"""
This module contains the functions used to extract data from the LinkedIn jobs API.
"""

import logging
import os
import pprint
import time

import config
from dotenv import load_dotenv
from FileHandler import FileHandler
from search_linkedin_jobs import search_linkedin_jobs
from tqdm import tqdm

# change current director to location of this file
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(THIS_DIR)

# Load the .env file
load_dotenv("../../.env")


# Get the API key from the environment variable
RAPID_API_KEY = os.environ.get("RAPID_API_KEY")


file_handler = FileHandler(
    raw_path="temp/data/raw", processed_path="temp/data/processed"
)


# Initialize pretty printer and logging
pp = pprint.PrettyPrinter(indent=4)
logging.basicConfig(
    level=config.LOGGING_LEVEL, format="%(asctime)s - %(levelname)s - %(message)s"
)


# Get the API URL from the config file
JOB_SEARCH_URL = config.JOB_SEARCH_URL


def get_all_jobs(search_term, location, pages):
    """
    This function takes in a search term, location and an optional page and
    uses them to make a request to the LinkedIn jobs API. The API returns a
    json object containing job search results that match the search term and
    location provided. The function also sets up logging to log the request
    and any errors that may occur.
    """
    all_jobs = []
    for page in range(0, pages):
        try:
            time.sleep(0.5)
            jobs = search_linkedin_jobs(
                search_term=search_term, location=location, page=page
            )
            if jobs:
                all_jobs.extend(jobs)  # change this line to extend instead of append

                logging.debug("Appended %d jobs for page %d", len(jobs), page)
                for job in jobs:
                    file_handler.save_data(
                        data=job,
                        source="linkedinjobs",
                        sink=file_handler.processed_path,
                    )

            else:
                logging.warning("No jobs found for page %d", page)

        except Exception as e:
            logging.error(
                "An error occurred while fetching jobs for page %d: %s", page, str(e)
            )

    return all_jobs


def extract():
    """
    This function extracts data from the LinkedIn jobs API and saves it locally.
    """
    file_handler.create_data_folders_if_not_exists()
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
                get_all_jobs(
                    search_term=position, location=location, pages=config.PAGES
                )

        logging.info("Extraction process completed.")

    except Exception as e:
        logging.error("An error occurred in the extract function: %s", str(e))


if __name__ == "__main__":
    logging.info("Application started.")
    extract()
    logging.info("Application finished.")
