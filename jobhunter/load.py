"""
This module contains the load function that loads the JSON files from the 
processed folder and uploads them to the database.
"""

import json
import logging
import os
import pprint
import sqlite3

from jobhunter import config
from jobhunter.FileHandler import FileHandler

pp = pprint.PrettyPrinter(indent=4)
logging.basicConfig(
    level=config.LOGGING_LEVEL, format="%(asctime)s - %(levelname)s - %(message)s"
)

file_handler = FileHandler(
    raw_path="temp/data/raw", processed_path="temp/data/processed"
)


def create_db_if_not_there():
    """This function creates the database if it doesn't exist."""
    logging.info("Checking and creating database if not present.")
    conn = sqlite3.connect(f"{config.DATABASE}")
    c = conn.cursor()

    try:
        c.execute(
            f"""CREATE TABLE IF NOT EXISTS {config.TABLE_JOBS}
                    (id INTEGER PRIMARY KEY,
                    primary_key TEXT,
                    date TEXT,
                    resume_similarity REAL,
                    title TEXT, 
                    company TEXT, 
                    salary_low REAL,
                    salary_high REAL,
                    location TEXT,
                    job_url TEXT,
                    company_url TEXT,
                    description TEXT
                    )"""
        )
        conn.commit()
        logging.info(
            "Successfully created or ensured the table %s exists.", config.TABLE_JOBS
        )
    except Exception as e:
        logging.error("Failed to create table: %s", e)
    finally:
        conn.close()


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


def check_and_upload_to_db(json_list):
    """
    This function checks if the primary key already exists in the database and if not,
    uploads the data to the database.

    """
    logging.info("Starting upload to database.")
    conn = sqlite3.connect(f"{config.DATABASE}")
    c = conn.cursor()

    for item in json_list:
        try:
            primary_key = item["primary_key"]
            c.execute(
                f"SELECT * FROM {config.TABLE_JOBS} WHERE primary_key=?", (primary_key,)
            )
            result = c.fetchone()
            if result:
                logging.warning("%s already in database, skipping...", primary_key)

            else:
                c.execute(
                    f"INSERT INTO {config.TABLE_JOBS} (primary_key, date, resume_similarity, title, company, salary_low, salary_high, location, job_url, company_url, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        primary_key,
                        item.get("date", ""),
                        item.get("resume_similarity", ""),
                        item.get("title", ""),
                        item.get("company", ""),
                        item.get("salary_low", ""),
                        item.get("salary_high", ""),
                        item.get("location", ""),
                        item.get("job_url", ""),
                        item.get("company_url", ""),
                        item.get("description", ""),
                    ),
                )
                conn.commit()
                logging.info("UPLOADED: %s uploaded to database", primary_key)
        except KeyError as e:
            logging.error("Skipping item due to missing key: %s", e)
        except Exception as e:
            logging.error("Skipping item due to error: %s", e)

    conn.close()


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
