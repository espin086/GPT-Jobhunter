import logging
import os
from pathlib import Path

# === General Configs ===
LOGGING_LEVEL = logging.INFO


# === Data Configs ===
CWD_PATH = Path(os.getcwd())
RAW_DATA_PATH = Path(f"{CWD_PATH}/temp/data/raw").resolve()
PROCESSED_DATA_PATH = Path(f"{CWD_PATH}/temp/data/processed").resolve()
RESUME_PATH = Path(f"{CWD_PATH}/temp/resumes/resume.txt").resolve()


# === Database Configs ===
DATABASE = "all_jobs.db"
TABLE_JOBS_NEW = "jobs_new"
TABLE_RESUMES = "resumes"
TABLE_APPLICATIONS = "applications"


# === API Configs ===
JOB_SEARCH_URL = "https://jsearch.p.rapidapi.com/search"
JOB_SEARCH_X_RAPIDAPI_HOST = "jsearch.p.rapidapi.com"


# == Job Search Configs ===
FILENAMES = "jobs"

POSITIONS = [
    "Vice President of Data Science",
    "Vice President of Machine Learning",
    "Vice President of Data Engineering",
    "Vice President of Artificial Intelligence",
    "Head of Data Science",
    "Head of Machine Learning",
    "Head of Data Engineering",
    "Head of Artificial Intelligence",
    "Senior Director of Data Science",
    "Senior Director of Machine Learning",
    "Senior Director of Data Engineering",
    "Senior Director of Artificial Intelligence",
    "Director of Data Science",
    "Director of Machine Learning",
    "Director of Data Engineering",
    "Director of Artificial Intelligence",
    "Principal Data Scientist",
    "Principal Machine Learning Engineer",
    "Principal Artificial Intelligence Engineer",
    "Principal Data Engineer",
    "Manager Machine Learning Engineering",
    "Manager Artificial Intelligence ",
    "Manager Data Science",
    "Manager Data Engineering",
    "Senior Machine Learning Engineer",
    "Senior Artificial Intelligence Engineer",
    "Senior Data Scientist",
    "Senior Data Engineer",
    "Lead Machine Learning Engineer",
    "Lead Artificial Intelligence Engineer",
    "Lead Data Scientist",
    "Lead Data Engineer",
]

# Enabling the remote jobs research
remote_jobs_only = ["true"]

# Pagination for API calls
PAGES = 10

# === Model Configs ===
VECTOR_SIZE = 50
WINDOW = 2
MIN_COUNT = 1
WORKERS = 4
EPOCHS = 100