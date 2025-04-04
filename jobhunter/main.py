"""
This is the main.py file that will be used to run the pipeline and query the SQLite database.
"""

import logging
import os
import sqlite3
import webbrowser
from pathlib import Path
import sys
import time

import pandas as pd
import PyPDF2
import streamlit as st
import streamlit.components.v1 as components
from config import PROCESSED_DATA_PATH, RAW_DATA_PATH, RESUME_PATH
from dataTransformer import DataTransformer
from extract import extract
from FileHandler import FileHandler
from load import load
from pandas.api.types import (
    is_categorical_dtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_object_dtype,
)
from SQLiteHandler import (
    delete_resume_in_db,
    fetch_resumes_from_db,
    get_resume_text,
    save_text_to_db,
    update_resume_in_db,
    update_similarity_in_db,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set page config at the start
st.set_page_config(
    page_title="GPT Job Hunter", 
    page_icon="🔍",
    layout="wide",  # Use wide layout for better space utilization
    initial_sidebar_state="collapsed"  # Start with sidebar collapsed
)

# Check for OpenAI API key
if not os.environ.get("OPENAI_API_KEY") and not st.session_state.get("openai_api_key"):
    logger.warning("OpenAI API Key not found in environment variables or session state")
    # Instead of stopping the app, we'll let the user enter the key in the UI
    # The key warning will be shown in the API Settings expander in the Resume Management tab

# Initialize the database
def initialize_database():
    """Create the SQLite database and necessary tables if they don't exist."""
    try:
        conn = sqlite3.connect("all_jobs.db")
        cursor = conn.cursor()
        
        # Create jobs_new table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                primary_key TEXT UNIQUE,
                date TEXT,
                resume_similarity REAL DEFAULT 0,
                title TEXT,
                company TEXT,
                company_url TEXT,
                company_type TEXT,
                job_type TEXT,
                job_is_remote TEXT,
                job_apply_link TEXT,
                job_offer_expiration_date TEXT,
                salary_low REAL,
                salary_high REAL,
                salary_currency TEXT,
                salary_period TEXT,
                job_benefits TEXT,
                city TEXT,
                state TEXT,
                country TEXT,
                apply_options TEXT,
                required_skills TEXT,
                required_experience TEXT,
                required_education TEXT,
                description TEXT,
                highlights TEXT,
                embeddings TEXT
            )
        ''')
        
        # Create resumes table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS resumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resume_name TEXT UNIQUE,
                resume_text TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        st.error(f"Error initializing database: {e}")
        sys.exit(1)

# Initialize database at startup
initialize_database()

def filter_dataframe(df: pd.DataFrame, key_prefix: str = "") -> pd.DataFrame:
    """
    Adds a UI on top of a dataframe to let users filter columns
    
    Args:
        df (pd.DataFrame): Original dataframe
        key_prefix (str): A prefix to ensure unique widget keys
        
    Returns:
        pd.DataFrame: Filtered dataframe
    """
    modify = st.checkbox("Add filters", key=f"{key_prefix}_add_filters")

    if not modify:
        return df

    df = df.copy()

    # Try to convert datetimes into standard format
    for col in df.columns:
        if is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.tz_localize(None)

    modification_container = st.container()

    with modification_container:
        to_filter_columns = st.multiselect(
            "Filter dataframe on", 
            df.columns, 
            key=f"{key_prefix}_filter_columns"
        )
        for column in to_filter_columns:
            left, right = st.columns((1, 20))
            widget_key_base = f"{key_prefix}_filter_{column}"
            if is_categorical_dtype(df[column]) or df[column].nunique() < 10:
                user_cat_input = right.multiselect(
                    f"Values for {column}",
                    df[column].unique(),
                    default=list(df[column].unique()),
                    key=f"{widget_key_base}_cat"
                )
                df = df[df[column].isin(user_cat_input)]
            elif is_numeric_dtype(df[column]):
                _min = float(df[column].min())
                _max = float(df[column].max())
                step = (_max - _min) / 100
                user_num_input = right.slider(
                    f"Values for {column}",
                    min_value=_min,
                    max_value=_max,
                    value=(_min, _max),
                    step=step,
                    key=f"{widget_key_base}_num"
                )
                df = df[df[column].between(*user_num_input)]
            elif is_datetime64_any_dtype(df[column]):
                user_date_input = right.date_input(
                    f"Values for {column}",
                    value=(
                        df[column].min(),
                        df[column].max(),
                    ),
                    key=f"{widget_key_base}_date"
                )
                if len(user_date_input) == 2:
                    user_date_input = tuple(map(pd.to_datetime, user_date_input))
                    start_date, end_date = user_date_input
                    df = df.loc[df[column].between(start_date, end_date)]
            else:
                user_text_input = right.text_input(
                    f"Substring or regex in {column}",
                    key=f"{widget_key_base}_text"
                )
                if user_text_input:
                    df = df[df[column].astype(str).str.contains(user_text_input)]

    return df

def open_next_job_urls(filtered_df: pd.DataFrame, last_opened_index: int, num_jobs: int):
    """
    Opens job URLs in the browser

    Args:
        filtered_df (pd.DataFrame): Dataframe containing job apply links
        last_opened_index (int): Index to start from
        num_jobs (int): Number of job URLs to open
    """
    
    # Extract job apply links from the dataframe
    job_apply_links = filtered_df["job_apply_link"].tolist()
    
    # Get a slice of job links to open based on the last opened index
    job_links_to_open = job_apply_links[last_opened_index:last_opened_index + num_jobs]
    
    # Open each job link in a new browser tab
    for job_link in job_links_to_open:
        if job_link and isinstance(job_link, str) and job_link.startswith("http"):
            try:
                webbrowser.open_new_tab(job_link)
                time.sleep(0.5)  # Small delay to prevent browser throttling
            except Exception as e:
                st.error(f"Failed to open URL: {job_link}. Error: {e}")
        else:
            st.warning(f"Invalid URL: {job_link}")
    
    # Display information about the opened URLs
    st.info(f"Opened {len(job_links_to_open)} job URLs in new browser tabs.")

file_handler = FileHandler(raw_path=RAW_DATA_PATH, processed_path=PROCESSED_DATA_PATH)


def run_transform():
    DataTransformer(
        raw_path=RAW_DATA_PATH,
        processed_path=PROCESSED_DATA_PATH,
        resume_path=RESUME_PATH,
        data=file_handler.import_job_data_from_dir(dirpath=RAW_DATA_PATH),
    ).transform()


# Initialize session state variables
if "active_resume" not in st.session_state:
    st.session_state.active_resume = None

if "openai_api_key" not in st.session_state:
    st.session_state.openai_api_key = os.environ.get("OPENAI_API_KEY", "")

if "data_queried" not in st.session_state:
    st.session_state["data_queried"] = False

if "query_result" not in st.session_state:
    st.session_state["query_result"] = pd.DataFrame()

if "filtered_result" not in st.session_state:
    st.session_state["filtered_result"] = pd.DataFrame()

if "last_opened_index" not in st.session_state:
    st.session_state["last_opened_index"] = 0

# Apply custom CSS to remove white lines and improve overall appearance
st.markdown("""
<style>
    /* Remove whitespace/padding in the main area */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    
    /* Remove white lines/dividers */
    .stHorizontalBlock {
        border: none !important;
        gap: 1rem;
    }
    
    /* Remove dividers between elements */
    div[data-testid="stVerticalBlock"] > div {
        border: none !important;
        box-shadow: none !important;
    }
    
    /* Remove all stDivider elements */
    .stDivider {
        display: none !important;
    }
    
    /* Remove borders from elements */
    button, input, .stSelectbox, .stTextInput, 
    .stMultiSelect, div[data-baseweb="select"], .stSlider {
        border: 1px solid #e0e0e0 !important;
        box-shadow: none !important;
    }
    
    /* Clean container styling */
    .job-search-container, .resume-container {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        border: none;
        box-shadow: none !important;
    }
    
    /* Remove dividers in dataframe */
    .dataframe {
        border: none !important;
    }
    .dataframe th, .dataframe td {
        border: none !important;
        border-bottom: 1px solid #f0f2f6 !important;
    }
    
    /* Header styling */
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        margin-bottom: 15px;
    }
    
    /* Rounded container corners and improve card appearance */
    div[data-testid="stVerticalBlock"] > div {
        border-radius: 10px !important;
    }
    
    /* Remove horizontal lines */
    hr {
        display: none !important;
    }
    
    /* Improve spacing between elements */
    .row-widget {
        margin-bottom: 10px !important;
    }
    
    /* Custom styling for pills */
    .job-pill {
        background-color: #e6f3ff;
        padding: 8px;
        border-radius: 5px;
        margin: 2px;
        display: inline-block;
        border: none !important;
    }
    
    /* Styling for the active resume */
    .active-resume {
        background-color: #e7f5e7;
        border-left: 4px solid #28a745;
        padding: 10px 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 4px 4px 0 0;
        padding: 10px 16px;
        background-color: #f0f2f6;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #4361ee !important;
        color: white !important;
    }
    
    /* Button styling for better visibility */
    .stButton > button {
        color: #000000 !important;
        background-color: #f0f2f6 !important;
        border-color: #d2d6db !important;
    }
    
    .stButton > button[data-baseweb="button"][kind="primary"] {
        background-color: #4361ee !important;
        color: white !important;
    }
    
    .stButton > button[data-baseweb="button"][kind="secondary"] {
        background-color: #f8f9fa !important;
        color: #000000 !important;
        border-color: #d2d6db !important;
    }
    
    /* Cards and containers */
    .card {
        padding: 1.5rem;
        border-radius: 0.5rem;
        background: white;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12);
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Print session state for debugging
if st.session_state.active_resume:
    logging.info(f"Active resume in session state: {st.session_state.active_resume}")

# New integrated UI structure with no sidebar
st.title("GPT Job Hunter")
st.write("AI-powered job search assistant")

# Main content area with tabs for integrated flow
# Combine Tab 2 and Tab 3
tab1, tab2 = st.tabs(["📄 Resume Management", "🔍 Job Search & Results"])

# Tab 1: Resume Management
with tab1:
    st.header("Resume Management")
    
    # OpenAI API Key Input Section - Make more prominent
    api_key_container = st.container()
    with api_key_container:
        st.markdown("""
        <div style="background-color: #f0f7fb; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 5px solid #0078ff;">
            <h3 style="margin-top: 0;">⚠️ OpenAI API Key Required</h3>
            <p>An OpenAI API key is <strong>required</strong> for analyzing resumes and calculating job matches. Your key is stored only in your browser session and not saved on any servers.</p>
            <p>You can get an API key from <a href="https://platform.openai.com/account/api-keys" target="_blank">OpenAI's website</a>.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # API Key input
        openai_api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            value=st.session_state.openai_api_key,
            placeholder="sk-...",
            help="Enter your OpenAI API key here. Get one at https://platform.openai.com/account/api-keys"
        )
        
        if openai_api_key:
            # Check if it looks like a valid API key
            if openai_api_key.startswith("sk-") and len(openai_api_key) > 30:
                st.session_state.openai_api_key = openai_api_key
                os.environ["OPENAI_API_KEY"] = openai_api_key
                st.success("✅ API key set successfully!")
            else:
                st.error("❌ This doesn't look like a valid OpenAI API key. API keys should start with 'sk-' and be at least 30 characters long.")
        else:
            st.warning("⚠️ Please enter an OpenAI API key to enable resume analysis and job matching.")
        
        # Add a horizontal line to separate the API key section from the rest
        st.markdown("<hr>", unsafe_allow_html=True)
    
    # Check for available resumes
    available_resumes = fetch_resumes_from_db()
    
    # Display current active resume if any
    if st.session_state.active_resume:
        st.success(f"Current active resume: **{st.session_state.active_resume}**")
    else:
        st.info("No active resume selected. Please upload or select a resume.")
    
    # Resume actions in columns for better organization
    st.markdown('<div class="resume-container">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">Resume Actions</div>', unsafe_allow_html=True)
    
    action_col1, action_col2 = st.columns(2)
    
    upload_tab = action_col1.expander("UPLOAD RESUME", expanded=False)
    create_tab = action_col2.expander("CREATE RESUME", expanded=False)
    
    # Handle Upload Resume
    with upload_tab:
        st.write("Upload your existing resume (PDF or TXT)")
        uploaded_file = st.file_uploader("Choose a file", type=["pdf", "txt"])
        
        if uploaded_file is not None:
            upload_col1, upload_col2 = st.columns(2)
            process_upload = upload_col1.button("Process Upload", key="process_upload")
            cancel_upload = upload_col2.button("Cancel", key="cancel_upload")
            
            if process_upload:
                with st.spinner("Processing resume..."):
                    try:
                        text = " "
                        if uploaded_file.type == "application/pdf":
                            logging.info("File uploaded is a pdf")
                            pdf_reader = PyPDF2.PdfReader(uploaded_file) # Updated PyPDF2 usage
                            for page in pdf_reader.pages:
                                text += page.extract_text() or ""
                        else:  # For txt files
                            text = uploaded_file.read().decode("utf-8")
                        
                        save_text_to_db(uploaded_file.name, text)
                        st.session_state.active_resume = uploaded_file.name
                        st.success(f"✅ Resume '{uploaded_file.name}' uploaded and set as active!")
                        
                        # Update similarity scores
                        with st.spinner("Analyzing resume for job matching..."):
                            update_similarity_in_db(uploaded_file.name)
                            st.success("Resume analyzed and ready for job matching!")
                            
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"An error occurred processing the PDF: {e}. Please ensure it's text-based.")
                        logger.error(f"PDF processing error: {e}", exc_info=True)
    
    # Handle Create Resume
    with create_tab:
        st.write("Create a new resume from scratch")
        file_name = st.text_input("Resume Name", placeholder="e.g., My Software Engineer Resume", key="create_resume_name")
        new_resume_text = st.text_area("Resume Content", height=300, placeholder="Paste your resume content here...", key="create_resume_content")
        
        create_col1, create_col2 = st.columns(2)
        save_new = create_col1.button("Save New Resume", key="save_new_resume")
        cancel_create = create_col2.button("Cancel Create", key="cancel_create") # Unique key
        
        if save_new:
            if file_name and new_resume_text:
                with st.spinner("Saving resume..."):
                    resume_name = f"{file_name}.txt" if not file_name.endswith( (".txt", ".pdf")) else file_name # Check both
                    save_text_to_db(resume_name, new_resume_text)
                    st.session_state.active_resume = resume_name
                    st.success(f"✅ Resume '{resume_name}' created and set as active!")
                    
                    with st.spinner("Analyzing resume for job matching..."):
                        update_similarity_in_db(resume_name)
                        st.success("Resume analyzed and ready for job matching!")
                    
                    st.experimental_rerun()
            else:
                st.warning("Please provide both a name and content for the resume.")
    
    st.markdown('</div>', unsafe_allow_html=True)  # Close resume-container
    
    # Show available resumes section if any exist
    if available_resumes:
        st.markdown('<div class="resume-container">', unsafe_allow_html=True)
        st.markdown('<div class="section-header">Your Resumes</div>', unsafe_allow_html=True)
        
        for idx, resume in enumerate(available_resumes):
            col1, col2, col3 = st.columns([3, 1, 1])
            
            is_active = resume == st.session_state.active_resume
            resume_style = "background-color: #e7f5e7; border-left: 4px solid #28a745; padding: 10px; border-radius: 5px;" if is_active else "padding: 10px;"
            
            with col1:
                st.markdown(f'''
                <div style="{resume_style}">
                    <strong>{resume}</strong>
                    {' (Active)' if is_active else ''}
                </div>
                ''', unsafe_allow_html=True)
            
            with col2:
                if st.button("Use", key=f"use_{idx}", help=f"Set {resume} as your active resume"):
                    st.session_state.active_resume = resume
                    with st.spinner("Analyzing resume for job matching..."):
                        update_similarity_in_db(resume)
                        st.success(f"✅ Resume '{resume}' is now active and ready for job matching!")
                    st.experimental_rerun()
            
            with col3:
                if st.button("View/Edit", key=f"view_{idx}", help=f"View or edit {resume}"):
                    st.session_state.editing_resume = resume
        
        st.markdown('</div>', unsafe_allow_html=True)  # Close resume-container
        
        if "editing_resume" in st.session_state:
            selected_resume = st.session_state.editing_resume
            st.markdown('<div class="resume-container">', unsafe_allow_html=True)
            st.subheader(f"Editing: {selected_resume}")
            
            resume_text = get_resume_text(selected_resume)
            edited_text = st.text_area("Resume Content", value=resume_text, height=400, key="edit_text_area")
            
            edit_col1, edit_col2, edit_col3 = st.columns(3)
            
            if edit_col1.button("Save Changes", key="save_edit"):
                if edited_text != resume_text:
                    with st.spinner("Saving changes..."):
                        update_resume_in_db(selected_resume, edited_text)
                        st.success(f"Resume '{selected_resume}' updated successfully!")
                        
                        if selected_resume == st.session_state.active_resume:
                            with st.spinner("Re-analyzing updated resume..."):
                                update_similarity_in_db(selected_resume)
                                st.success("Resume re-analyzed with new content!")
                        
                        del st.session_state.editing_resume
                        st.experimental_rerun()
                else:
                    st.info("No changes detected.")
                    del st.session_state.editing_resume
                    st.experimental_rerun()
            
            if edit_col2.button("Cancel Edit", key="cancel_edit"): # Unique key
                del st.session_state.editing_resume
                st.experimental_rerun()
            
            if edit_col3.button("Delete Resume", key="delete_resume"):
                st.session_state.confirming_delete = selected_resume
            
            if "confirming_delete" in st.session_state and st.session_state.confirming_delete == selected_resume:
                st.warning(f"Are you sure you want to delete '{selected_resume}'? This cannot be undone.")
                
                confirm_col1, confirm_col2 = st.columns(2)
                
                if confirm_col1.button("Yes, Delete", key="confirm_delete"):
                    with st.spinner("Deleting resume..."):
                        delete_resume_in_db(selected_resume)
                        if st.session_state.active_resume == selected_resume:
                            st.session_state.active_resume = None
                        
                        del st.session_state.editing_resume
                        del st.session_state.confirming_delete
                        st.success(f"Resume '{selected_resume}' deleted successfully!")
                        st.experimental_rerun()
                
                if confirm_col2.button("Cancel Delete", key="cancel_delete_confirm"): # Unique key
                    del st.session_state.confirming_delete
                    st.experimental_rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)  # Close resume-container
    else:
        st.info("No resumes found. Please upload or create one.")


# Tab 2: Job Search & Results (Combined)
with tab2:
    st.header("Job Search & Results")
    
    # --- Job Search Input Section --- 
    if not st.session_state.active_resume:
        st.warning("Please select or upload a resume first in the Resume Management tab.")
        st.stop() 
    else:
        st.success(f"Using active resume: **{st.session_state.active_resume}**")
    
    with st.container():
        st.markdown('<div class="job-search-container">', unsafe_allow_html=True)
        st.markdown('<div class="section-header">Search Parameters</div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            job_titles_input = st.text_input(
                "Job Titles",
                placeholder="Enter job titles separated by commas",
                help="e.g., Data Scientist, ML Engineer",
                key="job_titles_input"
            )
        with col2:
            country = st.selectbox(
                "Country", options=["us", "uk", "ca", "au", "de", "fr", "es", "it"], index=0, key="country_select"
            )
        with col3:
            date_posted = st.selectbox(
                "Time Frame", options=["all", "today", "3days", "week", "month"], index=0, key="date_posted_select"
            )
        location = st.text_input(
            "Location", placeholder="City, state, or region (e.g., Chicago, Remote)", key="location_input"
        )
        
        job_titles = [title.strip() for title in job_titles_input.split(",")] if job_titles_input else []
        if job_titles and job_titles[0]: 
            st.markdown("##### Selected Positions:")
            cols = st.columns(min(len(job_titles), 4))
            for i, title in enumerate(job_titles):
                with cols[i % len(cols)]:
                    st.markdown(f'<div class="job-pill">{title}</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)  # Close job-search-container
    
    search_disabled = not (job_titles and job_titles[0])
    search_button = st.button(
        "🔍 Find Jobs", type="primary", disabled=search_disabled, use_container_width=True, key="find_jobs_button"
    )
    
    if search_disabled:
        st.info("Please enter at least one job title to search.")

    # --- Job Search Execution Section --- 
    if search_button:
        # ... (spinner and pipeline execution logic remains the same)
        with st.spinner("Searching for jobs..."):
            if st.session_state.openai_api_key:
                os.environ["OPENAI_API_KEY"] = st.session_state.openai_api_key
                logging.info("Set OpenAI API key from session state for job search")
            
            steps = [
                lambda: extract(job_titles, country=country, date_posted=date_posted, location=location),
                run_transform,
                load, # load calls check_and_upload_to_db internally
            ]
            
            progress_container = st.container()
            with progress_container:
                progress_text = st.empty()
                progress_bar = st.progress(0)
            
            try:
                progress_text.text("Step 1/3: Searching for jobs...")
                total_jobs = steps[0]()
                progress_bar.progress(1/3)
                
                progress_text.text("Step 2/3: Processing job data...")
                steps[1]()
                progress_bar.progress(2/3)
                
                progress_text.text("Step 3/3: Saving to database...")
                steps[2]()
                progress_bar.progress(1.0)
                
                progress_text.empty()
                time.sleep(0.5)
                progress_container.empty()

                if total_jobs > 0:
                    st.success(f"✅ Search complete! Found {total_jobs} jobs matching your criteria. Updating results table...")
                else:
                     st.warning("No new jobs found matching your search criteria.")
                     st.markdown("""
                     <div style="background-color: #fff9e6; padding: 15px; border-radius: 8px; border-left: 5px solid #ffc107; margin: 10px 0;">
                         <h4 style="margin-top: 0;">Suggestions</h4>
                         <ul>
                             <li>Try more general job titles</li>
                             <li>Specify a major tech hub location</li>
                             <li>Broaden your search time frame</li>
                             <li>Check spelling</li>
                         </ul>
                     </div>
                     """, unsafe_allow_html=True)

                # --- Trigger results update AFTER pipeline finishes ---
                try:
                    conn = sqlite3.connect("all_jobs.db")
                    query = """
                        SELECT 
                            id, primary_key, date, 
                            CAST(resume_similarity AS REAL) AS resume_similarity,
                            title, company, company_url, company_type, job_type, 
                            job_is_remote, job_apply_link, job_offer_expiration_date, 
                            salary_low, salary_high, salary_currency, salary_period, 
                            job_benefits, city, state, country, apply_options, 
                            required_skills, required_experience, required_education, 
                            description, highlights
                        FROM jobs_new 
                        ORDER BY resume_similarity DESC, date DESC 
                    """
                    st.session_state["query_result"] = pd.read_sql(query, conn)
                    conn.close()
                    st.session_state["data_queried"] = True
                    st.session_state["last_opened_index"] = 0 # Reset index on new search
                    logger.info(f"Successfully queried and updated results for {len(st.session_state['query_result'])} jobs.")
                    # No need to display results here, they are displayed below based on session state
                except Exception as query_e:
                    st.error(f"An error occurred while querying the database after search: {query_e}")
                    logger.error(f"DB Query Error after search: {query_e}", exc_info=True)
                    st.session_state["data_queried"] = False # Mark as not queried if error
            
            except Exception as pipeline_error:
                 st.error(f"An error occurred during the job search pipeline: {pipeline_error}")
                 logger.error(f"Pipeline Error: {pipeline_error}", exc_info=True)
                 # Clear progress on error
                 progress_text.empty()
                 progress_container.empty()
                 st.session_state["data_queried"] = False # Ensure results aren't shown if pipeline fails

    # --- Results Display Section (Always attempts to display if data queried) ---
    st.markdown("--- Optional Separator ---") # Add a visual separator
    st.header("Search Results")
    
    if st.session_state["data_queried"] and not st.session_state["query_result"].empty:
        # Filter the dataframe - Use a single, consistent key prefix now
        filtered_df = filter_dataframe(st.session_state["query_result"], key_prefix="results_filter")
        
        # Store filtered results if needed elsewhere, though maybe not necessary now
        st.session_state["filtered_result"] = filtered_df 
        
        # Job count and action buttons
        col1_res, col2_res, col3_res = st.columns([2, 1, 1])
        
        with col1_res:
            st.write(f"Showing {len(filtered_df)} jobs")
            
        with col2_res:
            # Use simplified unique key
            if st.button("Open Top 5 Job URLs", type="primary", key="open_top_5"):
                open_next_job_urls(
                    filtered_df, # Use the filtered DF directly
                    0, # Always open the top 5 from the current view
                    5,
                )
                # Don't increment last_opened_index here, handle in next button
        
        with col3_res:
             # Use simplified unique key
            if st.button("Open Next 5 Job URLs", type="secondary", key="open_next_5"):
                open_next_job_urls(
                    filtered_df, # Use the filtered DF directly
                    st.session_state["last_opened_index"], # Use the state index
                    5,
                )
                st.session_state["last_opened_index"] += 5 # Increment state index
        
        # Display the dataframe
        st.dataframe(filtered_df, height=500)
        
    elif st.session_state["data_queried"] and st.session_state["query_result"].empty:
        # This case might occur if the search ran but found 0 jobs AND the DB was initially empty
        st.warning("No job results found in the database. Try a new search.") 
    else:
        # Initial state before any search is run
        st.info("Run a job search using the parameters above to see results here.")
        st.markdown("""
        <div style="background-color: #e7f5ff; padding: 20px; border-radius: 10px; margin-top: 20px;">
            <h4>How to use GPT Job Hunter</h4>
            <ol>
                <li>Ensure a resume is selected/uploaded in <b>Resume Management</b>.</li>
                <li>Enter job titles and criteria above, then click <b>Find Jobs</b>.</li>
                <li>Results will appear below after the search completes.</li>
                <li>Use filters and buttons to explore results.</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
