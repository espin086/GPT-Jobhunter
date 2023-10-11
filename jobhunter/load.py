import json
import logging
import os
import pprint
import sqlite3
import sys

import config

pp = pprint.PrettyPrinter(indent=4)
logging.basicConfig(
    level=config.LOGGING_LEVEL, format="%(asctime)s - %(levelname)s - %(message)s"
)


def load_json_files(directory):
    logging.info(f"Loading JSON files from {directory}")
    json_list = []
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            filepath = os.path.join(directory, filename)
            try:
                with open(filepath) as f:
                    json_obj = json.load(f)
                    json_list.append(json_obj)
                logging.info(f"Successfully loaded {filename}")
            except Exception as e:
                logging.error(f"Failed to load {filename}: {e}")
    return json_list


def create_db_if_not_there():
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
            f"Successfully created or ensured the table {config.TABLE_JOBS} exists."
        )
    except Exception as e:
        logging.error(f"Failed to create table: {e}")
    finally:
        conn.close()


def add_primary_key(json_list):
    logging.info("Adding primary keys to JSON data.")
    for item in json_list:
        try:
            company = item.get("company", "")
            title = item.get("title", "")
            primary_key = f"{company} - {title}"
            item["primary_key"] = primary_key
        except AttributeError as e:
            logging.error(
                f"AttributeError {e} occurred while processing {item}. Skipping item."
            )
    return json_list


def check_and_upload_to_db(json_list):
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
                logging.warning(f"{primary_key} already in database, skipping...")
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
                logging.info(f"UPLOADED: {primary_key} uploaded to database")
        except KeyError as e:
            logging.error(f"Skipping item due to missing key: {e}")
        except Exception as e:
            logging.error(f"Skipping item due to error: {e}")

    conn.close()


def load():
    logging.info("Main loading function initiated.")
    data = load_json_files(directory="temp/data/processed")
    data = add_primary_key(json_list=data)
    create_db_if_not_there()
    check_and_upload_to_db(json_list=data)


if __name__ == "__main__":
    logging.info("Jobhunter application started.")
    load()
    logging.info("Jobhunter application finished.")
