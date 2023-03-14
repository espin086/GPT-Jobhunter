import webbrowser
import sqlite3
from get_latest_jobs import get_latest_jobs



def job_url_opener():
    latest_jobs = get_latest_jobs()
    for row in latest_jobs:
        url = row[5]
        print(f"Opening job URL: {url}")
        webbrowser.open(url)

job_url_opener()