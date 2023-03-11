import webbrowser
import re

from get_latest_jobs import get_latest_jobs
from gpt_linkedin_con_message import recruiter_message


def linkedin_search(company, title):
    url = f"https://www.linkedin.com/company/{company}/people/?keywords={title}"
    webbrowser.open(url)
    return None

def clean_company_names():
    dedup_company_list = []
    clean_companies = []
    for job in get_latest_jobs():
        dedup_company_list.append(job[3])
        dedup_company_list = [*set(dedup_company_list)]
    for company in dedup_company_list:
        clean_companies.append(re.sub(r"\s+", "-", company))
    return clean_companies

def open_search_links(title):
    companies = clean_company_names()
    for company in companies:
        linkedin_search(company=company, title=title)
        
def write_recruiter_linkedin_connection_message():
    jobs = get_latest_jobs()
    for job in jobs:
        title = job[2].title()
        company = job[3].title()
        recruiter_message(company=company, title=title)

def recruiter_outreach():
    open_search_links(title='recruiter')
    write_recruiter_linkedin_connection_message()
    

if __name__ == "__main__":
    recruiter_outreach()
    



