import logging


# === General Configs ===
LOGGING_LEVEL = logging.DEBUG


# === Database Configs ===
DATABASE = "jobhunter.db"
TABLE_JOBS = "jobs"
TABLE_RESUMES = "resumes"
TABLE_APPLICATIONS = "applications"


# === API Configs ===
JOB_SEARCH_URL = "https://linkedin-jobs-search.p.rapidapi.com/"
JOB_SEARCH_X_RAPIDAPI_HOST = "linkedin-jobs-search.p.rapidapi.com"


# == Job Search Configs ===

FILENAMES = "linkedinjob"

POSITIONS = [
    "Principal Machine Learning",
    "Data Scientist",
    "Machine Learning Engineer",
    "AI/ML Architect",
    "AI/ML Developer",
    "Principal Machine Learning Engineer",
    "Senior Data Scientist",
    "Lead Data Scientist",
    "Machine Learning Operations Engineer",
]

# List of locations
LOCATIONS = ["remote"]

# Pagination for API calls
PAGES = 1


# === Model Configs ===
VECTOR_SIZE = 50
WINDOW = 2
MIN_COUNT = 1
WORKERS = 4
EPOCHS = 100
