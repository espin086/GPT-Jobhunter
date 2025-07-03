"""
Streamlit frontend for GPT Job Hunter that communicates with the FastAPI backend.
"""

import streamlit as st
import requests
import pandas as pd
import time
import logging
import io
import json
from typing import List, Dict, Any, Optional
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI backend URL - can be configured via environment variable
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Set page config
st.set_page_config(
    page_title="GPT Job Hunter", 
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
.main-header {
    font-size: 2.5rem;
    color: #1e88e5;
    text-align: center;
    margin-bottom: 2rem;
}
.metric-container {
    background-color: #f0f2f6;
    padding: 1rem;
    border-radius: 0.5rem;
    margin: 0.5rem 0;
}
.success-message {
    background-color: #d4edda;
    border: 1px solid #c3e6cb;
    color: #155724;
    padding: 0.75rem;
    border-radius: 0.25rem;
    margin: 1rem 0;
}
.error-message {
    background-color: #f8d7da;
    border: 1px solid #f5c6cb;
    color: #721c24;
    padding: 0.75rem;
    border-radius: 0.25rem;
    margin: 1rem 0;
}
</style>
""", unsafe_allow_html=True)


def make_api_request(method: str, endpoint: str, timeout: int = 30, **kwargs) -> Dict[str, Any]:
    """Make a request to the FastAPI backend."""
    url = f"{BACKEND_URL}{endpoint}"
    try:
        response = requests.request(method, url, timeout=timeout, **kwargs)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        st.error(f"Cannot connect to backend at {BACKEND_URL}. Please ensure the FastAPI server is running.")
        return {"error": "Connection failed"}
    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {str(e)}")
        return {"error": str(e)}
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")
        return {"error": str(e)}


def check_backend_health() -> bool:
    """Check if the backend is healthy."""
    try:
        response = make_api_request("GET", "/health")
        return response.get("status") == "healthy"
    except:
        return False


def initialize_database():
    """Initialize the database."""
    try:
        response = make_api_request("POST", "/initialize")
        return response.get("success", False)
    except:
        return False


def get_database_stats() -> Dict[str, Any]:
    """Get database statistics."""
    try:
        return make_api_request("GET", "/stats")
    except:
        return {}


def upload_resume(filename: str, content: str) -> bool:
    """Upload a resume to the backend."""
    try:
        data = {"filename": filename, "content": content}
        response = make_api_request("POST", "/resumes/upload", json=data)
        return response.get("success", False)
    except:
        return False


def upload_resume_file(file) -> bool:
    """Upload a resume file (PDF or TXT) to the backend."""
    try:
        files = {"file": (file.name, file.getvalue(), file.type)}
        response = make_api_request("POST", "/resumes/upload-file", files=files)
        return response.get("success", False)
    except:
        return False


def get_resumes() -> List[str]:
    """Get list of resumes from backend."""
    try:
        response = make_api_request("GET", "/resumes")
        return response.get("resumes", [])
    except:
        return []


def search_jobs(job_titles: List[str], country: str = "us", date_posted: str = "all", location: str = "") -> Dict[str, Any]:
    """Search for jobs via backend."""
    try:
        data = {
            "job_titles": job_titles,
            "country": country,
            "date_posted": date_posted,
            "location": location
        }
        # Use longer timeout for job searches (3 minutes) since they involve external API calls
        return make_api_request("POST", "/jobs/search", timeout=180, json=data)
    except:
        return {"error": "Search failed"}


def get_jobs(filters: Dict[str, Any] = None) -> Dict[str, Any]:
    """Get jobs from backend with optional filters."""
    try:
        params = filters or {}
        return make_api_request("GET", "/jobs", params=params)
    except:
        return {"jobs": [], "total_count": 0}


def update_similarity_scores(resume_name: str) -> Dict[str, Any]:
    """Update similarity scores for a resume."""
    try:
        data = {"resume_name": resume_name}
        # Use longer timeout for similarity updates since they involve AI processing
        return make_api_request("POST", "/similarity/update", timeout=120, json=data)
    except:
        return {"error": "Update failed"}


def main():
    """Main Streamlit application."""
    
    # Check backend health
    if not check_backend_health():
        st.error("🚨 Backend service is not available. Please start the FastAPI backend first.")
        st.info("Run: `python -m jobhunter.backend.api` or `uvicorn jobhunter.backend.api:app --host 0.0.0.0 --port 8000`")
        return
    
    # Main header
    st.markdown('<h1 class="main-header">🔍 GPT Job Hunter</h1>', unsafe_allow_html=True)
    st.markdown("### AI-powered job search with resume matching")
    
    # Initialize session state
    if "selected_resume" not in st.session_state:
        st.session_state.selected_resume = None
    if "last_search_results" not in st.session_state:
        st.session_state.last_search_results = None
    
    # Sidebar
    with st.sidebar:
        st.header("📋 Control Panel")
        
        # Database stats
        with st.expander("📊 Database Statistics", expanded=True):
            stats = get_database_stats()
            if stats and "error" not in stats:
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Jobs", stats.get("total_jobs", 0))
                    st.metric("Jobs w/ Embeddings", stats.get("jobs_with_embeddings", 0))
                with col2:
                    st.metric("Resumes", stats.get("total_resumes", 0))
                    st.metric("Jobs w/ Similarity", stats.get("jobs_with_similarity_scores", 0))
            else:
                st.error("Failed to load database statistics")
        
        # Resume Management
        st.header("📄 Resume Management")
        
        # Upload resume
        with st.expander("Upload Resume", expanded=False):
            uploaded_file = st.file_uploader("Choose a file", type=['txt', 'pdf'])
            if uploaded_file is not None:
                if st.button("Upload Resume"):
                    with st.spinner("Uploading and processing..."):
                        try:
                            # Use the file upload endpoint for both PDF and TXT files
                            success = upload_resume_file(uploaded_file)
                            if success:
                                st.success(f"✅ Resume '{uploaded_file.name}' uploaded successfully!")
                                st.rerun()
                            else:
                                st.error("Failed to upload resume. Please check the file format and try again.")
                        except Exception as e:
                            st.error(f"Error uploading file: {e}")
                
                # Show file info
                st.info(f"📄 **File:** {uploaded_file.name}")
                st.info(f"📏 **Size:** {uploaded_file.size:,} bytes")
                st.info(f"🔧 **Type:** {uploaded_file.type}")
                
                if uploaded_file.type == "application/pdf":
                    st.info("💡 **PDF files will be processed to extract text content**")
                elif uploaded_file.type == "text/plain":
                    st.info("💡 **Text file will be uploaded directly**")
        
        # Select resume
        resumes = get_resumes()
        if resumes:
            # Calculate the correct index safely
            current_index = 0
            if st.session_state.selected_resume and st.session_state.selected_resume in resumes:
                current_index = resumes.index(st.session_state.selected_resume) + 1
            
            selected_resume = st.selectbox(
                "Select Active Resume",
                ["None"] + resumes,
                index=current_index
            )
            
            if selected_resume != "None":
                st.session_state.selected_resume = selected_resume
            else:
                st.session_state.selected_resume = None
            
            # Update similarity scores
            if st.session_state.selected_resume:
                if st.button("🔄 Update Similarity Scores"):
                    with st.spinner("Updating similarity scores..."):
                        result = update_similarity_scores(st.session_state.selected_resume)
                        if result.get("success"):
                            st.success(f"✅ Updated {result.get('jobs_updated', 0)} jobs")
                        else:
                            st.error("Failed to update similarity scores")
        else:
            st.info("No resumes found. Upload one first.")
        
        # Job Search
        st.header("🔍 Job Search")
        with st.form("job_search_form"):
            job_titles_input = st.text_area(
                "Job Titles (one per line)",
                placeholder="Software Engineer\nData Scientist\nProduct Manager",
                height=100
            )
            col1, col2 = st.columns(2)
            with col1:
                country = st.selectbox("Country", ["us", "uk", "ca", "au", "de"], index=0)
                date_posted = st.selectbox("Date Posted", ["all", "today", "week", "month"], index=0)
            with col2:
                location = st.text_input("Location", placeholder="San Francisco, CA")
            
            search_submitted = st.form_submit_button("🚀 Search Jobs")
            
            if search_submitted and job_titles_input.strip():
                job_titles = [title.strip() for title in job_titles_input.strip().split('\n') if title.strip()]
                
                with st.spinner("Searching for jobs..."):
                    result = search_jobs(job_titles, country, date_posted, location)
                    
                    if "error" not in result:
                        st.session_state.last_search_results = result
                        if result.get("success"):
                            st.success(f"✅ Found {result.get('total_jobs_found', 0)} jobs!")
                        else:
                            st.warning("Search completed but no jobs found")
                    else:
                        st.error(f"Search failed: {result['error']}")
    
    # Main content area
    st.header("📊 Job Results")
    
    # Job filters
    with st.expander("🔍 Filter Jobs", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            min_similarity = st.slider("Min Similarity", 0.0, 1.0, 0.0, 0.01)
            company_filter = st.text_input("Company", placeholder="Google, Apple...")
        with col2:
            title_filter = st.text_input("Job Title", placeholder="Engineer, Manager...")
            location_filter = st.text_input("Location", placeholder="New York, Remote...")
        with col3:
            job_type_filter = st.selectbox("Job Type", ["All", "Full-time", "Part-time", "Contract", "Temporary"], index=0)
            remote_filter = st.selectbox("Remote", ["All", "Remote", "On-site"], index=0)
        with col4:
            min_salary = st.number_input("Min Salary", min_value=0, value=0, step=1000)
            max_salary = st.number_input("Max Salary", min_value=0, value=0, step=1000)
    
    # Apply filters and get jobs
    filters = {}
    if st.session_state.selected_resume:
        filters["resume_name"] = st.session_state.selected_resume
    if min_similarity > 0:
        filters["min_similarity"] = min_similarity
    if company_filter:
        filters["company"] = company_filter
    if title_filter:
        filters["title"] = title_filter
    if location_filter:
        filters["location"] = location_filter
    if job_type_filter != "All":
        filters["job_type"] = job_type_filter
    if remote_filter == "Remote":
        filters["is_remote"] = True
    elif remote_filter == "On-site":
        filters["is_remote"] = False
    if min_salary > 0:
        filters["min_salary"] = min_salary
    if max_salary > 0:
        filters["max_salary"] = max_salary
    
    # Get and display jobs
    jobs_data = get_jobs(filters)
    jobs = jobs_data.get("jobs", [])
    total_count = jobs_data.get("total_count", 0)
    
    if jobs:
        st.info(f"Showing {len(jobs)} of {total_count} jobs matching your criteria")
        
        # Convert to DataFrame for display
        df_data = []
        for job in jobs:
            df_data.append({
                "Similarity": round(job.get("resume_similarity", 0), 3),
                "Title": job.get("title", ""),
                "Company": job.get("company", ""),
                "Location": f"{job.get('city', '')}, {job.get('state', '')}".strip(", "),
                "Type": job.get("job_type", ""),
                "Remote": job.get("job_is_remote", ""),
                "Salary Low": job.get("salary_low", ""),
                "Salary High": job.get("salary_high", ""),
                "Apply Link": job.get("job_apply_link", ""),
                "Date": job.get("date", "")
            })
        
        df = pd.DataFrame(df_data)
        
        # Display the dataframe
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Apply Link": st.column_config.LinkColumn("Apply Link"),
                "Similarity": st.column_config.NumberColumn("Similarity", format="%.3f")
            }
        )
        
        # Bulk actions
        st.subheader("🔗 Bulk Actions")
        col1, col2 = st.columns([1, 3])
        with col1:
            num_links = st.number_input("Number of links to open", min_value=1, max_value=len(jobs), value=min(5, len(jobs)))
        with col2:
            if st.button(f"🔗 Open Top {num_links} Job Links"):
                links_opened = 0
                for i, job in enumerate(jobs[:num_links]):
                    link = job.get("job_apply_link")
                    if link and link.startswith("http"):
                        st.markdown(f"[Open Job {i+1}: {job.get('title', 'Unknown')}]({link})")
                        links_opened += 1
                st.success(f"Prepared {links_opened} job links for opening")
    
    else:
        st.info("No jobs found. Try adjusting your filters or running a new search.")
        
        # Show helpful suggestions
        if total_count == 0:
            st.markdown("""
            ### 💡 Suggestions:
            - Upload a resume to get similarity scores
            - Run a job search from the sidebar
            - Try broader search terms
            - Check different locations
            """)


if __name__ == "__main__":
    main()