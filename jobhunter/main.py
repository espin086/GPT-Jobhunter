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
from jobhunter.config import PROCESSED_DATA_PATH, RAW_DATA_PATH, RESUME_PATH
from jobhunter.dataTransformer import DataTransformer
from jobhunter.extract import extract
from jobhunter.FileHandler import FileHandler
from jobhunter.load import load
from pandas.api.types import (
    is_categorical_dtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_object_dtype,
)
from jobhunter.SQLiteHandler import (
    delete_resume_in_db,
    fetch_resumes_from_db,
    get_resume_text,
    save_text_to_db,
    update_resume_in_db,
    update_similarity_in_db,
)

# Add correct import for textAnalysis functions
from jobhunter.textAnalysis import get_openai_api_key, _is_placeholder_key

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set page config at the start
st.set_page_config(
    page_title="GPT Job Hunter", 
    page_icon="🔍",
    layout="wide",  # Use wide layout for better space utilization
    initial_sidebar_state="expanded"  # Start with sidebar expanded
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
    modify = st.checkbox("Add filters", value=True, key=f"{key_prefix}_add_filters")

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

# Handle file uploader reset by checking for a rerun trigger flag
if st.session_state.get("trigger_rerun_after_upload", False):
    # Clear the flag
    st.session_state["trigger_rerun_after_upload"] = False
    # Don't need to clear uploader here - just cleared the flag so next rerun will be clean

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

# --- UI Layout Starts Here ---

# Print session state for debugging (optional)
# logger.debug(f"Session State on Rerun: {st.session_state}")

# Main title in sidebar
st.sidebar.title("GPT Job Hunter")
st.sidebar.write("AI-powered job search assistant")

# --- Sidebar: Resume Management ---
st.sidebar.header("Resume Management")

# --- API Key Handling ---
api_key = get_openai_api_key() # Check once at the start of the section

api_key_container = st.sidebar.container() # Remove border parameter
with api_key_container:
    # Add CSS class for styling
    st.markdown('<div class="container-with-border">', unsafe_allow_html=True)
    if api_key:
        # Key is set, show confirmation, hide input
        masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
        st.success(f"✅ OpenAI API Key is configured (Using key: {masked_key})")
        # Optionally add a button to change/clear the key if needed
        if st.button("Change API Key", key="change_api_key"):
            st.session_state.openai_api_key = "" # Clear session state key
            st.experimental_rerun() # Use experimental_rerun instead of rerun
    else:
        # Key not set, show input section
        st.markdown("""
        <div style="background-color: #2e2e2e; border-left: 5px solid #0078ff; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
            <h3 style="margin-top: 0;">⚠️ OpenAI API Key Required</h3>
            <p>An OpenAI API key is <strong>required</strong> for analyzing resumes and calculating job matches.</p>
            <p>You can get an API key from <a href="https://platform.openai.com/account/api-keys" target="_blank">OpenAI's website</a>.</p>
        </div>
        """, unsafe_allow_html=True)
        entered_key = st.text_input(
            "Enter OpenAI API Key",
            type="password",
            placeholder="sk-...",
            help="Your key is stored only locally in your browser session.",
            key="api_key_input_field" # Unique key for the input
        )
        if entered_key:
            if _is_placeholder_key(entered_key) or not entered_key.startswith("sk-") or len(entered_key) < 30:
                st.error("❌ Invalid API key format. Must start with 'sk-' and be longer.")
            else:
                st.session_state.openai_api_key = entered_key
                os.environ["OPENAI_API_KEY"] = entered_key # Set for current run if needed by backend
                st.success("✅ API key accepted for this session!")
                time.sleep(1) # Brief pause before rerun
                st.experimental_rerun() # Use experimental_rerun instead of rerun
    st.markdown('</div>', unsafe_allow_html=True) # Close the CSS container

# --- Resume Selection and Upload ---
st.sidebar.markdown("<hr style='border-top: 1px solid #444;'>", unsafe_allow_html=True) # Separator

# Fetch available resumes
available_resumes = fetch_resumes_from_db()
available_resumes.sort(reverse=True) # Sort newest first

# Display active resume info
active_resume_placeholder = st.sidebar.empty()
if st.session_state.active_resume:
    active_resume_placeholder.markdown(f'<div class="active-resume-div">Active Resume: <strong>{st.session_state.active_resume}</strong></div>', unsafe_allow_html=True)
else:
    active_resume_placeholder.info("No active resume selected. Please upload or select one.")

# Resume Actions Container
resume_container = st.sidebar.container() # Remove border parameter
with resume_container:
    st.markdown('<div class="container-with-border">', unsafe_allow_html=True)
    st.subheader("Manage Resumes")
    
    # --- Upload Section ---
    st.markdown("**Upload New Resume**")
    uploaded_file = st.file_uploader(
        "Upload PDF or TXT",
        type=["pdf", "txt"],
        key="resume_uploader",
        label_visibility="collapsed"
    )
    # Automatic processing logic
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
                    st.session_state.active_resume = uploaded_file.name # Set newly uploaded as active
                    st.session_state.last_uploaded_file_id = uploaded_file.id # Track processed file

                    st.success(f"✅ Resume '{uploaded_file.name}' uploaded!")

                    # Analyze the newly uploaded resume immediately
                    with st.spinner("Analyzing resume for job matching..."):
                        update_success = update_similarity_in_db(uploaded_file.name)
                        if update_success:
                            st.success("Resume analyzed and ready!")
                        else:
                            st.error("Failed to analyze resume.")

                    # Use a flag to indicate we need to rerun instead
                    st.session_state["trigger_rerun_after_upload"] = True
                    st.experimental_rerun()

                except Exception as e:
                    st.error(f"Error processing file '{uploaded_file.name}': {e}")
                    logger.error(f"File processing error: {e}", exc_info=True)
                    st.session_state.last_uploaded_file_id = None

    # --- Selection / Deletion Section ---
    st.markdown("**Select or Delete Existing Resume**")
    if not available_resumes:
        st.info("No existing resumes found. Upload one first.")
    else:
        # Find index of current active resume for dropdown default
        try:
            current_index = available_resumes.index(st.session_state.active_resume) if st.session_state.active_resume in available_resumes else 0
        except ValueError:
            current_index = 0 # Default to first if active_resume is somehow invalid

        selected_resume = st.selectbox(
            "Select Active Resume",
            options=available_resumes,
            index=current_index,
            key="resume_select_dropdown", # Use a distinct key
            label_visibility="collapsed"
        )

        # Update active resume if selection changed
        if selected_resume != st.session_state.active_resume:
            st.session_state.active_resume = selected_resume
            # Update the displayed active resume immediately
            active_resume_placeholder.markdown(f'<div class="active-resume-div">Active Resume: <strong>{st.session_state.active_resume}</strong></div>', unsafe_allow_html=True)
            # Trigger analysis
            with st.spinner(f"Analyzing selected resume '{selected_resume}'..."):
                update_similarity_in_db(selected_resume)
                st.success(f"Resume '{selected_resume}' is now active and analyzed.")
            st.experimental_rerun() # Use experimental_rerun instead of rerun

        # Delete button (only enabled if a resume is selected/available)
        delete_disabled = not bool(selected_resume)
        if st.button("Delete Selected Resume", key="delete_selected", disabled=delete_disabled):
            if selected_resume:
                st.session_state.confirming_delete = selected_resume
                st.experimental_rerun() # Use experimental_rerun instead of rerun
    st.markdown('</div>', unsafe_allow_html=True) # Close the CSS container

# --- Deletion Confirmation Logic ---
# Moved outside the container, appears only when needed
if st.session_state.get("confirming_delete"):
    resume_to_delete = st.session_state.confirming_delete
    st.sidebar.warning(f"⚠️ Are you sure you want to delete '{resume_to_delete}'? This cannot be undone.")
    del_col1, del_col2 = st.sidebar.columns(2)
    if del_col1.button("Yes, Delete Permanently", key="confirm_delete_yes", type="primary"):
        with st.spinner(f"Deleting '{resume_to_delete}'..."):
            delete_resume_in_db(resume_to_delete)
            # Clear active resume if it was deleted
            if st.session_state.active_resume == resume_to_delete:
                st.session_state.active_resume = None
            # Clear confirmation state
            st.session_state.confirming_delete = None
            st.sidebar.success(f"🗑️ Resume '{resume_to_delete}' deleted.")
            time.sleep(1)
            st.experimental_rerun()
    if del_col2.button("Cancel", key="confirm_delete_cancel"):
        st.session_state.confirming_delete = None
        st.experimental_rerun()

# --- Sidebar: Job Search Parameters ---
st.sidebar.header("Job Search")

# Check for active resume before allowing search
if not st.session_state.active_resume:
    st.sidebar.warning("Please select or upload a resume above first.")
else:
    # Search Parameter Input
    search_container = st.sidebar.container() # Remove border parameter
    with search_container:
        st.markdown('<div class="container-with-border">', unsafe_allow_html=True)
        st.subheader("Search Parameters")
        
        job_titles_input = st.text_input(
            "Job Titles",
            placeholder="Enter job titles separated by commas",
            help="e.g., Data Scientist, ML Engineer",
            key="job_titles_input"
        )
        
        country = st.selectbox(
            "Country", options=["us", "uk", "ca", "au", "de", "fr", "es", "it"], index=0, key="country_select"
        )
        
        date_posted = st.selectbox(
            "Time Frame", options=["all", "today", "3days", "week", "month"], index=0, key="date_posted_select"
        )
        
        location = st.text_input(
            "Location", placeholder="City, state, or region (e.g., Chicago, Remote)", key="location_input"
        )

        job_titles = [title.strip() for title in job_titles_input.split(",")] if job_titles_input else []
        if job_titles and job_titles[0]:
            st.markdown("##### Selected Positions:")
            # Use st.container with horizontal scroll if many titles
            with st.container():
                # Display pills horizontally
                pill_html = "".join([f'<span class="job-pill">{title}</span>' for title in job_titles])
                st.markdown(f'<div style="line-height: 2.0;">{pill_html}</div>', unsafe_allow_html=True)

        # Search Button
        search_disabled = not (job_titles and job_titles[0])
        search_button = st.button(
            "🔍 Find Jobs", type="primary", disabled=search_disabled, key="find_jobs_button",
            use_container_width=True  # Make button full width in this column
        )
        if search_disabled:
            st.caption("ℹ️ Please enter at least one job title to search.")
        st.markdown('</div>', unsafe_allow_html=True) # Close the CSS container

    # --- Job Search Execution Section ---
    if search_button:
        # Replace sidebar spinner with a proper placeholder approach
        progress_message = st.sidebar.empty()
        progress_message.info("Searching for jobs...")
        
        if st.session_state.openai_api_key:
            os.environ["OPENAI_API_KEY"] = st.session_state.openai_api_key
            logging.info("Set OpenAI API key from session state for job search")

        steps = [
            lambda: extract(job_titles, country=country, date_posted=date_posted, location=location),
            run_transform,
            load,
        ]

        progress_container = st.sidebar.container()
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
            # Clear the initial progress message
            progress_message.empty()

            if total_jobs > 0:
                st.sidebar.success(f"✅ Search complete! Found {total_jobs} jobs. Refreshing results...")
            else:
                st.sidebar.warning("No new jobs found matching your search criteria.")
                st.sidebar.markdown("""
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
                st.sidebar.error(f"An error occurred while querying the database after search: {query_e}")
                logger.error(f"DB Query Error after search: {query_e}", exc_info=True)
                st.session_state["data_queried"] = False

        except Exception as pipeline_error:
            st.sidebar.error(f"An error occurred during the job search pipeline: {pipeline_error}")
            logger.error(f"Pipeline Error: {pipeline_error}", exc_info=True)
            progress_text.empty()
            progress_container.empty()
            st.session_state["data_queried"] = False

# --- Main Content Area: Job Search Results ---
st.title("Job Search Results")

# Check if data is ready to be displayed
if st.session_state["data_queried"] and not st.session_state["query_result"].empty:
    # Use the filter_dataframe function defined earlier
    temp_filtered_df = filter_dataframe(st.session_state["query_result"], key_prefix="results_filter")
    filtered_df = temp_filtered_df if temp_filtered_df is not None and not temp_filtered_df.empty else pd.DataFrame()

    # Store the filtered results in session state
    st.session_state["filtered_result"] = filtered_df

    # Display results only if the filtered DataFrame is not empty
    if not filtered_df.empty:
        # Show job count
        st.write(f"Showing {len(filtered_df)} jobs matching your criteria")
        
        # Format the date column to remove timestamps
        if 'date' in filtered_df.columns:
            filtered_df['date'] = pd.to_datetime(filtered_df['date']).dt.date
        
        # Select only the requested columns in the specified order
        display_columns = [
            'resume_similarity',  # 1
            'title',              # 2
            'highlights',         # 3 - Moved highlights to be next to title
            'salary_low',         # 4
            'salary_high',        # 5
            'date',               # 6
            'company',            # 7
            'job_apply_link',     # 8
            'job_is_remote',      # 9
            'description'         # 10
        ]
        
        # Filter to only include columns that exist in the dataframe
        display_columns = [col for col in display_columns if col in filtered_df.columns]
        
        # Create a display dataframe with only the selected columns
        display_df = filtered_df[display_columns]
        
        # Display the dataframe without the index
        st.dataframe(display_df, height=700, use_container_width=True, hide_index=True)
    else:
        # Message if filters result in empty view, but data exists
        st.warning("No jobs match the current filter criteria. Adjust filters above.")

elif st.session_state["data_queried"] and st.session_state["query_result"].empty:
    # If initial load or search yielded absolutely no results in the DB
    st.warning("No job results found in the database. Run a new search to populate it.")
else:
    # Initial state when DB is empty and no search run
    st.info("Database is currently empty. Upload a resume and run a job search from the sidebar.")
    st.markdown("""
    <div style="background-color: #2e2e2e; padding: 15px; border-radius: 10px; margin-top: 15px; max-width: 800px;">
        <h3>How to use GPT Job Hunter</h3>
        <ol>
            <li>Configure your OpenAI API Key in the sidebar</li>
            <li>Upload or select a resume in the Resume Management section</li>
            <li>Enter job titles and search criteria in the Job Search section</li>
            <li>Click 'Find Jobs' to start searching</li>
            <li>Results will appear here after the search completes</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)

# --- Apply custom CSS (Moved to end to ensure styles apply correctly) ---
st.markdown("""
<style>
    /* Apply Monospace font for VS Code feel */
    body, .stTextInput > div > div > input, .stTextArea > div > textarea, .stSelectbox > div > div {
        font-family: 'Consolas', 'Monaco', 'Courier New', monospace !important;
    }

    /* Adjust main container padding */
    .main .block-container {
        padding-top: 1rem; /* Reduce top padding */
        padding-bottom: 1rem;
        padding-left: 1rem; /* Reduce horizontal padding */
        padding-right: 1rem;
    }
    
    /* Make the sidebar a bit wider for better form display */
    [data-testid="stSidebar"] {
        min-width: 330px !important;
        max-width: 450px !important;
    }

    /* Reduce spacing in sidebar */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
        gap: 0.5rem;
    }

    /* Make headers smaller, especially in sidebar */
    [data-testid="stSidebar"] h1 {
        font-size: 1.5rem !important;
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
    
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        font-size: 1.2rem !important;
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }

    /* Tighten up container padding for more content space */
    .stContainer {
        padding: 10px !important; /* Reduce container padding */
    }

    /* Remove default Streamlit dividers/borders */
    .stHorizontalBlock, div[data-testid="stVerticalBlock"] > div:not([data-testid="stExpander"]), .stDivider {
        border: none !important;
        box-shadow: none !important;
    }
    .stDivider { display: none !important; }

    /* Styling for job pills - more compact */
    .job-pill {
        background-color: #3a3a3a;
        padding: 3px 8px; /* Smaller padding */
        border-radius: 12px;
        margin: 2px; /* Smaller margin */
        display: inline-block;
        border: 1px solid #555;
        font-size: 0.8em; /* Smaller font */
        line-height: 1.2;
    }

    /* Styling for the active resume - more compact */
    .active-resume-div {
        background-color: rgba(70, 90, 120, 0.3);
        border-left: 3px solid #4a90e2;
        padding: 8px 12px; /* Smaller padding */
        border-radius: 4px;
        margin: 8px 0; /* Smaller margin */
        font-size: 0.9em; /* Slightly smaller text */
    }

    /* Ensure consistent font in text area */
    .stTextArea textarea {
        font-family: 'Consolas', 'Monaco', 'Courier New', monospace !important;
    }

    /* Make buttons use less space */
    .stButton button {
        padding: 0.25rem 0.5rem; /* Smaller button padding */
        font-size: 0.9em; /* Smaller button text */
    }

    /* Make container borders subtle - add custom class for containers */
    .container-with-border {
        border: 1px solid #444 !important;
        border-radius: 6px !important;
        padding: 10px;
        margin-bottom: 10px;
    }

    /* Adjust DataFrame display - make font slightly larger in main display */
    .stDataFrame {
        font-size: 1.0em; /* Normal font size for better readability in main content */
    }
</style>
""", unsafe_allow_html=True)
