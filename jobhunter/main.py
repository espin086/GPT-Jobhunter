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
import pdfplumber
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
    st.session_state["data_queried"] = False # Will be set to True if initial load finds data

if "query_result" not in st.session_state:
    st.session_state["query_result"] = pd.DataFrame()

if "filtered_result" not in st.session_state:
    st.session_state["filtered_result"] = pd.DataFrame()

if "last_opened_index" not in st.session_state:
    st.session_state["last_opened_index"] = 0

# --- Function to Load Initial Data --- 
def load_initial_data():
    """Queries the database on app start to load existing jobs and set default resume."""
    if not st.session_state.get("initial_data_loaded", False): # Run only once per session
        logger.info("Attempting initial data load...")
        conn = None
        try:
            conn = sqlite3.connect("all_jobs.db")
            cursor = conn.cursor()

            # --- Load Existing Jobs --- 
            # Check if jobs_new table has data first
            count_query = "SELECT COUNT(*) FROM jobs_new"
            count_result = pd.read_sql(count_query, conn).iloc[0, 0]
            
            if count_result > 0:
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
                st.session_state["data_queried"] = True 
                st.session_state["last_opened_index"] = 0 
                logger.info(f"Successfully loaded {len(st.session_state['query_result'])} existing jobs on startup.")
            else:
                st.session_state["query_result"] = pd.DataFrame() 
                st.session_state["data_queried"] = False 
                logger.info("Jobs table is empty. No initial jobs loaded.")

            # --- Set Default Resume --- 
            available_resumes = fetch_resumes_from_db() # Assumes fetch_resumes_from_db uses the same connection if needed or opens its own
            if available_resumes:
                # Sort resumes reverse alphabetically (assuming later names are newer)
                available_resumes.sort(reverse=True)
                latest_resume = available_resumes[0]
                st.session_state.active_resume = latest_resume
                logger.info(f"Set default active resume to: {latest_resume}")
                # Trigger similarity calculation for the default resume
                with st.spinner(f"Analyzing default resume '{latest_resume}' for job matching..."): # Add spinner here
                    update_success = update_similarity_in_db(latest_resume)
                    if update_success:
                        logger.info(f"Successfully updated similarities for default resume: {latest_resume}")
                    else:
                         logger.error(f"Failed to update similarities for default resume: {latest_resume}")
                         # Optionally show an error in the UI if needed
                         # st.error("Failed to analyze default resume. Job matching might be incomplete.")
            else:
                 logger.info("No resumes found in database to set as default.")
                 st.session_state.active_resume = None # Ensure it's None if DB is empty
            
        except Exception as query_e:
            st.error(f"An error occurred during initial data load: {query_e}")
            logger.error(f"DB Query/Resume Error during initial load: {query_e}", exc_info=True)
            st.session_state["query_result"] = pd.DataFrame()
            st.session_state["data_queried"] = False
            st.session_state.active_resume = None
        finally:
            if conn:
                conn.close()
        st.session_state["initial_data_loaded"] = True # Mark initial load as attempted

# --- Load initial data --- 
load_initial_data()

# Apply custom CSS 
st.markdown("""
<style>
    /* Apply Monospace font for VS Code feel */
    body {
        font-family: 'Consolas', 'Monaco', 'Courier New', monospace !important;
    }

    /* Adjust main container padding */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }

    /* Remove default Streamlit dividers/borders */
    .stHorizontalBlock, div[data-testid="stVerticalBlock"] > div, .stDivider {
        border: none !important;
        box-shadow: none !important;
    }
    .stDivider { display: none !important; }
    hr { display: none !important; }
    
    /* Styling for containers - use theme background */
    .job-search-container, .resume-container {
        /* background-color: #2e2e2e; */ /* Let theme handle bg */
        padding: 20px;
        border-radius: 8px;
        margin-bottom: 20px;
        border: 1px solid #444; /* Add subtle border for dark theme */
    }

    /* Header styling */
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        margin-bottom: 15px;
        /* color: #d4d4d4; */ /* Let theme handle text color */
    }

    /* Custom styling for pills - subtle contrast */
    .job-pill {
        background-color: #3a3a3a; /* Darker pill bg */
        /* color: #d4d4d4; */ /* Let theme handle text color */
        padding: 8px;
        border-radius: 5px;
        margin: 2px;
        display: inline-block;
        border: none !important;
    }

    /* Styling for the active resume - subtle highlight */
    .active-resume-div {
        background-color: rgba(70, 90, 120, 0.3); /* Subtle blueish highlight */
        border-left: 4px solid #4a90e2; /* Blue accent */
        padding: 10px 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    
    /* Let Streamlit dark theme handle button colors primarily */
    /* Remove explicit light theme button colors */
    /* 
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
    */

</style>
""", unsafe_allow_html=True)

# Print session state for debugging
if st.session_state.active_resume:
    logging.info(f"Active resume in session state: {st.session_state.active_resume}")

# New integrated UI structure with no sidebar
st.title("GPT Job Hunter")
st.write("AI-powered job search assistant")

# --- Section 1: Resume Management --- 
st.header("Resume Management")

# OpenAI API Key Input Section - Make more prominent
api_key_container = st.container()
with api_key_container:
    st.markdown("""
    <div style="background-color: #2e2e2e; border-left: 5px solid #0078ff; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
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
        if openai_api_key.startswith("sk-") and len(openai_api_key) > 30:
            st.session_state.openai_api_key = openai_api_key
            os.environ["OPENAI_API_KEY"] = openai_api_key
            st.success("✅ API key set successfully!")
        else:
            st.error("❌ This doesn't look like a valid OpenAI API key. API keys should start with 'sk-' and be at least 30 characters long.")
    else:
        st.warning("⚠️ Please enter an OpenAI API key to enable resume analysis and job matching.")
    
    # Use a subtle divider for dark theme
    st.markdown("<hr style='border-top: 1px solid #444;'>", unsafe_allow_html=True)

# Check for available resumes
available_resumes = fetch_resumes_from_db()

# Display current active resume if any
if st.session_state.active_resume:
    # Use the new CSS class for active resume styling
    st.markdown(f'<div class="active-resume-div">Current active resume: <strong>{st.session_state.active_resume}</strong></div>', unsafe_allow_html=True)
else:
    st.info("No active resume selected. Please upload or select a resume below.")

# Resume actions 
st.markdown('<div class="resume-container">', unsafe_allow_html=True)
st.markdown('<div class="section-header">Resume Actions</div>', unsafe_allow_html=True)

upload_tab = st.expander("UPLOAD RESUME", expanded=not available_resumes) # Expand if no resumes exist

# Handle Upload Resume - Now Automatic
with upload_tab:
    st.write("Upload your existing resume (PDF or TXT). It will be processed automatically.")
    uploaded_file = st.file_uploader("Choose a file", type=["pdf", "txt"], key="resume_uploader") 
    
    # Automatically process if a file is uploaded
    if uploaded_file is not None:
        if uploaded_file.id != st.session_state.get("last_uploaded_file_id", None):
            with st.spinner(f"Processing '{uploaded_file.name}'..."):
                try:
                    text = " "
                    if uploaded_file.type == "application/pdf":
                        logging.info(f"Reading PDF file: {uploaded_file.name} using pdfplumber")
                        text = "" 
                        with pdfplumber.open(uploaded_file) as pdf:
                            for page in pdf.pages:
                                page_text = page.extract_text()
                                if page_text:
                                    text += page_text + "\n" 
                        logging.info(f"Successfully extracted text from PDF: {uploaded_file.name}")
                    else:  
                        logging.info(f"Reading TXT file: {uploaded_file.name}")
                        text = uploaded_file.read().decode("utf-8")
                        logging.info(f"Successfully read text from TXT: {uploaded_file.name}")
                    
                    save_text_to_db(uploaded_file.name, text)
                    st.session_state.active_resume = uploaded_file.name
                    st.success(f"✅ Resume '{uploaded_file.name}' uploaded and set as active!")
                    
                    with st.spinner("Analyzing resume for job matching..."):
                        update_success = update_similarity_in_db(uploaded_file.name)
                        if update_success:
                            st.success("Resume analyzed and ready for job matching!")
                        else:
                            st.error("Failed to analyze resume. Job matching might be incomplete.")
                    
                    st.session_state.last_uploaded_file_id = uploaded_file.id
                    st.experimental_rerun()
                        
                except Exception as e:
                    st.error(f"An error occurred processing the file '{uploaded_file.name}': {e}")
                    logger.error(f"File processing error: {e}", exc_info=True)
                    st.session_state.last_uploaded_file_id = None 

st.markdown('</div>', unsafe_allow_html=True)  

# "Your Resumes" section 
if available_resumes:
    st.markdown('<div class="resume-container">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">Your Resumes</div>', unsafe_allow_html=True)
    
    for idx, resume in enumerate(available_resumes):
        col1, col2, col3 = st.columns([3, 1, 1])
        is_active = resume == st.session_state.active_resume
        active_class = "active-resume-div" if is_active else ""
        with col1:
            st.markdown(f'''
            <div class="{active_class}" style="padding: 10px; border-radius: 5px;">
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
    st.markdown('</div>', unsafe_allow_html=True)  
    
    # Resume Editor (if view/edit clicked)
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
        if edit_col2.button("Cancel Edit", key="cancel_edit"):
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
            if confirm_col2.button("Cancel Delete", key="cancel_delete_confirm"):
                del st.session_state.confirming_delete
                st.experimental_rerun()
        st.markdown('</div>', unsafe_allow_html=True)  
else:
    # This message appears only if no resumes exist at all
    st.info("No resumes found. Please upload one using the section above.")


# --- Separator --- 
st.markdown("<hr style='border-top: 2px solid #555; margin-top: 30px; margin-bottom: 30px;'>", unsafe_allow_html=True)


# --- Section 2: Job Search & Results --- 
st.header("Job Search & Results")

# Check for active resume before allowing search
if not st.session_state.active_resume:
    st.warning("Please select or upload a resume in the Resume Management section above before searching.")
    st.stop() 
else:
    # Use the new CSS class for active resume display (already shown above, maybe remove here?)
    # st.markdown(f'<div class="active-resume-div">Using active resume: <strong>{st.session_state.active_resume}</strong></div>', unsafe_allow_html=True)
    pass # Resume is active, proceed

# Search Parameter Input
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
    
    st.markdown('</div>', unsafe_allow_html=True)  

# Search Button
search_disabled = not (job_titles and job_titles[0])
search_button = st.button(
    "🔍 Find Jobs", type="primary", disabled=search_disabled, use_container_width=True, key="find_jobs_button"
)
if search_disabled:
    st.info("Please enter at least one job title to search.")

# --- Job Search Execution Section --- 
if search_button:
    with st.spinner("Searching for jobs..."):
        if st.session_state.openai_api_key:
            os.environ["OPENAI_API_KEY"] = st.session_state.openai_api_key
            logging.info("Set OpenAI API key from session state for job search")
        
        steps = [
            lambda: extract(job_titles, country=country, date_posted=date_posted, location=location),
            run_transform,
            load, 
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
                 <div style="background-color: #3a3a3a; padding: 15px; border-radius: 8px; border-left: 5px solid #ffc107; margin: 10px 0;">
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
                st.session_state["last_opened_index"] = 0 
                logger.info(f"Successfully queried and updated results for {len(st.session_state['query_result'])} jobs.")
                # Force rerun to display results immediately after search
                st.experimental_rerun()
            except Exception as query_e:
                st.error(f"An error occurred while querying the database after search: {query_e}")
                logger.error(f"DB Query Error after search: {query_e}", exc_info=True)
                st.session_state["data_queried"] = False 
        
        except Exception as pipeline_error:
             st.error(f"An error occurred during the job search pipeline: {pipeline_error}")
             logger.error(f"Pipeline Error: {pipeline_error}", exc_info=True)
             progress_text.empty()
             progress_container.empty()
             st.session_state["data_queried"] = False 

# --- Results Display Section --- 
st.markdown("<hr style='border-top: 1px solid #444;'>", unsafe_allow_html=True)
st.header("Job Results")

if st.session_state["data_queried"] and not st.session_state["query_result"].empty:
    filtered_df = filter_dataframe(st.session_state["query_result"], key_prefix="results_filter")
    
    st.session_state["filtered_result"] = filtered_df 
    
    col1_res, col2_res, col3_res = st.columns([2, 1, 1])
    
    with col1_res:
        st.write(f"Showing {len(filtered_df)} jobs")
        
    with col2_res:
        if st.button("Open Top 5 Job URLs", type="primary", key="open_top_5"):
            open_next_job_urls(
                filtered_df, 
                0, 
                5,
            )
    
    with col3_res:
        if st.button("Open Next 5 Job URLs", type="secondary", key="open_next_5"):
            open_next_job_urls(
                filtered_df, 
                st.session_state["last_opened_index"], 
                5,
            )
            st.session_state["last_opened_index"] += 5 
    
    st.dataframe(filtered_df, height=500)
    
elif st.session_state["data_queried"] and st.session_state["query_result"].empty:
    st.warning("No job results found in the database. Run a new search to populate it.") 
else:
    st.info("Database is currently empty. Run a job search using the parameters above to populate results.")
    st.markdown("""
    <div style="background-color: #2e2e2e; padding: 20px; border-radius: 10px; margin-top: 20px;">
        <h4>How to use GPT Job Hunter</h4>
        <ol>
            <li>Ensure a resume is selected/uploaded in <b>Resume Management</b>.</li>
            <li>Enter job titles and criteria above, then click <b>Find Jobs</b>.</li>
            <li>Results will appear below after the search completes.</li>
            <li>Use filters and buttons to explore results.</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)
