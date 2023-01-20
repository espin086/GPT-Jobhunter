from search_jobs import search_linkedin_jobs
from extract_text_from_site import get_text_in_url
from text_similarity import text_similarity
import time

def get_text_resume(file):
    with open(file) as f:
        resume = [line.rstrip('\n') for line in f]
    resume = " ".join(resume) #to join list of strings into a single string
    return resume

def jobs_analysis(search_term, location):
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
    

analysis = jobs_analysis(search_term="Apple Artificial Intelligence", location="Los Angeles")


    
