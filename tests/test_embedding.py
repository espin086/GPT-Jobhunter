import os
import logging
import json
import pytest
import time
from pathlib import Path
import sqlite3

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import necessary modules (no need to append to sys.path since we use pytest)
from jobhunter import config
from jobhunter.textAnalysis import generate_gpt_embedding, get_openai_api_key
from jobhunter.text_similarity import text_similarity
from jobhunter.SQLiteHandler import get_resume_text, fetch_resumes_from_db
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def test_api_key():
    """Test if the OpenAI API key is properly configured."""
    logger.info("Testing OpenAI API key...")
    api_key = get_openai_api_key()
    
    if not api_key:
        logger.error("❌ OpenAI API key not found!")
        logger.info("Checking environment variable directly...")
        direct_key = os.environ.get("OPENAI_API_KEY")
        if direct_key:
            logger.info(f"Found API key in environment (masked): {direct_key[:4]}...{direct_key[-4:]}")
        else:
            logger.error("❌ No API key in environment variable either.")
        pytest.fail("OpenAI API key not found")
    
    logger.info(f"✅ Found API key (masked): {api_key[:4]}...{api_key[-4:]}")
    assert api_key is not None

def test_embedding_generation():
    """Test if embedding generation works properly."""
    logger.info("Testing embedding generation...")
    test_text = "This is a test text for embedding generation."
    
    try:
        embedding = generate_gpt_embedding(test_text)
        
        if not embedding:
            logger.error("❌ No embedding returned!")
            pytest.fail("No embedding returned")
            
        if all(v == 0.0 for v in embedding):
            logger.error("❌ Received zero vector embedding!")
            pytest.fail("Received zero vector embedding")
            
        logger.info(f"✅ Successfully generated embedding of dimension {len(embedding)}.")
        logger.info(f"First few values: {embedding[:5]}")
        assert len(embedding) > 0
        assert not all(v == 0.0 for v in embedding)
    except Exception as e:
        logger.error(f"❌ Error generating embedding: {e}")
        pytest.fail(f"Error generating embedding: {e}")

def test_similarity_calculation(test_text_pair):
    """Test if similarity calculation works properly."""
    logger.info("Testing similarity calculation...")
    text1, text2 = test_text_pair
    
    try:
        similarity = text_similarity(text1, text2)
        logger.info(f"Similarity score: {similarity}")
        
        if similarity == 0.0:
            logger.warning("⚠️ Similarity is exactly 0.0, which might indicate an issue.")
            
        assert similarity > 0.0
    except Exception as e:
        logger.error(f"❌ Error calculating similarity: {e}")
        pytest.fail(f"Error calculating similarity: {e}")

def test_create_tables():
    """Create database tables if they don't exist."""
    logger.info("Creating database tables if needed...")
    
    conn = None
    try:
        from jobhunter.SQLiteHandler import create_db_if_not_there
        create_db_if_not_there()
        
        # Verify the tables now exist
        conn = sqlite3.connect(config.DATABASE)
        cursor = conn.cursor()
        
        # Check for jobs_new table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='jobs_new'")
        jobs_table_exists = cursor.fetchone() is not None
        
        # Check for resumes table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='resumes'")
        resumes_table_exists = cursor.fetchone() is not None
        
        logger.info(f"Table status: jobs_new={jobs_table_exists}, resumes={resumes_table_exists}")
        
        # Create the test resume table if needed
        if resumes_table_exists:
            logger.info("Resume table exists, checking for test data")
            cursor.execute("SELECT COUNT(*) FROM resumes")
            resume_count = cursor.fetchone()[0]
            
            if resume_count == 0:
                logger.info("No test resumes found, adding a test resume")
                cursor.execute(
                    "INSERT INTO resumes (resume_name, resume_text) VALUES (?, ?)",
                    ("test_resume.txt", "This is a test resume for a Python developer with skills in machine learning, data science, and web development.")
                )
                conn.commit()
        else:
            logger.info("Creating test resume table")
            cursor.execute("""
                CREATE TABLE resumes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resume_name TEXT UNIQUE,
                    resume_text TEXT
                )
            """)
            # Add a test resume
            cursor.execute(
                "INSERT INTO resumes (resume_name, resume_text) VALUES (?, ?)",
                ("test_resume.txt", "This is a test resume for a Python developer with skills in machine learning, data science, and web development.")
            )
            conn.commit()
            
        # Assert that the tables exist
        assert jobs_table_exists, "jobs_new table does not exist"
        assert resumes_table_exists, "resumes table does not exist"
        
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        pytest.fail(f"Failed to create database tables: {e}")
    finally:
        if conn:
            conn.close()

def test_resume_similarity_with_fixtures(sample_resume_text, mock_job_text):
    """Test resume similarity using fixture data."""
    logger.info("Testing resume similarity with fixture data...")
    
    try:
        # Generate embeddings for the sample resume and job texts
        resume_embedding = generate_gpt_embedding(sample_resume_text)
        job_embedding = generate_gpt_embedding(mock_job_text)
        
        # Check resume embedding
        if all(v == 0.0 for v in resume_embedding):
            logger.error("❌ Resume embedding from fixture is a zero vector!")
            pytest.fail("Resume embedding from fixture is a zero vector!")
        
        # Check job embedding    
        if all(v == 0.0 for v in job_embedding):
            logger.error("❌ Job embedding from fixture is a zero vector!")
            pytest.fail("Job embedding from fixture is a zero vector!")
            
        # Calculate similarity
        similarity = cosine_similarity([resume_embedding], [job_embedding])[0][0]
        logger.info(f"Fixture resume-job similarity: {similarity}")
        
        assert similarity > 0.0, "Similarity score should be greater than zero"
        
    except Exception as e:
        logger.error(f"❌ Error in fixture similarity test: {e}")
        pytest.fail(f"Error in fixture similarity test: {e}")

def test_resume_similarity():
    """Test resume similarity with real resume data if available."""
    logger.info("Testing resume similarity with actual resume data...")
    
    # Ensure tables exist first
    test_create_tables()
    
    # Get available resumes
    try:
        resumes = fetch_resumes_from_db()
        
        if not resumes:
            logger.warning("No resumes found in database.")
            pytest.skip("No resumes found in database to test")
            
        logger.info(f"Found {len(resumes)} resumes: {resumes}")
        
        # Get the text of the first resume
        resume_text = get_resume_text(resumes[0])
        
        if not resume_text:
            logger.error(f"❌ Could not get text for resume: {resumes[0]}")
            pytest.fail(f"Could not get text for resume: {resumes[0]}")
            
        logger.info(f"Resume text length: {len(resume_text)} chars")
        logger.info(f"Resume text preview: {resume_text[:100]}...")
        
        # Generate embedding for the resume
        resume_embedding = generate_gpt_embedding(resume_text)
        
        if all(v == 0.0 for v in resume_embedding):
            logger.error("❌ Resume embedding is a zero vector!")
            pytest.fail("Resume embedding is a zero vector!")
            
        # Test with a fake job description
        job_text = "Software Engineer experienced in Python, machine learning, and web development."
        job_embedding = generate_gpt_embedding(job_text)
        
        # Calculate similarity
        similarity = cosine_similarity([resume_embedding], [job_embedding])[0][0]
        logger.info(f"Test resume-job similarity: {similarity}")
        
        assert similarity > 0.0
    except Exception as e:
        logger.error(f"❌ Error in resume similarity test: {e}")
        pytest.fail(f"Error in resume similarity test: {e}")

def test_sqlite_query():
    """Test if we can properly query job embeddings from the database."""
    logger.info("Testing SQLite job embeddings query...")
    
    # Ensure tables exist first
    test_create_tables()
    
    # Create a test job if none exist
    conn = None
    try:
        import sqlite3
        conn = sqlite3.connect(config.DATABASE)
        cursor = conn.cursor()
        
        # Check if there are any jobs
        cursor.execute("SELECT COUNT(*) FROM jobs_new")
        job_count = cursor.fetchone()[0]
        
        if job_count == 0:
            logger.info("No jobs found, creating a test job with embedding")
            
            # Create a test job with embedding
            test_embedding = generate_gpt_embedding("This is a test job for a Python developer")
            test_emb_json = json.dumps(test_embedding)
            
            cursor.execute("""
                INSERT INTO jobs_new (
                    primary_key, date, title, company, description, embeddings
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                "test_job_1", "2023-06-01", "Test Python Developer", 
                "Test Company", "This is a test job for a Python developer", test_emb_json
            ))
            conn.commit()
            logger.info("Created test job with embedding")
        
        # Check if there are any rows with non-null embeddings
        cursor.execute("SELECT COUNT(*) FROM jobs_new WHERE embeddings IS NOT NULL")
        count = cursor.fetchone()[0]
        logger.info(f"Jobs with embeddings: {count}")
        
        if count == 0:
            logger.warning("No jobs with embeddings found, adding embedding to existing job")
            cursor.execute("SELECT primary_key FROM jobs_new LIMIT 1")
            job_id = cursor.fetchone()[0]
            if job_id:
                # Add embedding to this job
                test_embedding = generate_gpt_embedding("This is a test job for a Python developer")
                test_emb_json = json.dumps(test_embedding)
                
                cursor.execute(
                    "UPDATE jobs_new SET embeddings = ? WHERE primary_key = ?",
                    (test_emb_json, job_id)
                )
                conn.commit()
                logger.info(f"Added embedding to job {job_id}")
                count = 1
        
        # Sample a job embedding to check format
        cursor.execute("SELECT primary_key, embeddings FROM jobs_new WHERE embeddings IS NOT NULL LIMIT 1")
        row = cursor.fetchone()
        
        if row:
            job_key, job_emb_json = row
            logger.info(f"Sample job: {job_key}")
            
            try:
                job_emb = json.loads(job_emb_json)
                logger.info(f"Embedding dimension: {len(job_emb)}")
                if all(v == 0.0 for v in job_emb):
                    logger.error("❌ Sample job has zero vector embedding!")
                else:
                    logger.info("✅ Sample job has non-zero embedding values.")
            except Exception as parse_error:
                logger.error(f"❌ Could not parse job embedding JSON: {job_emb_json[:100]}")
                logger.error(f"Error: {parse_error}")
                pytest.fail(f"Could not parse job embedding JSON: {parse_error}")
        
        assert count > 0, "No jobs with embeddings found in database"
    except Exception as e:
        logger.error(f"❌ Error in SQLite query test: {e}")
        pytest.fail(f"Error in SQLite query test: {e}")
    finally:
        if conn:
            conn.close() 