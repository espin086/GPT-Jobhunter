import sqlite3

def get_latest_jobs():
    # connect to the database
    conn = sqlite3.connect('../../data/jobhunter.db')

    # create a cursor
    c = conn.cursor()

    # execute the query
    c.execute("SELECT * FROM jobs WHERE date = (SELECT MAX(date) FROM jobs ORDER BY resume_sim ASC)")

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
    print(f"Date: {row[1]}")
    print(f"Resume Similarity: {row[2]}")
    print(f"Title: {row[3]}")
    print(f"Company Name: {row[4]}")
    print(f"Salary Max: {row[5]}")
    print(f"Job URL: {row[7]}\n")

