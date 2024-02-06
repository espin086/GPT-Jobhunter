"""
This module contains the functions used to extract data from the jobs API.
"""
import concurrent.futures
import logging
import os
import pprint
import time

from dotenv import load_dotenv
from tqdm import tqdm

from jobhunter import config
from jobhunter.FileHandler import FileHandler
from jobhunter.search_linkedin_jobs import search_linkedin_jobs

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

def get_all_jobs(search_term, location, pages):
    all_jobs = []
    


def extract(search_term, location, pages):
    """
    This function extracts data from the jobs API and saves it locally.
    """
    file_handler.create_data_folders_if_not_exists()
    try:
        positions = config.POSITIONS
        locations = config.REMOTE_JOBS_ONLY

        logging.info(
            "Starting extraction process for positions: %s",
            positions,
        )
        for position in tqdm(positions):
            get_all_jobs(
                search_term=position, location=location, pages=config.PAGES
            )

        logging.info("Extraction process completed.")

    except Exception as e:
        logging.error("An error occurred in the extract function: %s", str(e))



