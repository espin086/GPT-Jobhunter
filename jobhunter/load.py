"""
This module contains the load function that loads the JSON files from the 
processed folder and uploads them to the database.
"""

import json
import logging
import os
import pprint

from jobhunter import config
from jobhunter.FileHandler import FileHandler
from jobhunter.SQLiteHandler import check_and_upload_to_db, create_db_if_not_there

pp = pprint.PrettyPrinter(indent=4)
logging.basicConfig(
    level=config.LOGGING_LEVEL, format="%(asctime)s - %(levelname)s - %(message)s"
)

file_handler = FileHandler(
    raw_path="temp/data/raw", processed_path="temp/data/processed"
)


def add_primary_key(json_list):
    """
    This function adds a primary key to each JSON object in the list.

    """
    logging.info("Adding primary keys to JSON data.")
    for item in json_list:
        try:
            company = item.get("company", "")
            title = item.get("title", "")
            primary_key = f"{company} - {title}"
            item["primary_key"] = primary_key
        except AttributeError as e:
            logging.error(
                "AttributeError %s occurred while processing %s. Skipping item.",
                e,
                item,
            )
    return json_list


def load():
    """
    This function loads the JSON files from the processed folder and uploads them to the database.
    """
    logging.info("Main loading function initiated.")
    data = file_handler.load_json_files(directory="temp/data/processed")
    data = add_primary_key(json_list=data)
    create_db_if_not_there()
    check_and_upload_to_db(json_list=data)


if __name__ == "__main__":
    logging.info("Jobhunter application started.")
    load()
    logging.info("Jobhunter application finished.")
