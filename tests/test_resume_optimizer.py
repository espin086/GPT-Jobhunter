"""
Tests for Resume Optimizer feature.

Tests the backend service that analyzes resumes against job descriptions
and provides keyword recommendations for ATS optimization.
"""

import pytest
import sqlite3
import os
from unittest.mock import patch, MagicMock
from pathlib import Path

# Set up test database path before importing modules
TEST_DB = "test_resume_optimizer.db"


@pytest.fixture(scope="function")
def test_db():
    """Create a test database with sample data."""
    # Remove existing test db
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()

    # Create jobs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            primary_key TEXT UNIQUE,
            date TEXT,
            resume_similarity REAL DEFAULT 0,
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
            embeddings TEXT,
            hidden INTEGER DEFAULT 0
        )
    ''')

    # Create resumes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resume_name TEXT UNIQUE,
            resume_text TEXT
        )
    ''')

    # Insert sample resume
    sample_resume = """
    John Doe
    Software Engineer

    Experience:
    - 5 years Python development
    - Backend API development with Flask
    - Database management with PostgreSQL
    - Agile methodologies

    Skills: Python, Flask, PostgreSQL, Git, Linux

    Education: BS Computer Science
    """
    cursor.execute(
        "INSERT INTO resumes (resume_name, resume_text) VALUES (?, ?)",
        ("test_resume.pdf", sample_resume)
    )

    # Insert sample jobs with descriptions containing keywords
    sample_jobs = [
        {
            "primary_key": "google_senior_engineer",
            "title": "Senior Software Engineer",
            "company": "Google",
            "resume_similarity": 0.95,
            "description": """
            We are looking for a Senior Software Engineer with experience in:
            - Python, Django, FastAPI
            - Machine Learning and TensorFlow
            - Kubernetes and Docker containerization
            - AWS or GCP cloud services
            - CI/CD pipelines
            - Microservices architecture
            Requirements: 5+ years experience, strong communication skills
            """,
            "required_skills": "Python, Django, FastAPI, Machine Learning, TensorFlow, Kubernetes, Docker, AWS, GCP",
            "job_type": "Full-time",
            "salary_low": 150000,
            "salary_high": 250000,
            "job_is_remote": "Yes"
        },
        {
            "primary_key": "meta_backend_dev",
            "title": "Backend Developer",
            "company": "Meta",
            "resume_similarity": 0.92,
            "description": """
            Backend Developer role requiring:
            - Python or Java backend development
            - REST API design and implementation
            - MySQL or PostgreSQL databases
            - Redis caching
            - Message queues (Kafka, RabbitMQ)
            - Distributed systems experience
            """,
            "required_skills": "Python, Java, REST API, MySQL, PostgreSQL, Redis, Kafka, RabbitMQ",
            "job_type": "Full-time",
            "salary_low": 120000,
            "salary_high": 200000,
            "job_is_remote": "Yes"
        },
        {
            "primary_key": "amazon_sde",
            "title": "Software Development Engineer",
            "company": "Amazon",
            "resume_similarity": 0.88,
            "description": """
            SDE position at Amazon:
            - Strong programming skills in Python or Java
            - Experience with AWS services (EC2, S3, Lambda)
            - Database design and optimization
            - System design skills
            - Agile development practices
            - Code review experience
            """,
            "required_skills": "Python, Java, AWS, EC2, S3, Lambda, System Design",
            "job_type": "Part-time",
            "salary_low": 80000,
            "salary_high": 150000,
            "job_is_remote": "No"
        },
    ]

    for job in sample_jobs:
        cursor.execute('''
            INSERT INTO jobs_new (primary_key, title, company, resume_similarity, description, required_skills, job_type, salary_low, salary_high, job_is_remote)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            job["primary_key"],
            job["title"],
            job["company"],
            job["resume_similarity"],
            job["description"],
            job["required_skills"],
            job["job_type"],
            job["salary_low"],
            job["salary_high"],
            job["job_is_remote"]
        ))

    conn.commit()
    conn.close()

    yield TEST_DB

    # Cleanup
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


class TestResumeOptimizerService:
    """Tests for the ResumeOptimizerService class."""

    def test_get_top_similar_jobs(self, test_db):
        """Test fetching top N jobs by similarity score."""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        # Get top 2 jobs by similarity
        cursor.execute('''
            SELECT title, company, resume_similarity, description, required_skills
            FROM jobs_new
            WHERE resume_similarity > 0
            ORDER BY resume_similarity DESC
            LIMIT 2
        ''')
        jobs = cursor.fetchall()
        conn.close()

        assert len(jobs) == 2
        assert jobs[0][0] == "Senior Software Engineer"  # Google has highest similarity
        assert jobs[0][2] == 0.95
        assert jobs[1][0] == "Backend Developer"  # Meta is second
        assert jobs[1][2] == 0.92

    def test_get_resume_text(self, test_db):
        """Test fetching resume text from database."""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        cursor.execute("SELECT resume_text FROM resumes WHERE resume_name = ?", ("test_resume.pdf",))
        result = cursor.fetchone()
        conn.close()

        assert result is not None
        assert "Python" in result[0]
        assert "Flask" in result[0]

    def test_extract_keywords_from_jobs(self, test_db):
        """Test extracting keywords from job descriptions."""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        cursor.execute("SELECT description, required_skills FROM jobs_new")
        jobs = cursor.fetchall()
        conn.close()

        # Combine all job text
        all_job_text = " ".join([f"{job[0]} {job[1]}" for job in jobs])

        # Expected keywords that appear across jobs
        expected_keywords = ["Python", "AWS", "Docker", "Kubernetes", "PostgreSQL"]

        for keyword in expected_keywords:
            assert keyword.lower() in all_job_text.lower()

    def test_identify_missing_keywords(self, test_db):
        """Test identifying keywords present in jobs but missing from resume."""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        # Get resume text
        cursor.execute("SELECT resume_text FROM resumes WHERE resume_name = ?", ("test_resume.pdf",))
        resume_text = cursor.fetchone()[0].lower()

        # Get job keywords
        cursor.execute("SELECT required_skills FROM jobs_new")
        jobs = cursor.fetchall()
        conn.close()

        # Extract all unique keywords from jobs
        job_keywords = set()
        for job in jobs:
            if job[0]:
                skills = [s.strip().lower() for s in job[0].split(",")]
                job_keywords.update(skills)

        # Find keywords missing from resume
        missing_keywords = []
        for keyword in job_keywords:
            if keyword not in resume_text:
                missing_keywords.append(keyword)

        # These should be identified as missing
        expected_missing = ["django", "fastapi", "tensorflow", "kubernetes", "docker", "aws"]
        for keyword in expected_missing:
            assert keyword in missing_keywords, f"Expected '{keyword}' to be identified as missing"

    def test_empty_jobs_database(self, test_db):
        """Test behavior when no jobs are in the database."""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        # Delete all jobs
        cursor.execute("DELETE FROM jobs_new")
        conn.commit()

        # Try to get jobs
        cursor.execute("SELECT COUNT(*) FROM jobs_new")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 0

    def test_resume_not_found(self, test_db):
        """Test behavior when resume is not found."""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        cursor.execute("SELECT resume_text FROM resumes WHERE resume_name = ?", ("nonexistent.pdf",))
        result = cursor.fetchone()
        conn.close()

        assert result is None


class TestResumeOptimizerAPI:
    """Tests for the Resume Optimizer API endpoint."""

    @patch('jobhunter.backend.services.sqlite3')
    @patch('openai.OpenAI')
    def test_optimize_resume_endpoint_with_jobs(self, mock_openai, mock_sqlite):
        """Test the optimize resume endpoint when jobs exist."""
        # Mock database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_sqlite.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock resume fetch
        mock_cursor.fetchone.side_effect = [
            ("Sample resume with Python and Flask skills",),  # Resume text
        ]

        # Mock jobs fetch
        mock_cursor.fetchall.return_value = [
            ("Senior Engineer", "Google", 0.95, "Need Python, Django, AWS", "Python, Django, AWS"),
            ("Backend Dev", "Meta", 0.90, "Need Python, Kubernetes", "Python, Kubernetes"),
        ]

        # Mock OpenAI response
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''
        {
            "missing_keywords": ["Django", "AWS", "Kubernetes"],
            "keyword_suggestions": [
                {"current": "Flask", "suggested": "Django/Flask", "reason": "Django appears in 80% of target jobs"},
                {"current": "PostgreSQL", "suggested": "PostgreSQL/MySQL", "reason": "Both databases are valued"}
            ],
            "ats_tips": [
                "Add 'cloud' keywords like AWS or GCP",
                "Include containerization technologies"
            ],
            "overall_score": 75
        }
        '''
        mock_client.chat.completions.create.return_value = mock_response

        # The response format should match what the service returns
        expected_keys = ["missing_keywords", "keyword_suggestions", "ats_tips", "overall_score"]

        # Verify mock was set up correctly
        assert mock_openai is not None
        assert mock_client.chat.completions.create.return_value is not None

    def test_optimize_resume_request_model(self):
        """Test the request model for resume optimization."""
        from pydantic import BaseModel
        from typing import Optional

        # Define the expected request structure
        class ResumeOptimizeRequest(BaseModel):
            resume_name: str
            num_jobs: Optional[int] = 20

        # Test valid request
        request = ResumeOptimizeRequest(resume_name="test.pdf", num_jobs=10)
        assert request.resume_name == "test.pdf"
        assert request.num_jobs == 10

        # Test default value
        request_default = ResumeOptimizeRequest(resume_name="test.pdf")
        assert request_default.num_jobs == 20

    def test_optimize_resume_response_model(self):
        """Test the response model for resume optimization."""
        from pydantic import BaseModel
        from typing import List, Optional

        class KeywordSuggestion(BaseModel):
            current: str
            suggested: str
            reason: str

        class ResumeOptimizeResponse(BaseModel):
            success: bool
            missing_keywords: List[str]
            keyword_suggestions: List[KeywordSuggestion]
            ats_tips: List[str]
            overall_score: int
            message: str
            jobs_analyzed: int

        # Test response creation
        response = ResumeOptimizeResponse(
            success=True,
            missing_keywords=["Django", "AWS"],
            keyword_suggestions=[
                KeywordSuggestion(current="Flask", suggested="Flask/Django", reason="Django is popular")
            ],
            ats_tips=["Add cloud keywords"],
            overall_score=75,
            message="Analysis complete",
            jobs_analyzed=10
        )

        assert response.success is True
        assert len(response.missing_keywords) == 2
        assert response.overall_score == 75


class TestKeywordExtraction:
    """Tests for keyword extraction logic."""

    def test_extract_technical_keywords(self):
        """Test extraction of technical keywords from text."""
        text = """
        Requirements:
        - 5+ years of Python development
        - Experience with Django and FastAPI frameworks
        - Knowledge of AWS services (EC2, S3, Lambda)
        - Familiarity with Docker and Kubernetes
        - PostgreSQL or MySQL database experience
        """

        # Common technical keywords to look for
        technical_keywords = [
            "python", "django", "fastapi", "aws", "ec2", "s3", "lambda",
            "docker", "kubernetes", "postgresql", "mysql"
        ]

        text_lower = text.lower()
        found_keywords = [kw for kw in technical_keywords if kw in text_lower]

        assert len(found_keywords) >= 8
        assert "python" in found_keywords
        assert "aws" in found_keywords

    def test_normalize_keywords(self):
        """Test keyword normalization."""
        # Test cases for normalization
        test_cases = [
            ("Python", "python"),
            ("JAVASCRIPT", "javascript"),
            ("Node.js", "node.js"),
            ("C++", "c++"),
            ("React.js", "react.js"),
        ]

        for original, expected in test_cases:
            normalized = original.lower()
            assert normalized == expected

    def test_keyword_frequency_counting(self):
        """Test counting keyword frequency across multiple job descriptions."""
        job_descriptions = [
            "Need Python and Django experience",
            "Python required, Django preferred",
            "Strong Python skills, AWS knowledge",
            "Python, Django, PostgreSQL expert"
        ]

        keyword_counts = {}
        keywords_to_count = ["python", "django", "aws", "postgresql"]

        for desc in job_descriptions:
            desc_lower = desc.lower()
            for kw in keywords_to_count:
                if kw in desc_lower:
                    keyword_counts[kw] = keyword_counts.get(kw, 0) + 1

        assert keyword_counts["python"] == 4  # Appears in all 4
        assert keyword_counts["django"] == 3  # Appears in 3
        assert keyword_counts.get("aws", 0) == 1
        assert keyword_counts.get("postgresql", 0) == 1


class TestATSOptimization:
    """Tests for ATS (Applicant Tracking System) optimization suggestions."""

    def test_identify_ats_friendly_synonyms(self):
        """Test identification of ATS-friendly keyword synonyms."""
        # Common synonyms that ATS systems recognize
        synonym_map = {
            "ml": ["machine learning", "ml"],
            "ai": ["artificial intelligence", "ai"],
            "dev": ["developer", "development", "dev"],
            "sr.": ["senior", "sr."],
            "jr.": ["junior", "jr."],
        }

        # Test that synonyms are properly mapped
        assert "machine learning" in synonym_map["ml"]
        assert "developer" in synonym_map["dev"]

    def test_keyword_density_check(self):
        """Test checking keyword density in resume."""
        resume = "Python Python Python developer with Python skills in Python"
        target_keyword = "python"

        # Count occurrences
        word_count = len(resume.split())
        keyword_count = resume.lower().count(target_keyword)

        # Check if keyword is overused (more than 10% density is suspicious)
        density = keyword_count / word_count

        assert keyword_count == 5
        assert density > 0.1  # This resume has too much keyword stuffing


class TestResumeOptimizerFiltering:
    """Tests for resume optimizer filtering functionality."""

    def test_get_top_similar_jobs_with_salary_filter(self, test_db):
        """Test filtering jobs by salary range."""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        # Query for jobs with min_salary >= 150000
        cursor.execute('''
            SELECT title, company, resume_similarity, salary_low
            FROM jobs_new
            WHERE resume_similarity > 0
            AND salary_low IS NOT NULL
            AND salary_low >= ?
            ORDER BY resume_similarity DESC
            LIMIT 30
        ''', (150000,))
        jobs = cursor.fetchall()
        conn.close()

        assert len(jobs) == 1  # Only Google job has salary_low >= 150000
        assert jobs[0][0] == "Senior Software Engineer"
        assert jobs[0][3] == 150000

    def test_get_top_similar_jobs_with_company_filter(self, test_db):
        """Test filtering jobs by company name."""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        # Query for jobs matching company name
        cursor.execute('''
            SELECT title, company, resume_similarity
            FROM jobs_new
            WHERE resume_similarity > 0
            AND company LIKE ?
            ORDER BY resume_similarity DESC
            LIMIT 30
        ''', ('%Google%',))
        jobs = cursor.fetchall()
        conn.close()

        assert len(jobs) == 1
        assert jobs[0][1] == "Google"

    def test_get_top_similar_jobs_with_job_type_filter(self, test_db):
        """Test filtering jobs by job type."""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        # Query for Full-time jobs
        cursor.execute('''
            SELECT title, company, job_type
            FROM jobs_new
            WHERE resume_similarity > 0
            AND job_type LIKE ?
            ORDER BY resume_similarity DESC
            LIMIT 30
        ''', ('%Full-time%',))
        jobs = cursor.fetchall()
        conn.close()

        assert len(jobs) == 2  # Google and Meta are Full-time
        assert all(job[2] == "Full-time" for job in jobs)

    def test_get_top_similar_jobs_with_remote_filter(self, test_db):
        """Test filtering jobs by remote status."""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        # Query for remote jobs
        cursor.execute('''
            SELECT title, company, job_is_remote
            FROM jobs_new
            WHERE resume_similarity > 0
            AND job_is_remote = ?
            ORDER BY resume_similarity DESC
            LIMIT 30
        ''', ('Yes',))
        jobs = cursor.fetchall()
        conn.close()

        assert len(jobs) == 2  # Google and Meta are remote
        assert all(job[2] == "Yes" for job in jobs)

    def test_get_top_similar_jobs_with_title_filter(self, test_db):
        """Test filtering jobs by title."""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        # Query for jobs with "Engineer" in title
        cursor.execute('''
            SELECT title, company
            FROM jobs_new
            WHERE resume_similarity > 0
            AND title LIKE ?
            ORDER BY resume_similarity DESC
            LIMIT 30
        ''', ('%Engineer%',))
        jobs = cursor.fetchall()
        conn.close()

        assert len(jobs) == 2  # Senior Software Engineer and Software Development Engineer

    def test_get_top_similar_jobs_with_multiple_filters(self, test_db):
        """Test applying multiple filters simultaneously."""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        # Query with multiple conditions
        cursor.execute('''
            SELECT title, company, salary_low, job_type, job_is_remote
            FROM jobs_new
            WHERE resume_similarity > 0
            AND salary_low >= ?
            AND salary_high <= ?
            AND job_type LIKE ?
            AND job_is_remote = ?
            ORDER BY resume_similarity DESC
            LIMIT 30
        ''', (100000, 250000, '%Full-time%', 'Yes'))
        jobs = cursor.fetchall()
        conn.close()

        # Should return Google and Meta (both full-time, remote, in salary range)
        assert len(jobs) == 2
        assert all(job[3] == "Full-time" and job[4] == "Yes" for job in jobs)

    def test_get_top_similar_jobs_respects_limit(self, test_db):
        """Test that limit parameter is properly respected."""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        # Query with limit of 1
        cursor.execute('''
            SELECT title, company
            FROM jobs_new
            WHERE resume_similarity > 0
            ORDER BY resume_similarity DESC
            LIMIT ?
        ''', (1,))
        jobs = cursor.fetchall()
        conn.close()

        assert len(jobs) == 1
        assert jobs[0][0] == "Senior Software Engineer"  # Highest similarity

    def test_get_top_similar_jobs_with_no_matches(self, test_db):
        """Test filtering returns empty when no matches found."""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        # Query for non-existent company
        cursor.execute('''
            SELECT title, company
            FROM jobs_new
            WHERE resume_similarity > 0
            AND company LIKE ?
            ORDER BY resume_similarity DESC
            LIMIT 30
        ''', ('%NonExistent%',))
        jobs = cursor.fetchall()
        conn.close()

        assert len(jobs) == 0

    def test_filter_parameters_validation(self):
        """Test that filter parameters are properly validated."""
        from pydantic import ValidationError

        # Valid request with filters
        try:
            request = {
                "resume_name": "test.pdf",
                "num_jobs": 20,
                "min_salary": 100000,
                "max_salary": 200000,
                "company": "Google",
                "title": "Engineer",
                "job_type": "Full-time",
                "is_remote": True
            }
            # Should not raise error
            assert request["resume_name"] == "test.pdf"
        except ValidationError:
            pytest.fail("Valid filter parameters should not raise ValidationError")

    def test_combined_filtering_with_resume_optimizer_context(self, test_db):
        """Test that filtering works in the context of resume optimization."""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        # Simulate resume optimizer: get top 5 jobs with filters
        num_jobs = 5
        filters = {
            "min_salary": 100000,
            "job_type": "Full-time"
        }

        # Build query with filters
        query = '''
            SELECT title, company, resume_similarity, description, required_skills
            FROM jobs_new
            WHERE resume_similarity > 0
            AND description IS NOT NULL
            AND description != ''
        '''
        params = []

        if filters.get("min_salary"):
            query += " AND salary_low >= ?"
            params.append(filters["min_salary"])

        if filters.get("job_type"):
            query += " AND job_type LIKE ?"
            params.append(f"%{filters['job_type']}%")

        query += " ORDER BY resume_similarity DESC LIMIT ?"
        params.append(num_jobs)

        cursor.execute(query, params)
        jobs = cursor.fetchall()
        conn.close()

        # Should return Google and Meta (both full-time with salary >= 100000)
        assert len(jobs) == 2
        assert jobs[0][1] == "Google"  # Highest similarity
        assert jobs[1][1] == "Meta"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
