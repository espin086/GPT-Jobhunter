"""
This is a module for performing a job analysis on LinkedIn. It imports functions from other modules, including search_jobs, extract_text_from_site and text_similarity, to search for jobs on LinkedIn, extract job descriptions from job URLs, and calculate the similarity between a given resume text and a job description. The main function, jobs_analysis, takes a search term and a location as inputs and returns a list of dictionaries, each containing a job's title, url, description, and resume similarity score. The module also includes a main function that allows the user to input a search term and location through command line arguments.
"""


from search_jobs import search_linkedin_jobs
from extract_text_from_site import get_text_in_url
from text_similarity import text_similarity
import time
import logging

import argparse
import pprint


pp = pprint.PrettyPrinter(indent=4)
logging.basicConfig(level=logging.INFO)


def get_text_resume(file):
    """
    This function reads a text file and returns the content as a single string.
    
    Args:
    file (str): The name of the file to be read.
    
    Returns:
    str : A string containing the contents of the file.
    """
    with open(file) as f:
        resume = [line.rstrip('\n') for line in f]
    resume = " ".join(resume) #to join list of strings into a single string
    return resume

def jobs_analysis(search_term, location):
    """
    This function performs a job analysis by searching for jobs on LinkedIn using a given search term and location. It uses the search_linkedin_jobs function to retrieve a list of jobs, and then for each job, it uses the get_text_in_url function to extract the job description from the job's webpage. The function then uses the text_similarity function to calculate the similarity between the job description and a given resume text. The function then adds this similarity score to the job dictionary and appends it to a list of job analysis, which is returned at the end of the function.
    
    Args:
    search_term (str): A string representing the job title or role to search for on LinkedIn
    location (str): A string representing the location to search for jobs in
    
    Returns:
    list: A list of dictionaries, each containing a job's title, url, description, and resume similarity score.
    
    """
    RESUME = get_text_resume(file='resume.txt')
    # PARTITION_STRING = "Show more"
    
    
    jobs = search_linkedin_jobs(search_term=search_term, location=location, page=1)
    jobs_analysis = []
    for job in jobs:
        time.sleep(1)
        job_url = job['job_url']
        job['job_description'] = get_text_in_url(url=job_url)
        description = job['job_description']
        job['resume_similarity'] = text_similarity(text1=RESUME.encode('utf-8'), text2=description.encode('utf-8'))
        print(job['job_title'], " : ", job['resume_similarity'], job['job_url'], "\n")
        jobs_analysis.append(job)
    return jobs_analysis
    




    
if __name__ == "__main__":
    
    
    parser = argparse.ArgumentParser(description="This searches for jobs on linkedin and calculates similarity with your resume.")
    
    parser.add_argument('search', metavar='search', type=str, help='the term to search for, like job title')
    parser.add_argument('location', metavar='location', type=str, help='the location of the job')
    

    args = parser.parse_args()

    jobs_analysis(search_term=args.search, location=args.location)

    
    