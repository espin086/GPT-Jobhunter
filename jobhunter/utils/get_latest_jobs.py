import sqlite3
import webbrowser

def get_latest_jobs():
    # connect to the database
    conn = sqlite3.connect('/Users/jjespinoza/Documents/jobhunter/data/jobhunter.db')

    # create a cursor
    c = conn.cursor()

    # execute the query
    c.execute("""SELECT DISTINCT date, resume_sim, title, company_name, salary_max, job_url
FROM jobs 
WHERE date BETWEEN strftime('%Y-%m-%d', (SELECT MAX(date) FROM jobs), '-1 day') AND (SELECT MAX(date) FROM jobs)
    AND title not like '%manager%'
    AND title not like '%health%'
    AND title not like '%clinic%'
    AND title not like '%data engineer%'
    AND title not like '%data analytics%'
    AND title not like '%business intelligence%'
    AND company_name not in('confidential1234', 'storm3')
    AND resume_sim > .15
ORDER BY date DESC, CAST(resume_sim as float) DESC
LIMIT 150;

    """
    )

    # fetch the results
    results = c.fetchall()

    # close the connection
    conn.close()

    return results
def job_url_opener():
    latest_jobs = get_latest_jobs()
    for row in latest_jobs:
        url = row[5]
        print(f"Opening job URL: {url}")
        webbrowser.open(url)

if __name__ == "__main__":
    latest_jobs = get_latest_jobs()
    for row in latest_jobs:
        print('-'* 30)
        print(f"Date: {row[0]}")
        print(f"Resume Similarity: {row[1]}")
        print(f"Title: {row[2]}")
        print(f"Company Name: {row[3]}")
        print(f"Salary Max: {row[4]}")
        print(f"Job URL: {row[5]}\n")

    job_url_opener()

