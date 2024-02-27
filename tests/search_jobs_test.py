"""
This tests the search_jobs.py module.
"""

import os
import sys

from dotenv import load_dotenv

# Add the directory containing search_linkedin_jobs.py to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from jobhunter.search_jobs import RAPID_API_KEY, search_jobs


def test_search_linkedin_jobs():
    """
    This is a test function for search_jobs().
    """
    search_term = "Software Engineer"
    page = 1
    result = search_jobs(search_term, page)
    assert result is not None and result != {
        "message": "You are not subscribed to this API."
    }


def test_check_api_key():
    """
    This is a test function for api key availability.
    """
    assert RAPID_API_KEY is not None