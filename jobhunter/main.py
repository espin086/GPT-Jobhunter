"""
This is the main.py file that will be used to run the pipeline and query the SQLite database.
"""
import os
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

from jobhunter.config import (
    LOCATIONS,
    POSITIONS,
    PROCESSED_DATA_PATH,
    RAW_DATA_PATH,
    RESUME_PATH,
)
from jobhunter.dataTransformer import DataTransformer
from jobhunter.extract import extract
from jobhunter.FileHandler import FileHandler
from jobhunter.load import load

file_handler = FileHandler(raw_path=RAW_DATA_PATH, processed_path=PROCESSED_DATA_PATH)


def run_transform():
    DataTransformer(
        raw_path=RAW_DATA_PATH,
        processed_path=PROCESSED_DATA_PATH,
        resume_path=RESUME_PATH,
        data=file_handler.import_job_data_from_dir(dirpath=RAW_DATA_PATH),
    ).transform()


# Streamlit app
st.title("Positions & Locations")

st.write(POSITIONS)
st.write(LOCATIONS)

st.title("Start Searching for Jobs")

if st.button("Run Search"):
    steps = [
        extract,
        run_transform,
        load,
    ]
    progress_bar = st.progress(0)

    for i, step in enumerate(steps):
        step()  # Execute each function
        progress_bar.progress((i + 1) / len(steps))  # Update progress bar

    file_handler.delete_local()

    st.success("Search complete!")
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
        st.success("Results returned successfully!")

    except Exception as e:
        st.error(f"An error occurred: {e}")
