"""
This code defines a function to search for jobs using the JSearch API and includes command-line argument parsing using argparse. It also includes a module-level docstring and exception handling for errors.

The function search_jobs takes in the job title, location, date posted range, and a flag for remote jobs. It returns a dictionary containing the JSON response from the API. If an error occurs while making the API call, an exception is raised.

The command-line arguments are parsed using argparse and include the job title, location, date posted range, and remote job flag. The allowed values for date posted range are "all", "today", "3days", "week", and "month", and the allowed values for remote job flag are "true" and "false". The default date posted range is "today" and the default remote job flag is "false".

The module-level docstring provides an overview of the code's purpose and usage, as well as documentation for the search_jobs function's arguments, return value, and possible exceptions.

"""


import logging
import requests
import json
import argparse
import pprint
import os

import jobhunter.utils.aws_secrets_manager


pp = pprint.PrettyPrinter(indent=4)
logging.basicConfig(level=logging.INFO)


def search_jobs(title, location, date_posted="today", remote="false"):
    """
    Search for jobs using the JSearch API.

    Args:
        title (str): The job title to search for.
        location (str): The location to search for jobs in.
        date_posted (str, optional): The date range to filter job postings by. Defaults to "today".
        remote (str, optional): Whether to only search for remote jobs. Defaults to "false".

    Returns:
        dict: A dictionary containing the JSON response from the API.

    Raises:
        Exception: If an error occurs while making the API call.

    """
    try:
        url = "https://jsearch.p.rapidapi.com/search"
        querystring = {
            "query": "{0}, {1}".format(title, location),
            "num_pages": 10,
            "date_posted": date_posted,
            "remote_jobs_only": remote,
        }
        headers = {
            "X-RapidAPI-Key": aws_secrets_manager.get_secret(
                secret_name="rapidapikey", region_name="us-west-1"
            )["rapidapikey"],
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
        }
        response = requests.request("GET", url, headers=headers, params=querystring)
        response_json = json.loads(response.text)
        return response_json
    except Exception as e:
        logging.error("An error occurred while searching for jobs: {}".format(str(e)))
        raise Exception("An error occurred while searching for jobs.") from e


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Search for jobs using the JSearch API."
    )
    parser.add_argument("title", help="The job title to search for.")
    parser.add_argument("location", help="The location to search for jobs in.")
    parser.add_argument(
        "-d",
        "--date-posted",
        choices=["all", "today", "3days", "week", "month"],
        default="today",
        help="The date range to filter job postings by. Allowed values are 'all', 'today', '3days', 'week', and 'month'. Defaults to 'today'.",
    )
    parser.add_argument(
        "-r",
        "--remote",
        choices=["true", "false"],
        default="false",
        help="Whether to only search for remote jobs. Allowed values are 'true' and 'false'. Defaults to 'false'.",
    )
    args = parser.parse_args()

    try:
        result = search_jobs(args.title, args.location, args.date_posted, args.remote)
        print(result)
    except Exception as e:
        print(e)
