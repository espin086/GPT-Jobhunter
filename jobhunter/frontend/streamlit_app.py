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
    """Make a request to the FastAPI backend with authentication."""
    url = f"{BACKEND_URL}{endpoint}"

    # Add JWT token to headers if user is logged in
    token = st.session_state.get("access_token")
    if token:
        # Ensure headers dict exists and add Authorization header
        headers = kwargs.get("headers", {})
        if headers is None:
            headers = {}
        headers["Authorization"] = f"Bearer {token}"
        kwargs["headers"] = headers
        logger.info(f"Making authenticated request to {endpoint} with token: {token[:10]}...{token[-10:]}")
    else:
        logger.warning(f"No access token found for request to {endpoint}")

    try:
        response = requests.request(method, url, timeout=timeout, **kwargs)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        # Handle 401 Unauthorized - token expired or invalid
        if e.response.status_code == 401:
            error_detail = e.response.json().get("detail", "Authentication failed") if e.response.text else "Authentication failed"
            logger.error(f"401 Unauthorized on {endpoint}: {error_detail}")
            st.error(f"Authentication failed: {error_detail}")

            # Clear session and force rerun (auto-logout on 401)
            if "access_token" in st.session_state:
                del st.session_state.access_token
            if "user_info" in st.session_state:
                del st.session_state.user_info
            st.rerun()
            return {"error": error_detail}

        st.error(f"API request failed: {e.response.status_code} - {e.response.text}")
        return {"error": str(e)}
    except requests.exceptions.ConnectionError:
        st.error(f"Cannot connect to backend at {BACKEND_URL}. Please ensure the FastAPI server is running.")
        return {"error": "Connection failed"}
    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {str(e)}")
        return {"error": str(e)}
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")
        logger.error(f"Unexpected error in API request: {e}", exc_info=True)
        return {"error": str(e)}


def check_backend_health() -> bool:
    """Check if the backend is healthy."""
    try:
        response = make_api_request("GET", "/health")
        return response.get("status") == "healthy"
    except:
        return False


# ============================================================================
# Authentication Functions
# ============================================================================

def login_user(username_or_email: str, password: str) -> bool:
    """Login user and store JWT token."""
    try:
        url = f"{BACKEND_URL}/auth/login"
        response = requests.post(
            url,
            json={"username_or_email": username_or_email, "password": password},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        # Store token and user info in session state
        st.session_state.access_token = data.get("access_token")

        # User info is nested in the 'user' object
        user_data = data.get("user", {})
        st.session_state.user_info = {
            "username": user_data.get("username"),
            "email": user_data.get("email"),
            "full_name": user_data.get("full_name")
        }
        return True
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            st.error("Invalid username/email or password")
        else:
            st.error(f"Login failed: {e.response.text}")
        return False
    except Exception as e:
        st.error(f"Login error: {str(e)}")
        return False


def register_user(email: str, username: str, password: str, full_name: str = "") -> bool:
    """Register a new user."""
    try:
        url = f"{BACKEND_URL}/auth/register"
        response = requests.post(
            url,
            json={
                "email": email,
                "username": username,
                "password": password,
                "full_name": full_name
            },
            timeout=10
        )
        response.raise_for_status()
        st.success("Registration successful! Please log in.")
        return True
    except requests.exceptions.HTTPError as e:
        try:
            error_detail = e.response.json().get("detail", str(e))
        except:
            error_detail = str(e)
        st.error(f"Registration failed: {error_detail}")
        return False
    except Exception as e:
        st.error(f"Registration error: {str(e)}")
        return False


def logout_user():
    """Logout user and clear session."""
    if "access_token" in st.session_state:
        del st.session_state.access_token
    if "user_info" in st.session_state:
        del st.session_state.user_info
    st.rerun()


def is_logged_in() -> bool:
    """Check if user is logged in."""
    return "access_token" in st.session_state and st.session_state.access_token is not None


def show_login_page():
    """Display login/register page."""
    st.markdown('<h1 class="main-header">🔍 GPT Job Hunter</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">AI-powered job search with intelligent resume matching</p>', unsafe_allow_html=True)

    st.markdown("---")

    # Check backend health first
    if not check_backend_health():
        st.error("🚨 Backend service is not available. Please start the FastAPI backend first.")
        st.info("Run: `make dev` or `python -m jobhunter.backend.api`")
        return

    # Create tabs for login and register
    tab1, tab2 = st.tabs(["🔑 Login", "📝 Register"])

    with tab1:
        st.subheader("Login to Your Account")

        with st.form("login_form"):
            username_or_email = st.text_input("Username or Email", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            submit = st.form_submit_button("Login", use_container_width=True)

            if submit:
                if not username_or_email or not password:
                    st.error("Please fill in all fields")
                else:
                    if login_user(username_or_email, password):
                        st.success("✅ Login successful!")
                        st.rerun()

    with tab2:
        st.subheader("Create New Account")
        st.markdown("*Get started in one step - create your account and upload your resume!*")

        # Account details section
        st.markdown("##### Account Details")
        reg_email = st.text_input("Email *", key="reg_email", placeholder="you@example.com")
        reg_username = st.text_input("Username *", key="reg_username", placeholder="johndoe")
        reg_full_name = st.text_input("Full Name", key="reg_full_name", placeholder="John Doe")

        col1, col2 = st.columns(2)
        with col1:
            reg_password = st.text_input("Password *", type="password", key="reg_password")
        with col2:
            reg_password_confirm = st.text_input("Confirm Password *", type="password", key="reg_password_confirm")

        st.markdown("---")

        # Resume upload section (REQUIRED)
        st.markdown("##### Upload Your Resume *")
        st.info("📄 Your resume is required to get personalized job matches. We'll analyze it to find jobs that match your skills!")

        resume_file = st.file_uploader(
            "Choose your resume (PDF or TXT)",
            type=['pdf', 'txt'],
            key="registration_resume",
            help="Upload your resume to get started with AI-powered job matching"
        )

        if resume_file:
            st.success(f"✅ Resume selected: **{resume_file.name}**")
        else:
            st.warning("⚠️ Please upload your resume to complete registration")

        st.markdown("---")

        # Register button
        if st.button("🚀 Create Account & Start Job Hunting!", type="primary", use_container_width=True):
            # Validation
            errors = []
            if not reg_email:
                errors.append("Email is required")
            if not reg_username:
                errors.append("Username is required")
            if not reg_password:
                errors.append("Password is required")
            elif len(reg_password) < 8:
                errors.append("Password must be at least 8 characters long")
            if reg_password != reg_password_confirm:
                errors.append("Passwords do not match")
            if not resume_file:
                errors.append("Please upload your resume")

            if errors:
                for error in errors:
                    st.error(f"❌ {error}")
            else:
                # Step 1: Register the user
                with st.spinner("Creating your account..."):
                    if register_user(reg_email, reg_username, reg_password, reg_full_name):
                        # Step 2: Auto-login
                        st.success("✅ Account created!")
                        with st.spinner("Logging you in..."):
                            if login_user(reg_username, reg_password):
                                # Step 3: Upload resume
                                st.success("✅ Logged in!")
                                with st.spinner("Uploading your resume..."):
                                    if upload_resume_file(resume_file):
                                        st.success("✅ Resume uploaded!")
                                        # Step 4: Set flags for onboarding
                                        st.session_state.selected_resume = resume_file.name
                                        st.session_state.show_onboarding = True
                                        st.session_state.onboarding_resume = resume_file.name
                                        st.balloons()
                                        st.success("🎉 All set! Starting your personalized job hunt setup...")
                                        time.sleep(2)
                                        st.rerun()
                                    else:
                                        st.error("Resume upload failed. You can upload it after logging in.")
                                        st.rerun()
                            else:
                                st.error("Auto-login failed. Please log in manually.")
                    else:
                        pass  # Error message already shown by register_user()


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
        if "error" in response:
            st.error(f"Upload failed: {response['error']}")
            return False
        return response.get("success", False)
    except Exception as e:
        st.error(f"Upload error: {str(e)}")
        logger.error(f"Resume upload error: {e}", exc_info=True)
        return False


def upload_resume_file(file) -> bool:
    """Upload a resume file (PDF or TXT) to the backend."""
    try:
        files = {"file": (file.name, file.getvalue(), file.type)}
        response = make_api_request("POST", "/resumes/upload-file", files=files)
        if "error" in response:
            st.error(f"File upload failed: {response['error']}")
            return False
        return response.get("success", False)
    except Exception as e:
        st.error(f"File upload error: {str(e)}")
        logger.error(f"Resume file upload error: {e}", exc_info=True)
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


def get_filtered_job_count(filters: Dict[str, Any] = None) -> int:
    """Get count of jobs matching filters (lightweight endpoint for UI preview)."""
    try:
        params = filters or {}
        response = make_api_request("GET", "/jobs/count", params=params)
        return response.get("count", 0)
    except:
        return 0


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


def save_job_to_tracking(job_id: int) -> bool:
    """Save a job to the tracking board."""
    try:
        data = {"job_id": job_id}
        response = make_api_request("POST", "/jobs/save", json=data)
        return response.get("success", False)
    except:
        return False


def pass_job(job_id: int) -> bool:
    """Pass/hide a job from the main list."""
    try:
        data = {"job_id": job_id}
        response = make_api_request("POST", "/jobs/pass", json=data)
        return response.get("success", False)
    except:
        return False


def get_tracked_jobs() -> Dict[str, List[Dict]]:
    """Get all tracked jobs organized by status."""
    try:
        return make_api_request("GET", "/jobs/tracked")
    except:
        return {"apply": [], "hr_screen": [], "round_1": [], "round_2": [], "rejected": []}


def update_job_status(job_id: int, new_status: str) -> bool:
    """Update the status of a tracked job."""
    try:
        data = {"job_id": job_id, "new_status": new_status}
        response = make_api_request("PUT", f"/jobs/tracked/{job_id}/status", json=data)
        return response.get("success", False)
    except:
        return False


def optimize_resume(resume_name: str, num_jobs: int = 20, filters: Dict[str, Any] = None) -> Dict[str, Any]:
    """Get resume optimization suggestions from backend with optional filters."""
    try:
        data = {"resume_name": resume_name, "num_jobs": num_jobs}

        # Add filters to request if provided
        if filters:
            data.update(filters)

        # Use longer timeout for AI processing
        return make_api_request("POST", "/resumes/optimize", timeout=120, json=data)
    except:
        return {"success": False, "message": "Optimization request failed"}


def generate_optimized_resume(resume_name: str, optimization_results: Dict[str, Any]) -> Dict[str, Any]:
    """Generate optimized resume HTML from backend."""
    try:
        data = {
            "resume_name": resume_name,
            "optimization_results": optimization_results
        }
        # Use longer timeout for AI processing (resume generation)
        return make_api_request("POST", "/resumes/generate-optimized", timeout=180, json=data)
    except:
        return {"success": False, "message": "Resume generation failed"}


def run_onboarding_workflow(resume_name: str) -> Dict[str, Any]:
    """Run the complete onboarding workflow for a resume."""
    try:
        data = {"resume_name": resume_name}
        # Use very long timeout for full onboarding (up to 5 minutes)
        return make_api_request("POST", "/onboarding/process", timeout=300, json=data)
    except:
        return {"success": False, "message": "Onboarding workflow failed"}


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
            job_id = job.get("id")
            if job_id and save_job_to_tracking(job_id):
                st.toast("💾 Job saved to tracker!")
                st.rerun()
            else:
                st.toast("❌ Failed to save job")
    with col3:
        if st.button("👁️ View", key=f"view_{index}", use_container_width=True):
            # Store the expanded state in session
            if f"expanded_{index}" not in st.session_state:
                st.session_state[f"expanded_{index}"] = False
            st.session_state[f"expanded_{index}"] = not st.session_state.get(f"expanded_{index}", False)
    with col4:
        if st.button("👎 Pass", key=f"pass_{index}", use_container_width=True):
            job_id = job.get("id")
            if job_id and pass_job(job_id):
                st.toast("❌ Job hidden")
                st.rerun()
            else:
                st.toast("❌ Failed to hide job")

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


# ============================================================================
# Onboarding Screen
# ============================================================================

# ATS tips and facts for job seekers during onboarding
ONBOARDING_FACTS = [
    "ATS Tip: Use standard section headers like 'Experience' and 'Education' - ATS systems look for these exact words.",
    "ATS Tip: Avoid tables, columns, and graphics in your resume - most ATS systems can't parse them correctly.",
    "ATS Tip: Include the exact job title from the posting in your resume - ATS matches on keywords.",
    "ATS Tip: Use a simple, clean font like Arial or Calibri - fancy fonts can confuse ATS parsers.",
    "ATS Tip: Save your resume as a .docx or .pdf - these formats are most ATS-compatible.",
    "ATS Tip: Spell out acronyms at least once (e.g., 'Search Engine Optimization (SEO)') for better keyword matching.",
    "ATS Tip: Put your most relevant skills near the top - ATS systems weight content by position.",
    "ATS Tip: Use bullet points instead of paragraphs - ATS systems parse them more accurately.",
    "ATS Tip: Include both hard skills (Python, Excel) and soft skills (leadership, communication) for broader matches.",
    "ATS Tip: Quantify your achievements with numbers - '30% increase in sales' stands out to both ATS and humans.",
    "ATS Tip: Remove headers and footers - many ATS systems skip or misread this content.",
    "ATS Tip: Use standard date formats (Jan 2020 - Present) - ATS systems parse these reliably.",
]

STEP_DETAILS = {
    "job_title_suggestions": {
        "name": "Analyzing Resume",
        "icon": "🧠",
        "active_message": "Our AI is reading your resume and identifying your key skills...",
        "complete_message": "Resume analyzed successfully!"
    },
    "job_search": {
        "name": "Searching Jobs",
        "icon": "🔍",
        "active_message": "Hunting for jobs matching your profile...",
        "complete_message": "Job search complete!"
    },
    "similarity_calculation": {
        "name": "Calculating Matches",
        "icon": "📊",
        "active_message": "Computing how well each job matches your skills...",
        "complete_message": "Match scores calculated!"
    },
    "resume_optimization": {
        "name": "Optimizing Resume",
        "icon": "✨",
        "active_message": "Generating ATS optimization recommendations...",
        "complete_message": "Optimization tips ready!"
    }
}


def show_onboarding_screen(resume_name: str):
    """
    Display the engaging onboarding processing screen.

    This function orchestrates the full onboarding workflow while showing
    an engaging UI with progress updates and fun facts.
    """
    import random

    # Full-page onboarding view
    st.markdown('<h1 class="main-header">🚀 Setting Up Your Job Hunt</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Hang tight! We\'re doing the heavy lifting so you don\'t have to.</p>', unsafe_allow_html=True)

    st.markdown("---")

    # Create containers for dynamic updates
    progress_container = st.container()
    steps_container = st.container()
    facts_container = st.container()

    # Initialize step tracking
    steps_order = ["job_title_suggestions", "job_search", "similarity_calculation", "resume_optimization"]
    step_results = {}

    with progress_container:
        # Overall progress bar
        progress_bar = st.progress(0, text="Starting onboarding...")

    with facts_container:
        # Fun fact display
        st.markdown("---")
        fact_placeholder = st.empty()
        fact_placeholder.info(f"💡 **Did you know?** {random.choice(ONBOARDING_FACTS)}")

    with steps_container:
        # Step progress display
        st.subheader("📋 Progress")
        step_placeholders = {}
        for step_name in steps_order:
            step_info = STEP_DETAILS[step_name]
            step_placeholders[step_name] = st.empty()
            step_placeholders[step_name].markdown(f"""
            <div style="background: #f5f5f5; padding: 1rem; border-radius: 8px; margin-bottom: 0.5rem; border-left: 4px solid #ddd;">
                <span style="font-size: 1.2rem;">⏳</span>
                <strong>{step_info['name']}</strong>
                <span style="color: #999; margin-left: 0.5rem;">Pending...</span>
            </div>
            """, unsafe_allow_html=True)

    # Run the onboarding workflow
    progress_bar.progress(5, text="🧠 Connecting to AI services...")

    # Show a random fact before starting
    time.sleep(1)
    fact_placeholder.info(f"💡 **Did you know?** {random.choice(ONBOARDING_FACTS)}")

    # Call the onboarding API
    progress_bar.progress(10, text="🚀 Starting onboarding workflow...")

    result = run_onboarding_workflow(resume_name)

    # Process results and update UI
    if result.get("success") or result.get("steps"):
        steps = result.get("steps", [])

        # Update each step's display
        for i, step in enumerate(steps):
            step_name = step.get("step_name", "")
            step_success = step.get("success", False)
            step_message = step.get("message", "")
            step_data = step.get("data", {})

            progress_pct = 10 + ((i + 1) / len(steps_order)) * 80
            step_info = STEP_DETAILS.get(step_name, {"name": step_name, "icon": "📌"})

            if step_success:
                # Show success state
                detail_text = ""
                if step_name == "job_title_suggestions" and step_data:
                    suggestions = step_data.get("suggestions", [])
                    if suggestions:
                        detail_text = f"<br><span style='color: #666; font-size: 0.9rem;'>→ Suggested: {', '.join(suggestions)}</span>"
                elif step_name == "job_search" and step_data:
                    total_jobs = step_data.get("total_jobs", 0)
                    detail_text = f"<br><span style='color: #666; font-size: 0.9rem;'>→ Found {total_jobs} jobs!</span>"
                elif step_name == "similarity_calculation" and step_data:
                    jobs_updated = step_data.get("jobs_updated", 0)
                    detail_text = f"<br><span style='color: #666; font-size: 0.9rem;'>→ Scored {jobs_updated} jobs</span>"
                elif step_name == "resume_optimization" and step_data:
                    score = step_data.get("overall_score", 0)
                    detail_text = f"<br><span style='color: #666; font-size: 0.9rem;'>→ ATS Score: {score}/100</span>"

                step_placeholders[step_name].markdown(f"""
                <div style="background: #d4edda; padding: 1rem; border-radius: 8px; margin-bottom: 0.5rem; border-left: 4px solid #28a745;">
                    <span style="font-size: 1.2rem;">✅</span>
                    <strong>{step_info['name']}</strong>
                    <span style="color: #155724; margin-left: 0.5rem;">{step_info.get('complete_message', 'Complete!')}</span>
                    {detail_text}
                </div>
                """, unsafe_allow_html=True)
            else:
                # Show failure state
                step_placeholders[step_name].markdown(f"""
                <div style="background: #fff3cd; padding: 1rem; border-radius: 8px; margin-bottom: 0.5rem; border-left: 4px solid #ffc107;">
                    <span style="font-size: 1.2rem;">⚠️</span>
                    <strong>{step_info['name']}</strong>
                    <span style="color: #856404; margin-left: 0.5rem;">{step_message[:50]}...</span>
                </div>
                """, unsafe_allow_html=True)

            progress_bar.progress(int(progress_pct), text=f"{step_info['icon']} {step_info['name']} complete!")

        # Final progress
        progress_bar.progress(100, text="🎉 Onboarding complete!")

        # Celebration!
        st.balloons()

        # Show brief summary
        st.markdown("---")
        st.success(f"""
        ### 🎉 You're All Set!

        **Summary:**
        - 📋 Suggested job titles: {', '.join(result.get('job_titles_suggested', ['N/A']))}
        - 🔍 Jobs found: **{result.get('total_jobs_found', 0)}**
        - 📊 Jobs with match scores: **{result.get('jobs_with_similarity', 0)}**
        - ✨ Resume ATS Score: **{result.get('optimization_score', 0)}/100**

        *Redirecting to your dashboard...*
        """)

        # Store results in session state
        st.session_state.onboarding_complete = True
        st.session_state.onboarding_results = result
        st.session_state.job_suggestions = result.get("job_titles_suggested", [])

        # Extract FULL optimization results from the onboarding steps
        optimization_data = None
        for step in result.get("steps", []):
            if step.get("step_name") == "resume_optimization" and step.get("data"):
                optimization_data = step.get("data")
                break

        if optimization_data:
            st.session_state.optimization_results = {
                "success": True,
                "overall_score": optimization_data.get("overall_score", 0),
                "missing_keywords": optimization_data.get("missing_keywords", []),
                "keyword_suggestions": optimization_data.get("keyword_suggestions", []),
                "ats_tips": optimization_data.get("ats_tips", []),
                "jobs_analyzed": optimization_data.get("jobs_analyzed", 0),
                "analysis_source": optimization_data.get("analysis_source", "job_database"),
                "message": f"Analyzed resume against {optimization_data.get('jobs_analyzed', 0)} similar jobs"
            }
        else:
            st.session_state.optimization_results = {
                "success": True,
                "overall_score": result.get("optimization_score", 0),
                "jobs_analyzed": result.get("jobs_with_similarity", 0),
                "analysis_source": "job_database"
            }

        st.session_state.similarity_needs_update = False
        st.session_state.last_similarity_resume = resume_name

        # Clear onboarding flags and AUTO-REDIRECT to main app (no button needed)
        st.session_state.show_onboarding = False
        st.session_state.onboarding_resume = None

        # Brief pause to show summary, then redirect
        time.sleep(3)
        st.rerun()

    else:
        # Error state
        progress_bar.progress(100, text="⚠️ Onboarding encountered issues")
        st.error(f"""
        ### Onboarding Had Some Issues

        **Error:** {result.get('message', 'Unknown error')}

        Don't worry! You can still use the app manually:
        - Upload your resume in the sidebar
        - Click "Smart Search" to find jobs
        - Use the Resume Optimizer tab for tips
        """)

        if st.button("Continue Anyway", type="primary"):
            # Clear ALL onboarding flags to prevent re-triggering
            st.session_state.show_onboarding = False
            st.session_state.onboarding_resume = None
            st.session_state.onboarding_complete = True
            st.rerun()


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
    if "similarity_needs_update" not in st.session_state:
        st.session_state.similarity_needs_update = False
    if "last_similarity_resume" not in st.session_state:
        st.session_state.last_similarity_resume = None
    if "generated_resume_html" not in st.session_state:
        st.session_state.generated_resume_html = None
    if "optimization_results" not in st.session_state:
        st.session_state.optimization_results = None
    if "last_optimized_resume" not in st.session_state:
        st.session_state.last_optimized_resume = None

    # Clear cached Word bytes if resume changed
    if "last_optimized_resume" in st.session_state and st.session_state.last_optimized_resume != st.session_state.selected_resume:
        if "word_docx_bytes" in st.session_state:
            del st.session_state.word_docx_bytes
        if "word_filename" in st.session_state:
            del st.session_state.word_filename

    # Sidebar
    with st.sidebar:
        # User info and logout button
        if is_logged_in() and "user_info" in st.session_state:
            user_info = st.session_state.user_info
            st.markdown(f"""
            <div style="background: linear-gradient(90deg, #1e88e5 0%, #7b1fa2 100%);
                        padding: 1rem; border-radius: 8px; margin-bottom: 1rem; color: white;">
                <div style="font-weight: 600; font-size: 0.9rem;">👤 {user_info.get('username', 'User')}</div>
                <div style="font-size: 0.75rem; opacity: 0.9;">{user_info.get('email', '')}</div>
            </div>
            """, unsafe_allow_html=True)

            # Debug: Check if token exists
            token = st.session_state.get("access_token")
            if not token:
                st.warning("⚠️ Authentication token missing! Please log out and log in again.")
            else:
                # Show token status (first/last few chars only for security)
                token_preview = f"{token[:10]}...{token[-10:]}" if len(token) > 20 else "***"
                with st.expander("🔐 Auth Status", expanded=False):
                    st.success("✅ Token present")
                    st.code(token_preview, language=None)

            if st.button("🚪 Logout", use_container_width=True):
                logout_user()

            st.markdown("---")

        st.header("📋 Quick Start")

        # Resume Management
        st.subheader("📄 Your Resume")

        # Get existing resumes
        resumes = get_resumes()

        if resumes:
            # Clear session state if selected resume no longer exists
            if st.session_state.selected_resume and st.session_state.selected_resume not in resumes:
                st.session_state.selected_resume = None
                st.session_state.job_suggestions = None

            # Set default if none selected
            if not st.session_state.selected_resume:
                st.session_state.selected_resume = resumes[-1]

            # Resume selector dropdown
            current_index = resumes.index(st.session_state.selected_resume) if st.session_state.selected_resume in resumes else 0

            selected = st.selectbox(
                "Select Resume",
                options=resumes,
                index=current_index,
                key="resume_selector",
                help="Choose which resume to use for job matching and optimization"
            )

            # Check if resume changed
            if selected != st.session_state.selected_resume:
                st.session_state.selected_resume = selected
                st.session_state.job_suggestions = None  # Clear suggestions for new resume
                st.session_state.optimization_results = None  # Clear optimization results
                st.session_state.similarity_needs_update = True  # Flag for similarity update
                st.rerun()

            # Show update similarity button if jobs exist and resume changed
            stats = get_database_stats()
            job_count = stats.get("total_jobs", 0)

            if job_count > 0:
                # Check if similarity scores need updating
                needs_update = (
                    st.session_state.similarity_needs_update or
                    st.session_state.last_similarity_resume != st.session_state.selected_resume
                )

                if needs_update:
                    st.warning(f"⚠️ Similarity scores need updating for **{selected}**")
                    if st.button("🔄 Update Job Matches", use_container_width=True, type="primary"):
                        with st.spinner("Recalculating similarity scores... This may take a moment."):
                            result = update_similarity_scores(st.session_state.selected_resume)
                            if result.get("success"):
                                st.session_state.similarity_needs_update = False
                                st.session_state.last_similarity_resume = st.session_state.selected_resume
                                st.success(f"✅ Updated {result.get('jobs_updated', 0)} jobs!")
                                st.rerun()
                            else:
                                st.error("Failed to update similarity scores")
                else:
                    st.success(f"✅ **Active:** {selected}")
            else:
                st.success(f"✅ **Active:** {selected}")

            # Upload new resume (collapsed by default)
            with st.expander("📤 Upload New Resume"):
                st.info("📄 Upload a new resume to automatically search for matching jobs!")
                uploaded_file = st.file_uploader("Choose a file", type=['txt', 'pdf'], key="resume_uploader")

                # Auto-upload when file is selected
                if uploaded_file is not None:
                    # Use session state to track if this file has been processed
                    file_key = f"{uploaded_file.name}_{uploaded_file.size}"
                    if 'last_uploaded_file' not in st.session_state or st.session_state.last_uploaded_file != file_key:
                        with st.spinner("Uploading resume..."):
                            try:
                                success = upload_resume_file(uploaded_file)
                                if success:
                                    st.session_state.last_uploaded_file = file_key
                                    st.session_state.selected_resume = uploaded_file.name
                                    st.session_state.job_suggestions = None
                                    st.session_state.optimization_results = None
                                    # Trigger onboarding workflow for the new resume
                                    st.session_state.show_onboarding = True
                                    st.session_state.onboarding_resume = uploaded_file.name
                                    st.success(f"✅ Resume uploaded! Starting job search...")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("Upload failed. Please try again.")
                            except Exception as e:
                                st.error(f"Error: {e}")
        else:
            # No resumes yet - clear session state and show uploader prominently
            if st.session_state.selected_resume:
                st.session_state.selected_resume = None
                st.session_state.job_suggestions = None

            st.info("👋 **Start by uploading your resume** to get personalized job matches!")
            st.markdown("*We'll automatically find jobs matching your skills and optimize your resume for ATS.*")
            uploaded_file = st.file_uploader("Choose a file", type=['txt', 'pdf'], key="first_resume_uploader")

            # Auto-upload when file is selected
            if uploaded_file is not None:
                file_key = f"{uploaded_file.name}_{uploaded_file.size}"
                if 'last_uploaded_file' not in st.session_state or st.session_state.last_uploaded_file != file_key:
                    with st.spinner("Uploading resume..."):
                        try:
                            success = upload_resume_file(uploaded_file)
                            if success:
                                st.session_state.last_uploaded_file = file_key
                                st.session_state.selected_resume = uploaded_file.name
                                # Trigger onboarding workflow for the new resume
                                st.session_state.show_onboarding = True
                                st.session_state.onboarding_resume = uploaded_file.name
                                st.success(f"✅ Resume uploaded! Starting your personalized job search...")
                                time.sleep(1)
                                st.rerun()
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
    
    # Main content area with tabs
    tab0, tab1, tab2 = st.tabs(["🎯 Resume Optimizer", "📊 Job Matches", "📋 Job Tracker"])

    # TAB 0: Resume Optimizer
    with tab0:
        st.header("🎯 Resume Optimizer")
        st.caption("Get AI-powered recommendations to improve your resume for ATS systems")

        # Check if resume is uploaded
        if not st.session_state.selected_resume:
            st.info("👋 Please upload a resume in the sidebar first to get started.")
        else:
            st.success(f"📄 Analyzing: **{st.session_state.selected_resume}**")

            # Get database stats to show context
            stats = get_database_stats()
            job_count = stats.get("jobs_with_similarity_scores", 0)

            if job_count > 0:
                st.info(f"📊 Found **{job_count} jobs** in your search history. Analysis will use the top matching jobs.")
            else:
                st.warning("💡 No job searches yet. Analysis will use AI's general knowledge. For better results, search for jobs first!")

            # Analysis parameters
            col1, col2 = st.columns([2, 1])
            with col1:
                num_jobs_to_analyze = st.slider(
                    "Number of top jobs to analyze",
                    min_value=5,
                    max_value=30,
                    value=20,
                    help="Analyze against your top N most similar jobs"
                )
            with col2:
                analyze_button = st.button("🔍 Analyze My Resume", type="primary", use_container_width=True)

            # Basic filters
            st.subheader("🎯 Filter & Refine Your Analysis")
            col1, col2, col3 = st.columns(3)
            with col1:
                resume_min_similarity = st.slider(
                    "Min Match Score",
                    0.0,
                    1.0,
                    0.0,
                    0.05,
                    help="Only analyze jobs with at least this similarity score"
                )
            with col2:
                resume_location_filter = st.text_input(
                    "Location",
                    placeholder="San Francisco, Remote...",
                    help="Filter by location (city, state, country)"
                )
            with col3:
                resume_remote_filter = st.selectbox(
                    "Work Style",
                    ["All", "Remote Only", "Hybrid", "On-site"],
                    index=0,
                    help="Filter by remote status"
                )

            # Advanced filters
            with st.expander("⚙️ Advanced Filters"):
                col1, col2 = st.columns(2)
                with col1:
                    resume_company_filter = st.text_input(
                        "Company",
                        placeholder="Google, Apple...",
                        help="Filter by company name"
                    )
                    resume_title_filter = st.text_input(
                        "Job Title",
                        placeholder="Engineer, Manager...",
                        help="Filter by job title"
                    )
                    resume_job_type_filter = st.selectbox(
                        "Job Type",
                        ["All", "Full-time", "Part-time", "Contract", "Temporary"],
                        index=0,
                        help="Filter by job type"
                    )
                with col2:
                    resume_min_salary = st.number_input(
                        "Min Salary ($)",
                        min_value=0,
                        value=0,
                        step=10000,
                        help="Filter by minimum salary (0 for no limit)"
                    )
                    resume_max_salary = st.number_input(
                        "Max Salary ($)",
                        min_value=0,
                        value=0,
                        step=10000,
                        help="Filter by maximum salary (0 for no limit)"
                    )
                    st.caption("💡 Leave salary at 0 to show all")

            # Live preview of filtered job count
            preview_filters = {}
            if resume_min_similarity > 0:
                preview_filters["min_similarity"] = resume_min_similarity
            if resume_location_filter:
                preview_filters["location"] = resume_location_filter
            if resume_remote_filter == "Remote Only":
                preview_filters["is_remote"] = True
            elif resume_remote_filter == "On-site":
                preview_filters["is_remote"] = False

            if resume_company_filter:
                preview_filters["company"] = resume_company_filter
            if resume_title_filter:
                preview_filters["title"] = resume_title_filter
            if resume_job_type_filter != "All":
                preview_filters["job_type"] = resume_job_type_filter
            if resume_min_salary > 0:
                preview_filters["min_salary"] = resume_min_salary
            if resume_max_salary > 0:
                preview_filters["max_salary"] = resume_max_salary

            # Get count of jobs matching current filters
            filtered_count = get_filtered_job_count(preview_filters if preview_filters else None)

            # Display live preview
            col1, col2 = st.columns([2, 1])
            with col1:
                if filtered_count > 0:
                    st.success(f"✅ Analysis will use **{filtered_count}** jobs matching your filters")
                else:
                    st.warning("⚠️ No jobs match your current filters. Consider adjusting them.")
            with col2:
                st.metric("Sample Size", filtered_count)

            if analyze_button:
                with st.spinner("🤖 AI is analyzing your resume... This may take 30-60 seconds."):
                    # Build filters dictionary
                    optimization_filters = {}
                    if resume_min_similarity > 0:
                        optimization_filters["min_similarity"] = resume_min_similarity
                    if resume_location_filter:
                        optimization_filters["location"] = resume_location_filter
                    if resume_remote_filter == "Remote Only":
                        optimization_filters["is_remote"] = True
                    elif resume_remote_filter == "On-site":
                        optimization_filters["is_remote"] = False
                    # Note: "Hybrid" and "All" don't set is_remote filter

                    # Advanced filters
                    if resume_company_filter:
                        optimization_filters["company"] = resume_company_filter
                    if resume_title_filter:
                        optimization_filters["title"] = resume_title_filter
                    if resume_job_type_filter != "All":
                        optimization_filters["job_type"] = resume_job_type_filter
                    if resume_min_salary > 0:
                        optimization_filters["min_salary"] = resume_min_salary
                    if resume_max_salary > 0:
                        optimization_filters["max_salary"] = resume_max_salary

                    result = optimize_resume(st.session_state.selected_resume, num_jobs_to_analyze, optimization_filters)
                    st.session_state.optimization_results = result
                    # Store the number of jobs and filters used for re-analysis
                    st.session_state.num_jobs_analyzed = num_jobs_to_analyze
                    st.session_state.optimization_filters = optimization_filters

                    # Auto-generate the optimized resume
                    if result.get("success"):
                        with st.spinner("✨ AI is creating your optimized resume... This may take 1-2 minutes."):
                            optimization_data = {
                                "missing_keywords": result.get("missing_keywords", []),
                                "keyword_suggestions": [
                                    {
                                        "current": ks.current if hasattr(ks, 'current') else ks.get('current', ''),
                                        "suggested": ks.suggested if hasattr(ks, 'suggested') else ks.get('suggested', ''),
                                        "reason": ks.reason if hasattr(ks, 'reason') else ks.get('reason', '')
                                    }
                                    for ks in result.get("keyword_suggestions", [])
                                ],
                                "ats_tips": result.get("ats_tips", []),
                                "overall_score": result.get("overall_score", 0)
                            }

                            generated_result = generate_optimized_resume(
                                st.session_state.selected_resume,
                                optimization_data
                            )

                            if generated_result.get("success"):
                                st.session_state.generated_resume_html = generated_result.get("html_content")
                                st.session_state.last_optimized_resume = st.session_state.selected_resume
                                # Clear any cached Word bytes since we have new HTML
                                if "word_docx_bytes" in st.session_state:
                                    del st.session_state.word_docx_bytes
                                if "word_filename" in st.session_state:
                                    del st.session_state.word_filename
                                st.success("✅ Optimized resume generated successfully!")
                            else:
                                st.error(f"❌ Resume generation failed: {generated_result.get('message', 'Unknown error')}")

            # Display results
            if st.session_state.optimization_results:
                result = st.session_state.optimization_results

                if not result.get("success"):
                    st.error(f"❌ {result.get('message', 'Analysis failed')}")
                else:
                    # Success - display results
                    st.divider()

                    # Overall Score Section
                    score = result.get("overall_score", 0)
                    jobs_analyzed = result.get("jobs_analyzed", 0)
                    analysis_source = result.get("analysis_source", "ai_general")

                    # Score visualization
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        # Determine score color
                        if score >= 80:
                            score_color = "#28a745"  # Green
                            score_emoji = "🌟"
                            score_label = "Excellent"
                        elif score >= 60:
                            score_color = "#ffc107"  # Yellow
                            score_emoji = "👍"
                            score_label = "Good"
                        elif score >= 40:
                            score_color = "#fd7e14"  # Orange
                            score_emoji = "📈"
                            score_label = "Needs Improvement"
                        else:
                            score_color = "#dc3545"  # Red
                            score_emoji = "⚠️"
                            score_label = "Needs Work"

                        st.markdown(f"""
                        <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); border-radius: 16px; margin-bottom: 1rem;">
                            <div style="font-size: 4rem; font-weight: 700; color: {score_color};">{score}</div>
                            <div style="font-size: 1.2rem; color: #666;">ATS Compatibility Score</div>
                            <div style="font-size: 1.5rem; margin-top: 0.5rem;">{score_emoji} {score_label}</div>
                        </div>
                        """, unsafe_allow_html=True)

                        if analysis_source == "job_database":
                            st.caption(f"📊 Based on analysis of {jobs_analyzed} jobs from your searches")
                        else:
                            st.caption("🤖 Based on AI's general knowledge of job market trends")

                    st.divider()

                    # Missing Keywords Section
                    st.subheader("🔑 Missing Keywords")
                    st.markdown("*Add these keywords to your resume - they appear in your target jobs but are missing from your resume:*")

                    missing_keywords = result.get("missing_keywords", [])
                    if missing_keywords:
                        # Display keywords in columns using Streamlit native components
                        cols = st.columns(4)
                        for i, keyword in enumerate(missing_keywords):
                            with cols[i % 4]:
                                st.markdown(f"""
                                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 0.5rem 0.75rem; border-radius: 16px; font-weight: 600; font-size: 0.85rem; text-align: center; margin-bottom: 0.5rem; box-shadow: 0 2px 4px rgba(0,0,0,0.15);">
                                    {keyword}
                                </div>
                                """, unsafe_allow_html=True)
                    else:
                        st.success("✅ Great! No critical keywords missing.")

                    st.divider()

                    # Keyword Suggestions Section
                    st.subheader("💡 Keyword Improvements")
                    st.markdown("*Consider these alternative or enhanced keywords for better ATS matching:*")

                    keyword_suggestions = result.get("keyword_suggestions", [])
                    if keyword_suggestions:
                        for i, suggestion in enumerate(keyword_suggestions):
                            # Handle both dict and Pydantic model formats
                            if hasattr(suggestion, 'current'):
                                current = suggestion.current
                                suggested = suggestion.suggested
                                reason = suggestion.reason
                            else:
                                current = suggestion.get("current", "")
                                suggested = suggestion.get("suggested", "")
                                reason = suggestion.get("reason", "")

                            with st.container():
                                col1, col2 = st.columns([3, 2])
                                with col1:
                                    st.markdown(f"""
                                    <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; margin-bottom: 0.5rem; border-left: 4px solid #1e88e5;">
                                        <span style="color: #dc3545; text-decoration: line-through;">{current}</span>
                                        <span style="margin: 0 0.5rem;">→</span>
                                        <span style="color: #28a745; font-weight: 600;">{suggested}</span>
                                    </div>
                                    """, unsafe_allow_html=True)
                                with col2:
                                    st.caption(f"💡 {reason}")
                    else:
                        st.info("No specific keyword improvements suggested.")

                    st.divider()

                    # ATS Tips Section
                    st.subheader("📝 ATS Optimization Tips")
                    st.markdown("*Actionable recommendations to improve your resume's ATS compatibility:*")

                    ats_tips = result.get("ats_tips", [])
                    if ats_tips:
                        for i, tip in enumerate(ats_tips, 1):
                            st.markdown(f"""
                            <div style="background: #e8f5e9; padding: 1rem; border-radius: 8px; margin-bottom: 0.75rem; border-left: 4px solid #28a745;">
                                <strong>{i}.</strong> {tip}
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("No additional tips at this time.")

                    # Action Buttons
                    st.divider()
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🔄 Re-analyze", use_container_width=True):
                            # Re-run the analysis with the same parameters and filters
                            num_jobs_param = st.session_state.get("num_jobs_analyzed", 20)
                            filters_param = st.session_state.get("optimization_filters", None)
                            with st.spinner("🤖 AI is re-analyzing your resume... This may take 30-60 seconds."):
                                result = optimize_resume(st.session_state.selected_resume, num_jobs_param, filters_param)
                                st.session_state.optimization_results = result
                            st.rerun()
                    with col2:
                        if job_count == 0:
                            st.info("💡 Search for jobs to get more targeted recommendations!")

                    # Download Options Section
                    st.divider()
                    st.subheader("📥 Download Your Optimized Resume")

                    # Display the generated resume
                    if st.session_state.generated_resume_html:
                        st.markdown("*Changes from the original are highlighted in **yellow**.*")

                        # Download buttons
                        col1, col2 = st.columns(2)
                        with col1:
                            # Prepare Word document automatically if not done
                            if "word_docx_bytes" not in st.session_state:
                                with st.spinner("📝 Preparing Word document..."):
                                    try:
                                        # Only send resume_name - HTML will be fetched from database by backend
                                        data = {
                                            "resume_name": st.session_state.selected_resume
                                        }
                                        url = f"{BACKEND_URL}/resumes/download-word"
                                        token = st.session_state.get("access_token")
                                        headers = {"Authorization": f"Bearer {token}"}
                                        response = requests.post(url, json=data, headers=headers, timeout=60)
                                        if response.status_code == 200:
                                            st.session_state.word_docx_bytes = response.content
                                            st.session_state.word_filename = f"{st.session_state.selected_resume.rsplit('.', 1)[0]}_optimized.docx"
                                        else:
                                            st.error(f"Failed to prepare Word document: {response.text}")
                                    except Exception as e:
                                        logger.error(f"Word generation error: {e}")
                                        st.error(f"Error preparing Word document: {str(e)}")

                            # Word download button
                            if "word_docx_bytes" in st.session_state and st.session_state.word_docx_bytes:
                                st.download_button(
                                    label="📥 Download as Word (.docx)",
                                    data=st.session_state.word_docx_bytes,
                                    file_name=st.session_state.word_filename,
                                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                    use_container_width=True,
                                    type="primary"
                                )
                            else:
                                st.info("⏳ Preparing Word document...")

                        with col2:
                            # PDF download using browser print
                            st.markdown("""
                            <style>
                            .pdf-button {
                                display: inline-block;
                                padding: 0.5rem 1rem;
                                background: linear-gradient(90deg, #1e88e5 0%, #1976d2 100%);
                                color: white;
                                text-decoration: none;
                                border-radius: 8px;
                                font-weight: 600;
                                text-align: center;
                                width: 100%;
                                border: none;
                                cursor: pointer;
                            }
                            </style>
                            <button class="pdf-button" onclick="window.print()">📄 Download as PDF</button>
                            """, unsafe_allow_html=True)

                        st.divider()

                        # Display HTML in an expandable container
                        with st.expander("👁️ Preview Optimized Resume", expanded=True):
                            st.components.v1.html(st.session_state.generated_resume_html, height=800, scrolling=True)

    # TAB 1: Job Matches
    with tab1:
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

    # TAB 2: Job Tracker (Kanban Board)
    with tab2:
        st.header("📋 Job Application Tracker")
        st.caption("Track your job applications from initial application to final outcome")

        # Get tracked jobs
        tracked_data = get_tracked_jobs()

        # Define columns
        columns = [
            {"key": "apply", "title": "📝 Apply", "color": "#e3f2fd"},
            {"key": "hr_screen", "title": "📞 HR Screen", "color": "#fff3e0"},
            {"key": "round_1", "title": "💼 1st Round", "color": "#f3e5f5"},
            {"key": "round_2", "title": "🎯 2nd Round", "color": "#e8f5e9"},
            {"key": "rejected", "title": "❌ Rejected/Ghosted", "color": "#ffebee"}
        ]

        # Create columns for Kanban board
        cols = st.columns(len(columns))

        for idx, col_info in enumerate(columns):
            with cols[idx]:
                jobs = tracked_data.get(col_info["key"], [])
                st.markdown(f"""
                <div style="background: {col_info['color']}; padding: 0.75rem; border-radius: 8px; margin-bottom: 1rem;">
                    <h4 style="margin: 0; color: #333;">{col_info['title']}</h4>
                    <p style="margin: 0; color: #666; font-size: 0.9rem;">{len(jobs)} jobs</p>
                </div>
                """, unsafe_allow_html=True)

                # Display jobs in this column
                for job in jobs:
                    import html
                    job_title = html.escape(job.get("title", "Unknown"))
                    company = html.escape(job.get("company", "Unknown"))
                    similarity = job.get("resume_similarity", 0)
                    job_id = job.get("job_id")  # Fixed: use 'job_id' not 'id'

                    # Skip jobs with invalid job_id
                    if job_id is None:
                        st.error(f"⚠️ Invalid job data for '{job_title}'. Please refresh the page.")
                        continue

                    # Job card HTML
                    st.markdown(f"""
                    <div style="background: white; border: 1px solid #ddd; border-radius: 8px; padding: 0.75rem; margin-bottom: 0.75rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <div style="font-weight: 600; color: #333; margin-bottom: 0.25rem;">{job_title}</div>
                        <div style="color: #666; font-size: 0.85rem; margin-bottom: 0.5rem;">{company}</div>
                        <div style="font-size: 0.8rem; color: #999;">Match: {int(similarity * 100)}%</div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Status update buttons
                    # Show move buttons based on current column
                    if col_info["key"] == "apply":
                        if st.button("→ HR Screen", key=f"move_{job_id}_hr", use_container_width=True):
                            if update_job_status(job_id, "hr_screen"):
                                st.toast("✅ Moved to HR Screen!")
                                st.rerun()
                    elif col_info["key"] == "hr_screen":
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("→ Round 1", key=f"move_{job_id}_r1", use_container_width=True):
                                if update_job_status(job_id, "round_1"):
                                    st.toast("✅ Moved to Round 1!")
                                    st.rerun()
                        with col_b:
                            if st.button("❌ Reject", key=f"move_{job_id}_rej_hr", use_container_width=True):
                                if update_job_status(job_id, "rejected"):
                                    st.toast("Moved to Rejected")
                                    st.rerun()
                    elif col_info["key"] == "round_1":
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("→ Round 2", key=f"move_{job_id}_r2", use_container_width=True):
                                if update_job_status(job_id, "round_2"):
                                    st.toast("✅ Moved to Round 2!")
                                    st.rerun()
                        with col_b:
                            if st.button("❌ Reject", key=f"move_{job_id}_rej_r1", use_container_width=True):
                                if update_job_status(job_id, "rejected"):
                                    st.toast("Moved to Rejected")
                                    st.rerun()
                    elif col_info["key"] == "round_2":
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("✅ Offer!", key=f"move_{job_id}_offer", use_container_width=True):
                                st.balloons()
                                st.toast("🎉 Congratulations!")
                        with col_b:
                            if st.button("❌ Reject", key=f"move_{job_id}_rej_r2", use_container_width=True):
                                if update_job_status(job_id, "rejected"):
                                    st.toast("Moved to Rejected")
                                    st.rerun()

                    st.divider()

        # Show empty state if no tracked jobs
        if all(len(tracked_data.get(col["key"], [])) == 0 for col in columns):
            st.info("📌 No jobs in your tracker yet. Go to the 'Job Matches' tab and click 'Save' on any job to start tracking!")


if __name__ == "__main__":
    # Check if user is logged in
    if is_logged_in():
        # Check if we need to show onboarding
        if st.session_state.get("show_onboarding") and st.session_state.get("onboarding_resume"):
            show_onboarding_screen(st.session_state.onboarding_resume)
        else:
            main()
    else:
        show_login_page()