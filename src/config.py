import logging

# === General Configs ===
LOGGING_LEVEL = logging.INFO


# === Database Configs ===
DATABASE = "all_jobs.db"
TABLE_JOBS = "jobs"
TABLE_RESUMES = "resumes"
TABLE_APPLICATIONS = "applications"


# === API Configs ===
JOB_SEARCH_URL = "https://linkedin-jobs-search.p.rapidapi.com/"
JOB_SEARCH_X_RAPIDAPI_HOST = "linkedin-jobs-search.p.rapidapi.com"


# == Job Search Configs ===

FILENAMES = "linkedinjob"

POSITIONS = [
    "Principal Machine Learning Engineer",
    "Senior Machine Learning Engineer",
    "Senior Artificial Intelligence Engineer",
    "Senior Data Scientist",
    "Principal Data Scientist",
    "Lead Machine Learning Engineer",
    "Lead Artificial Intelligence Engineer",
    "Lead Data Scientist",
    "Machine Learning Architect",
    "AI Research Scientist",
    "Machine Learning Consultant",
    "Data Science Manager",
    "Data Science Team Lead",
    "AI Solutions Architect",
    "AI Product Manager",
]

# List of locations
LOCATIONS = ["remote"]

# Pagination for API calls
PAGES = 5


# === Model Configs ===
VECTOR_SIZE = 50
WINDOW = 2
MIN_COUNT = 1
WORKERS = 4
EPOCHS = 100
