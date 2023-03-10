"""
Perform job analysis on LinkedIn.

This module imports functions from other modules, including search_jobs,
extract_text_from_site, and text_similarity, to search for jobs on LinkedIn,
extract job descriptions from job URLs, and calculate the similarity between a
given resume text and a job description.

The main function jobs_analysis takes a search term and a location as inputs
and returns a list of dictionaries, each containing a job's title, URL,
description, and resume similarity score. The module also includes a main
function that allows the user to input a search term and location through
command-line arguments.
"""

import time
import logging
import re
import json
import datetime
import argparse
import pprint
import yaml
import boto3
import os
import sqlite3
from jobhunter.utils.search_linkedin_jobs import search_linkedin_jobs
from jobhunter.utils.extract_text_from_site import get_text_in_url
from jobhunter.utils.text_similarity import text_similarity
from utils.is_url_in_jobs_table import check_url_in_db


pp = pprint.PrettyPrinter(indent=4)
logging.basicConfig(level=logging.INFO)


with open("/Users/jjespinoza/Documents/jobhunter/jobhunter/config.yaml") as f:
    data = yaml.load(f, Loader=yaml.FullLoader)

bucket_name = data["dev"]["bucket"]
email = data["default"]["email"]


def save_locally(data):
    """
    Saves a list of dictionaries to a JSON file locally in the ../data/temp directory.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
    file_path = os.path.join("..", "data", "temp", f"{timestamp}.json")
    with open(file_path, "w") as f:
        json.dump(data, f)
    logging.info("Saved data to %s", file_path)
    return None


def standardize_wage(wage):
    """
    Standardize wage to a numeric value.

    This function takes in a wage string and standardizes it to a numeric value.
    First, the function removes any dollar signs or commas using a regular expression.
    Then, it removes any non-numeric characters. Finally, if the wage is less than $25,000,
    the function multiplies it by 1000 to convert it from thousands to dollars.

    Args:
        wage (str): A string representing the wage amount to standardize.

    Returns:
        float: The standardized wage as a numeric value.

    """
    wage = re.sub(r"[$,]", "", wage)
    wage = re.sub("[^0-9]", "", wage)
    wage = float(wage)
    if wage < 25000:
        wage *= 1000
    return wage


def standardize_wages(wages):
    """
    Return a list of standardized wages.

    Args:
    wages (list): A list of strings representing wages.

    Returns:
    list: A list of standardized wage values as floats.

    """
    return [standardize_wage(wage) for wage in wages]


def get_text_resume(file):
    """
    This function reads a text file and returns the content as a single string.

    Args:
    file (str): The name of the file to be read.

    Returns:
    str : A string containing the contents of the file.
    """
    with open(file) as f:
        resume = [line.rstrip("\n") for line in f]
    resume = " ".join(resume)  # to join list of strings into a single string
    return resume


def jobs_analysis(search_term, location, min_salary, minsim):
    """
    Perform a job analysis by searching for jobs on LinkedIn.

    This function uses the search_linkedin_jobs function to retrieve a list of jobs using a given search term and location. Then, it extracts the job description from each job's webpage using the get_text_in_url function. The function then calculates the similarity between the job description and a given resume text using the text_similarity function. It appends this similarity score to the job dictionary and adds the dictionary to a list of job analysis, which it returns.

    Args:

    search_term (str): Job title or role to search for on LinkedIn
    location (str): Location to search for jobs in
    Returns:

    list: A list of dictionaries, each containing a job's title, URL, description, and resume similarity score.
    """
    resume = get_text_resume(file="/Users/jjespinoza/Documents/jobhunter/jobhunter/resumes/resume.txt")

    pagination = 1

    try:

        while pagination <= 5:
            jobs = search_linkedin_jobs(
                search_term=search_term, location=location, page=pagination
            )

            jobs_analysis = []

            for job in jobs:
                logging.info(
                    "------------------------------------ Analyzing Job ------------------------------------"
                )

                #TODO: check that the job we are searching for isn't already in our database
                # check if the job_url is in the database
                
            
                job_url = job["job_url"]

                if check_url_in_db(job_url) == False:
                    logging.info("NEW job!!!")
                    job["job_description"] = get_text_in_url(
                        url=job_url
                    )  # scraps text from site
                    description = job["job_description"]

                    logging.info("calculating resume similarity")
                    job["resume_similarity"] = text_similarity(
                        text1=resume, text2=description
                    )
                    logging.info("similarity: {}".format(job["resume_similarity"]))

                    if job["resume_similarity"] > minsim:
                        logging.info("high job similarity, analyzing job")

                        logging.info("extracting emails and salaries")
                        job["emails"] = re.findall(
                            r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", description
                        )
                        job["salary"] = standardize_wages(
                            re.findall(r"\$\d+[,\d+]*(?:[\.\d{2}]+)?", description)
                        )

                        if not job["salary"]:
                            logging.info("keeping job with no salary")
                            logging.info("saved file to s3")
                            save_locally(data=job)
                            jobs_analysis.append(job)
                            logging.debug(job)
                            job["salary"] = 0

                        else:
                            logging.info("analyzing salary")
                            if max(job["salary"]) > int(min_salary):
                                save_locally(data=job)
                                jobs_analysis.append(job)
                                logging.info("keeping job with high salary")
                                logging.info("saved file to s3")
                                logging.debug(job)
                            else:
                                logging.info("ignore job with low salary")
                    else:
                        logging.info("low job similarity, ignoring")
                else:
                    logging.info("job already in database, so ignoring")
            pagination = pagination + 1

        return jobs_analysis
    except:
        logging.info("ERROR: in getting page")


if __name__ == "__main__":
    PARSER = argparse.ArgumentParser(
        description="This searches for jobs on linkedin and calculates similarity with your resume."
    )

    PARSER.add_argument(
        "search",
        metavar="search",
        type=str,
        help="the term to search for, like job title",
    )
    PARSER.add_argument(
        "location", metavar="location", type=str, help="the location of the job"
    )
    PARSER.add_argument(
        "minsal", metavar="minsal", type=str, help="the minimum salary to consider"
    )
    PARSER.add_argument(
        "minsim",
        metavar="minsim",
        type=float,
        help="the minimum similarity score from resume to job description",
    )

    ARGS = PARSER.parse_args()

    jobs_analysis(
        search_term=ARGS.search,
        location=ARGS.location,
        min_salary=ARGS.minsal,
        minsim=ARGS.minsim,
    )
