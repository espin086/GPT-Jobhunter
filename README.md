This module allows you to perform a job analysis on LinkedIn by searching for jobs using a given search term and location, extracting job descriptions from job URLs, and calculating the similarity between a given resume text and a job description.

Installation
To use this module, you will need to have the following dependencies installed:

search_jobs: a module for searching for jobs on LinkedIn
extract_text_from_site: a module for extracting text from a website
text_similarity: a module for calculating the similarity between two pieces of text
time: a module for adding delay between requests
logging: a module for generating log messages
argparse: a module for parsing command line arguments
pprint: a module for pretty-printing data structures

Usage
The main function of this module, jobs_analysis, takes a search term and a location as inputs and returns a list of dictionaries, each containing a job's title, url, description, and resume similarity score. The module also includes a main function that allows the user to input a search term and location through command line arguments.

To use this module, you will need to have a resume text file named 'resume.txt' in the same directory as the module. The function get_text_resume reads this file and returns the content as a single string.


```from job_analysis import jobs_analysis

jobs = jobs_analysis(search_term='software engineer', location='San Francisco, CA')
pprint.pprint(jobs)

or 

python job_analysis.py search location```

