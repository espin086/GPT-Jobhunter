import concurrent.futures
import logging
import os
import pprint
import time

from dotenv import load_dotenv
from tqdm import tqdm

from jobhunter import config
from FileHandler import FileHandler
from search_jobs import search_jobs
import argparse
import logging
import argparse

# import config

# change current director to location of this file
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(THIS_DIR)

file_handler = FileHandler(
    raw_path=config.RAW_DATA_PATH, processed_path=config.PROCESSED_DATA_PATH
)

# Load the .env file
load_dotenv("../../.env")

# Get the API key from the environment variable
RAPID_API_KEY = os.environ.get("RAPID_API_KEY")

# Get the API URL from the config file
JOB_SEARCH_URL = config.JOB_SEARCH_URL

# Get the API URL from the config file
SELECTED_KEYS = config.SELECTED_KEYS


def get_all_jobs(search_term, pages):
    all_jobs = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for page in range(0, pages):
            futures.append(
                executor.submit(
                    search_jobs,
                    search_term=search_term,
                    page=page,
                )
            )
        for future in concurrent.futures.as_completed(futures):
            try:
                jobs = future.result()
                if jobs:
                    all_jobs.extend(jobs)
                    logging.debug("Appended %d jobs for page %d", len(jobs), page)
                    for job in all_jobs:
                        file_handler.save_data(
                            data=job,
                            source="jobs",
                            sink=file_handler.raw_path,
                        )
                else:
                    logging.warning("No jobs found for page %d", page)
            except Exception as e:
                logging.error(
                    "An error occurred while fetching jobs for page %d: %s",
                    page,
                    str(e),
                )
    print(len(all_jobs))
    return all_jobs


def extract(POSITIONS):
    """
    This function extracts data from the jobs API and saves it locally.
    """
    file_handler.create_data_folders_if_not_exists()
    try:
        positions = POSITIONS

        logging.info(
            "Starting extraction process for positions: %s",
            positions,
        )
        for position in tqdm(positions):
            get_all_jobs(
                search_term=position,
                pages=config.PAGES,
            )

        logging.info("Extraction process completed.")

    except Exception as e:
        logging.error("An error occurred in the extract function: %s", str(e))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Job Extraction")
    parser.add_argument(
        "positions",
        metavar="POSITIONS",
        type=str,
        nargs="+",
        help="List of positions to extract jobs for",
    )
    args = parser.parse_args()
    logging.info("Application started.")
    extract(args.positions)
    logging.info("Application finished.")
