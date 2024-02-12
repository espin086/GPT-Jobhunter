"""
This is the main.py file that will be used to run the pipeline and query the SQLite database.
"""
import logging
import os
import sqlite3
from pathlib import Path

import pandas as pd
import PyPDF2
import streamlit as st

from config import (
    REMOTE_JOBS_ONLY,
    POSITIONS,
    PROCESSED_DATA_PATH,
    RAW_DATA_PATH,
    RESUME_PATH,
)
from dataTransformer import DataTransformer
from extract import extract
from FileHandler import FileHandler
from load import load
from SQLiteHandler import (
    fetch_resumes_from_db,
    get_resume_text,
    save_text_to_db,
    update_similarity_in_db,
)

logging.basicConfig(level=logging.INFO)

file_handler = FileHandler(raw_path=RAW_DATA_PATH, processed_path=PROCESSED_DATA_PATH)


def run_transform():
    DataTransformer(
        raw_path=RAW_DATA_PATH,
        processed_path=PROCESSED_DATA_PATH,
        resume_path=RESUME_PATH,
        data=file_handler.import_job_data_from_dir(dirpath=RAW_DATA_PATH),
    ).transform()


# Streamlit app
st.title("Positions & Remote Jobs")

st.write(POSITIONS)
st.write(REMOTE_JOBS_ONLY)

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


if "button_clicked" not in st.session_state:
    st.session_state.button_clicked = False

if st.button("Upload Resume") or st.session_state.button_clicked:
    st.session_state.button_clicked = True
    uploaded_file = st.file_uploader("Choose a file", type=["pdf", "txt"])
    text = " "
    logging.info("File uploader initialized")
    if uploaded_file is not None:
        try:
            if uploaded_file.type == "application/pdf":
                logging.info("File uploaded is a pdf")
                pdf = PyPDF2.PdfFileReader(uploaded_file)
                number_of_pages = pdf.getNumPages()
                for page_num in range(0, number_of_pages):
                    page = pdf.getPage(page_num)
                    text += page.extractText()
                    print(text)
                logging.info("Resume text extracted successfully!")
            else:  # For txt files
                text = uploaded_file.read().decode("utf-8")
            logging.info("Resume text extracted successfully!")

            save_text_to_db(uploaded_file.name, text)
            logging.info("Resume text saved to database!")
            st.success("Saved to database!")
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            st.error(f"An error occurred: {e}")

if "select_resume_button_clicked" not in st.session_state:
    st.session_state.select_resume_button_clicked = False

if st.button("Select Resume") or st.session_state.select_resume_button_clicked:
    st.session_state.select_resume_button_clicked = True

    available_resumes = fetch_resumes_from_db()
    selected_resume = st.selectbox("Choose a resume:", available_resumes)

    if st.button("Use Selected Resume"):
        # Here you can add the code to process the selected resume
        update_similarity_in_db(selected_resume)


if st.button("Query DB"):
    try:
        # Connect to SQLite database
        conn = sqlite3.connect("all_jobs.db")

        # Perform SQL query
        query = "SELECT * FROM jobs_new ORDER BY date DESC, resume_similarity DESC"
        df = pd.read_sql(query, conn)

        # Close database connection
        conn.close()

        # Display data as a dataframe in Streamlit
        st.write(df)
        st.success("Results returned successfully!")

    except Exception as e:
        st.error(f"An error occurred: {e}")
