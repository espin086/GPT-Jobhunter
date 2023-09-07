"""
This module uses the LinkedIn Jobs API to search for jobs on LinkedIn by providing a search term, 
location and an optional page number. The module utilizes the requests and json libraries to make 
the API request and parse the response, respectively. Additionally, the module employs the logging 
and argparse libraries to set up logging and command-line arguments, and the pprint library to 
print the results in a pretty format. The main function in the module is 'search_linkedin_jobs()' 
which takes in a search term, location and an optional page number as input and returns a json 
object containing job search results that match the search term and location provided. The module 
also uses the os library to access the API key as an environment variable. The main function in 
the module is 'main()' which performs a job search on LinkedIn using the 'search_linkedin_jobs()' 
function and returns the json object returned by the LinkedIn jobs API. 
The module also defines a command-line interface for running the script.
"""


import argparse
import json
import logging
import os
import pprint

import requests
import config
from dotenv import load_dotenv


# Load the .env file
load_dotenv("../.env")

# Get the API key from the environment variable
RAPID_API_KEY = os.environ.get("RAPID_API_KEY")

# Get the API URL from the config file
JOB_SEARCH_URL = config.JOB_SEARCH_URL

pp = pprint.PrettyPrinter(indent=4)
logging.basicConfig(level=config.LOGGING_LEVEL)


def search_linkedin_jobs(search_term, location, page=1):
    """
    This function takes in a search term, location and an optional page
    number as input and uses them to make a request to the LinkedIn jobs API.
    The API returns a json object containing job search results that match
    the search term and location provided. The function also sets up logging
    to log the request and any errors that may occur.

    Args:
    search_term (str): The job title or position you want to search for.
    location (str): The location you want to search for jobs in.
    page (int, optional): The page number of the search results you want to retrieve. Default is 1.

    Returns:
    json: A json object containing the search results.

    Raises:
    Exception: If an exception is encountered during the API request, it is logged as an error.
    """

    url = JOB_SEARCH_URL
    payload = {"search_terms": search_term, "location": location, "page": page}
    headers = {
        "content-type": "application/json",
        "X-RapidAPI-Key": RAPID_API_KEY,
        "X-RapidAPI-Host": config.JOB_SEARCH_X_RAPIDAPI_HOST,
    }

    try:
        response = requests.request(
            "POST", url, json=payload, headers=headers, timeout=5
        )
        json_object = json.loads(response.text)
        return json_object
    except ValueError as value_err:
        logging.error(value_err)
        return None


def main(search_term, location, page):
    """
    main() is a function that performs a job search on LinkedIn
    using the search_linkedin_jobs() function.

    Args:
    search_term (str): The job title or keyword to search for.
    location (str): The location to search for the job.
    page (int, optional): The page number of the search results. Default is 1.

    Returns:
    json: The json object returned by the LinkedIn jobs API.
    """
    results = search_linkedin_jobs(
        search_term=search_term, location=location, page=page
    )
    return results


def entrypoint():
    """
    This is the entrypoint for the script.
    It defines the command-line interface for running the script.
    """
    parser = argparse.ArgumentParser(description="This searches for jobs on LinkedIn")

    parser.add_argument(
        "search",
        type=str,
        metavar="search",
        help="the term to search for, like job title",
    )

    parser.add_argument(
        "location", type=str, metavar="location", help="the location of the job"
    )

    parser.add_argument(
        "page",
        type=int,
        default=1,
        metavar="page",
        help="the page of results, page 1, 2, 3,...etc.",
    )

    args = parser.parse_args()

    result = main(search_term=args.search, location=args.location, page=args.page)

    pp.pprint(result)


if __name__ == "__main__":
    entrypoint()
