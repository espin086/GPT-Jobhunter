"""
This tests the search_linkedin_jobs.py module.
"""

import os


from search_linkedin_jobs import search_linkedin_jobs
from search_linkedin_jobs import RAPID_API_KEY


# Get the directory where the script is located
script_directory = os.path.dirname(os.path.abspath(__file__))

# Change the working directory to the script's directory
os.chdir(script_directory)


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
    assert result is not None
