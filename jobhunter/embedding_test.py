import os
import logging
import json
import time
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the parent directory to sys.path to import jobhunter modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.append(str(parent_dir))

# Import necessary modules
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
        return False
    
    logger.info(f"✅ Found API key (masked): {api_key[:4]}...{api_key[-4:]}")
    return True

def test_embedding_generation():
    """Test if embedding generation works properly."""
    logger.info("Testing embedding generation...")
    test_text = "This is a test text for embedding generation."
    
    try:
        embedding = generate_gpt_embedding(test_text)
        
        if not embedding:
            logger.error("❌ No embedding returned!")
            return False
            
        if all(v == 0.0 for v in embedding):
            logger.error("❌ Received zero vector embedding!")
            return False
            
        logger.info(f"✅ Successfully generated embedding of dimension {len(embedding)}.")
        logger.info(f"First few values: {embedding[:5]}")
        return True
    except Exception as e:
        logger.error(f"❌ Error generating embedding: {e}")
        return False

def test_similarity_calculation():
    """Test if similarity calculation works properly."""
    logger.info("Testing similarity calculation...")
    text1 = "I am a software engineer with experience in Python and machine learning."
    text2 = "Looking for a Python developer with machine learning background."
    
    try:
        similarity = text_similarity(text1, text2)
        logger.info(f"Similarity score: {similarity}")
        
        if similarity == 0.0:
            logger.warning("⚠️ Similarity is exactly 0.0, which might indicate an issue.")
            
        return similarity > 0.0
    except Exception as e:
        logger.error(f"❌ Error calculating similarity: {e}")
        return False

def test_resume_similarity():
    """Test resume similarity with real resume data if available."""
    logger.info("Testing resume similarity with actual resume data...")
    
    # Get available resumes
    try:
        resumes = fetch_resumes_from_db()
        
        if not resumes:
            logger.warning("No resumes found in database.")
            return False
            
        logger.info(f"Found {len(resumes)} resumes: {resumes}")
        
        # Get the text of the first resume
        resume_text = get_resume_text(resumes[0])
        
        if not resume_text:
            logger.error(f"❌ Could not get text for resume: {resumes[0]}")
            return False
            
        logger.info(f"Resume text length: {len(resume_text)} chars")
        logger.info(f"Resume text preview: {resume_text[:100]}...")
        
        # Generate embedding for the resume
        resume_embedding = generate_gpt_embedding(resume_text)
        
        if all(v == 0.0 for v in resume_embedding):
            logger.error("❌ Resume embedding is a zero vector!")
            return False
            
        # Test with a fake job description
        job_text = "Software Engineer experienced in Python, machine learning, and web development."
        job_embedding = generate_gpt_embedding(job_text)
        
        # Calculate similarity
        similarity = cosine_similarity([resume_embedding], [job_embedding])[0][0]
        logger.info(f"Test resume-job similarity: {similarity}")
        
        return similarity > 0.0
    except Exception as e:
        logger.error(f"❌ Error in resume similarity test: {e}")
        return False

def test_sqlite_query():
    """Test if we can properly query job embeddings from the database."""
    logger.info("Testing SQLite job embeddings query...")
    
    try:
        import sqlite3
        conn = sqlite3.connect(config.DATABASE)
        cursor = conn.cursor()
        
        # Check if there are any rows with non-null embeddings
        cursor.execute("SELECT COUNT(*) FROM jobs_new WHERE embeddings IS NOT NULL")
        count = cursor.fetchone()[0]
        logger.info(f"Jobs with embeddings: {count}")
        
        # Check for zero-vector embeddings (stored as JSON strings)
        cursor.execute("SELECT COUNT(*) FROM jobs_new WHERE embeddings IS NOT NULL")
        total_with_emb = cursor.fetchone()[0]
        
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
            except:
                logger.error(f"❌ Could not parse job embedding JSON: {job_emb_json[:100]}")
        
        conn.close()
        return count > 0
    except Exception as e:
        logger.error(f"❌ Error in SQLite query test: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("RESUME SIMILARITY DIAGNOSIS TOOL")
    print("=" * 60)
    
    tests = [
        ("API Key Configuration", test_api_key),
        ("Embedding Generation", test_embedding_generation),
        ("Similarity Calculation", test_similarity_calculation),
        ("Resume Similarity", test_resume_similarity),
        ("SQLite Job Embeddings", test_sqlite_query)
    ]
    
    results = []
    
    for name, test_func in tests:
        print(f"\n{'-' * 40}")
        print(f"RUNNING TEST: {name}")
        print(f"{'-' * 40}")
        
        try:
            start_time = time.time()
            result = test_func()
            duration = time.time() - start_time
            
            results.append((name, result, duration))
            
            status = "PASSED" if result else "FAILED"
            print(f"\nTEST {status} in {duration:.2f}s\n")
        except Exception as e:
            print(f"\nTEST ERROR: {e}\n")
            results.append((name, False, 0))
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for name, result, duration in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{name}: {status} ({duration:.2f}s)")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED - Your embedding system should be working!")
    else:
        print("❌ SOME TESTS FAILED - See details above for what needs fixing.")
    print("=" * 60) 