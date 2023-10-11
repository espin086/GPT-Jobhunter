import sqlite3

import pandas as pd
import streamlit as st
from config import LOCATIONS, POSITIONS
from delete_local import delete_local
from extract import extract
from load import load
from transform import transform

st.title("Config Manager")

st.write(POSITIONS)
st.write(LOCATIONS)


# Streamlit app
st.title("Pipeline Manager")

if st.button("Run Pipeline"):
    steps = [extract, transform, load, delete_local]
    progress_bar = st.progress(0)

    for i, step in enumerate(steps):
        step()  # Execute each function
        progress_bar.progress((i + 1) / len(steps))  # Update progress bar

    st.success("Pipeline completed.")

# Button to Query SQLite Database
if st.button("Query SQLite Database"):
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
