import datetime
import json
import logging
import os
import pprint
import time


from jobhunter.app import config
from jobhunter.app.utilities.search_linkedin_jobs import main as search_linkedin_jobs
from tqdm import tqdm


pp = pprint.PrettyPrinter(indent=4)
logging.basicConfig(level=config.LOGGING_LEVEL)


def save_raw_data(data, source):
    """
    Saves a list of dictionaries to a JSON file locally in the ../data/raw directory.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
    file_path = os.path.join("../temp/", "data", "raw", f"{source}-{timestamp}.json")
    with open(file_path, "w") as f:
        json.dump(data, f)
    logging.debug("Saved data to %s", file_path)
    return None


def get_all_jobs(search_term, location, pages):
    all_jobs = []
    for page in range(0, pages):
        time.sleep(0.1)
        jobs = search_linkedin_jobs(
            search_term=search_term, location=location, page=page
        )
        all_jobs.append(jobs)
    return all_jobs


def save_jobs(search_term, location, pages):
    jobs = get_all_jobs(search_term=search_term, location=location, pages=pages)
    for job in jobs:
        for item in job:
            save_raw_data(item, source="linkedinjobs")


def extract():
    positions = config.POSITIONS
    locations = config.LOCATIONS
    for position in tqdm(positions):
        for location in locations:
            save_jobs(search_term=position, location=location, pages=config.PAGES)


if __name__ == "__main__":
    extract()
