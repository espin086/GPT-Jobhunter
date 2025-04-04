#!/usr/bin/env python3
"""
Script to rebuild all embeddings and recalculate similarities for all resumes.

This script can be used to fix issues with zero similarity scores by:
1. Regenerating all job embeddings in the database
2. Recalculating similarity scores for all resumes against the jobs

Usage:
    python -m jobhunter.rebuild_embeddings

This is useful when:
- You've replaced your OpenAI API key
- You're seeing zero similarity scores in the UI
- You've imported new jobs that don't have embeddings
"""

import json
import logging
import os
import sqlite3
import time
from pathlib import Path

import numpy as np
import streamlit as st  # For progress bars
from tqdm import tqdm  # For command-line progress bars

from jobhunter import config
from jobhunter.textAnalysis import generate_gpt_embedding, generate_gpt_embeddings_batch
from jobhunter.SQLiteHandler import (
    fetch_resumes_from_db,
    get_resume_text,
    update_similarity_in_db,
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_openai_api_key():
    """Check if OpenAI API key is available"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable is not set.")
        print("\n❌ OPENAI_API_KEY environment variable is not set.")
        print("Please set your OpenAI API key with:")
        print("export OPENAI_API_KEY=your-key-here")
        return False
        
    if len(api_key) < 20 or "your-api-key" in api_key.lower():
        logger.error("OPENAI_API_KEY appears to be invalid.")
        print("\n❌ OPENAI_API_KEY appears to be invalid.")
        print("Please check your OpenAI API key and ensure it's correctly set.")
        return False
        
    # Mask the key for logging
    masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
    logger.info(f"Using OpenAI API key (masked): {masked_key}")
    print(f"✅ Found OpenAI API key (masked): {masked_key}")
    return True

def rebuild_job_embeddings():
    """Rebuild embeddings for all jobs in the database"""
    print("\n🔄 Rebuilding job embeddings...")
    
    # Connect to the database
    conn = sqlite3.connect("all_jobs.db")
    cursor = conn.cursor()
    
    try:
        # Fetch all jobs
        cursor.execute("SELECT primary_key, title, description FROM jobs_new")
        jobs = cursor.fetchall()
        
        if not jobs:
            logger.warning("No jobs found in database.")
            print("❌ No jobs found in database. Try extracting jobs first.")
            return False
            
        total_jobs = len(jobs)
        logger.info(f"Found {total_jobs} jobs in database.")
        print(f"Found {total_jobs} jobs in database.")
        
        # Process in batches to avoid API rate limits
        batch_size = 100  # Adjust based on rate limits
        updated_count = 0
        
        for start_idx in range(0, total_jobs, batch_size):
            end_idx = min(start_idx + batch_size, total_jobs)
            batch = jobs[start_idx:end_idx]
            
            # Prepare texts for batch embedding
            texts = []
            primary_keys = []
            
            for job_id, title, description in batch:
                # Combine title and description for better embedding
                combined_text = f"{title}\n\n{description}" if title and description else description or title or ""
                texts.append(combined_text)
                primary_keys.append(job_id)
            
            # Generate embeddings in batch
            print(f"Generating embeddings for batch {start_idx//batch_size + 1}/{(total_jobs+batch_size-1)//batch_size}...")
            embeddings = generate_gpt_embeddings_batch(texts)
            
            if not embeddings:
                logger.error(f"Failed to generate embeddings for batch {start_idx}-{end_idx}.")
                print(f"❌ Failed to generate embeddings for batch {start_idx}-{end_idx}.")
                continue
                
            # Update database with new embeddings
            update_data = []
            for idx, (embedding, job_id) in enumerate(zip(embeddings, primary_keys)):
                if embedding and any(v != 0.0 for v in embedding):
                    # Convert embedding to JSON string
                    embedding_json = json.dumps(embedding)
                    update_data.append((embedding_json, job_id))
                    updated_count += 1
                else:
                    logger.warning(f"Empty or zero embedding for job {job_id}, skipping update")
            
            if update_data:
                cursor.executemany(
                    "UPDATE jobs_new SET embeddings = ? WHERE primary_key = ?",
                    update_data
                )
                conn.commit()
                
            # Give some feedback
            print(f"✅ Updated {len(update_data)}/{len(batch)} embeddings in batch {start_idx//batch_size + 1}")
            
            # Slow down to avoid rate limits
            time.sleep(2)
            
        # Summary
        logger.info(f"Updated embeddings for {updated_count}/{total_jobs} jobs.")
        print(f"\n✅ Updated embeddings for {updated_count}/{total_jobs} jobs.")
        return updated_count > 0
        
    except Exception as e:
        logger.error(f"Error rebuilding job embeddings: {e}", exc_info=True)
        print(f"❌ Error rebuilding job embeddings: {e}")
        return False
    finally:
        conn.close()

def recalculate_all_similarities():
    """Recalculate similarity scores for all resumes"""
    print("\n🔄 Recalculating similarity scores for all resumes...")
    
    # Get all resumes
    resumes = fetch_resumes_from_db()
    
    if not resumes:
        logger.warning("No resumes found in database.")
        print("❌ No resumes found in database. Try uploading a resume first.")
        return False
        
    logger.info(f"Found {len(resumes)} resumes in database.")
    print(f"Found {len(resumes)} resumes in database: {', '.join(resumes)}")
    
    # Update similarity for each resume
    success_count = 0
    
    for resume_name in resumes:
        print(f"\nUpdating similarity scores for resume: {resume_name}")
        success = update_similarity_in_db(resume_name)
        
        if success:
            success_count += 1
            print(f"✅ Successfully updated similarity scores for {resume_name}")
        else:
            print(f"❌ Failed to update similarity scores for {resume_name}")
    
    # Summary
    if success_count == len(resumes):
        logger.info(f"Successfully updated similarity scores for all {len(resumes)} resumes.")
        print(f"\n✅ Successfully updated similarity scores for all {len(resumes)} resumes.")
        return True
    else:
        logger.warning(f"Updated similarity scores for {success_count}/{len(resumes)} resumes.")
        print(f"\n⚠️ Updated similarity scores for {success_count}/{len(resumes)} resumes.")
        return success_count > 0

def main():
    """Main function to run the rebuild process"""
    print("\n" + "="*50)
    print("📊 GPT-JobHunter: Embedding Rebuilder")
    print("="*50)
    
    # Check API key
    if not check_openai_api_key():
        return
    
    # Rebuild job embeddings
    job_success = rebuild_job_embeddings()
    
    # Recalculate similarities
    if job_success:
        similarity_success = recalculate_all_similarities()
        
        if similarity_success:
            print("\n" + "="*50)
            print("✅ Embeddings and similarities successfully rebuilt!")
            print("="*50)
        else:
            print("\n" + "="*50)
            print("⚠️ Some issues occurred during similarity recalculation.")
            print("="*50)
    else:
        print("\n" + "="*50)
        print("❌ Failed to rebuild job embeddings. Cannot proceed with similarity recalculation.")
        print("="*50)

if __name__ == "__main__":
    main() 