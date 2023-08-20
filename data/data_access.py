import sqlite3


def init_db():
    conn = sqlite3.connect("data/job_search.db")
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS applicants (
            id INTEGER PRIMARY KEY,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone_number TEXT,
            resume_path TEXT,
            preferred_job_title TEXT,
            preferred_location TEXT
        )
    """
    )
    conn.commit()
    conn.close()


init_db()
