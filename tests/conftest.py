import os
import sys
import pytest
from pathlib import Path

# Add project root to Python path for test imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Ensure API keys are available from environment before tests run
@pytest.fixture(scope="session", autouse=True)
def ensure_env_variables():
    """Make sure necessary environment variables are set."""
    from dotenv import load_dotenv
    
    # Try multiple locations for .env file using relative paths
    # This works both locally and in Docker
    
    # Try current directory first
    if os.path.exists(".env"):
        load_dotenv(".env")
    
    # Try project root
    project_root = Path(__file__).parent.parent
    if os.path.exists(project_root / ".env"):
        load_dotenv(project_root / ".env")
    
    # Skip API-dependent tests if OPENAI_API_KEY is not available
    if not os.environ.get("OPENAI_API_KEY"):
        print("WARNING: OPENAI_API_KEY environment variable not set - some tests may be skipped")

@pytest.fixture
def test_text_pair():
    """Return a pair of texts for similarity testing."""
    return (
        "Software developer with experience in Python, machine learning, and web development.",
        "Looking for a Python programmer with AI skills for a web application project."
    )

@pytest.fixture
def sample_resume_text():
    """Return a sample resume text for testing."""
    return """
    John Doe
    Software Engineer
    
    EXPERIENCE
    Senior Python Developer, ABC Tech (2020-Present)
    - Developed machine learning models for data analysis
    - Built RESTful APIs using FastAPI and Flask
    - Led a team of 5 developers on various projects
    
    Software Engineer, XYZ Solutions (2018-2020)
    - Implemented CI/CD pipelines using GitHub Actions
    - Developed microservices architecture for scaling applications
    
    SKILLS
    Languages: Python, JavaScript, SQL
    Frameworks: Flask, FastAPI, React, Django
    Tools: Docker, Kubernetes, Git
    Cloud: AWS, Azure
    
    EDUCATION
    M.S. Computer Science, Stanford University (2018)
    B.S. Computer Engineering, MIT (2016)
    """

@pytest.fixture
def mock_job_text():
    """Return a sample job description text for testing."""
    return """
    Senior Python Developer
    
    Company: Tech Innovations Inc.
    Location: Remote
    
    Job Description:
    We're looking for an experienced Python developer to join our team. The ideal candidate
    will have strong experience with machine learning, data analysis, and web development.
    
    Requirements:
    - 3+ years of experience with Python
    - Familiarity with machine learning frameworks
    - Experience with RESTful APIs
    - Knowledge of cloud technologies (AWS or Azure)
    
    Benefits:
    - Competitive salary
    - Remote work options
    - Health insurance
    - 401k matching
    """ 