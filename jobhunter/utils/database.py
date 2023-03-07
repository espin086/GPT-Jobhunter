import sqlite3

# Create a connection to the database
conn = sqlite3.connect('../../data/jobhunter.db')

# Create a cursor object to execute SQL commands
c = conn.cursor()


# Create a table
c.execute('''CREATE TABLE IF NOT EXISTS jobs
             (id INTEGER PRIMARY KEY,
              posted_date TEXT,
              resume_similarity REAL,
              job_title TEXT, 
              company TEXT, 
              salary INTEGER,
              job_location TEXT,
              job_url TEXT,
              job_description TEXT)''')

# Commit the changes and close the connection
conn.commit()
conn.close()