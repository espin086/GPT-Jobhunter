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
    """
    This function checks if a job is already in the database and uploads it if it's not.
    """
    db_name = "all_jobs.db"
    
    if not json_list:
        logger.info("No new jobs to add to the database.")
        return
    
    # Start by creating a connection to the database
    logger.info("Starting upload process for %s received items.", len(json_list))
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # Check if embeddings column exists, add it if it doesn't
    cursor.execute("PRAGMA table_info(jobs_new)")
    columns = [col[1] for col in cursor.fetchall()]
    if "embeddings" not in columns:
        logger.info("Adding embeddings column to jobs_new table")
        cursor.execute("ALTER TABLE jobs_new ADD COLUMN embeddings TEXT")
        conn.commit()

    # Query existing primary keys
    try:
        cursor.execute("SELECT primary_key FROM jobs_new")
        existing_keys = {row[0] for row in cursor.fetchall()}
        logger.info("Found %s existing jobs in database.", len(existing_keys))
    except sqlite3.Error as e:
        logger.error("Error fetching existing keys: %s", e)
        conn.close()
        return
    
    # Identify new unique items to add
    new_items = []
    internal_duplicates = set()
    duplicates_count = 0
    invalid_items = 0
    
    for item in json_list:
        try:
            # Skip items without a primary key or where it's already processed in this batch
            if not item.get("primary_key"):
                invalid_items += 1
                continue
                
            # Check if it's already in our database
            if item["primary_key"] in existing_keys:
                duplicates_count += 1
                continue
                
            # Check for internal duplicates in this batch
            if item["primary_key"] in internal_duplicates:
                duplicates_count += 1
                continue
                
            # This is a new unique item
            internal_duplicates.add(item["primary_key"])
            new_items.append(item)
                
        except Exception as e:
            logger.error("Error processing item %s: %s", item, e)
            invalid_items += 1

    # If no new items, we're done
    if not new_items:
        logger.info("No new unique jobs to add among %s items. Skipped %s existing, %s duplicate, and %s invalid items.", 
                   len(json_list), duplicates_count, len(internal_duplicates) - len(new_items), invalid_items)
        conn.close()
        return
        
    # Generate embeddings for new items in batch - with progress
    logger.info("Generating embeddings for %s new items...", len(new_items))
    successful_items = []
    
    # Extract texts for embedding (job description and title)
    texts = []
    for item in new_items:
        # Create a combined text from job title and description for better embedding
        title = item.get("title", "")
        description = item.get("description", "")
        combined_text = f"{title}\n\n{description}"
        texts.append(combined_text)
    
    # Get embeddings in batch
    try:
        from jobhunter.textAnalysis import generate_gpt_embeddings_batch
        embeddings_batch = generate_gpt_embeddings_batch(texts)
        
        if embeddings_batch:
            logger.info(f"Successfully generated {len(embeddings_batch)} embeddings in batch")
            
            # Match embeddings back to items
            for i, (item, embedding) in enumerate(zip(new_items, embeddings_batch)):
                if embedding and any(v != 0.0 for v in embedding):
                    # Store embedding as JSON string
                    item["embeddings"] = json.dumps(embedding)
                    successful_items.append(item)
                elif embedding:
                    logger.warning(f"Zero embedding generated for item {i} ({item.get('primary_key')})")
                    item["embeddings"] = None  # Store as NULL in database
                    successful_items.append(item)
                else:
                    logger.error(f"Failed to generate embedding for item {i} ({item.get('primary_key')})")
                    # Still add the item, just without embedding
                    item["embeddings"] = None
                    successful_items.append(item)
        else:
            logger.error("Batch embedding generation failed, proceeding without embeddings")
            for item in new_items:
                item["embeddings"] = None
                successful_items.append(item)
    except Exception as e:
        logger.error(f"Error during batch embedding generation: {e}", exc_info=True)
        # Proceed without embeddings if there's an error
        for item in new_items:
            item["embeddings"] = None
            successful_items.append(item)
    
    # Insert new items to database
    try:
        # Prepare SQL and values list
        keys = ["primary_key", "date", "title", "company", "company_url", "company_type", 
                "job_type", "job_is_remote", "job_apply_link", "job_offer_expiration_date", 
                "salary_low", "salary_high", "salary_currency", "salary_period", "job_benefits", 
                "city", "state", "country", "apply_options", "required_skills", "required_experience", 
                "required_education", "description", "highlights", "embeddings"]
        
        placeholders = ", ".join(["?"] * len(keys))
        sql = f"INSERT INTO jobs_new ({', '.join(keys)}) VALUES ({placeholders})"
        
        # Extract values in order, handling possible missing keys
        values_list = []
        for item in successful_items:
            values = []
            for key in keys:
                if key == "embeddings":
                    # Handle embeddings separately
                    values.append(item.get("embeddings"))
                else:
                    values.append(item.get(key, None))
            values_list.append(values)
        
        # Commit in reasonable batches
        batch_size = 50
        total_inserted = 0
        
        for i in range(0, len(values_list), batch_size):
            batch = values_list[i:i+batch_size]
            cursor.executemany(sql, batch)
            conn.commit()
            total_inserted += len(batch)
            logger.info(f"Inserted batch {i//batch_size + 1}: {len(batch)} items")
        
        logger.info("Successfully added %s new jobs to the database.", total_inserted)
    except sqlite3.Error as e:
        logger.error("Error inserting new items to database: %s", e)
    finally:
        conn.close()


def save_text_to_db(filename, text):
    """Save resume text to the database."""
    conn = sqlite3.connect("all_jobs.db")
    cursor = conn.cursor()

    try:
        # Create the table with a primary key and filename
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resume_name TEXT UNIQUE,
            resume_text TEXT
        )
        """
        )

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

        conn.commit()
    except Exception as e:
        logging.error("Failed to save resume to database: %s", e, exc_info=True)
        conn.rollback()
        raise
    finally:
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
            try:
                job_embedding_list = json.loads(job_embedding_json)
                
                # Validate the embedding
                if not isinstance(job_embedding_list, list):
                    logger.warning(f"Invalid embedding format for job {job_id}: not a list")
                    return job_id, 0.0
                    
                if len(job_embedding_list) < 100:  # Sanity check on embedding dimension
                    logger.warning(f"Invalid embedding dimension for job {job_id}: {len(job_embedding_list)}")
                    return job_id, 0.0
                    
                if all(v == 0.0 for v in job_embedding_list):
                    logger.warning(f"Zero vector embedding for job {job_id}")
                    return job_id, 0.0
                
                # Calculate similarity
                job_embedding = np.array(job_embedding_list).reshape(1, -1)
                similarity_score = cosine_similarity(resume_embedding_np, job_embedding)[0][0]
                
                # Ensure we get a valid float
                result = float(similarity_score)
                
                # Sanity check on the score
                if result < 0.0 or result > 1.0:
                    logger.warning(f"Invalid similarity score for job {job_id}: {result}")
                    result = max(0.0, min(1.0, result))  # Clamp to valid range
                
                return job_id, result
                
            except json.JSONDecodeError:
                logger.error(f"Error decoding JSON embedding for job {job_id}, using zero similarity")
                return job_id, 0.0
        else:
            # No embedding stored
            logger.debug(f"No embedding found for job {job_id}")
            return job_id, 0.0
    except Exception as e:
        logger.error(f"Error calculating similarity for job {job_id}: {e}")
        return job_id, 0.0


def update_similarity_in_db(resume_name):
    """Updates the similarity scores concurrently for all jobs against the specified resume."""
    try:
        # 1. Get resume text & embedding
        resume_text = get_resume_text(resume_name)
        if not resume_text:
            logger.error(f"Resume {resume_name} not found.")
            st.error(f"Resume '{resume_name}' not found in database. Please upload it first.")
            return False
            
        logger.info(f"Generating embedding for active resume: {resume_name}")
        try:
            from jobhunter.textAnalysis import generate_gpt_embedding
            resume_embedding = generate_gpt_embedding(resume_text) 
            
            if not resume_embedding:
                logger.error(f"Failed to generate embedding for resume {resume_name} - result is None.")
                st.error(f"Failed to generate embedding for resume {resume_name}. Check OpenAI API key/quota.")
                return False
                
            if all(v == 0.0 for v in resume_embedding):
                logger.error(f"Failed to generate embedding for resume {resume_name} - got zero vector.")
                st.error(f"Failed to generate embedding for resume {resume_name}. Check your API key and quota.")
                return False
                
            # Quick stats on the embedding
            non_zero_count = sum(1 for v in resume_embedding if v != 0.0)
            non_zero_percentage = (non_zero_count / len(resume_embedding)) * 100
            logger.info(f"Resume embedding stats: dimension={len(resume_embedding)}, non-zero={non_zero_percentage:.1f}%")
            
            resume_embedding_np = np.array(resume_embedding).reshape(1, -1)
            logger.info(f"Successfully generated embedding for resume {resume_name}")
            
        except Exception as resume_emb_error:
            logger.error(f"Error generating resume embedding: {resume_emb_error}", exc_info=True)
            st.error(f"Error generating resume embedding: {resume_emb_error}")
            return False

        # Connect to database & Fetch jobs
        conn = sqlite3.connect("all_jobs.db")
        cursor = conn.cursor()
        logger.info("Fetching job primary keys and embeddings...")
        cursor.execute("SELECT primary_key, embeddings FROM jobs_new")
        jobs_data = cursor.fetchall() # List of (job_id, job_embedding_json)
        logger.info(f"Fetched {len(jobs_data)} jobs.")
        
        # Check if any jobs have embeddings
        jobs_with_embeddings = sum(1 for _, emb in jobs_data if emb is not None)
        logger.info(f"Jobs with stored embeddings: {jobs_with_embeddings}/{len(jobs_data)}")
        
        if not jobs_data:
            logger.warning("No jobs found to update similarity scores.")
            conn.close()
            st.warning("No jobs found in database. Run a job search to populate it.")
            return True

        # Setup progress bar
        total_jobs = len(jobs_data)
        progress_text = st.empty()
        progress_bar = st.progress(0)
        progress_text.text(f"Calculating similarity for {total_jobs} jobs against '{resume_name}' (concurrently)...")

        # 2. Calculate similarities concurrently
        similarity_results = {}
        skipped_count = 0
        zero_emb_count = 0
        start_time = time.time()
        
        # Prepare arguments for the helper function
        # Need to pass resume_embedding_np to each worker
        from functools import partial
        calculation_helper = partial(_calculate_similarity_for_job, resume_embedding_np=resume_embedding_np)

        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_SIMILARITY_WORKERS) as executor:
            # Use map to run the helper concurrently
            future_results = executor.map(calculation_helper, jobs_data)

            # Process results as they complete
            for index, (job_id, score) in enumerate(future_results):
                if score is None:
                    skipped_count += 1
                elif score == 0.0:
                    zero_emb_count += 1
                    similarity_results[job_id] = score
                else:
                    similarity_results[job_id] = score
                    
                # Update progress bar periodically
                if (index + 1) % 100 == 0 or (index + 1) == total_jobs:
                     progress = (index + 1) / total_jobs
                     progress_bar.progress(progress)

        end_time = time.time()
        logger.info(f"Similarity calculation finished in {end_time - start_time:.2f} seconds.")
        logger.info(f"Results: {len(similarity_results)} calculated, {skipped_count} skipped, {zero_emb_count} zero scores.")

        # Log summary of similarity scores
        if similarity_results:
            scores = list(similarity_results.values())
            avg_score = sum(scores) / len(scores)
            max_score = max(scores)
            min_score = min(scores)
            logger.info(f"Similarity scores - min: {min_score:.4f}, avg: {avg_score:.4f}, max: {max_score:.4f}")
            
            # Check if all scores are 0
            if max_score == 0.0:
                logger.warning("⚠️ All similarity scores are zero! This indicates a possible issue.")

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
            
        conn.close()
        
        # Final UI update
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
