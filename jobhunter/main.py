"""
This is the main.py file that will be used to run the pipeline and query the SQLite database.
"""
import sqlite3

import pandas as pd
import streamlit as st
from config import LOCATIONS, POSITIONS
from extract import extract
from FileHandler import FileHandler
from load import load

from jobhunter.dataTransformer import DataTransformer

st.title("Config Manager")

st.write(POSITIONS)
st.write(LOCATIONS)


file_handler = FileHandler(
    raw_path="temp/data/raw", processed_path="temp/data/processed"
)

transform = DataTransformer(
    file_handler.import_job_data_from_dir(dirpath="temp/data/raw")
).transform


# Streamlit app
st.title("Pipeline Manager")

if st.button("Run Pipeline and Query SQLite Database"):
    steps = [
        extract,
        transform,
        load,
    ]
    progress_bar = st.progress(0)

    for i, step in enumerate(steps):
        step()  # Execute each function
        progress_bar.progress((i + 1) / len(steps))  # Update progress bar

    file_handler.delete_local()

    st.success("Pipeline completed.")
    try:
        # Connect to SQLite database
        conn = sqlite3.connect("all_jobs.db")

        # Perform SQL query
        query = "SELECT * FROM jobs ORDER BY date DESC, resume_similarity DESC"
        df = pd.read_sql(query, conn)

        # Close database connection
        conn.close()

        # Display data as a dataframe in Streamlit
        st.write(df)
        st.success("Successfully queried the SQLite database.")

    except Exception as e:
        st.error(f"An error occurred: {e}")
