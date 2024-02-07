import json
import logging
import sqlite3

from sklearn.metrics.pairwise import cosine_similarity

from jobhunter import config
from jobhunter.textAnalysis import generate_gpt_embedding


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
                    company_url TEXT,
                    company_type TEXT,
                    job_type TEXT,
                    job_is_remote TEXT,
                    job_offer_expiration_date TEXT,
                    salary_low REAL,
                    salary_high REAL,
                    salary_currency TEXT,
                    salary_period TEXT,
                    job_benfits TEXT,
                    city TEXT,
                    state TEXT,
                    country TEXT,
                    apply_options TEXT,
                    required_skills TEXT,
                    required_experience TEXT,
                    required_eduaction TEXT,                    
                    description TEXT,
                    highlights TEXT,
                    embeddings TEXT
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
                logging.info("Generating embeddings for %s", "primary_key")
                embeddings = generate_gpt_embedding(
                    item.get("description", "") + item.get("title", "")
                )
                logging.info("Embeddings generated for %s", "primary_key")
                c.execute(
                    f"INSERT INTO {config.TABLE_JOBS} (primary_key, date, resume_similarity, title, company, salary_low, salary_high, location, job_url, company_url, description, embeddings) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        primary_key,
                        item.get("date", ""),
                        item.get("resume_similarity", ""),
                        item.get("title", ""),
                        item.get("company", ""),
                        item.get("company_url", ""),
                        item.get("company_type", ""),
                        item.get("job_type", ""),
                        item.get("job_is_remote", ""),
                        item.get("job_offer_expiration_date", ""),
                        item.get("salary_low", ""),
                        item.get("salary_high", ""),
                        item.get("salary_currency", ""),
                        item.get("salary_period", ""),
                        item.get("job_benefits", ""),
                        item.get("city", ""),
                        item.get("state", ""),
                        item.get("country", ""),
                        item.get("apply_options", ""),
                        item.get("required_skills", ""),
                        item.get("required_experience", ""),
                        item.get("required_eduaction", ""),
                        item.get("description", ""),
                        item.get("highlights", ""),
                        str(embeddings),
                    ),
                )
                conn.commit()
                logging.info("UPLOADED: %s uploaded to database", primary_key)
        except KeyError as e:
            logging.error("Skipping item due to missing key: %s", e)
        except Exception as e:
            logging.error("Skipping item due to error: %s", e)

    conn.close()


def save_text_to_db(filename, text):
    conn = sqlite3.connect(f"{config.DATABASE}")
    cursor = conn.cursor()

    # Create the table with a primary key and filename
    try:
        cursor.execute(
            f"""
        CREATE TABLE IF NOT EXISTS {config.TABLE_RESUMES} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE,
            content TEXT
        )
        """
        )
    except Exception as e:
        logging.error("Failed to create table: %s", e)

    try:
        # Check if a record with the given filename already exists
        cursor.execute(
            f"SELECT id FROM {config.TABLE_RESUMES} WHERE filename = ?", (filename,)
        )
        record = cursor.fetchone()

        if record:
            # If a record exists, update it
            cursor.execute(
                f"UPDATE {config.TABLE_RESUMES} SET content = ? WHERE filename = ?",
                (text, filename),
            )
        else:
            # Otherwise, insert a new record
            cursor.execute(
                f"INSERT INTO {config.TABLE_RESUMES} (filename, content) VALUES (?, ?)",
                (filename, text),
            )
    except Exception as e:
        logging.error("Failed to insert or update record: %s", e)

    conn.commit()
    conn.close()


def fetch_resumes_from_db():
    conn = sqlite3.connect(f"{config.DATABASE}")
    cursor = conn.cursor()

    conn = sqlite3.connect(f"{config.DATABASE}")
    cursor = conn.cursor()

    # Create the table with a primary key and filename
    try:
        cursor.execute(
            f"""
        CREATE TABLE IF NOT EXISTS {config.TABLE_RESUMES} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE,
            content TEXT
        )
        """
        )
    except Exception as e:
        logging.error("Failed to create table: %s", e)

    cursor.execute(f"SELECT filename FROM {config.TABLE_RESUMES}")
    records = cursor.fetchall()

    conn.close()

    return [record[0] for record in records]


def get_resume_text(filename):
    """Fetches the text content of a resume from the database."""
    conn = sqlite3.connect(f"{config.DATABASE}")
    cursor = conn.cursor()

    cursor.execute(
        f"SELECT content FROM {config.TABLE_RESUMES} WHERE filename = ?", (filename,)
    )
    record = cursor.fetchone()
    logging.info("Resume text fetched from database")
    conn.close()

    return record[0] if record else None


def fetch_primary_keys_from_db() -> list:
    """Fetches the list of primary keys from the specified table in the database."""

    conn = sqlite3.connect(config.DATABASE)
    c = conn.cursor()

    # Fetch the primary keys from the table
    c.execute(f"SELECT primary_key FROM {config.TABLE_JOBS}")
    primary_keys = [row[0] for row in c.fetchall()]

    conn.close()
    return primary_keys


def update_similarity_in_db(filename):
    primary_keys = fetch_primary_keys_from_db()
    conn = sqlite3.connect(f"{config.DATABASE}")
    c = conn.cursor()
    resume_text = get_resume_text(filename)
    resume_embedding = generate_gpt_embedding(resume_text)
    for primary_key in primary_keys:
        try:
            c.execute(
                f"SELECT embeddings FROM {config.TABLE_JOBS} WHERE primary_key=?",
                (primary_key,),
            )
            res = c.fetchone()
            if res:
                embeddings = json.loads(res[0])
                similarity = cosine_similarity([embeddings], [resume_embedding])[0][0]
                c.execute(
                    f"UPDATE {config.TABLE_JOBS} SET resume_similarity = ? WHERE primary_key = ?",
                    (similarity, primary_key),
                )
                conn.commit()
                logging.info(
                    "UPDATED: Similarity updated for %s in database", primary_key
                )
        except Exception as e:
            logging.error("Error fetching embeddings from database: %s", e)

    conn.close()
