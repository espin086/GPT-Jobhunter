import datetime
import json
import logging
import os
import pprint
import time

from jobhunter.app import config
from jobhunter.app.utilities.search_linkedin_jobs import main as search_linkedin_jobs
from tqdm import tqdm

# Initialize pretty printer and logging
pp = pprint.PrettyPrinter(indent=4)
logging.basicConfig(
    level=config.LOGGING_LEVEL, format="%(asctime)s - %(levelname)s - %(message)s"
)


def save_raw_data(data, source):
    """
    Saves a list of dictionaries to a JSON file locally in the ../data/raw directory.
    """
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
        file_path = os.path.join("temp/", "data", "raw", f"{source}-{timestamp}.json")

        with open(file_path, "w") as f:
            json.dump(data, f)

        logging.info("Saved data successfully.")
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
                all_jobs.append(jobs)
                logging.debug("Appended jobs for page %d", page)
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
            logging.info("Jobs found. Saving...")
            for job in jobs:
                for item in job:
                    save_raw_data(item, source="linkedinjobs")
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
