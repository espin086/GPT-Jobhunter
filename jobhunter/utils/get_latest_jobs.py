import sqlite3

def get_latest_jobs():
    # connect to the database
    conn = sqlite3.connect('/Users/jjespinoza/Documents/jobhunter/data/jobhunter.db')

    # create a cursor
    c = conn.cursor()

    # execute the query
    c.execute("""SELECT DISTINCT date, resume_sim, title, company_name, salary_max, job_url
FROM jobs 
WHERE date BETWEEN strftime('%Y-%m-%d', (SELECT MAX(date) FROM jobs), '-14 day') AND (SELECT MAX(date) FROM jobs)
ORDER BY CAST(resume_sim as float) DESC
LIMIT 30;

    """
    )

    # fetch the results
    results = c.fetchall()

    # close the connection
    conn.close()

    return results

if __name__ == "__main__":
    latest_jobs = get_latest_jobs()

# print the results
for row in latest_jobs:
    print('-'* 30)
    print(f"Date: {row[0]}")
    print(f"Resume Similarity: {row[1]}")
    print(f"Title: {row[2]}")
    print(f"Company Name: {row[3]}")
    print(f"Salary Max: {row[4]}")
    print(f"Job URL: {row[5]}\n")

