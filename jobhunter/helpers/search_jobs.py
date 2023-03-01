"""
This module uses the LinkedIn Jobs API to search for jobs on LinkedIn by providing a search term, location and an optional page number. The module utilizes the requests and json libraries to make the API request and parse the response, respectively. Additionally, the module employs the logging and argparse libraries to set up logging and command-line arguments, and the pprint library to print the results in a pretty format. The main function in the module is 'search_linkedin_jobs()' which takes in a search term, location and an optional page number as input and returns a json object containing job search results that match the search term and location provided. The module also uses the os library to access the API key as an environment variable. The main function in the module is 'main()' which performs a job search on LinkedIn using the 'search_linkedin_jobs()' function and returns the json object returned by the LinkedIn jobs API. The module also defines a command-line interface for running the script.
"""


import logging
import requests
import json
import argparse
import pprint
import os
import aws_secrets_manager


pp = pprint.PrettyPrinter(indent=4)
logging.basicConfig(level=logging.INFO)


def search_linkedin_jobs(search_term, location, page=1):
    """
    This function takes in a search term, location and an optional page number as input and uses them to make a request to the LinkedIn jobs API. The API returns a json object containing job search results that match the search term and location provided. The function also sets up logging to log the request and any errors that may occur.

    Args:
    search_term (str): The job title or position you want to search for.
    location (str): The location you want to search for jobs in.
    page (int, optional): The page number of the search results you want to retrieve. Default is 1.

    Returns:
    json: A json object containing the search results.

    Raises:
    Exception: If an exception is encountered during the API request, it is logged as an error.
    """

    url = "https://linkedin-jobs-search.p.rapidapi.com/"
    payload = {"search_terms": search_term, "location": location, "page": "1"}
    headers = {
        "content-type": "application/json",
        "X-RapidAPI-Key": aws_secrets_manager.get_secret(
            secret_name="rapidapikey", region_name="us-west-1"
        )["rapidapikey"],
        "X-RapidAPI-Host": "linkedin-jobs-search.p.rapidapi.com",
    }

    logging.info(
        "Making request to LinkedIn jobs API with search term: {}, location: {}".format(
            search_term, location
        )
    )

    try:
        response = requests.request("POST", url, json=payload, headers=headers)
        json_object = json.loads(response.text)
        return json_object

    except Exception as e:
        logging.error("Encountered exception: {}".format(e))


def main(search_term, location, page):
    """
    main() is a function that performs a job search on LinkedIn using the search_linkedin_jobs() function.

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="This searches for jobs on LinkedIn")

    parser.add_argument(
        "search",
        metavar="search",
        type=str,
        help="the term to search for, like job title",
    )
    parser.add_argument(
        "location", metavar="location", type=str, help="the location of the job"
    )
    parser.add_argument(
        "page",
        metavar="page",
        type=int,
        help="the page of results, page 1, 2, 3,...etc.",
    )

    args = parser.parse_args()

    result = main(search_term=args.search, location=args.location, page=args.page)

    pp.pprint(result)
