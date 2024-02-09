import argparse
import json
import logging
import os
import pprint
from typing import Dict, List, Mapping

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


def search_jobs(
    search_term: str, remote_jobs_only: str, page: int = 1
) -> List[Dict]:
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
        response = requests.get(url, headers=headers, params=querystring)
        json_object = json.loads(response.text)
        json_response_data = json_object.get("data")
        return json_response_data
    except ValueError as value_err:
        logging.error(value_err)
        return [{"error": value_err}]


def main(search_term, remote_jobs_only, page):
    results = search_jobs(
        search_term=search_term, remote_jobs_only=remote_jobs_only, page=page
    )
    return results


def entrypoint():
    parser = argparse.ArgumentParser(description="This searches for jobs")

    parser.add_argument(
        "search",
        type=str,
        metavar="search",
        help="the term to search for, like job title",
    )

    parser.add_argument(
        "remote_jobs_only",
        type=str,
        metavar="remote_jobs_only",
        help="Search for only remote jobs",
    )

    parser.add_argument(
        "page",
        type=int,
        default=1,
        metavar="page",
        help="the page of results, page 1, 2, 3,...etc.",
    )

    args = parser.parse_args()

    result = main(
        search_term=args.search, remote_jobs_only=args.remote_jobs_only, page=args.page
    )

    pp.pprint(result)


if __name__ == "__main__":
    entrypoint()
