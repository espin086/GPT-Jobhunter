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
import streamlit.components.v1 as components
from pandas.api.types import (
    is_categorical_dtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_object_dtype,
)

from config import (
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

def filter_dataframe(df: pd.DataFrame) -> pd.DataFrame:

    modify = st.checkbox("Add filters")

    if not modify:
        return df

    df = df.copy()

    # Try to convert datetimes into a standard format (datetime, no timezone)
    for col in df.columns:
        if pd.api.types.is_object_dtype(df[col]):
            try:
                df[col] = pd.to_datetime(df[col]).dt.date
            except Exception:
                pass

    to_filter_columns = st.multiselect("Filter dataframe on", df.columns)

    for column in to_filter_columns:
        unique_values = df[column].dropna().unique()
        if len(unique_values) == 0:
            st.warning(f"No available data for filtering on {column}. Skipping this filter.")
            continue

        left, right = st.columns((1, 20))
        left.write("↳")
        # Update the rest of your filtering logic here
        if is_categorical_dtype(df[column]) or df[column].nunique() < 15:
            # Ensure that the default list does not contain NaN
            user_cat_input = right.multiselect(
                f"Values for {column}",
                options=unique_values,  # Use the filtered list of unique values
                default=unique_values,  # Default to all unique values (excluding NaN)
            )
            df = df[df[column].isin(user_cat_input)]
        elif is_numeric_dtype(df[column]):
            _min = float(df[column].min())
            _max = float(df[column].max())
            step = (_max - _min) / 100
            user_num_input = right.slider(
                f"Values for {column}",
                _min,
                _max,
                (_min, _max),
                step=step,
            )
            df = df[df[column].between(*user_num_input)]
        elif is_datetime64_any_dtype(df[column]):
            min_date = df[column].min()
            max_date = df[column].max()
            user_date_input = right.date_input(f"Date range for {column}", value=(min_date, max_date), key=column)
            df = df[(df[column] >= user_date_input[0]) & (df[column] <= user_date_input[1])]
        else:
            user_text_input = right.text_input(
                f"Substring or regex in {column}",
            )
            if user_text_input:
                df = df[df[column].str.contains(user_text_input)]
    return df

logging.basicConfig(level=logging.INFO)

file_handler = FileHandler(raw_path=RAW_DATA_PATH, processed_path=PROCESSED_DATA_PATH)


def run_transform():
    DataTransformer(
        raw_path=RAW_DATA_PATH,
        processed_path=PROCESSED_DATA_PATH,
        resume_path=RESUME_PATH,
        data=file_handler.import_job_data_from_dir(dirpath=RAW_DATA_PATH),
    ).transform()

if "button_clicked" not in st.session_state:
    st.session_state.button_clicked = False

if "select_resume_button_clicked" not in st.session_state:
    st.session_state.select_resume_button_clicked = False

if 'data_queried' not in st.session_state:
    st.session_state['data_queried'] = False

if 'query_result' not in st.session_state:
    st.session_state['query_result'] = pd.DataFrame()

with st.sidebar:
    st.image(
        "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR_xdPASjFQb1WY8M3-9yeilpa_46ECb_mTjg&usqp=CAU"
    )
    st.title("GPT - Job Hunter")
    choice = st.radio("Navigation", ["Search", "Resumes", "Jobs"])
    st.info(
        "Revolutionize your job search with our AI-powered tool! Analyzing job postings using GPT, it offers personalized resume recommendations, empowering job seekers with tailored insights for success."
    )

if choice == "Search":
    st.title("Positions")

    job_titles_input = st.text_input("Enter job titles (comma-separated):")
    job_titles = [title.strip() for title in job_titles_input.split(',')]
    st.write("Job Titles:", job_titles)

    st.title("Start Searching for Jobs")

    if st.button("Run Search"):
        if job_titles:
            steps = [
                lambda: extract(job_titles),
                run_transform,
                load,
            ]
            progress_bar = st.progress(0)

            for i, step in enumerate(steps):
                step()  # Execute each function
                progress_bar.progress((i + 1) / len(steps))  # Update progress bar

            file_handler.delete_local()

            st.success("Search complete!")
        else:
            st.warning("Please enter job titles before running the search.")

elif choice == "Resumes":
    st.title("Resumes")
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

    if st.button("Select Resume") or st.session_state.select_resume_button_clicked:
        st.session_state.select_resume_button_clicked = True

        available_resumes = fetch_resumes_from_db()
        selected_resume = st.selectbox("Choose a resume:", available_resumes)

        if st.button("Use Selected Resume"):
            # Here you can add the code to process the selected resume
            update_similarity_in_db(selected_resume)

elif choice == "Jobs":
    st.title("Jobs")
    if st.button("Query DB"):
        st.session_state['data_queried'] = True
        try:
            # Connect to SQLite database
            conn = sqlite3.connect("all_jobs.db")

            # Perform SQL query
            query = """
                SELECT 
                    id, 
                    primary_key, 
                    date, 
                    CAST(resume_similarity AS REAL) AS resume_similarity,
                    title,
                    company,
                    company_url,
                    company_type,
                    job_type,
                    job_is_remote,
                    job_offer_expiration_date,
                    salary_low,
                    salary_high,
                    salary_currency,
                    salary_period,
                    job_benefits,
                    city,
                    state,
                    country,
                    apply_options,
                    required_skills,
                    required_experience,
                    required_education,
                    description,
                    highlights
                FROM jobs_new 
                ORDER BY date DESC, resume_similarity DESC

            """
            st.session_state['query_result'] = pd.read_sql(query, conn)
            conn.close()
            st.success("Results returned successfully!")
        except Exception as e:
            st.error(f"An error occurred: {e}")

    if st.session_state['data_queried']:
        filtered_df = filter_dataframe(st.session_state['query_result'])
        st.dataframe(filtered_df)