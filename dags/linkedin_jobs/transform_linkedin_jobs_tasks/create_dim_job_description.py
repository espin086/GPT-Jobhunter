import requests
from google.cloud import bigquery
import pandas as pd
import time

import urllib.request
import logging

from bs4 import BeautifulSoup


def get_text_in_url(url):
    """
    This function takes in a single argument, a url, and returns the text on the webpage as a string. It uses the urlopen function from the urllib library to open the url, then uses the BeautifulSoup library to parse the HTML of the webpage. It removes all script and style elements from the HTML, then uses the .get_text() method from BeautifulSoup to extract the text from the webpage. The function then performs additional text cleaning operations such as removing leading and trailing whitespace, breaking multi-headlines into a line each, and dropping blank lines.

    Args:
    url (str): The url of the webpage from which text will be extracted

    Returns:
    str : A string containing the cleaned text from the webpage
    """
    logging.debug(f"Fetching HTML from {url}")
    html = urllib.request.urlopen(url).read()
    soup = BeautifulSoup(html, features="html.parser")

    logging.debug("Removing script and style elements from HTML")
    # kill all script and style elements
    for script in soup(["script", "style"]):
        script.extract()  # rip it out

    # get text
    text = soup.get_text()

    logging.debug("Cleaning extracted text")
    # break into lines and remove leading and trailing space on each
    lines = (line.strip() for line in text.splitlines())
    # break multi-headlines into a line each
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    # drop blank lines
    text = "\n".join(chunk for chunk in chunks if chunk)

    return text


# Initialize the BigQuery client
client = bigquery.Client()


def download_job_description(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        return None


def download_job_descriptions_and_upload_to_bq():
    # Query the job_url column from BigQuery
    query = """
    SELECT DISTINCT job_url
    FROM `ai-solutions-lab-randd.jobhunter.dim_job_description`
    """
    try:
        existing_job_urls = client.query(query).to_dataframe()["job_url"]
    except Exception as e:
        print(f"Table 'dim_job_description' not found. Creating the table...")
        existing_job_urls = pd.Series([])

    # Query the job_url column from raw_listings table in BigQuery
    query = """
    SELECT DISTINCT job_url
    FROM `ai-solutions-lab-randd.jobhunter.raw_listings`
    """
    all_job_urls = client.query(query).to_dataframe()["job_url"]

    # Get job_urls that are not already in dim_job_description table
    job_urls_to_scrape = [url for url in all_job_urls if url not in existing_job_urls]

    if not job_urls_to_scrape:
        print(
            "All job URLs are already in the dim_job_description table. Nothing to scrape."
        )
        return

    # Download job descriptions and store them in a list with tqdm
    job_descriptions = []
    for url in job_urls_to_scrape:
        description = get_text_in_url(url)
        job_descriptions.append(description)
        time.sleep(1)

    # Create a new DataFrame with job_url and job_description columns
    data = {"job_url": job_urls_to_scrape, "job_description": job_descriptions}
    df = pd.DataFrame(data)

    # Upload the DataFrame to a new BigQuery table 'dim_job_description' and append the values
    table_id = "ai-solutions-lab-randd.jobhunter.dim_job_description"
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_APPEND",  # Append data to the table
        schema=[
            {"name": "job_url", "type": "STRING"},
            {"name": "job_description", "type": "STRING"},
        ],
    )
    job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
    job.result()

    print(
        "Job descriptions downloaded and uploaded to BigQuery table 'dim_job_description'."
    )


def main():
    download_job_descriptions_and_upload_to_bq()


if __name__ == "__main__":
    main()
