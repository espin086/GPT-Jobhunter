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


# Database functions
def add_applicant(
    first_name,
    last_name,
    email,
    phone_number,
    resume_path,
    preferred_job_title,
    preferred_location,
):
    conn = sqlite3.connect("data/job_search.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO applicants (first_name, last_name, email, phone_number, resume_path, preferred_job_title, preferred_location) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            first_name,
            last_name,
            email,
            phone_number,
            resume_path,
            preferred_job_title,
            preferred_location,
        ),
    )
    conn.commit()
    conn.close()


def get_all_applicants():
    conn = sqlite3.connect("data/job_search.db")
    c = conn.cursor()
    c.execute("SELECT * FROM applicants")
    data = c.fetchall()
    conn.close()
    return data


def update_applicant(id, **kwargs):
    conn = sqlite3.connect("data/job_search.db")
    c = conn.cursor()
    for key, value in kwargs.items():
        c.execute(f"UPDATE applicants SET {key} = ? WHERE id = ?", (value, id))
    conn.commit()
    conn.close()


def delete_applicant(id):
    conn = sqlite3.connect("data/job_search.db")
    c = conn.cursor()
    c.execute("DELETE FROM applicants WHERE id = ?", (id,))
    conn.commit()
    conn.close()
