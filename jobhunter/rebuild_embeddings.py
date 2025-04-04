#!/usr/bin/env python3
"""
Tool to rebuild embeddings for all jobs in the database and recalculate similarity scores.
"""

import os
import logging
import json
import sqlite3
import time
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import needed modules
from jobhunter.textAnalysis import generate_gpt_embedding, generate_gpt_embeddings_batch
from jobhunter.SQLiteHandler import update_similarity_in_db, fetch_resumes_from_db
from jobhunter.FileHandler import FileHandler
from jobhunter import config

def check_api_key():
    """Make sure we have a valid API key before proceeding."""
    import os
    
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        logger.error("OpenAI API Key not found in environment variables.")
        print("ERROR: OpenAI API key not found!")
        print("Please set your API key in the .env file or export it directly:")
        print("export OPENAI_API_KEY=your-api-key-here")
        return False
        
    # Basic sanity check on key format
    if not key.startswith("sk-") or len(key) < 20:
        logger.error(f"OpenAI API Key appears to be invalid: {key[:5]}...")
        print("ERROR: OpenAI API key appears invalid.")
        print("Make sure your key starts with 'sk-' and is the correct length.")
        return False
        
    return True

def rebuild_job_embeddings():
    """Generate new embeddings for all jobs in the database."""
    logger.info("Rebuilding job embeddings...")
    
    # Connect to database
    conn = sqlite3.connect("all_jobs.db")
    cursor = conn.cursor()
    
    # Get all jobs
    try:
        cursor.execute("SELECT primary_key, title, description FROM jobs_new")
        jobs = cursor.fetchall()
        logger.info(f"Found {len(jobs)} jobs in database.")
        
        if not jobs:
            logger.error("No jobs found in database!")
            conn.close()
            return False
            
        # Prepare job texts for embedding
        job_texts = []
        job_ids = []
        
        print(f"Preparing {len(jobs)} jobs for embedding generation...")
        for job_id, title, description in jobs:
            combined_text = f"{title}\n\n{description}" if title and description else title or description or ""
            if combined_text:
                job_texts.append(combined_text)
                job_ids.append(job_id)
            else:
                logger.warning(f"Job {job_id} has no text to embed!")
        
        # Generate embeddings in batches
        BATCH_SIZE = 50
        successful_embeddings = 0
        failed_embeddings = 0
        
        for i in range(0, len(job_texts), BATCH_SIZE):
            batch_texts = job_texts[i:i+BATCH_SIZE]
            batch_ids = job_ids[i:i+BATCH_SIZE]
            
            print(f"Processing batch {i//BATCH_SIZE + 1}/{(len(job_texts) + BATCH_SIZE - 1) // BATCH_SIZE}...")
            
            # Generate embeddings
            embeddings = generate_gpt_embeddings_batch(batch_texts)
            
            if not embeddings:
                logger.error(f"Failed to generate embeddings for batch {i//BATCH_SIZE + 1}!")
                failed_embeddings += len(batch_texts)
                continue
                
            if len(embeddings) != len(batch_ids):
                logger.error(f"Mismatch in batch {i//BATCH_SIZE + 1}: {len(embeddings)} embeddings for {len(batch_ids)} jobs!")
                failed_embeddings += len(batch_texts)
                continue
            
            # Update database
            batch_updates = []
            for job_id, embedding in zip(batch_ids, embeddings):
                if embedding and not all(v == 0.0 for v in embedding):
                    # Convert embedding to JSON string
                    embedding_json = json.dumps(embedding)
                    batch_updates.append((embedding_json, job_id))
                    successful_embeddings += 1
                else:
                    logger.warning(f"Zero or invalid embedding for job {job_id}")
                    failed_embeddings += 1
            
            if batch_updates:
                try:
                    cursor.executemany(
                        "UPDATE jobs_new SET embeddings = ? WHERE primary_key = ?",
                        batch_updates
                    )
                    conn.commit()
                    logger.info(f"Updated embeddings for {len(batch_updates)} jobs in batch {i//BATCH_SIZE + 1}.")
                except sqlite3.Error as e:
                    logger.error(f"Database error updating batch {i//BATCH_SIZE + 1}: {e}")
                    failed_embeddings += len(batch_updates)
                    successful_embeddings -= len(batch_updates)
            
            # Add a small delay between batches
            if i + BATCH_SIZE < len(job_texts):
                time.sleep(0.5)
        
        conn.close()
        
        print(f"Rebuilding complete! Successful: {successful_embeddings}, Failed: {failed_embeddings}")
        return successful_embeddings > 0
        
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        if conn:
            conn.close()
        return False
    except Exception as e:
        logger.error(f"Error rebuilding embeddings: {e}")
        if conn:
            conn.close()
        return False

def recalculate_similarities():
    """Recalculate similarity scores for all resumes."""
    logger.info("Recalculating similarity scores...")
    
    # Get all resumes
    resumes = fetch_resumes_from_db()
    
    if not resumes:
        logger.error("No resumes found in database!")
        print("No resumes found. Please upload at least one resume first.")
        return False
    
    print(f"Found {len(resumes)} resumes: {resumes}")
    
    # Update similarity for each resume
    for resume in resumes:
        print(f"Processing similarity for resume: {resume}")
        success = update_similarity_in_db(resume)
        
        if success:
            print(f"✓ Similarity updated for '{resume}'")
        else:
            print(f"✗ Failed to update similarity for '{resume}'")
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("JOB EMBEDDING REBUILDER & SIMILARITY RECALCULATOR")
    print("=" * 60)
    print("\nThis tool will regenerate all job embeddings and recalculate resume similarities.\n")
    
    if not check_api_key():
        sys.exit(1)
    
    choice = input("Ready to proceed? This may use a significant amount of OpenAI API credits. (y/n): ")
    if choice.lower() != 'y':
        print("Operation cancelled.")
        sys.exit(0)
    
    print("\nStep 1: Rebuilding job embeddings...")
    rebuild_success = rebuild_job_embeddings()
    
    if rebuild_success:
        print("\nStep 2: Recalculating similarity scores...")
        similarity_success = recalculate_similarities()
        
        if similarity_success:
            print("\n✓ Process completed successfully!")
        else:
            print("\n✗ Failed to recalculate similarities!")
    else:
        print("\n✗ Failed to rebuild job embeddings!")
    
    print("\nDone!") 