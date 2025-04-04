import json
import logging
import sqlite3
import time

import streamlit as st
from sklearn.metrics.pairwise import cosine_similarity

from jobhunter.text_similarity import text_similarity
from jobhunter.textAnalysis import generate_gpt_embedding

logger = logging.getLogger(__name__)


def create_db_if_not_there():
    """Create the database if it doesn't exist."""
    logging.info("Checking and creating database if not present.")
    conn = sqlite3.connect("all_jobs.db")
    c = conn.cursor()

    try:
        c.execute(
            """CREATE TABLE IF NOT EXISTS jobs_new
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
                    job_apply_link TEXT,
                    job_offer_expiration_date TEXT,
                    salary_low REAL,
                    salary_high REAL,
                    salary_currency TEXT,
                    salary_period TEXT,
                    job_benefits TEXT,
                    city TEXT,
                    state TEXT,
                    country TEXT,
                    apply_options TEXT,
                    required_skills TEXT,
                    required_experience TEXT,
                    required_education TEXT,
                    description TEXT,
                    highlights TEXT,
                    embeddings TEXT
                    )"""
        )
        conn.commit()
        logging.info(
            "Successfully created or ensured the table jobs_new exists."
        )
    except Exception as e:
        logging.error("Failed to create table: %s", e)
    finally:
        conn.close()


def check_and_upload_to_db(json_list):
    """Check if the primary key exists in the database and upload data if not."""
    logging.info("Starting upload to database.")
    conn = sqlite3.connect("all_jobs.db")
    c = conn.cursor()
    
    jobs_added = 0
    jobs_skipped = 0
    embedding_failures = 0

    for item in json_list:
        try:
            primary_key = item["primary_key"]
            c.execute(
                "SELECT * FROM jobs_new WHERE primary_key=?",
                (primary_key,),
            )
            result = c.fetchone()
            if result:
                logging.warning("%s already in the database, skipping...", primary_key)
                jobs_skipped += 1
            else:
                # Try to generate embeddings with detailed logging and error handling
                try:
                    logging.info("Generating embeddings for %s", primary_key)
                    # Combine description and title for embedding
                    text_to_embed = item.get("description", "") + " " + item.get("title", "")
                    
                    # Truncate text if it's extremely long (to avoid potential token limits)
                    max_chars = 10000
                    if len(text_to_embed) > max_chars:
                        text_to_embed = text_to_embed[:max_chars]
                        logging.warning(f"Truncated job text for {primary_key} to {max_chars} characters")
                    
                    # Generate the embedding
                    embeddings = generate_gpt_embedding(text_to_embed)
                    
                    if not embeddings or all(x == 0 for x in embeddings):
                        logging.warning(f"Zero embeddings returned for job {primary_key}, this may affect similarity calculations")
                    else:
                        logging.info(f"Embeddings successfully generated for {primary_key} with length {len(embeddings)}")
                except Exception as embedding_error:
                    # If embedding fails, log the error but continue with a zero vector
                    logging.error(f"Error generating embeddings for {primary_key}: {embedding_error}")
                    embeddings = [0.0] * 1536  # Default embedding size for ada-002
                    embedding_failures += 1
                
                # Insert the job record with embeddings (or zeros if embedding failed)
                try:
                    c.execute(
                        "INSERT INTO jobs_new (primary_key, date, resume_similarity, title, company, company_url, company_type, job_type, job_is_remote,job_apply_link, job_offer_expiration_date, salary_low,  salary_high, salary_currency, salary_period,  job_benefits, city, state, country, apply_options, required_skills, required_experience, required_education, description, highlights, embeddings) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                            item.get("job_apply_link", ""),
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
                            item.get("required_education", ""),
                            item.get("description", ""),
                            item.get("highlights", ""),
                            json.dumps(embeddings),  # Store as JSON string for consistency
                        ),
                    )
                    conn.commit()
                    jobs_added += 1
                    logging.info("UPLOADED: %s uploaded to the database", primary_key)
                except Exception as insert_error:
                    logging.error(f"Failed to insert job {primary_key} to database: {insert_error}")
        except KeyError as e:
            logging.error("Skipping item due to missing key: %s", e)
        except Exception as e:
            logging.error("Skipping item due to error: %s", e)

    logging.info(f"Database upload complete: {jobs_added} jobs added, {jobs_skipped} jobs skipped, {embedding_failures} embedding failures")
    conn.close()


def save_text_to_db(filename, text):
    """Save resume text to the database."""
    conn = sqlite3.connect("all_jobs.db")
    cursor = conn.cursor()

    # Create the table with a primary key and filename
    try:
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resume_name TEXT UNIQUE,
            resume_text TEXT
        )
        """
        )
    except Exception as e:
        logging.error("Failed to create table: %s", e)

    try:
        # Check if a record with the given filename already exists
        cursor.execute(
            "SELECT id FROM resumes WHERE resume_name = ?",
            (filename,),
        )
        record = cursor.fetchone()

        if record:
            # If a record exists, update it
            cursor.execute(
                "UPDATE resumes SET resume_text = ? WHERE resume_name = ?",
                (text, filename),
            )
        else:
            # Otherwise, insert a new record
            cursor.execute(
                "INSERT INTO resumes (resume_name, resume_text) VALUES (?, ?)",
                (filename, text),
            )
    except Exception as e:
        logging.error("Failed to insert or update record: %s", e)

    conn.commit()
    conn.close()


def update_resume_in_db(filename, new_text):
    """Update resume text in the database."""
    conn = sqlite3.connect("all_jobs.db")
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE resumes SET resume_text = ? WHERE resume_name = ?",
        (new_text, filename),
    )
    conn.commit()
    conn.close()
    return True


def delete_resume_in_db(filename):
    """Delete resume from the database."""
    conn = sqlite3.connect("all_jobs.db")
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM resumes WHERE resume_name = ?",
        (filename,),  # Add a comma to create a tuple
    )
    conn.commit()
    conn.close()


def fetch_resumes_from_db():
    """Fetch all resumes from the database
    
    Returns:
        list: List of resume names
    """
    try:
        # Connect to the database
        conn = sqlite3.connect("all_jobs.db")
        cursor = conn.cursor()
        
        # Execute the query using the hardcoded table name instead of config.TABLE_RESUMES
        cursor.execute("SELECT resume_name FROM resumes")
        
        # Fetch the results and extract the resume names
        resume_names = [row[0] for row in cursor.fetchall()]
        
        # Close the connection
        conn.close()
        
        return resume_names
    except Exception as e:
        logging.error(f"Error fetching resumes from database: {e}")
        return []


def get_resume_text(filename):
    """Fetch the text content of a resume from the database."""
    conn = sqlite3.connect("all_jobs.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT resume_text FROM resumes WHERE resume_name = ?",
        (filename,),
    )
    record = cursor.fetchone()
    logging.info("Resume text fetched from the database")
    conn.close()

    return record[0] if record else None


def fetch_primary_keys_from_db() -> list:
    """Fetch primary keys from the database."""
    conn = sqlite3.connect("all_jobs.db")
    c = conn.cursor()

    # Fetch the primary keys from the table
    c.execute("SELECT primary_key FROM jobs_new")
    primary_keys = [row[0] for row in c.fetchall()]

    conn.close()
    return primary_keys


def update_similarity_in_db(resume_name):
    """Updates the similarity scores for all jobs in the database using the specified resume.
    
    Args:
        resume_name (str): The name of the resume to use for updating similarities
    """
    try:
        # Get resume text
        resume_text = get_resume_text(resume_name)
        if not resume_text:
            logger.error(f"Resume {resume_name} not found in database")
            return

        # Connect to database
        conn = sqlite3.connect("all_jobs.db")
        cursor = conn.cursor()

        # Get all job primary keys and descriptions
        cursor.execute("SELECT primary_key, description FROM jobs_new")
        jobs = cursor.fetchall()

        # If there are no jobs, return
        if not jobs:
            logger.warning("No jobs found in database to update similarity scores")
            conn.close()
            return

        # Create a progress bar for the UI
        total_jobs = len(jobs)
        progress_text = st.empty()
        progress_bar = st.progress(0)
        progress_text.text(f"Processing {total_jobs} jobs for similarity scores (sequentially)...")

        updated_count = 0
        skipped_count = 0
        update_batch = [] # Store updates to commit periodically
        COMMIT_INTERVAL = 20 # Commit after every 20 updates
        
        # --- MODIFIED: Sequential Processing --- 
        for index, (job_id, description) in enumerate(jobs):
            # Update progress
            progress_bar.progress((index + 1) / total_jobs)
            progress_text.text(f"Processing job {index+1}/{total_jobs} sequentially...")
            
            if not description:
                logger.warning(f"Job {job_id} has no description, skipping similarity calculation")
                skipped_count += 1
                continue
                
            try:
                # Calculate similarity between job description and resume sequentially
                similarity = text_similarity(description, resume_text)
                update_batch.append((similarity, job_id))
                updated_count += 1
                logger.info(f"Computed similarity for job {job_id}: {similarity:.4f}")
            except Exception as e:
                logger.error(f"Error calculating similarity for job {job_id}: {e}")
                skipped_count += 1
            
            # Commit updates periodically
            if len(update_batch) >= COMMIT_INTERVAL:
                logger.info(f"Committing {len(update_batch)} similarity updates to DB...")
                cursor.executemany(
                    "UPDATE jobs_new SET resume_similarity = ? WHERE primary_key = ?",
                    update_batch
                )
                conn.commit()
                update_batch = [] # Clear the batch
                
        # Commit any remaining updates
        if update_batch:
            logger.info(f"Committing final {len(update_batch)} similarity updates to DB...")
            cursor.executemany(
                "UPDATE jobs_new SET resume_similarity = ? WHERE primary_key = ?",
                update_batch
            )
            conn.commit()
            
        conn.close()
        
        # Update progress to completion
        progress_bar.progress(1.0)
        progress_text.text(f"Completed! Updated {updated_count} jobs, skipped {skipped_count} jobs")
        time.sleep(1)  # Keep the completion message visible briefly
        progress_text.empty()
        progress_bar.empty()
        
        logger.info(f"Updated similarity scores for {updated_count} jobs using resume '{resume_name}'")
        return True
        
    except Exception as e:
        logger.error(f"Error updating similarity scores: {e}")
        return False
