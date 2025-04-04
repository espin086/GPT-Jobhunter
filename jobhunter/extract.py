import argparse
import concurrent.futures
import json
import logging
import os
import pprint
import time
import random
import requests
import platform

from dotenv import load_dotenv
from jobhunter.FileHandler import FileHandler
from tqdm import tqdm

from jobhunter import config

# change current director to location of this file
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(THIS_DIR)

file_handler = FileHandler(
    raw_path=config.RAW_DATA_PATH, processed_path=config.PROCESSED_DATA_PATH
)

# Load environment variables - first try .env file in various locations, but rely on actual env vars which work in Docker
# This ensures compatibility with both local development and containerized environments
load_dotenv() # Try current directory first
load_dotenv("../.env") # Try one level up (project root when running locally)
load_dotenv("../../.env") # Try two levels up (for backward compatibility)

# Get the API key from the environment variable
RAPID_API_KEY = os.environ.get("RAPID_API_KEY")

# Get the API URL from the config file
JOB_SEARCH_URL = config.JOB_SEARCH_URL

# Get the API URL from the config file
SELECTED_KEYS = config.SELECTED_KEYS

# Define API rate limiting parameters
USE_CONCURRENT_REQUESTS = False  # Set to False to use sequential processing
DELAY_BETWEEN_REQUESTS = 2.0  # Seconds between API calls (adjust as needed)

# Retry settings for search_jobs
MAX_RETRIES = 3
INITIAL_BACKOFF = 2.0
MAX_BACKOFF = 60.0

# Define the search_jobs function directly here
def search_jobs(search_term, page=1, country="us", date_posted="all", delay=DELAY_BETWEEN_REQUESTS):
    """Search for jobs using the API directly."""
    url = JOB_SEARCH_URL
    querystring = {
        "query": search_term, 
        "page": str(page),
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
            
            # Handle rate limiting
            if response.status_code == 429:
                if retries == MAX_RETRIES:
                    logging.error(f"Maximum retries reached for '{search_term}' on page {page}. Rate limit exceeded.")
                    raise requests.exceptions.RequestException(f"429 Client Error: Too Many Requests for url: {response.url}")
                
                # Calculate backoff with jitter
                jitter = random.uniform(0, 0.1 * backoff_time)
                wait_time = min(backoff_time + jitter, MAX_BACKOFF)
                
                logging.warning(f"Rate limit hit. Retrying in {wait_time:.2f} seconds (retry {retries+1}/{MAX_RETRIES}).")
                time.sleep(wait_time)
                
                # Increase backoff time exponentially
                backoff_time *= 2
                retries += 1
                continue
                
            # Check for other errors
            response.raise_for_status()
            
            # Parse response
            json_object = response.json()
            json_response_data = json_object.get("data")
            
            if not json_response_data:
                logging.warning(f"No jobs found for search term: '{search_term}' on page {page}.")
                raise ValueError(f"No jobs found for search term: '{search_term}' on page {page}")
                
            logging.info(f"Found {len(json_response_data)} jobs for '{search_term}' on page {page}.")
            return json_response_data
            
        except requests.exceptions.RequestException as req_err:
            if "429" not in str(req_err):
                logging.error(f"API Request failed: {req_err}")
                raise
                
        except ValueError as value_err:
            logging.error(f"An unexpected value error occurred: {value_err}")
            raise
    
    # If we've exhausted retries
    raise requests.exceptions.RequestException(f"Maximum retries reached for '{search_term}' on page {page}")

def get_all_jobs(search_term, pages, country="us", date_posted="all"):
    all_jobs = []
    
    # Always use Sequential processing 
    pages_to_fetch = 1 # Keep limit to 1 page for testing
    for page_index in range(pages_to_fetch):
        page_number_for_api = page_index + 1 # API pages are often 1-based
        try:
            # Use search_jobs with all expected parameters
            logging.info(f"Fetching page {page_number_for_api}/{pages} for search term '{search_term}'") # Log the correct page number
            jobs = search_jobs(
                search_term=search_term, 
                page=page_number_for_api, # Pass 1-based index to API
                country=country,
                date_posted=date_posted,
                delay=DELAY_BETWEEN_REQUESTS
            )
            
            if jobs:
                logging.debug(f"Received {len(jobs)} jobs from API")
                # Log a sample job to aid debugging if needed
                if jobs and logging.getLogger().level <= logging.DEBUG:
                    logging.debug(f"Sample job data fields: {list(jobs[0].keys())}")
                    
                all_jobs.extend(jobs)
                logging.debug(f"Appended {len(jobs)} jobs for page {page_number_for_api}")
                for job in jobs:
                    try:
                        file_handler.save_data(
                            data=job,
                            source="jobs",
                            sink=file_handler.raw_path,
                        )
                    except Exception as e:
                        logging.error(f"Failed to save job data: {str(e)}")
                        logging.debug(f"Problematic job data: {json.dumps(job)[:500]}...")
        except ValueError as e:
            # This catches the "No jobs found" error from search_jobs
            logging.warning(f"{str(e)}")
            # Stop processing if no jobs found on the first page
            break 
        except Exception as e:
            logging.error(
                f"An error occurred while fetching jobs for page {page_number_for_api}: {str(e)}"
            )
            # Stop processing if an error occurs on the first page
            break 
            
    # Check if we found any jobs across all pages
    if not all_jobs:
        error_msg = f"No jobs found for search term: '{search_term}' across all {pages} pages"
        logging.error(error_msg)
        raise ValueError(error_msg)
        
    logging.info(f"Total jobs found for '{search_term}': {len(all_jobs)}")
    return all_jobs


def extract(POSITIONS, country="us", date_posted="all", location=""):
    """
    Load the data from the API and save it to a file.
    """
    # Enhanced debug logging for Docker environments
    logging.info("=== ENVIRONMENT DIAGNOSTICS ===")
    logging.info(f"Platform: {platform.platform()}")
    logging.info(f"Current working directory: {os.getcwd()}")
    logging.info(f"THIS_DIR value: {THIS_DIR}")
    logging.info(f"RAPID_API_KEY available: {'Yes' if RAPID_API_KEY else 'No'}")
    logging.info(f"RAPID_API_KEY masked: {RAPID_API_KEY[:4] + '****' if RAPID_API_KEY and len(RAPID_API_KEY) > 4 else 'None'}")
    logging.info(f"RAW_DATA_PATH: {config.RAW_DATA_PATH}")
    logging.info(f"PROCESSED_DATA_PATH: {config.PROCESSED_DATA_PATH}")
    logging.info("=== END DIAGNOSTICS ===")
    
    try:
        # Ensure data directories exist
        os.makedirs(config.RAW_DATA_PATH, exist_ok=True)
        os.makedirs(config.PROCESSED_DATA_PATH, exist_ok=True)
        logging.info(f"Created data folders at {config.RAW_DATA_PATH} and {config.PROCESSED_DATA_PATH}")
    except Exception as e:
        logging.error(f"Error creating data folders: {e}")
        raise

    # Validate API key before proceeding
    if not RAPID_API_KEY:
        error_msg = "RAPID_API_KEY is missing. Cannot perform job search."
        logging.error(error_msg)
        raise ValueError(error_msg)
        
    try:
        # Create directories if they don't exist
        file_handler.create_data_folders_if_not_exists()
        logging.info(f"Created data folders at {file_handler.raw_path} and {file_handler.processed_path}")
        
        # Validate inputs
        if not POSITIONS or not isinstance(POSITIONS, list) or len(POSITIONS) == 0:
            error_msg = "No positions provided for job search"
            logging.error(error_msg)
            raise ValueError(error_msg)
            
        # Log the API configuration
        logging.info(f"API Configuration: Using country='{country}', date_posted='{date_posted}'")
        logging.info(f"Using API key: {RAPID_API_KEY[:4]}...{RAPID_API_KEY[-4:] if RAPID_API_KEY else 'None'}")
        
        try:
            positions = POSITIONS
            total_jobs_found = 0

            logging.info(
                "Starting extraction process for positions: %s",
                positions,
            )
            
            # Default location based on country if none provided
            if not location:
                # Map country codes to default locations
                country_locations = {
                    "us": "United States",
                    "uk": "United Kingdom",
                    "ca": "Canada",
                    "au": "Australia",
                    "de": "Germany",
                    "fr": "France",
                    "es": "Spain",
                    "it": "Italy"
                }
                location = country_locations.get(country.lower(), country)
            
            search_results = {}  # To track results per position
            
            for position_index, position in enumerate(positions):
                try:
                    # Try original position first
                    # Format search term according to API recommendation: "job title in location"
                    # Check if position already contains location information
                    if "in " + location.lower() not in position.lower() and " jobs in " not in position.lower():
                        search_term = f"{position} jobs in {location}"
                        logging.info(f"Reformatted search term to: '{search_term}'")
                    else:
                        search_term = position
                    
                    try:
                        jobs = get_all_jobs(
                            search_term=search_term,
                            pages=1, # Keep pages=1 for testing limit
                            country=country,
                            date_posted=date_posted,
                        )
                        
                        job_count = len(jobs)
                        total_jobs_found += job_count
                        search_results[position] = job_count
                        
                        logging.info(f"Found {job_count} jobs for position '{position}'")
                        
                    except ValueError as e:
                        # Initial search failed, try with more general terms
                        logging.warning(f"Initial search failed: {str(e)}")
                        logging.info("Attempting search with more general terms...")
                        
                        # Generate more general search terms based on the position
                        general_terms = []
                        
                        # Split the position into words and extract key components
                        words = position.lower().split()
                        
                        # If title contains 'senior', 'principal', etc., try without those qualifiers
                        qualifiers = ['senior', 'principal', 'lead', 'staff', 'head', 'chief', 'vp', 'vice president', 'director']
                        
                        # If title is something like "Principal Machine Learning Engineer"
                        # Try "Machine Learning Engineer" and "Machine Learning"
                        position_without_qualifiers = ' '.join([w for w in words if w.lower() not in qualifiers])
                        if position_without_qualifiers and position_without_qualifiers != position:
                            general_terms.append(position_without_qualifiers)
                        
                        # Try to extract key domain/role
                        domains = [
                            'machine learning', 'data science', 'data engineering', 'software engineering', 
                            'artificial intelligence', 'ai', 'ml', 'software development', 
                            'developer', 'engineer', 'programming'
                        ]
                        
                        for domain in domains:
                            if domain in position.lower():
                                general_terms.append(domain)
                                break
                        
                        # Default fallbacks if no domain match
                        if not general_terms:
                            if 'engineer' in position.lower() or 'engineering' in position.lower():
                                general_terms.append('engineer')
                            elif 'developer' in position.lower():
                                general_terms.append('developer')
                            elif 'data' in position.lower():
                                general_terms.append('data')
                        
                        # If still no general terms, use some defaults
                        if not general_terms:
                            general_terms = ['software engineer', 'developer', 'engineer']
                        
                        # Try each general term
                        for term in general_terms:
                            try:
                                fallback_search_term = f"{term} jobs in {location}"
                                logging.info(f"Trying fallback search term: '{fallback_search_term}'")
                                
                                fallback_jobs = get_all_jobs(
                                    search_term=fallback_search_term,
                                    pages=1,  # Keep fallback pages=1
                                    country=country,
                                    date_posted=date_posted,
                                )
                                
                                if fallback_jobs:
                                    logging.info(f"Fallback search successful! Found {len(fallback_jobs)} jobs")
                                    # Add fallback jobs to total
                                    total_jobs_found += len(fallback_jobs)
                                    # Note: we still associate these with the original position in results
                                    search_results[position] = len(fallback_jobs)
                                    break  # Stop trying other terms if we found jobs
                                
                            except ValueError:
                                logging.warning(f"Fallback search term '{fallback_search_term}' returned no results")
                                continue  # Try next term
                            except Exception as fallback_err:
                                logging.error(f"Error in fallback search: {str(fallback_err)}")
                                continue  # Try next term
                
                except ValueError as e:
                    logging.error(f"Failed to find jobs for position '{position}': {str(e)}")
                    search_results[position] = 0
                    
                    continue
                except Exception as e:
                    logging.error(f"Unexpected error for position '{position}': {str(e)}")
                    search_results[position] = 0
                    
                    continue

            # Log the results summary
            logging.info("=== Job Search Results Summary ===")
            for position, count in search_results.items():
                logging.info(f"Position '{position}': {count} jobs found")
            logging.info(f"Total jobs found across all positions: {total_jobs_found}")
            
            # Instead of raising an error when no jobs are found, return 0 and log a warning
            if total_jobs_found == 0:
                warning_msg = (
                    f"No jobs found for any of the specified positions: {positions}. "
                    f"Please check:\n"
                    f"1. API key (current: {RAPID_API_KEY[:4]}...{RAPID_API_KEY[-4:] if RAPID_API_KEY else 'None'})\n"
                    f"2. API subscription status\n"
                    f"3. API rate limits\n"
                    f"4. Search parameters (country='{country}', date_posted='{date_posted}')\n"
                    f"5. Search terms (try more general terms like 'software engineer' or 'data scientist')\n"
                    f"6. Location (try major tech hubs like 'San Francisco', 'New York', or 'Seattle')"
                )
                logging.warning(warning_msg)
                
            return total_jobs_found

        except Exception as e:
            logging.error("An error occurred in the extract function: %s", str(e))
            # Return 0 instead of raising the error
            return 0

    except Exception as e:
        logging.error("An error occurred in the extract function: %s", str(e))
        # Return 0 instead of raising the error
        return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Job Extraction")
    parser.add_argument(
        "positions",
        metavar="POSITIONS",
        type=str,
        nargs="+",
        help="List of positions to extract jobs for",
    )
    parser.add_argument(
        "--country",
        type=str,
        default="us",
        help="Country code for job search (e.g., 'us', 'uk')",
    )
    parser.add_argument(
        "--date-posted",
        type=str,
        default="all",
        help="Time frame for job posting (e.g., 'all', 'today', 'week', 'month')",
    )
    parser.add_argument(
        "--location",
        type=str,
        default="",
        help="Location to search for jobs (e.g., 'Chicago', 'New York')",
    )
    args = parser.parse_args()
    logging.info("Application started.")
    extract(args.positions, args.country, args.date_posted, args.location)
    logging.info("Application finished.")
