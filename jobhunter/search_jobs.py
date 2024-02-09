"""
This module uses the L Jobs API to search for jobs by providing a search term,
location and an optional page number. The module utilizes the requests and json libraries to make
the API request and parse the response, respectively. Additionally, the module employs the logging
and argparse libraries to set up logging and command-line arguments, and the pprint library to
print the results in a pretty format. The main function in the module is 'search_linkedin_jobs()'
which takes in a search term, location and an optional page number as input and returns a json
object containing job search results that match the search term and location provided. The module
also uses the os library to access the API key as an environment variable. The main function in
the module is 'main()' which performs a job search using the 'search__jobs()'
function and returns the json object returned by the  jobs API.
The module also defines a command-line imnterface for running the script.
"""

import argparse
import json
import logging
import os
import pprint
from typing import Dict, List, Mapping, Union

import requests
from dotenv import load_dotenv

import config

# Add the path to the .env file
dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")

load_dotenv(dotenv_path)


# Get the API key from the environment variable
RAPID_API_KEY = os.environ.get("RAPID_API_KEY")

# Get the API URL from the config file
JOB_SEARCH_URL = config.JOB_SEARCH_URL

pp = pprint.PrettyPrinter(indent=4)
logging.basicConfig(level=config.LOGGING_LEVEL)


def search_jobs(search_term: str, remote_jobs_only: str, page: int = 1) -> List[Dict]:
    """
    This function takes in a search term, remote_jobs_only(true/false) and an optional page
    number as input and uses them to make a request to the LinkedIn jobs API.
    The API returns a json object containing job search results that match
    the search term and location provided. The function also sets up logging
    to log the request and any errors that may occur.

    Args:
    search_term (str): The job title or position you want to search for.
    remote_jobs_only (str):  Search for only remote jobs if set it true else search for all the jobs in any location.
    page (int, optional): The page number of the search results you want to retrieve. Default is 1.

    Returns:
    json: A json object containing the search results.

    Raises:
    Exception: If an exception is encountered during the API request, it is logged as an error.
    """

    url = JOB_SEARCH_URL
    querystring = {
        "query": search_term,
        "page": page,
        "remote_jobs_only": remote_jobs_only,
    }
    headers = {
        "X-RapidAPI-Key": str(RAPID_API_KEY),
        "X-RapidAPI-Host": config.JOB_SEARCH_X_RAPIDAPI_HOST,
    }

    try:
        response = requests.get(
            url, headers=headers, params=querystring
        )
        json_object = json.loads(response.text)
        json_response_data = json_object.get('data')
        return json_response_data
    except ValueError as value_err:
        logging.error(value_err)
        return [{"error": value_err}]


def main(search_term, remote_jobs_only, page):
    """
    main() is a function that performs a job search on
    using the search_jobs() function.

    Args:
    search_term (str): The job title or keyword to search for.
    remote_jobs_only (str):  Search for only remote jobs if set it true else search for all the jobs in any location.
    page (int, optional): The page number of the search results. Default is 1.

    Returns:
    json: The json object returned by the  jobs API.
    """
    results = search_jobs(
        search_term=search_term, remote_jobs_only=remote_jobs_only, page=page
    )
    return results


def entrypoint():
    """
    This is the entrypoint for the script.
    It defines the command-line interface for running the script.
    """
    parser = argparse.ArgumentParser(description="This searches for jobs")

    parser.add_argument(
        "search",
        type=str,
        metavar="search",
        help="the term to search for, like job title",
    )

    parser.add_argument(
        "remote_jobs_only", type=str, metavar="remote_jobs_only", help="Search for only remote jobs"
    )

    parser.add_argument(
        "page",
        type=int,
        default=1,
        metavar="page",
        help="the page of results, page 1, 2, 3,...etc.",
    )

    args = parser.parse_args()

    result = main(search_term=args.search, remote_jobs_only=args.remote_jobs_only, page=args.page)

    pp.pprint(result)


if __name__ == "__main__":
    entrypoint()
