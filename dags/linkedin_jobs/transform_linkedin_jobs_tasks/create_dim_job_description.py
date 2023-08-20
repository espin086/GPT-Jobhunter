import requests
from google.cloud import storage
import pandas as pd
import time
import json
import random
from bs4 import BeautifulSoup
import logging
import urllib.request
import socket
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO)


# Define the existing functions here...
def get_text_in_url(url):
    try:
        logging.info(f"Fetching HTML from {url}")
        # Set a custom timeout value for the urlopen function (in seconds)
        # You can adjust this value based on your needs
        timeout = 10
        html = urllib.request.urlopen(url, timeout=timeout).read()
        soup = BeautifulSoup(html, features="html.parser")

        logging.info("Removing script and style elements from HTML")
        # kill all script and style elements
        for script in soup(["script", "style"]):
            script.extract()  # rip it out

        # get text
        text = soup.get_text()

        logging.info("Cleaning extracted text")
        # break into lines and remove leading and trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # drop blank lines
        text = "\n".join(chunk for chunk in chunks if chunk)

        return text

    except urllib.error.HTTPError as e:
        logging.warning(
            f"Failed to fetch HTML from {url}. HTTP Error {e.code}: {e.reason}"
        )
        return ""
    except urllib.error.URLError as e:
        logging.warning(f"Failed to fetch HTML from {url}. Error: {e.reason}")
        return ""
    except socket.timeout:
        logging.warning(f"Timed out while fetching HTML from {url}.")
        return ""
    except Exception as e:
        logging.warning(
            f"An error occurred while fetching HTML from {url}. Error: {str(e)}"
        )
        return ""


def scrape_and_save_job_descriptions(job_urls_to_scrape, bucket_name, folder_name):
    # Rest of the code remains the same

    for url in job_urls_to_scrape:
        description = get_text_in_url(url)
        if description:
            job_descriptions_dict = {"url": url, "description": description}
            json_data = json.dumps(
                [job_descriptions_dict], indent=4
            )  # Wrap in a list for BigQuery

            # Create a unique filename based on the URL
            file_name = url.replace("/", "_").replace(":", "_") + ".json"

            # Upload the JSON data to Cloud Storage
            storage_client = storage.Client()
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(folder_name + file_name)
            blob.upload_from_string(json_data)

        time.sleep(random.uniform(0.5, 1.5))
        print(f"Downloaded job description for {url}")

    print("All job descriptions saved to JSON and uploaded to Cloud Storage.")


def main():
    bucket_name = "jobhunter"  # Replace with your actual bucket name
    folder_name = "raw-json-job-descriptions/"  # Folder path within the bucket

    # Initialize the BigQuery client
    client = bigquery.Client()

    # Query the job_url column from BigQuery
    query = """
    SELECT DISTINCT linkedin_job_url_cleaned
    FROM `ai-solutions-lab-randd.jobhunter.dim_job_description`
    """
    try:
        existing_job_urls = client.query(query).to_dataframe()
    except Exception as e:
        print(f"Table 'dim_job_description' not found. Creating the table...")
        existing_job_urls = pd.DataFrame(columns=["linkedin_job_url_cleaned"])

    # Query the job_url column from raw_listings table in BigQuery
    query = """
    SELECT DISTINCT linkedin_job_url_cleaned
    FROM `ai-solutions-lab-randd.jobhunter.raw_listings`
    """
    all_job_urls = client.query(query).to_dataframe()

    # Convert existing_job_urls Series to a set
    existing_urls_set = set(existing_job_urls["linkedin_job_url_cleaned"])

    # Find job_urls that are not already in dim_job_description table
    job_urls_to_scrape = all_job_urls[
        ~all_job_urls["linkedin_job_url_cleaned"].isin(existing_urls_set)
    ]["linkedin_job_url_cleaned"]

    if job_urls_to_scrape.empty:
        print(
            "All job URLs are already in the dim_job_description table. Nothing to scrape."
        )
        return

    # Randomize the order of job_urls_to_scrape
    job_urls_to_scrape = job_urls_to_scrape.sample(frac=1).tolist()

    scrape_and_save_job_descriptions(job_urls_to_scrape, bucket_name, folder_name)


if __name__ == "__main__":
    main()
