from jobhunter.utils import conn

# Create a cursor object to execute SQL commands
c = conn.cursor()


# Create a table
c.execute('''CREATE TABLE IF NOT EXISTS jobs
             (id INTEGER PRIMARY KEY,
              date TEXT,
              resume_sim REAL,
              title TEXT, 
              company_name TEXT, 
              salary_max INTEGER,
              location TEXT,
              job_url TEXT,
              company_url TEXT,
              description TEXT)''')

# Commit the changes and close the connection
conn.commit()
conn.close()