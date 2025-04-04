import argparse
import json
import logging
import os
import pprint
import time  # For implementing delays
import random  # For jitter in retry timing
from typing import Dict, List, Mapping, Optional

import requests
from dotenv import load_dotenv

from jobhunter import config

# import config

# Add the path to the .env file
dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")

load_dotenv(dotenv_path)

# Get the API key from the environment variable
RAPID_API_KEY = os.environ.get("RAPID_API_KEY")

# === API Key Check ===
if RAPID_API_KEY is None:
    logging.error("RAPID_API_KEY environment variable not found.")
    raise ValueError(
        "RAPID_API_KEY environment variable not found. "
        "Please set it in your .env file or environment."
    )
# === End API Key Check ===


# Get the API URL from the config file
JOB_SEARCH_URL = config.JOB_SEARCH_URL

# === API Throttling Settings ===
# Delay between API requests in seconds (adjust as needed)
DEFAULT_REQUEST_DELAY = 1.0
# Maximum number of retries for rate-limited requests
MAX_RETRIES = 3
# Initial backoff time in seconds (will increase exponentially with each retry)
INITIAL_BACKOFF = 2.0
# Maximum backoff time in seconds
MAX_BACKOFF = 60.0
# === End API Throttling Settings ===

pp = pprint.PrettyPrinter(indent=4)
logging.basicConfig(level=config.LOGGING_LEVEL)


def search_jobs(
    search_term: str, 
    page: int = 1, 
    num_pages: int = 1,
    country: str = "us",
    date_posted: str = "all",
    delay: float = DEFAULT_REQUEST_DELAY
) -> List[Dict]:
    """
    Search for jobs with built-in throttling and retry logic for API rate limits.
    
    Args:
        search_term: The search term to look for
        page: The page number of results to fetch
        num_pages: Number of pages to fetch
        country: Country code for job search (e.g., 'us', 'uk')
        date_posted: Time frame for job posting (e.g., 'all', 'today', 'week', 'month')
        delay: Time in seconds to wait before making the request (throttling)
        
    Returns:
        List of job dictionaries from the API response
        
    Raises:
        ValueError: If no jobs are found for the search term
        requests.exceptions.RequestException: For API request errors including rate limits
    """
    url = JOB_SEARCH_URL
    querystring = {
        "query": search_term, 
        "page": str(page),
        "num_pages": str(num_pages),
        "country": country,
        "date_posted": date_posted
    }
    headers = {
        "X-RapidAPI-Key": str(RAPID_API_KEY),
        "X-RapidAPI-Host": config.JOB_SEARCH_X_RAPIDAPI_HOST,
    }

    # Implement retry logic with exponential backoff
    retries = 0
    backoff_time = INITIAL_BACKOFF
    
    # Apply initial delay before first request (throttling)
    if delay > 0:
        time.sleep(delay)
    
    while retries <= MAX_RETRIES:
        try:
            logging.info(f"Searching for '{search_term}' on page {page}...")
            response = requests.get(url, headers=headers, params=querystring)
            
            # Handle rate limiting specifically (429 Too Many Requests)
            if response.status_code == 429:
                if retries == MAX_RETRIES:
                    logging.error(f"Maximum retries reached for '{search_term}' on page {page}. Rate limit exceeded.")
                    raise requests.exceptions.RequestException(f"429 Client Error: Too Many Requests for url: {response.url}")
                
                # Calculate backoff with jitter to avoid all clients hitting at once
                jitter = random.uniform(0, 0.1 * backoff_time)
                wait_time = min(backoff_time + jitter, MAX_BACKOFF)
                
                logging.warning(f"Rate limit hit. Retrying in {wait_time:.2f} seconds (retry {retries+1}/{MAX_RETRIES}).")
                time.sleep(wait_time)
                
                # Increase backoff time exponentially
                backoff_time *= 2
                retries += 1
                continue
                
            # For other errors, use regular error handling
            response.raise_for_status()  # Raise an exception for other bad status codes (4xx or 5xx)

            # Log the response details for debugging
            logging.info(f"API Response Status: {response.status_code}")
            logging.info(f"API Response Headers: {dict(response.headers)}")
            
            try:
                json_object = response.json()  # Use response.json() for better error handling
                
                # Log a portion of the raw response for debugging
                logging.info(f"API Raw Response (first 500 chars): {response.text[:500]}...")
                
                # Log response structure
                if isinstance(json_object, dict):
                    logging.info(f"API Response Structure: {list(json_object.keys())}")
                
                json_response_data = json_object.get("data")

                # Log the raw response for debugging if no data found
                if not json_response_data:
                    logging.warning(f"No jobs found for search term: '{search_term}' on page {page}.")
                    logging.info(f"Full API Response: {json_object}")
                    # Raise an exception as requested
                    raise ValueError(f"No jobs found for search term: '{search_term}' on page {page}")

                logging.info(f"Found {len(json_response_data)} jobs for '{search_term}' on page {page}.")
                return json_response_data
            
            except json.JSONDecodeError as json_err:
                logging.error(f"Failed to decode JSON response: {json_err}")
                logging.error(f"Response text: {response.text}")
                raise ValueError("Failed to parse API response.") from json_err
            
        except requests.exceptions.RequestException as req_err:
            # Only retry on rate limit errors (handled above)
            if "429" not in str(req_err):
                logging.error(f"API Request failed: {req_err}")
                raise  # Re-raise the original error for other request errors
            
        except ValueError as value_err:
            logging.error(f"An unexpected value error occurred: {value_err}")
            raise  # Re-raise
    
    # If we've exhausted retries (should be handled in the loop, but just in case)
    raise requests.exceptions.RequestException(f"Maximum retries reached for '{search_term}' on page {page}")


def main(search_term, page=1, num_pages=config.PAGES, country="us", date_posted="all"):
    """
    Main function to search for jobs with the specified parameters.
    
    Args:
        search_term: The search term to look for
        page: The page number of results to fetch
        num_pages: Number of pages to fetch (default: from config)
        country: Country code for job search
        date_posted: Time frame for job posting
        
    Returns:
        List of job dictionaries from the API response
    """
    results = search_jobs(
        search_term=search_term, 
        page=page,
        num_pages=num_pages,
        country=country,
        date_posted=date_posted
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
        "--page",
        type=int,
        default=1,
        metavar="page",
        help="the page of results, page 1, 2, 3,...etc.",
    )
    
    parser.add_argument(
        "--num-pages",
        type=int,
        default=config.PAGES,
        help=f"number of pages to fetch (default: {config.PAGES})",
    )
    
    parser.add_argument(
        "--country",
        type=str,
        default="us",
        help="country code for job search (e.g., 'us', 'uk')",
    )
    
    parser.add_argument(
        "--date-posted",
        type=str,
        default="all",
        help="time frame for job posting (e.g., 'all', 'today', 'week', 'month')",
    )

    args = parser.parse_args()

    result = main(
        search_term=args.search, 
        page=args.page,
        num_pages=args.num_pages,
        country=args.country,
        date_posted=args.date_posted
    )

    pp.pprint(result)


if __name__ == "__main__":
    entrypoint()
