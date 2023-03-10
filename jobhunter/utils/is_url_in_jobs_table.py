import sqlite3

def check_url_in_db(url):
    # Create a connection to the database
    conn = sqlite3.connect('/Users/jjespinoza/Documents/jobhunter/data/jobhunter.db')
    # Create a cursor object to execute SQL commands
    c = conn.cursor()

    # Execute a SELECT query to check if the URL exists in the 'job_url' column of the 'jobs' table
    c.execute("SELECT job_url FROM jobs WHERE job_url=?", (url,))
    result = c.fetchone() # fetchone() method returns a single row or None if there is no matching row

    # Close the connection
    conn.close()

    # Check if the query returned a result and return True or False accordingly
    if result is not None:
        return True
    else:
        return False
if __name__ == "__main__":
    url = 'https://www.linkedin.com/jobs/view/manager-of-data-science-at-gama-1-technologies-3515460976'
    is_url_in_db = check_url_in_db(url)
    print(is_url_in_db)