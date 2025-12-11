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

# Custom CSS for a cleaner, more modern look with job cards
st.markdown("""
<style>
.main-header {
    font-size: 3rem;
    font-weight: 700;
    background: linear-gradient(90deg, #1e88e5 0%, #7b1fa2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-align: center;
    margin-bottom: 0.5rem;
}
.subtitle {
    font-size: 1.2rem;
    color: #666;
    text-align: center;
    margin-bottom: 2rem;
}
/* Cleaner spacing */
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}
/* Make buttons more prominent */
.stButton>button {
    width: 100%;
    background: linear-gradient(90deg, #1e88e5 0%, #1976d2 100%);
    color: white;
    border: none;
    padding: 0.75rem 1.5rem;
    font-weight: 600;
    border-radius: 8px;
    transition: all 0.3s ease;
}
.stButton>button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(30, 136, 229, 0.4);
}
/* Cleaner dataframe styling */
.dataframe {
    font-size: 0.9rem;
}
/* Better expander styling */
.streamlit-expanderHeader {
    font-weight: 600;
    color: #1e88e5;
}

/* Job Card Styling */
.job-card {
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    transition: all 0.3s ease;
    position: relative;
}
.job-card:hover {
    box-shadow: 0 4px 16px rgba(0,0,0,0.12);
    transform: translateY(-2px);
    border-color: #1e88e5;
}
.match-score {
    display: inline-block;
    padding: 0.4rem 0.8rem;
    border-radius: 20px;
    font-weight: 700;
    font-size: 0.9rem;
    margin-bottom: 0.5rem;
}
.match-high {
    background: #d4edda;
    color: #155724;
}
.match-medium {
    background: #fff3cd;
    color: #856404;
}
.match-low {
    background: #f8f9fa;
    color: #6c757d;
}
.job-title {
    font-size: 1.4rem;
    font-weight: 700;
    color: #1e88e5;
    margin: 0.5rem 0;
    line-height: 1.3;
}
.job-company {
    font-size: 1.1rem;
    color: #333;
    font-weight: 600;
    margin-bottom: 0.5rem;
}
.job-meta {
    color: #666;
    font-size: 0.95rem;
    margin: 0.5rem 0;
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    align-items: center;
}
.job-badge {
    display: inline-block;
    padding: 0.25rem 0.6rem;
    border-radius: 12px;
    font-size: 0.85rem;
    font-weight: 600;
}
.badge-remote {
    background: #e3f2fd;
    color: #1976d2;
}
.badge-hybrid {
    background: #fff3e0;
    color: #f57c00;
}
.badge-onsite {
    background: #f5f5f5;
    color: #616161;
}
.badge-salary {
    background: #e8f5e9;
    color: #2e7d32;
    font-weight: 700;
}
.job-date {
    color: #999;
    font-size: 0.85rem;
}
.job-actions {
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid #e0e0e0;
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


def get_job_title_suggestions(resume_name: str) -> Dict[str, Any]:
    """Get AI-generated job title suggestions based on resume."""
    try:
        data = {"resume_name": resume_name}
        # Use longer timeout for AI processing
        return make_api_request("POST", "/resumes/suggest-job-titles", timeout=60, json=data)
    except:
        return {"error": "Suggestion failed"}


def format_relative_time(date_str: str) -> str:
    """Convert date string to relative time (e.g., '2d ago')."""
    if not date_str:
        return "Unknown"
    try:
        from datetime import datetime

        # Try different date formats
        job_date = None

        # Try ISO format with timezone (e.g., 2025-12-08T00:00:00.000Z)
        try:
            if 'T' in date_str:
                # Remove timezone and milliseconds for easier parsing
                clean_date = date_str.split('T')[0]
                job_date = datetime.strptime(clean_date, "%Y-%m-%d")
        except:
            pass

        # Try simple date format (e.g., 2025-12-08)
        if not job_date:
            try:
                job_date = datetime.strptime(date_str.split()[0], "%Y-%m-%d")
            except:
                pass

        # If we couldn't parse it, return a safe default
        if not job_date:
            return "Recently"

        now = datetime.now()
        diff = now - job_date

        if diff.days == 0:
            return "Today"
        elif diff.days == 1:
            return "Yesterday"
        elif diff.days < 0:
            return "Recently"  # Future date, shouldn't happen but handle it
        elif diff.days < 7:
            return f"{diff.days}d ago"
        elif diff.days < 30:
            weeks = diff.days // 7
            return f"{weeks}w ago"
        elif diff.days < 365:
            months = diff.days // 30
            return f"{months}mo ago"
        else:
            years = diff.days // 365
            return f"{years}y ago"
    except Exception as e:
        # Fail gracefully - don't let date parsing break the whole card
        return "Recently"


def format_salary(salary_low: Optional[float], salary_high: Optional[float], currency: Optional[str] = "USD") -> str:
    """Format salary range for display."""
    if not salary_low and not salary_high:
        return None

    def format_amount(amount):
        if amount >= 1000:
            return f"${int(amount/1000)}K"
        return f"${int(amount)}"

    if salary_low and salary_high:
        return f"{format_amount(salary_low)}-{format_amount(salary_high)}"
    elif salary_low:
        return f"{format_amount(salary_low)}+"
    elif salary_high:
        return f"Up to {format_amount(salary_high)}"
    return None


def render_job_card(job: Dict[str, Any], index: int):
    """Render a single job as a card."""
    import html

    # Calculate match score styling
    similarity = job.get("resume_similarity", 0)
    if similarity >= 0.9:
        match_class = "match-high"
        match_emoji = "🟢"
    elif similarity >= 0.7:
        match_class = "match-medium"
        match_emoji = "🟡"
    else:
        match_class = "match-low"
        match_emoji = "⚪"

    # Format salary
    salary_str = format_salary(job.get("salary_low"), job.get("salary_high"))

    # Determine remote status
    is_remote = job.get("job_is_remote", "").lower()
    if "yes" in is_remote or "remote" in is_remote:
        remote_badge = '<span class="job-badge badge-remote">🏠 Remote</span>'
    elif "hybrid" in is_remote:
        remote_badge = '<span class="job-badge badge-hybrid">🔀 Hybrid</span>'
    else:
        remote_badge = '<span class="job-badge badge-onsite">🏢 On-site</span>'

    # Format location - escape HTML
    city = job.get("city", "")
    state = job.get("state", "")
    location = f"{city}, {state}".strip(", ") or "Location not specified"
    location = html.escape(location)

    # Format date
    date_posted = format_relative_time(job.get("date", ""))

    # Escape user content to prevent HTML injection
    job_title = html.escape(job.get("title", "Unknown Title"))
    company_name = html.escape(job.get("company", "Unknown Company"))
    salary_display = html.escape(salary_str) if salary_str else ""

    # Build salary badge HTML (always include, even if empty, to maintain structure)
    salary_badge_html = f'<span class="job-badge badge-salary">💰 {salary_display}</span>' if salary_str else '<span></span>'

    # Build card HTML - ensure it's always valid with no conditional structure
    card_html = f"""<div class="job-card">
    <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 0.5rem;">
        <span class="match-score {match_class}">{match_emoji} {int(similarity * 100)}% Match</span>
        {salary_badge_html}
    </div>
    <h3 class="job-title">{job_title}</h3>
    <div class="job-company">{company_name}</div>
    <div class="job-meta">
        <span>{location}</span>
        <span>•</span>
        {remote_badge}
        <span>•</span>
        <span class="job-date">Posted {date_posted}</span>
    </div>
</div>"""

    st.markdown(card_html, unsafe_allow_html=True)

    # Action buttons below the card
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        apply_link = job.get("job_apply_link", "")
        if apply_link:
            # Use markdown link styled as button for older Streamlit versions
            st.markdown(
                f'<a href="{apply_link}" target="_blank" style="display: inline-block; padding: 0.5rem 1rem; background: linear-gradient(90deg, #1e88e5 0%, #1976d2 100%); color: white; text-decoration: none; border-radius: 8px; font-weight: 600; text-align: center; width: 100%;">🚀 Apply Now</a>',
                unsafe_allow_html=True
            )
        else:
            st.markdown('<div style="padding: 0.5rem; text-align: center; color: #999;">No link</div>', unsafe_allow_html=True)
    with col2:
        if st.button("🔖 Save", key=f"save_{index}", use_container_width=True):
            st.toast("💾 Job saved!")
    with col3:
        if st.button("👁️ View", key=f"view_{index}", use_container_width=True):
            # Store the expanded state in session
            if f"expanded_{index}" not in st.session_state:
                st.session_state[f"expanded_{index}"] = False
            st.session_state[f"expanded_{index}"] = not st.session_state.get(f"expanded_{index}", False)
    with col4:
        if st.button("👎 Pass", key=f"pass_{index}", use_container_width=True):
            st.toast("❌ Marked as not interested")

    # Show details if expanded
    if st.session_state.get(f"expanded_{index}", False):
        with st.container():
            st.markdown("---")
            st.write("**📋 Full Job Details**")

            if job.get("description"):
                st.write("**Description:**")
                st.write(job.get("description"))

            col_a, col_b = st.columns(2)
            with col_a:
                if job.get("required_skills"):
                    st.write("**Required Skills:**")
                    st.write(job.get("required_skills"))
                if job.get("required_experience"):
                    st.write("**Experience:**")
                    st.write(job.get("required_experience"))
            with col_b:
                if job.get("required_education"):
                    st.write("**Education:**")
                    st.write(job.get("required_education"))
                if job.get("job_benefits"):
                    st.write("**Benefits:**")
                    st.write(job.get("job_benefits"))

            st.markdown("---")


def main():
    """Main Streamlit application."""
    
    # Check backend health
    if not check_backend_health():
        st.error("🚨 Backend service is not available. Please start the FastAPI backend first.")
        st.info("Run: `python -m jobhunter.backend.api` or `uvicorn jobhunter.backend.api:app --host 0.0.0.0 --port 8000`")
        return
    
    # Main header with improved styling
    st.markdown('<h1 class="main-header">🔍 GPT Job Hunter</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">AI-powered job search with intelligent resume matching</p>', unsafe_allow_html=True)
    
    # Initialize session state
    if "selected_resume" not in st.session_state:
        st.session_state.selected_resume = None
    if "last_search_results" not in st.session_state:
        st.session_state.last_search_results = None
    if "job_suggestions" not in st.session_state:
        st.session_state.job_suggestions = None
    
    # Sidebar
    with st.sidebar:
        st.header("📋 Quick Start")

        # Resume Management
        st.subheader("📄 Your Resume")
        
        # Get existing resumes and auto-select the latest one
        resumes = get_resumes()
        if resumes:
            # Auto-select the most recent resume (last in list)
            # But first, clear the session state if the selected resume no longer exists
            if st.session_state.selected_resume and st.session_state.selected_resume not in resumes:
                st.session_state.selected_resume = None
                st.session_state.job_suggestions = None  # Clear suggestions too

            if not st.session_state.selected_resume:
                st.session_state.selected_resume = resumes[-1]

            # Show current resume with a clean indicator
            st.success(f"✅ **Active:** {st.session_state.selected_resume}")

            # Upload new resume (collapsed by default)
            with st.expander("📤 Upload New Resume"):
                uploaded_file = st.file_uploader("Choose a file", type=['txt', 'pdf'], key="resume_uploader")

                # Auto-upload when file is selected
                if uploaded_file is not None:
                    # Use session state to track if this file has been processed
                    file_key = f"{uploaded_file.name}_{uploaded_file.size}"
                    if 'last_uploaded_file' not in st.session_state or st.session_state.last_uploaded_file != file_key:
                        with st.spinner("Uploading and processing resume..."):
                            try:
                                success = upload_resume_file(uploaded_file)
                                if success:
                                    st.session_state.last_uploaded_file = file_key
                                    st.session_state.selected_resume = uploaded_file.name
                                    st.success(f"✅ Uploaded and activated!")
                                    st.experimental_rerun()
                                else:
                                    st.error("Upload failed. Please try again.")
                            except Exception as e:
                                st.error(f"Error: {e}")
        else:
            # No resumes yet - clear session state and show uploader prominently
            if st.session_state.selected_resume:
                st.session_state.selected_resume = None
                st.session_state.job_suggestions = None

            st.info("👋 Start by uploading your resume")
            uploaded_file = st.file_uploader("Choose a file", type=['txt', 'pdf'], key="first_resume_uploader")

            # Auto-upload when file is selected
            if uploaded_file is not None:
                file_key = f"{uploaded_file.name}_{uploaded_file.size}"
                if 'last_uploaded_file' not in st.session_state or st.session_state.last_uploaded_file != file_key:
                    with st.spinner("Uploading and processing resume..."):
                        try:
                            success = upload_resume_file(uploaded_file)
                            if success:
                                st.session_state.last_uploaded_file = file_key
                                st.session_state.selected_resume = uploaded_file.name
                                st.success(f"✅ Resume uploaded!")
                                st.experimental_rerun()
                            else:
                                st.error("Upload failed. Please try again.")
                        except Exception as e:
                            st.error(f"Error: {e}")

        # AI-Powered Job Suggestions
        if st.session_state.selected_resume:
            st.divider()
            st.subheader("🎯 AI Suggestions")

            # Get or generate suggestions
            if st.session_state.job_suggestions is None:
                with st.spinner("🤖 Analyzing your resume..."):
                    result = get_job_title_suggestions(st.session_state.selected_resume)
                    if result.get("success"):
                        st.session_state.job_suggestions = result.get("suggestions", [])

            # Display suggestions
            if st.session_state.job_suggestions:
                st.write("**Recommended for you:**")
                # Display as clickable chips
                cols = st.columns(len(st.session_state.job_suggestions))
                for i, suggestion in enumerate(st.session_state.job_suggestions):
                    with cols[i]:
                        if st.button(f"💼 {suggestion}", key=f"suggestion_{i}", use_container_width=True):
                            # Pre-fill the job search form with this suggestion
                            st.session_state.pre_fill_job_title = suggestion

                # Smart Search button
                if st.button("🚀 Smart Search All 3", use_container_width=True, type="primary"):
                    with st.spinner("🔄 Searching for jobs and calculating matches..."):
                        result = search_jobs(st.session_state.job_suggestions, "us", "all", "")
                        if "error" not in result:
                            st.session_state.last_search_results = result
                            if result.get("success"):
                                st.success(f"✅ Found {result.get('total_jobs_found', 0)} jobs!")
                            else:
                                st.warning("⚠️ No jobs found. Try different titles or locations.")
                        else:
                            st.error(f"❌ Search failed: {result['error']}")

        # Job Search
        st.divider()
        st.subheader("🔍 Manual Search")

        with st.form("job_search_form"):
            # Pre-fill if suggestion was clicked
            default_value = ""
            if "pre_fill_job_title" in st.session_state:
                default_value = st.session_state.pre_fill_job_title
                del st.session_state.pre_fill_job_title

            job_titles_input = st.text_area(
                "Job Titles",
                value=default_value,
                placeholder="Software Engineer\nData Scientist\nProduct Manager",
                height=100,
                help="Enter one job title per line"
            )

            location = st.text_input("📍 Location (optional)", placeholder="San Francisco, CA")

            col1, col2 = st.columns(2)
            with col1:
                country = st.selectbox("Country", ["us", "uk", "ca", "au", "de"], index=0)
            with col2:
                date_posted = st.selectbox("Recency", ["all", "today", "week", "month"], index=0)

            search_submitted = st.form_submit_button("🚀 Search Jobs", use_container_width=True)

            if search_submitted and job_titles_input.strip():
                job_titles = [title.strip() for title in job_titles_input.strip().split('\n') if title.strip()]

                with st.spinner("🔄 Searching for jobs and calculating matches..."):
                    result = search_jobs(job_titles, country, date_posted, location)

                    if "error" not in result:
                        st.session_state.last_search_results = result
                        if result.get("success"):
                            st.success(f"✅ Found {result.get('total_jobs_found', 0)} jobs!")
                        else:
                            st.warning("⚠️ No jobs found. Try different titles or locations.")
                    else:
                        st.error(f"❌ Search failed: {result['error']}")
    
    # Main content area
    st.header("📊 Job Matches")

    # Essential filters only - clean and simple
    col1, col2, col3 = st.columns(3)
    with col1:
        min_similarity = st.slider("🎯 Min Match Score", 0.0, 1.0, 0.0, 0.05, help="Filter jobs by resume similarity")
    with col2:
        location_filter = st.text_input("📍 Location", placeholder="San Francisco, Remote...")
    with col3:
        remote_filter = st.selectbox("🏠 Work Style", ["All", "Remote Only", "Hybrid", "On-site"], index=0)

    # Advanced filters collapsed by default
    with st.expander("⚙️ Advanced Filters"):
        col1, col2 = st.columns(2)
        with col1:
            company_filter = st.text_input("Company", placeholder="Google, Apple...")
            title_filter = st.text_input("Job Title", placeholder="Engineer, Manager...")
            job_type_filter = st.selectbox("Job Type", ["All", "Full-time", "Part-time", "Contract", "Temporary"], index=0)
        with col2:
            min_salary = st.number_input("Min Salary ($)", min_value=0, value=0, step=10000)
            max_salary = st.number_input("Max Salary ($)", min_value=0, value=0, step=10000)
            st.info("💡 Leave salary at 0 to show all")
    
    # Apply filters and get jobs
    filters = {}
    if st.session_state.selected_resume:
        filters["resume_name"] = st.session_state.selected_resume
    if min_similarity > 0:
        filters["min_similarity"] = min_similarity
    if location_filter:
        filters["location"] = location_filter
    if remote_filter == "Remote Only":
        filters["is_remote"] = True
    elif remote_filter == "On-site":
        filters["is_remote"] = False
    # Note: "Hybrid" and "All" don't set is_remote filter

    # Advanced filters
    if company_filter:
        filters["company"] = company_filter
    if title_filter:
        filters["title"] = title_filter
    if job_type_filter != "All":
        filters["job_type"] = job_type_filter
    if min_salary > 0:
        filters["min_salary"] = min_salary
    if max_salary > 0:
        filters["max_salary"] = max_salary
    
    # Get and display jobs
    jobs_data = get_jobs(filters)
    jobs = jobs_data.get("jobs", [])
    total_count = jobs_data.get("total_count", 0)
    
    if jobs:
        # Header with view toggle
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info(f"📊 Showing {len(jobs)} of {total_count} jobs matching your criteria")
        with col2:
            view_mode = st.selectbox("View", ["🎴 Cards", "📊 Table"], label_visibility="collapsed")

        st.divider()

        # Display jobs based on view mode
        if view_mode == "🎴 Cards":
            # Card-based view (DEFAULT)
            for i, job in enumerate(jobs):
                render_job_card(job, i)

        else:
            # Table view (legacy)
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

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Apply Link": st.column_config.LinkColumn("Apply Link"),
                    "Similarity": st.column_config.NumberColumn("Similarity", format="%.3f")
                }
            )

            # Bulk actions (only in table view)
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
        # Show helpful onboarding message
        if total_count == 0:
            st.info("👋 Welcome! Get started in 2 easy steps:")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("""
                ### 1️⃣ Upload Resume
                - Go to the sidebar
                - Upload your PDF or TXT resume
                - It will be processed automatically
                """)
            with col2:
                st.markdown("""
                ### 2️⃣ Search Jobs
                - Enter job titles you're interested in
                - Click "Search Jobs"
                - We'll find matches and calculate similarity scores
                """)
        else:
            st.info(f"💡 {total_count} jobs in database, but none match your current filters. Try adjusting the filters above.")


if __name__ == "__main__":
    main()