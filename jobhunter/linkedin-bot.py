"""
This is a module for performing a job analysis on LinkedIn. It imports functions from other modules, including search_jobs, extract_text_from_site and text_similarity, to search for jobs on LinkedIn, extract job descriptions from job URLs, and calculate the similarity between a given resume text and a job description. The main function, jobs_analysis, takes a search term and a location as inputs and returns a list of dictionaries, each containing a job's title, url, description, and resume similarity score. The module also includes a main function that allows the user to input a search term and location through command line arguments.
"""

import importlib
from utils.search_jobs import search_linkedin_jobs
from utils.extract_text_from_site import get_text_in_url
from utils.text_similarity import text_similarity
from utils.emailer import send_email
import time
import logging
import re
import json
import datetime
import argparse
import pprint

import os

pp = pprint.PrettyPrinter(indent=4)
logging.basicConfig(level=logging.INFO)


import yaml

with open('config.yaml') as f:
    data = yaml.load(f, Loader=yaml.FullLoader)
    
bucket_name = data['dev']['bucket']
email = data['default']['email']


def save_to_s3(data, bucket_name):
    """
    Saves a list of dictionaries to a JSON file on S3.
    """
    import boto3

    s3 = boto3.resource("s3")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    file_name = f"output/{timestamp}.json"
    s3.Object(bucket_name, file_name).put(Body=json.dumps(data))
    logging.info("Saved data to %s/%s", bucket_name, file_name)
    return None


def standardize_wage(wage):
    wage = re.sub(r"[$,]", "", wage)
    wage = re.sub("[^0-9]", "", wage)
    wage = float(wage)
    if wage < 25000:
        wage *= 1000
    return wage


def standardize_wages(wages):
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
    This function performs a job analysis by searching for jobs on LinkedIn using a given search term and location. It uses the search_linkedin_jobs function to retrieve a list of jobs, and then for each job, it uses the get_text_in_url function to extract the job description from the job's webpage. The function then uses the text_similarity function to calculate the similarity between the job description and a given resume text. The function then adds this similarity score to the job dictionary and appends it to a list of job analysis, which is returned at the end of the function.

    Args:
    search_term (str): A string representing the job title or role to search for on LinkedIn
    location (str): A string representing the location to search for jobs in

    Returns:
    list: A list of dictionaries, each containing a job's title, url, description, and resume similarity score.

    """
    RESUME = get_text_resume(file="resumes/resume.txt")

    pagination = 1

    while pagination <= 1:
        jobs = search_linkedin_jobs(
            search_term=search_term, location=location, page=pagination
        )

        jobs_analysis = []

        for job in jobs:
            time.sleep(1)
            logging.info(
                "------------------------------------ Analyzing Job ------------------------------------"
            )

            job_url = job["job_url"]
            job["job_description"] = get_text_in_url(
                url=job_url
            )  # scraps text from site
            description = job["job_description"]

            logging.info("calculating resume similarity")
            job["resume_similarity"] = text_similarity(
                text1=RESUME, text2=description
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
                    save_to_s3(data=job, bucket_name="linkedin-bot")
                    jobs_analysis.append(job)
                    logging.debug(job)
                    salary = 0

                else:
                    logging.info("analyzing salary")
                    if max(job["salary"]) > int(min_salary):
                        save_to_s3(data=job, bucket_name=bucket_name)
                        jobs_analysis.append(job)
                        logging.info("keeping job with high salary")
                        logging.info("saved file to s3")
                        logging.debug(job)
                    else:
                        logging.info("ignore job with low salary")
            else:
                logging.info("low job similarity, ignoring")

        pagination = pagination + 1

    return jobs_analysis


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="This searches for jobs on linkedin and calculates similarity with your resume."
    )

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
        "minsal", metavar="minsal", type=str, help="the minimum salary to consider"
    )
    parser.add_argument(
        "minsim",
        metavar="minsim",
        type=float,
        help="the minimum similarity score from resume to job description",
    )

    args = parser.parse_args()

    jobs = jobs_analysis(
        search_term=args.search,
        location=args.location,
        min_salary=args.minsal,
        minsim=args.minsim,
    )

    send_email(
        email=email,
        subject="linkedin-bot ran",
        body="Ran analysis for {0} in the location {1}".format(
            args.search, args.location
        ),
    )
