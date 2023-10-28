import logging
import sqlite3

from jobhunter import config


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
