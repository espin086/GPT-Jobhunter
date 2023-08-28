import json
import sqlite3
import os


from jobhunter.app import config


def load_json_files(directory):
    """
    Load all JSON files in a directory into a list of JSON objects.

    Args:
    directory (str): path to directory containing JSON files

    Returns:
    list: a list of JSON objects
    """
    json_list = []
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            filepath = os.path.join(directory, filename)
            with open(filepath) as f:
                json_obj = json.load(f)
                json_list.append(json_obj)
    return json_list


def create_db_if_not_there():
    # Create a connection to the database
    conn = sqlite3.connect(f"../../database/{config.DATABASE}")

    # Create a cursor object to execute SQL commands
    c = conn.cursor()

    # Create a table
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

    # Commit the changes and close the connection
    conn.commit()
    conn.close()


def add_primary_key(json_list):
    for item in json_list:
        try:
            company = item.get("company", "")
            title = item.get("title", "")
            primary_key = f"{company} - {title}"
            item["primary_key"] = primary_key
        except AttributeError as e:
            print(f"ERROR: {e} occurred while processing {item}. Skipping item.")

    return json_list


def check_and_upload_to_db(json_list):
    conn = sqlite3.connect(f"../../database/{config.DATABASE}")
    c = conn.cursor()

    for item in json_list:
        try:
            primary_key = item["primary_key"]
            c.execute(
                f"SELECT * FROM {config.TABLE_JOBS} WHERE primary_key=?", (primary_key,)
            )
            result = c.fetchone()
            if result:
                print(f"{primary_key} already in database, skipping...")
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
                print(f"UPLOADED: {primary_key} uploaded to database")
        except KeyError as e:
            print(f"SKIPPED: Skipping item due to missing key: {e}")
        except Exception as e:
            print(f"SKIPPED: Skipping item due to error: {e}")

    # -----------------main-------------------


def load():
    data = load_json_files(directory="../temp/data/processed")
    data = add_primary_key(json_list=data)
    create_db_if_not_there()
    check_and_upload_to_db(json_list=data)


if __name__ == "__main__":
    load()
