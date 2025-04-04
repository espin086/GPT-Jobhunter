import json
import logging
import sqlite3
import time
import numpy as np  # Import numpy for array handling
import concurrent.futures # Re-import concurrent futures

import streamlit as st
from sklearn.metrics.pairwise import cosine_similarity # Import cosine_similarity

from jobhunter.textAnalysis import generate_gpt_embedding, generate_gpt_embeddings_batch

logger = logging.getLogger(__name__)

# Define batch size for OpenAI API calls
OPENAI_BATCH_SIZE = 100 # Adjust based on testing and rate limits
# Define batch size for DB commits
DB_COMMIT_INTERVAL = 50
# Define workers for CPU-bound similarity calculation
MAX_SIMILARITY_WORKERS = 8 # Adjust based on CPU cores

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
    """Check if primary key exists, generate embeddings via synchronous batching, remove duplicates, and upload."""
    logging.info(f"Starting upload process for {len(json_list)} received items.")
    conn = None
    jobs_to_process = []
    processed_keys_in_this_run = set() # Keep track of keys added in this run
    jobs_skipped = 0
    
    try:
        conn = sqlite3.connect("all_jobs.db")
        c = conn.cursor()

        # 1. Identify jobs not already in the database AND not duplicated in this run
        logging.info("Checking database for existing jobs and filtering internal duplicates...")
        existing_keys = set(fetch_primary_keys_from_db()) 
        
        for item in json_list:
            try:
                primary_key = item["primary_key"]
                
                # Skip if already in DB OR already added in this run
                if primary_key in existing_keys or primary_key in processed_keys_in_this_run:
                    jobs_skipped += 1
                    continue # Skip this duplicate item

                # Basic validation: Ensure item has necessary fields for embedding
                if item.get("description") or item.get("title"):
                    jobs_to_process.append(item)
                    processed_keys_in_this_run.add(primary_key) # Mark as processed for this run
                else:
                    logging.warning(f"Skipping item {primary_key} due to missing description and title.")
                    jobs_skipped += 1
                        
            except KeyError:
                logging.error("Skipping item due to missing primary_key.")
                jobs_skipped += 1
            except Exception as e:
                 logging.error(f"Error checking item {item.get('primary_key', 'Unknown')}: {e}")
                 jobs_skipped += 1
                 
        logging.info(f"Identified {len(jobs_to_process)} unique new jobs to process. Skipped {jobs_skipped} existing, duplicate, or invalid items.")

        if not jobs_to_process:
            logging.info("No new jobs to add to the database.")
            if conn: conn.close()
            return

        # 2. Generate embeddings in batches using synchronous API calls
        embedding_results = {}
        embedding_failures_count = 0
        total_batches = (len(jobs_to_process) + OPENAI_BATCH_SIZE - 1) // OPENAI_BATCH_SIZE
        logging.info(f"Generating embeddings in {total_batches} batches (size={OPENAI_BATCH_SIZE})...")
        start_time = time.time()

        for i in range(0, len(jobs_to_process), OPENAI_BATCH_SIZE):
            batch_items = jobs_to_process[i : i + OPENAI_BATCH_SIZE]
            batch_texts = []
            batch_pks = []
            
            logger.info(f"Processing batch {i // OPENAI_BATCH_SIZE + 1}/{total_batches}...")
            
            for item in batch_items:
                pk = item["primary_key"]
                text_to_embed = item.get("description", "") + " " + item.get("title", "")
                batch_texts.append(text_to_embed)
                batch_pks.append(pk)
            
            batch_embeddings = generate_gpt_embeddings_batch(batch_texts)
            
            if batch_embeddings and len(batch_embeddings) == len(batch_pks):
                for pk, embedding in zip(batch_pks, batch_embeddings):
                    if embedding is None: 
                        embedding_results[pk] = None 
                        embedding_failures_count += 1
                    else:
                        embedding_results[pk] = embedding
            else:
                logger.error(f"Batch {i // OPENAI_BATCH_SIZE + 1} failed or returned mismatched results. Marking all items in batch as failed.")
                for pk in batch_pks:
                    embedding_results[pk] = None
                embedding_failures_count += len(batch_pks) - sum(1 for pk in batch_pks if embedding_results.get(pk) is None) 

            if total_batches > 1 and (i // OPENAI_BATCH_SIZE + 1) < total_batches:
                 time.sleep(0.5) 
                 
        end_time = time.time()
        logging.info(f"Embedding generation finished in {end_time - start_time:.2f} seconds. Encountered {embedding_failures_count} individual failures.")

        # 3. Insert jobs with their embeddings sequentially (batched commits)
        logging.info("Inserting processed jobs into the database...")
        jobs_added = 0
        insert_batch_count = 0

        for item in jobs_to_process:
            primary_key = item["primary_key"] 
            embedding_data = embedding_results.get(primary_key)

            if embedding_data is None:
                final_embedding_json = json.dumps([0.0] * 1536) 
            else:
                final_embedding_json = json.dumps(embedding_data)

            try:
                c.execute(
                    "INSERT INTO jobs_new (primary_key, date, resume_similarity, title, company, company_url, company_type, job_type, job_is_remote,job_apply_link, job_offer_expiration_date, salary_low,  salary_high, salary_currency, salary_period,  job_benefits, city, state, country, apply_options, required_skills, required_experience, required_education, description, highlights, embeddings) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        primary_key,
                        item.get("date", ""),
                        item.get("resume_similarity", 0.0), # Default new job similarity to 0.0
                        item.get("title", ""),
                        item.get("company", ""),
                        item.get("company_url", ""),
                        item.get("company_type", ""),
                        item.get("job_type", ""),
                        item.get("job_is_remote", ""),
                        item.get("job_apply_link", ""),
                        item.get("job_offer_expiration_date", ""),
                        item.get("salary_low", None), # Use None for potentially missing numeric vals
                        item.get("salary_high", None),
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
                        final_embedding_json, 
                    ),
                )
                jobs_added += 1
                insert_batch_count += 1
                if insert_batch_count % DB_COMMIT_INTERVAL == 0:
                    conn.commit()

            except sqlite3.Error as insert_error:
                # Log UNIQUE constraint errors specifically, others generally
                if "UNIQUE constraint failed" in str(insert_error):
                    logger.warning(f"Attempted to insert duplicate primary key {primary_key}. This should have been caught earlier. Error: {insert_error}")
                else:
                    logger.error(f"Failed to insert job {primary_key} into database: {insert_error}")
            except Exception as general_error:
                logger.error(f"Unexpected error inserting job {primary_key}: {general_error}")

        if insert_batch_count % DB_COMMIT_INTERVAL != 0:
            conn.commit()
            
        logging.info(f"Database upload complete: {jobs_added} new jobs added, {jobs_skipped} jobs skipped initially (existing/duplicate/invalid), {embedding_failures_count} embedding generation failures occurred.")

    except sqlite3.Error as db_error:
         logging.error(f"Database error during upload process: {db_error}", exc_info=True)
    except Exception as e:
         logging.error(f"An unexpected error occurred during the upload process: {e}", exc_info=True)
    finally:
         if conn:
             conn.close()
             logging.info("Database connection closed.")


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


def _calculate_similarity_for_job(job_data, resume_embedding_np):
    """Helper function to calculate similarity for one job concurrently."""
    job_id, job_embedding_json = job_data
    try:
        if job_embedding_json:
            job_embedding_list = json.loads(job_embedding_json)
            if isinstance(job_embedding_list, list) and any(v != 0.0 for v in job_embedding_list):
                job_embedding = np.array(job_embedding_list).reshape(1, -1)
                similarity_score = cosine_similarity(resume_embedding_np, job_embedding)[0][0]
                return job_id, float(similarity_score)
            else:
                # Invalid or zero embedding stored
                return job_id, None # Indicate skipped
        else:
            # No embedding stored
            return job_id, None # Indicate skipped
    except json.JSONDecodeError:
        logger.error(f"THREAD Error decoding JSON embedding for job {job_id}, skipping.")
        return job_id, None
    except Exception as e:
        logger.error(f"THREAD Error calculating similarity for job {job_id}: {e}")
        return job_id, None


def update_similarity_in_db(resume_name):
    """Updates the similarity scores concurrently for all jobs against the specified resume."""
    try:
        # 1. Get resume text & embedding (unchanged)
        resume_text = get_resume_text(resume_name)
        if not resume_text:
            logger.error(f"Resume {resume_name} not found.")
            return False
        logger.info(f"Generating embedding for active resume: {resume_name}")
        try:
            resume_embedding = generate_gpt_embedding(resume_text) 
            if not resume_embedding or all(v == 0.0 for v in resume_embedding):
                logger.error(f"Failed to generate embedding for resume {resume_name}.")
                st.error(f"Failed to generate embedding for resume {resume_name}. Check OpenAI API key/quota.")
                return False
            resume_embedding_np = np.array(resume_embedding).reshape(1, -1)
            logger.info(f"Successfully generated embedding for resume {resume_name}.")
        except Exception as resume_emb_error:
            logger.error(f"Error generating resume embedding: {resume_emb_error}")
            st.error(f"Error generating resume embedding: {resume_emb_error}")
            return False

        # Connect to database & Fetch jobs (unchanged)
        conn = sqlite3.connect("all_jobs.db")
        cursor = conn.cursor()
        logger.info("Fetching job primary keys and embeddings...")
        cursor.execute("SELECT primary_key, embeddings FROM jobs_new")
        jobs_data = cursor.fetchall() # List of (job_id, job_embedding_json)
        logger.info(f"Fetched {len(jobs_data)} jobs.")
        if not jobs_data:
            logger.warning("No jobs found to update similarity scores.")
            conn.close()
            return True

        # Setup progress bar (unchanged)
        total_jobs = len(jobs_data)
        progress_text = st.empty()
        progress_bar = st.progress(0)
        progress_text.text(f"Calculating similarity for {total_jobs} jobs against '{resume_name}' (concurrently)...")

        # 2. Calculate similarities concurrently
        similarity_results = {}
        skipped_count = 0
        start_time = time.time()
        
        # Prepare arguments for the helper function
        # Need to pass resume_embedding_np to each worker, lambda can do this
        from functools import partial
        calculation_helper = partial(_calculate_similarity_for_job, resume_embedding_np=resume_embedding_np)

        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_SIMILARITY_WORKERS) as executor:
            # Use map to run the helper concurrently
            future_results = executor.map(calculation_helper, jobs_data)

            # Process results as they complete
            for index, (job_id, score) in enumerate(future_results):
                if score is None:
                    skipped_count += 1
                else:
                    similarity_results[job_id] = score
                # Update progress bar periodically, not necessarily on every result
                if (index + 1) % 100 == 0 or (index + 1) == total_jobs: # Update every 100 jobs or at the end
                     progress = (index + 1) / total_jobs
                     progress_bar.progress(progress)
                     # Progress text can be updated less frequently if desired
                     # progress_text.text(f"Calculating similarity: {int(progress * 100)}% completed...")

        end_time = time.time()
        logger.info(f"Similarity calculation finished in {end_time - start_time:.2f} seconds.")

        # 3. Update database with calculated similarities (batched)
        update_batch = list(similarity_results.items()) # Convert dict items to list of tuples [(job_id, score), ...]
        updated_count = len(update_batch)
        logger.info(f"Updating database for {updated_count} jobs with new similarity scores...")

        for i in range(0, updated_count, DB_COMMIT_INTERVAL):
            batch_to_commit = update_batch[i : i + DB_COMMIT_INTERVAL]
            # Need to swap order for executemany: [(score, job_id), ...]
            swapped_batch = [(score, job_id) for job_id, score in batch_to_commit]
            try:
                cursor.executemany(
                    "UPDATE jobs_new SET resume_similarity = ? WHERE primary_key = ?",
                    swapped_batch
                )
                conn.commit()
            except sqlite3.Error as db_update_err:
                 logger.error(f"Database error updating batch starting at index {i}: {db_update_err}")
                 # Consider how to handle partial batch failures if necessary
            
        conn.close()
        
        # Final UI update (unchanged)
        progress_bar.progress(1.0)
        progress_text.text(f"Completed! Updated similarity for {updated_count} jobs, skipped {skipped_count} jobs for resume '{resume_name}'.")
        time.sleep(1.5)
        progress_text.empty()
        progress_bar.empty()
        
        logger.info(f"Finished updating similarity scores. Updated: {updated_count}, Skipped: {skipped_count} for '{resume_name}'")
        return True
        
    except Exception as e:
        logger.error(f"An unexpected error in update_similarity_in_db: {e}", exc_info=True)
        st.error(f"An unexpected error occurred updating similarity scores: {e}")
        if 'progress_text' in locals() and progress_text: progress_text.empty()
        if 'progress_bar' in locals() and progress_bar: progress_bar.empty()
        # Ensure connection is closed on error if opened
        if 'conn' in locals() and conn: conn.close()
        return False
