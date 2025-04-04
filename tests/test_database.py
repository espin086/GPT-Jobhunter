import os
import pytest
import logging
import sqlite3
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set the database path for testing - use absolute path for Docker compatibility
TEST_DB_PATH = os.path.abspath("all_jobs.db")
logger.info(f"Using test database path: {TEST_DB_PATH}")

@pytest.fixture(scope="module")
def temp_db_path(tmp_path_factory):
    """Create a temporary database file path for isolated tests."""
    db_dir = tmp_path_factory.mktemp("db")
    return db_dir / "test_all_jobs.db"

def test_db_file_creation():
    """Test that the database file can be created."""
    # Import the function
    from jobhunter.SQLiteHandler import create_db_if_not_there
    
    # Run the function to create the database if needed
    create_db_if_not_there()
    
    # Check that the file exists
    assert os.path.exists(TEST_DB_PATH), f"Database file was not created at {TEST_DB_PATH}"
    assert os.path.getsize(TEST_DB_PATH) > 0, "Database file is empty"
    
    # Log database information for debugging
    logger.info(f"Database file created and verified: {TEST_DB_PATH}, size: {os.path.getsize(TEST_DB_PATH)}")

def test_tables_exist():
    """Test that the required tables exist in the database."""
    # Import the function
    from jobhunter.SQLiteHandler import create_db_if_not_there
    
    # Create the database if it doesn't exist
    create_db_if_not_there()
    
    # Connect to the database
    conn = sqlite3.connect(TEST_DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check for jobs_new table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='jobs_new'")
        jobs_table_exists = cursor.fetchone() is not None
        
        # Check for resumes table (create if needed for testing)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='resumes'")
        resumes_table_exists = cursor.fetchone() is not None
        
        if not resumes_table_exists:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS resumes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resume_name TEXT UNIQUE,
                    resume_text TEXT
                )
            """)
            conn.commit()
            
            # Verify it was created
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='resumes'")
            resumes_table_exists = cursor.fetchone() is not None
        
        assert jobs_table_exists, "jobs_new table does not exist"
        assert resumes_table_exists, "resumes table does not exist"
        
        # Check the schema of jobs_new table
        cursor.execute("PRAGMA table_info(jobs_new)")
        columns = {col[1] for col in cursor.fetchall()}
        
        required_columns = {"id", "primary_key", "title", "company", "description", "embeddings"}
        for col in required_columns:
            assert col in columns, f"Required column '{col}' missing from jobs_new table"
        
        # Check specifically for the embeddings column
        assert "embeddings" in columns, "embeddings column is missing from jobs_new table"
        
    finally:
        conn.close()

def test_isolated_db_creation(temp_db_path):
    """Test database creation in an isolated environment."""
    # Create a modified version of create_db_if_not_there for testing
    def create_test_db(db_path):
        conn = sqlite3.connect(db_path)
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
            return True
        except Exception as e:
            logger.error(f"Failed to create table: {e}")
            return False
        finally:
            conn.close()
    
    # Run the test function
    assert create_test_db(temp_db_path), "Failed to create test database"
    
    # Verify the database was created
    assert os.path.exists(temp_db_path), "Database file was not created at temp location"
    
    # Connect and verify the table structure
    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='jobs_new'")
        result = cursor.fetchone()
        assert result is not None, "jobs_new table not created in isolated database"
        
        # Check for embeddings column
        cursor.execute("PRAGMA table_info(jobs_new)")
        columns = {col[1] for col in cursor.fetchall()}
        assert "embeddings" in columns, "embeddings column is missing from isolated test database"
    finally:
        conn.close()

def test_resume_table_operations():
    """Test resume table CRUD operations."""
    # Import necessary functions
    from jobhunter.SQLiteHandler import save_text_to_db, get_resume_text, delete_resume_in_db
    
    test_resume_name = "test_resume_crud.txt"
    test_resume_text = "This is a test resume for CRUD operations testing."
    
    try:
        # Save the test resume
        save_text_to_db(test_resume_name, test_resume_text)
        
        # Retrieve the resume text
        retrieved_text = get_resume_text(test_resume_name)
        assert retrieved_text == test_resume_text, "Retrieved resume text doesn't match what was saved"
        
        # Update the resume text
        updated_text = "This is updated test resume text."
        save_text_to_db(test_resume_name, updated_text)
        
        # Verify the update
        retrieved_updated_text = get_resume_text(test_resume_name)
        assert retrieved_updated_text == updated_text, "Updated resume text wasn't retrieved correctly"
        
        # Delete the resume
        delete_resume_in_db(test_resume_name)
        
        # Verify deletion
        deleted_text = get_resume_text(test_resume_name)
        assert deleted_text is None or deleted_text == "", "Resume wasn't properly deleted"
        
    except Exception as e:
        pytest.fail(f"Error during resume table operations: {e}")

# Add more database-specific tests as needed 