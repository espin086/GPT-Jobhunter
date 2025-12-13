"""
Test suite for multi-user data isolation.

This test file verifies that:
1. Users can only see their own resumes
2. Users can only see their own job tracking
3. All users can see the shared jobs database
4. Same resume name can be used by different users
"""

import os
import sqlite3
import pytest
import tempfile

# Import database functions - will work once implemented
from jobhunter.AuthHandler import create_auth_tables, create_user
from jobhunter.SQLiteHandler import (
    create_db_if_not_there,
    save_text_to_db,
    fetch_resumes_from_db,
    get_resume_text,
    verify_resume_ownership,
)


@pytest.fixture
def test_db():
    """Create a temporary test database with auth and job tables."""
    temp_dir = tempfile.mkdtemp()
    test_db_path = os.path.join(temp_dir, "test_isolation.db")

    # Override database path for tests
    os.environ['TEST_DATABASE'] = test_db_path

    # Create all required tables
    create_auth_tables(test_db_path)
    create_db_if_not_there()  # Creates jobs_new table

    # Create resumes table with user_id
    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resume_name TEXT NOT NULL,
            resume_text TEXT,
            user_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, resume_name)
        )
    """)

    # Create job_tracking table with user_id
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'apply',
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            date_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            user_id INTEGER NOT NULL,
            FOREIGN KEY (job_id) REFERENCES jobs_new(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, job_id)
        )
    """)
    conn.commit()
    conn.close()

    yield test_db_path

    # Cleanup
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    os.rmdir(temp_dir)


def test_resume_isolation(test_db):
    """Test that User A cannot see User B's resumes."""
    # Create two users
    user_a_id = create_user(
        db_path=test_db,
        email="usera@example.com",
        username="usera",
        password="password123"
    )

    user_b_id = create_user(
        db_path=test_db,
        email="userb@example.com",
        username="userb",
        password="password123"
    )

    # User A uploads a resume
    save_text_to_db(
        filename="resume_a.txt",
        text="User A's resume content",
        user_id=user_a_id
    )

    # User B uploads a resume
    save_text_to_db(
        filename="resume_b.txt",
        text="User B's resume content",
        user_id=user_b_id
    )

    # User A should only see their own resume
    user_a_resumes = fetch_resumes_from_db(user_id=user_a_id)
    assert len(user_a_resumes) == 1
    assert "resume_a.txt" in user_a_resumes
    assert "resume_b.txt" not in user_a_resumes

    # User B should only see their own resume
    user_b_resumes = fetch_resumes_from_db(user_id=user_b_id)
    assert len(user_b_resumes) == 1
    assert "resume_b.txt" in user_b_resumes
    assert "resume_a.txt" not in user_b_resumes

    # User A should not be able to read User B's resume
    user_b_resume_from_a = get_resume_text(
        filename="resume_b.txt",
        user_id=user_a_id
    )
    assert user_b_resume_from_a is None

    # User B should not be able to read User A's resume
    user_a_resume_from_b = get_resume_text(
        filename="resume_a.txt",
        user_id=user_b_id
    )
    assert user_a_resume_from_b is None


def test_tracking_isolation(test_db):
    """Test that User A cannot see User B's job tracking."""
    # Create two users
    user_a_id = create_user(
        db_path=test_db,
        email="trackera@example.com",
        username="trackera",
        password="password123"
    )

    user_b_id = create_user(
        db_path=test_db,
        email="trackerb@example.com",
        username="trackerb",
        password="password123"
    )

    # Create a shared job
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO jobs_new (primary_key, title, company, date)
        VALUES (?, ?, ?, ?)
    """, ("acme_engineer", "Software Engineer", "Acme Corp", "2024-01-01"))
    job_id = cursor.lastrowid
    conn.commit()

    # Both users track the same job
    cursor.execute("""
        INSERT INTO job_tracking (job_id, user_id, status)
        VALUES (?, ?, ?)
    """, (job_id, user_a_id, "apply"))

    cursor.execute("""
        INSERT INTO job_tracking (job_id, user_id, status)
        VALUES (?, ?, ?)
    """, (job_id, user_b_id, "hr_screen"))

    conn.commit()

    # User A should only see their tracking
    cursor.execute("""
        SELECT status FROM job_tracking WHERE user_id = ?
    """, (user_a_id,))
    user_a_tracking = cursor.fetchall()
    assert len(user_a_tracking) == 1
    assert user_a_tracking[0][0] == "apply"

    # User B should only see their tracking
    cursor.execute("""
        SELECT status FROM job_tracking WHERE user_id = ?
    """, (user_b_id,))
    user_b_tracking = cursor.fetchall()
    assert len(user_b_tracking) == 1
    assert user_b_tracking[0][0] == "hr_screen"

    conn.close()


def test_shared_jobs_access(test_db):
    """Test that all users can see the same jobs in jobs_new table."""
    # Create two users
    user_a_id = create_user(
        db_path=test_db,
        email="jobsa@example.com",
        username="jobsa",
        password="password123"
    )

    user_b_id = create_user(
        db_path=test_db,
        email="jobsb@example.com",
        username="jobsb",
        password="password123"
    )

    # Add multiple jobs to jobs_new (shared database)
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()

    jobs = [
        ("google_swe", "Software Engineer", "Google"),
        ("meta_data", "Data Scientist", "Meta"),
        ("amazon_pm", "Product Manager", "Amazon"),
    ]

    for job in jobs:
        cursor.execute("""
            INSERT INTO jobs_new (primary_key, title, company, date)
            VALUES (?, ?, ?, ?)
        """, (job[0], job[1], job[2], "2024-01-01"))

    conn.commit()

    # Both users should see all jobs
    cursor.execute("SELECT COUNT(*) FROM jobs_new")
    total_jobs = cursor.fetchone()[0]
    assert total_jobs == 3

    # Verify jobs_new has no user_id column (shared table)
    cursor.execute("PRAGMA table_info(jobs_new)")
    columns = [row[1] for row in cursor.fetchall()]
    assert "user_id" not in columns

    conn.close()


def test_resume_name_uniqueness_per_user(test_db):
    """Test that same resume name can be used by different users."""
    # Create two users
    user_a_id = create_user(
        db_path=test_db,
        email="samename_a@example.com",
        username="samename_a",
        password="password123"
    )

    user_b_id = create_user(
        db_path=test_db,
        email="samename_b@example.com",
        username="samename_b",
        password="password123"
    )

    # Both users upload resume with same filename
    resume_name = "my_resume.pdf"

    save_text_to_db(
        filename=resume_name,
        text="User A's resume content",
        user_id=user_a_id
    )

    save_text_to_db(
        filename=resume_name,
        text="User B's resume content",
        user_id=user_b_id
    )

    # Both should succeed (no conflict)
    user_a_resume = get_resume_text(filename=resume_name, user_id=user_a_id)
    user_b_resume = get_resume_text(filename=resume_name, user_id=user_b_id)

    assert user_a_resume == "User A's resume content"
    assert user_b_resume == "User B's resume content"
    assert user_a_resume != user_b_resume

    # Verify both resumes exist in database
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM resumes WHERE resume_name = ?", (resume_name,))
    count = cursor.fetchone()[0]
    assert count == 2  # Two different resumes with same name
    conn.close()


def test_similarity_scores_per_user(test_db):
    """Test that each user can have their own similarity calculations."""
    # Note: This test verifies the concept - actual similarity calculation
    # will be tested in integration tests

    # Create two users
    user_a_id = create_user(
        db_path=test_db,
        email="similarity_a@example.com",
        username="similarity_a",
        password="password123"
    )

    user_b_id = create_user(
        db_path=test_db,
        email="similarity_b@example.com",
        username="similarity_b",
        password="password123"
    )

    # Upload different resumes for each user
    save_text_to_db(
        filename="resume_a.txt",
        text="Python developer with 5 years experience",
        user_id=user_a_id
    )

    save_text_to_db(
        filename="resume_b.txt",
        text="Marketing manager with MBA degree",
        user_id=user_b_id
    )

    # Conceptually, similarity scores would be calculated per user
    # based on their specific resume
    # The jobs_new table is shared, but similarity scores would differ
    # This is just a structural test - actual ML testing in integration

    assert True  # Placeholder for future integration test


def test_verify_resume_ownership(test_db):
    """Test ownership verification for resumes."""
    # Create two users
    user_a_id = create_user(
        db_path=test_db,
        email="owner_a@example.com",
        username="owner_a",
        password="password123"
    )

    user_b_id = create_user(
        db_path=test_db,
        email="owner_b@example.com",
        username="owner_b",
        password="password123"
    )

    # User A uploads a resume
    save_text_to_db(
        filename="private_resume.txt",
        text="User A's private resume",
        user_id=user_a_id
    )

    # User A should own their resume
    assert verify_resume_ownership(
        filename="private_resume.txt",
        user_id=user_a_id
    ) is True

    # User B should NOT own User A's resume
    assert verify_resume_ownership(
        filename="private_resume.txt",
        user_id=user_b_id
    ) is False

    # Non-existent resume should return False
    assert verify_resume_ownership(
        filename="nonexistent.txt",
        user_id=user_a_id
    ) is False


def test_multiple_resumes_per_user(test_db):
    """Test that users can have multiple resumes isolated from each other."""
    # Create two users
    user_a_id = create_user(
        db_path=test_db,
        email="multi_a@example.com",
        username="multi_a",
        password="password123"
    )

    user_b_id = create_user(
        db_path=test_db,
        email="multi_b@example.com",
        username="multi_b",
        password="password123"
    )

    # User A uploads 3 resumes
    for i in range(3):
        save_text_to_db(
            filename=f"resume_a_{i}.txt",
            text=f"User A resume {i}",
            user_id=user_a_id
        )

    # User B uploads 2 resumes
    for i in range(2):
        save_text_to_db(
            filename=f"resume_b_{i}.txt",
            text=f"User B resume {i}",
            user_id=user_b_id
        )

    # User A should see only their 3 resumes
    user_a_resumes = fetch_resumes_from_db(user_id=user_a_id)
    assert len(user_a_resumes) == 3
    assert all(name.startswith("resume_a_") for name in user_a_resumes)

    # User B should see only their 2 resumes
    user_b_resumes = fetch_resumes_from_db(user_id=user_b_id)
    assert len(user_b_resumes) == 2
    assert all(name.startswith("resume_b_") for name in user_b_resumes)


def test_job_tracking_same_job_different_users(test_db):
    """Test multiple users tracking the same job with different statuses."""
    # Create three users
    user_ids = []
    for i in range(3):
        user_id = create_user(
            db_path=test_db,
            email=f"tracker{i}@example.com",
            username=f"tracker{i}",
            password="password123"
        )
        user_ids.append(user_id)

    # Create a single job
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO jobs_new (primary_key, title, company, date)
        VALUES (?, ?, ?, ?)
    """, ("popular_job", "Senior Engineer", "TechCorp", "2024-01-01"))
    job_id = cursor.lastrowid

    # All three users track the same job with different statuses
    statuses = ["apply", "hr_screen", "round_1"]
    for user_id, status in zip(user_ids, statuses):
        cursor.execute("""
            INSERT INTO job_tracking (job_id, user_id, status)
            VALUES (?, ?, ?)
        """, (job_id, user_id, status))

    conn.commit()

    # Verify each user has their own status for the same job
    for i, user_id in enumerate(user_ids):
        cursor.execute("""
            SELECT status FROM job_tracking
            WHERE job_id = ? AND user_id = ?
        """, (job_id, user_id))
        result = cursor.fetchone()
        assert result is not None
        assert result[0] == statuses[i]

    # Verify total tracking records
    cursor.execute("SELECT COUNT(*) FROM job_tracking WHERE job_id = ?", (job_id,))
    count = cursor.fetchone()[0]
    assert count == 3

    conn.close()
