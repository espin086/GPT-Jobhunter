"""
This tests the search_linkedin_jobs.py module.
"""

import os
import sys

from dotenv import load_dotenv

# Add the directory containing search_linkedin_jobs.py to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from search_linkedin_jobs import RAPID_API_KEY, search_linkedin_jobs


def test_search_linkedin_jobs():
    """
    This is a test function for search_linkedin_jobs().
    """
    search_term = "Software Engineer"
    location = "United States"
    page = 1
    result = search_linkedin_jobs(search_term, location, page)
    assert result is not None and result != {
        "message": "You are not subscribed to this API."
    }


def test_check_api_key():
    """
    This is a test function for api key availability.
    """
    assert RAPID_API_KEY is not None


def test_search_linkedin_jobs():
    """
    This is a test function for search_linkedin_jobs().
    """
    search_term = "Software Engineer"
    location = "United States"
    page = 1
    result = search_linkedin_jobs(search_term, location, page)
    assert result is not None and result != {
        "message": "You are not subscribed to this API."
    }
