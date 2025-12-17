"""
FastAPI backend application for GPT Job Hunter.
"""

import logging
from datetime import datetime
from typing import List, Optional
import os

from fastapi import FastAPI, HTTPException, status, Depends, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn

from jobhunter.backend.models import (
    JobSearchRequest, JobSearchResponse,
    ResumeUploadRequest, ResumeResponse, ResumeListResponse, ResumeContentResponse,
    JobFilterRequest, JobListResponse, JobCountResponse,
    SimilarityUpdateRequest, SimilarityUpdateResponse,
    JobTitleSuggestionsRequest, JobTitleSuggestionsResponse,
    SaveJobRequest, PassJobRequest, JobTrackingResponse, TrackedJobsResponse, UpdateJobStatusRequest,
    ResumeOptimizeRequest, ResumeOptimizeResponse,
    GenerateOptimizedResumeRequest, GenerateOptimizedResumeResponse,
    ErrorResponse, HealthResponse,
    UserRegisterRequest, UserLoginRequest, UserResponse, TokenResponse,
    PasswordResetRequest, PasswordResetConfirm, LogoutResponse,
    OnboardingRequest, OnboardingResponse
)
from jobhunter.backend.services import (
    JobSearchService, ResumeService, JobDataService, DatabaseService, AIService, JobTrackingService,
    ResumeOptimizerService, AuthService, OnboardingService
)
from jobhunter.backend.auth_service import get_current_user

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="GPT Job Hunter API",
    description="AI-powered job search backend API with resume matching capabilities",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
job_search_service = JobSearchService()
resume_service = ResumeService()
job_data_service = JobDataService()
database_service = DatabaseService()
ai_service = AIService()
job_tracking_service = JobTrackingService()
resume_optimizer_service = ResumeOptimizerService()
auth_service = AuthService()
onboarding_service = OnboardingService()


# Custom dependency for file uploads that manually extracts token
async def get_current_user_from_header(request: Request):
    """
    Alternative auth dependency that manually extracts token from Authorization header.
    Useful for file upload endpoints where OAuth2PasswordBearer might have issues.
    """
    from jobhunter.backend.auth_service import verify_token
    from jobhunter.AuthHandler import get_user_by_id

    # Extract Authorization header
    auth_header = request.headers.get("Authorization")
    logger.info(f"File upload auth - Authorization header present: {auth_header is not None}")

    if not auth_header:
        logger.error("File upload auth - No Authorization header found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract token from "Bearer <token>"
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        logger.error(f"File upload auth - Invalid Authorization header format: {auth_header[:20]}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]
    logger.info(f"File upload auth - Extracted token: {token[:10]}...{token[-10:]}")

    # Verify token
    user_id = verify_token(token)
    if user_id is None:
        logger.error("File upload auth - Token verification failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    user = get_user_by_id(user_id=user_id)
    if user is None:
        logger.error(f"File upload auth - User not found for ID: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.get('is_active'):
        logger.error(f"File upload auth - Inactive user: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )

    logger.info(f"File upload auth - SUCCESS for user: {user.get('username')} (ID: {user_id})")
    return user


# Startup event handler
@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup."""
    try:
        database_service.initialize_database()
        logger.info("Database initialized successfully on startup")

        # Initialize auth tables
        from jobhunter.AuthHandler import create_auth_tables
        create_auth_tables()
        logger.info("Auth tables initialized successfully on startup")
    except Exception as e:
        logger.error(f"Failed to initialize database on startup: {e}")


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error", "detail": str(exc)}
    )


# ============================================================================
# Authentication Endpoints
# ============================================================================

@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: UserRegisterRequest):
    """
    Register a new user account.

    - **email**: Valid email address (must be unique)
    - **username**: Username (3-50 characters, must be unique)
    - **password**: Password (minimum 8 characters)
    - **full_name**: Optional full name
    """
    try:
        success, message, user_response = auth_service.register_user(request)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )

        return user_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@app.post("/auth/login", response_model=TokenResponse)
async def login(request: UserLoginRequest):
    """
    Login with username/email and password to receive JWT token.

    - **username_or_email**: Username or email address
    - **password**: User password

    Returns a JWT access token that should be included in the Authorization header
    for all protected endpoints as: `Authorization: Bearer <token>`
    """
    try:
        success, message, token_response = auth_service.login_user(request)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=message,
                headers={"WWW-Authenticate": "Bearer"}
            )

        return token_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@app.post("/auth/logout", response_model=LogoutResponse)
async def logout(current_user: dict = Depends(get_current_user)):
    """
    Logout the current user.

    Note: Since we're using JWT tokens, logout is handled client-side
    by removing the token. This endpoint confirms the user was authenticated.
    """
    logger.info(f"User logged out: {current_user['username']}")
    return LogoutResponse(
        success=True,
        message="Logged out successfully"
    )


@app.post("/auth/password-reset-request")
async def request_password_reset(request: PasswordResetRequest):
    """
    Request a password reset token.

    - **email**: Email address of the account

    If the email exists, a reset token will be generated.
    In production, this token would be sent via email.
    For development/testing, check the server logs.
    """
    try:
        success, message = auth_service.request_password_reset(request.email)
        return {"success": success, "message": message}

    except Exception as e:
        logger.error(f"Password reset request error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password reset request failed: {str(e)}"
        )


@app.post("/auth/password-reset-confirm")
async def confirm_password_reset(request: PasswordResetConfirm):
    """
    Confirm password reset using token.

    - **token**: Password reset token (from email or logs)
    - **new_password**: New password (minimum 8 characters)
    """
    try:
        success, message = auth_service.reset_password(request.token, request.new_password)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )

        return {"success": success, "message": message}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset confirmation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password reset failed: {str(e)}"
        )


@app.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Get current authenticated user information.

    Requires: Valid JWT token in Authorization header.
    """
    from datetime import datetime

    return UserResponse(
        id=current_user['id'],
        email=current_user['email'],
        username=current_user['username'],
        full_name=current_user.get('full_name'),
        is_active=bool(current_user['is_active']),
        created_at=datetime.fromisoformat(current_user['created_at']) if current_user.get('created_at') else datetime.now(),
        last_login=datetime.fromisoformat(current_user['last_login']) if current_user.get('last_login') else None
    )


# ============================================================================
# Health & Database Endpoints
# ============================================================================

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        # Check database connectivity
        stats = database_service.get_database_stats()
        
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now(),
            version="1.0.0"
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unhealthy"
        )


# Initialize database endpoint
@app.post("/initialize")
async def initialize_database():
    """Initialize the database with required tables."""
    try:
        success = database_service.initialize_database()
        if success:
            return {"message": "Database initialized successfully", "success": True}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initialize database"
            )
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database initialization failed: {str(e)}"
        )


# Database stats endpoint
@app.get("/stats")
async def get_database_stats():
    """Get database statistics."""
    try:
        stats = database_service.get_database_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get database stats: {str(e)}"
        )


# Job search endpoints
@app.post("/jobs/search", response_model=JobSearchResponse)
async def search_jobs(request: JobSearchRequest):
    """
    Search for jobs based on criteria.
    
    This endpoint performs the complete job search pipeline:
    1. Extracts jobs from external API
    2. Transforms and cleans the data
    3. Loads jobs into the database
    """
    try:
        total_jobs = job_search_service.search_jobs(request)
        
        return JobSearchResponse(
            total_jobs_found=total_jobs,
            message=f"Successfully found {total_jobs} jobs" if total_jobs > 0 else "No jobs found",
            success=total_jobs > 0
        )
    except Exception as e:
        logger.error(f"Job search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Job search failed: {str(e)}"
        )


@app.get("/jobs", response_model=JobListResponse)
async def get_jobs(
    resume_name: Optional[str] = None,
    min_similarity: Optional[float] = 0.0,
    company: Optional[str] = None,
    title: Optional[str] = None,
    location: Optional[str] = None,
    job_type: Optional[str] = None,
    is_remote: Optional[bool] = None,
    min_salary: Optional[float] = None,
    max_salary: Optional[float] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Get filtered list of jobs from the database.

    Supports filtering by various criteria including similarity scores,
    company, title, location, job type, remote status, and salary range.
    """
    try:
        filter_request = JobFilterRequest(
            resume_name=resume_name,
            min_similarity=min_similarity,
            company=company,
            title=title,
            location=location,
            job_type=job_type,
            is_remote=is_remote,
            min_salary=min_salary,
            max_salary=max_salary,
            limit=limit,
            offset=offset
        )

        jobs, total_count = job_data_service.get_jobs(filter_request)

        return JobListResponse(
            jobs=jobs,
            total_count=total_count,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        logger.error(f"Failed to get jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get jobs: {str(e)}"
        )


@app.get("/jobs/count", response_model=JobCountResponse)
async def count_jobs(
    resume_name: Optional[str] = None,
    min_similarity: Optional[float] = 0.0,
    company: Optional[str] = None,
    title: Optional[str] = None,
    location: Optional[str] = None,
    job_type: Optional[str] = None,
    is_remote: Optional[bool] = None,
    min_salary: Optional[float] = None,
    max_salary: Optional[float] = None
):
    """
    Get count of jobs matching filter criteria (without fetching the jobs).

    This is a lightweight endpoint useful for displaying filter previews in the UI.
    Supports the same filtering criteria as /jobs endpoint.
    """
    try:
        filter_request = JobFilterRequest(
            resume_name=resume_name,
            min_similarity=min_similarity,
            company=company,
            title=title,
            location=location,
            job_type=job_type,
            is_remote=is_remote,
            min_salary=min_salary,
            max_salary=max_salary,
            limit=1,  # Only need count, not actual jobs
            offset=0
        )

        _, total_count = job_data_service.get_jobs(filter_request)

        return JobCountResponse(count=total_count)
    except Exception as e:
        logger.error(f"Failed to count jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to count jobs: {str(e)}"
        )


# ============================================================================
# Resume Management Endpoints (Protected)
# ============================================================================

@app.post("/resumes/upload", response_model=ResumeResponse)
async def upload_resume(
    request: ResumeUploadRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a resume to the database.

    The resume content should be provided as plain text.

    **Requires authentication.**
    """
    try:
        user_id = current_user['id']
        success = resume_service.upload_resume(request, user_id=user_id)

        return ResumeResponse(
            resume_name=request.filename,
            success=success,
            message=f"Resume '{request.filename}' uploaded successfully"
        )
    except Exception as e:
        logger.error(f"Resume upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Resume upload failed: {str(e)}"
        )


@app.post("/resumes/upload-file")
async def upload_resume_file(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user_from_header)
):
    """
    Upload a resume file (PDF or TXT).

    Accepts PDF and TXT files and extracts text content.

    **Requires authentication.**
    """
    try:
        logger.info(f"=== FILE UPLOAD RECEIVED ===")
        logger.info(f"User: {current_user.get('username')} (ID: {current_user.get('id')})")
        logger.info(f"File: {file.filename}, content_type: {file.content_type}")

        # Validate file type
        if file.content_type not in ["application/pdf", "text/plain"]:
            logger.warning(f"Rejected file with content_type: {file.content_type}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF and TXT files are supported"
            )
        
        # Extract text content
        content = ""
        if file.content_type == "text/plain":
            logger.info("Processing text file...")
            content_bytes = await file.read()
            content = content_bytes.decode("utf-8")
        elif file.content_type == "application/pdf":
            logger.info("Processing PDF file...")
            # Handle PDF extraction
            try:
                import pdfplumber
                import io
                content_bytes = await file.read()

                # Convert bytes to file-like object
                pdf_file = io.BytesIO(content_bytes)

                with pdfplumber.open(pdf_file) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            content += page_text + "\n"

            except ImportError as ie:
                logger.error(f"PDF library not available: {ie}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="PDF processing not available - pdfplumber not installed"
                )

        logger.info(f"Extracted {len(content)} characters from file")

        if not content.strip():
            logger.warning("No text content extracted from file")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No text content could be extracted from the file"
            )

        # Upload to database
        logger.info(f"Uploading resume to database: {file.filename}")
        user_id = current_user['id']
        request = ResumeUploadRequest(filename=file.filename, content=content)
        success = resume_service.upload_resume(request, user_id=user_id)
        logger.info(f"Resume upload {'succeeded' if success else 'failed'}")
        
        return ResumeResponse(
            resume_name=file.filename,
            success=success,
            message=f"Resume '{file.filename}' uploaded successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File upload failed: {str(e)}"
        )


@app.get("/resumes", response_model=ResumeListResponse)
async def get_resumes(current_user: dict = Depends(get_current_user)):
    """
    Get list of all uploaded resumes for the current user.

    **Requires authentication.**
    """
    try:
        user_id = current_user['id']
        resumes = resume_service.get_resumes(user_id=user_id)
        return ResumeListResponse(resumes=resumes)
    except Exception as e:
        logger.error(f"Failed to get resumes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get resumes: {str(e)}"
        )


@app.get("/resumes/{resume_name}", response_model=ResumeContentResponse)
async def get_resume_content(
    resume_name: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get content of a specific resume owned by the current user.

    **Requires authentication.**
    """
    try:
        user_id = current_user['id']
        content = resume_service.get_resume_content(resume_name, user_id=user_id)
        if content is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Resume '{resume_name}' not found"
            )
        
        return ResumeContentResponse(
            resume_name=resume_name,
            content=content
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get resume content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get resume content: {str(e)}"
        )


@app.put("/resumes/{resume_name}", response_model=ResumeResponse)
async def update_resume(
    resume_name: str,
    request: ResumeUploadRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update content of an existing resume owned by the current user.

    **Requires authentication.**
    """
    try:
        user_id = current_user['id']
        success = resume_service.update_resume(resume_name, request.content, user_id=user_id)
        
        return ResumeResponse(
            resume_name=resume_name,
            success=success,
            message=f"Resume '{resume_name}' updated successfully"
        )
    except Exception as e:
        logger.error(f"Resume update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Resume update failed: {str(e)}"
        )


@app.delete("/resumes/{resume_name}", response_model=ResumeResponse)
async def delete_resume(
    resume_name: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a resume owned by the current user.

    **Requires authentication.**
    """
    try:
        user_id = current_user['id']
        success = resume_service.delete_resume(resume_name, user_id=user_id)
        
        return ResumeResponse(
            resume_name=resume_name,
            success=success,
            message=f"Resume '{resume_name}' deleted successfully"
        )
    except Exception as e:
        logger.error(f"Resume deletion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Resume deletion failed: {str(e)}"
        )


@app.post("/resumes/suggest-job-titles", response_model=JobTitleSuggestionsResponse)
async def suggest_job_titles(
    request: JobTitleSuggestionsRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Analyze resume using AI and suggest 3 optimal job titles.

    This endpoint uses OpenAI to analyze the resume content and suggest
    job titles that:
    - Match the candidate's experience and skills
    - Are high-paying roles (typically $100K+)
    - Are in-demand positions with high job posting volume
    - Use standard job market terminology

    Returns 3 job title suggestions.

    **Requires authentication.**
    """
    try:
        user_id = current_user['id']
        logger.info(f"Generating job title suggestions for: {request.resume_name}")
        success, suggestions, message = ai_service.suggest_job_titles(request.resume_name, user_id=user_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND if "not found" in message.lower() else status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=message
            )

        return JobTitleSuggestionsResponse(
            suggestions=suggestions,
            success=True,
            message=message
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Job title suggestion failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate job title suggestions: {str(e)}"
        )


@app.post("/resumes/optimize", response_model=ResumeOptimizeResponse)
async def optimize_resume(
    request: ResumeOptimizeRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Analyze resume against job postings and provide ATS optimization recommendations.

    This endpoint analyzes the resume against the top similar jobs from your searches
    (if available) or uses AI's general knowledge of job market trends.

    Supports optional filtering to refine which jobs are analyzed:
    - min_similarity: Minimum resume similarity score (0.0-1.0)
    - location: Filter by location (city, state, country)
    - is_remote: Filter by remote status (true for remote, false for on-site, null for all)
    - company: Filter by company name
    - title: Filter by job title
    - job_type: Filter by job type (Full-time, Part-time, Contract, Temporary)
    - min_salary: Filter by minimum salary
    - max_salary: Filter by maximum salary

    Returns:
    - missing_keywords: Keywords present in target jobs but missing from resume
    - keyword_suggestions: Suggestions for improving existing keywords
    - ats_tips: Actionable tips for ATS optimization
    - overall_score: ATS compatibility score (0-100)
    - jobs_analyzed: Number of jobs used for analysis
    - analysis_source: 'job_database' or 'ai_general'

    **Requires authentication.**
    """
    try:
        user_id = current_user['id']

        # Build filters dictionary from request
        filters = {
            "min_similarity": request.min_similarity,
            "location": request.location,
            "is_remote": request.is_remote,
            "company": request.company,
            "title": request.title,
            "job_type": request.job_type,
            "min_salary": request.min_salary,
            "max_salary": request.max_salary
        }

        # Remove None values to avoid applying unnecessary filters
        filters = {k: v for k, v in filters.items() if v is not None}

        logger.info(f"Optimizing resume: {request.resume_name} against top {request.num_jobs} jobs with filters: {filters}")

        result = resume_optimizer_service.optimize_resume(
            resume_name=request.resume_name,
            num_jobs=request.num_jobs,
            user_id=user_id,
            filters=filters if filters else None
        )

        return ResumeOptimizeResponse(
            success=result.get("success", False),
            missing_keywords=result.get("missing_keywords", []),
            keyword_suggestions=result.get("keyword_suggestions", []),
            ats_tips=result.get("ats_tips", []),
            overall_score=result.get("overall_score", 0),
            message=result.get("message", ""),
            jobs_analyzed=result.get("jobs_analyzed", 0),
            analysis_source=result.get("analysis_source", "none")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resume optimization failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to optimize resume: {str(e)}"
        )


@app.post("/resumes/generate-optimized", response_model=GenerateOptimizedResumeResponse)
async def generate_optimized_resume(
    request: GenerateOptimizedResumeRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate an optimized resume in HTML format with highlighted changes.

    This endpoint takes the original resume and optimization results,
    then generates a professionally formatted HTML resume with:
    - All optimization suggestions incorporated
    - Changes highlighted in yellow
    - Professional formatting (white background, Calibri font, narrow margins)
    - Clean dividing lines between sections
    - No orphaned words on lines

    **Requires authentication.**
    """
    try:
        user_id = current_user['id']
        logger.info(f"Generating optimized resume HTML for: {request.resume_name}")

        result = resume_optimizer_service.generate_optimized_resume_html(
            resume_name=request.resume_name,
            optimization_results=request.optimization_results,
            user_id=user_id
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate optimized resume"
            )

        return GenerateOptimizedResumeResponse(
            success=result.get("success", False),
            html_content=result.get("html_content"),
            message=result.get("message", ""),
            original_resume=result.get("original_resume"),
            changes_highlighted=result.get("changes_highlighted", False)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resume generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate optimized resume: {str(e)}"
        )


@app.post("/resumes/download-word")
async def download_optimized_resume_word(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Download the optimized resume as a Word document (.docx).

    This endpoint fetches the user's optimized HTML from the database and converts
    it to a Word document with proper formatting, narrow margins, Calibri font,
    and yellow highlights for changes.

    **Requires authentication.**
    """
    try:
        user_id = current_user['id']
        resume_name = request.get("resume_name")

        if not resume_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing resume_name"
            )

        logger.info(f"Generating Word document for: {resume_name} (user_id: {user_id})")

        # Fetch the optimized HTML from database for this user
        from jobhunter.SQLiteHandler import get_optimized_resume_html
        html_content = get_optimized_resume_html(resume_name, user_id)

        if not html_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No optimized resume found for '{resume_name}'. Please generate the resume first."
            )

        docx_bytes = resume_optimizer_service.generate_optimized_resume_docx(
            resume_name=resume_name,
            html_content=html_content,
            user_id=user_id
        )

        if not docx_bytes:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate Word document"
            )

        # Create a streaming response with the Word document
        import io
        docx_stream = io.BytesIO(docx_bytes)

        # Generate filename
        filename = f"{resume_name.rsplit('.', 1)[0]}_optimized.docx"

        return StreamingResponse(
            docx_stream,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Word document generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Word document: {str(e)}"
        )


# ============================================================================
# Similarity Scoring Endpoints (Protected)
# ============================================================================

@app.post("/similarity/update", response_model=SimilarityUpdateResponse)
async def update_similarity_scores(
    request: SimilarityUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update similarity scores for all jobs against a specific resume owned by the current user.

    This calculates embeddings and similarity scores between the specified
    resume and all jobs in the database.

    **Requires authentication.**
    """
    try:
        user_id = current_user['id']
        success, jobs_updated = job_data_service.update_similarity_scores(request.resume_name, user_id=user_id)

        return SimilarityUpdateResponse(
            success=success,
            message=f"Successfully updated similarity scores for {jobs_updated} jobs" if success else "Failed to update similarity scores",
            jobs_updated=jobs_updated
        )
    except Exception as e:
        logger.error(f"Similarity update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Similarity update failed: {str(e)}"
        )


# ============================================================================
# Job Tracking Endpoints (Protected)
# ============================================================================

@app.post("/jobs/save", response_model=JobTrackingResponse)
async def save_job(
    request: SaveJobRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Save a job to the user's tracking board.

    Adds the job to job_tracking table with 'apply' status.

    **Requires authentication.**
    """
    try:
        user_id = current_user['id']
        success, message = job_tracking_service.save_job(request.job_id, user_id=user_id)

        return JobTrackingResponse(
            success=success,
            message=message
        )
    except Exception as e:
        logger.error(f"Failed to save job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save job: {str(e)}"
        )


@app.post("/jobs/pass", response_model=JobTrackingResponse)
async def pass_job(
    request: PassJobRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Pass/hide a job for the current user.

    Marks the job as hidden (hidden = 1) so it won't appear in main job list.

    **Requires authentication.**
    """
    try:
        user_id = current_user['id']
        success, message = job_tracking_service.pass_job(request.job_id, user_id=user_id)

        return JobTrackingResponse(
            success=success,
            message=message
        )
    except Exception as e:
        logger.error(f"Failed to pass job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pass job: {str(e)}"
        )


@app.get("/jobs/tracked", response_model=TrackedJobsResponse)
async def get_tracked_jobs(current_user: dict = Depends(get_current_user)):
    """
    Get all tracked jobs for the current user organized by status for Kanban board.

    Returns jobs grouped into columns:
    - apply: Jobs to apply to
    - hr_screen: HR phone screen stage
    - round_1: First round interviews
    - round_2: Second round interviews
    - rejected: Rejected or ghosted applications

    **Requires authentication.**
    """
    try:
        user_id = current_user['id']
        jobs_by_status = job_tracking_service.get_tracked_jobs(user_id=user_id)

        return TrackedJobsResponse(
            apply=jobs_by_status.get("apply", []),
            hr_screen=jobs_by_status.get("hr_screen", []),
            round_1=jobs_by_status.get("round_1", []),
            round_2=jobs_by_status.get("round_2", []),
            rejected=jobs_by_status.get("rejected", [])
        )
    except Exception as e:
        logger.error(f"Failed to get tracked jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tracked jobs: {str(e)}"
        )


@app.put("/jobs/tracked/{job_id}/status", response_model=JobTrackingResponse)
async def update_job_status(
    job_id: int,
    request: UpdateJobStatusRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update the status of a tracked job for the current user.

    Moves the job between Kanban columns by updating its status.
    Valid statuses: apply, hr_screen, round_1, round_2, rejected

    **Requires authentication.**
    """
    try:
        user_id = current_user['id']

        # Validate that job_id in path matches request body
        if job_id != request.job_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job ID in path must match job ID in request body"
            )

        success, message = job_tracking_service.update_job_status(request.job_id, request.new_status, user_id=user_id)

        return JobTrackingResponse(
            success=success,
            message=message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update job status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update job status: {str(e)}"
        )


# ============================================================================
# Onboarding Endpoints (Protected)
# ============================================================================

@app.post("/onboarding/process", response_model=OnboardingResponse)
async def process_onboarding(
    request: OnboardingRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Run the complete onboarding workflow for a resume.

    This endpoint orchestrates the full automated onboarding process:
    1. Get AI job title suggestions based on resume
    2. Run smart search with suggested titles
    3. Calculate similarity scores for all jobs
    4. Run resume optimizer for ATS recommendations

    This is a long-running operation (may take 1-2 minutes).

    **Requires authentication.**
    """
    try:
        user_id = current_user['id']
        logger.info(f"Starting onboarding process for resume: {request.resume_name}, user: {user_id}")

        result = onboarding_service.process_onboarding(
            resume_name=request.resume_name,
            user_id=user_id
        )

        logger.info(f"Onboarding completed: {result.message}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Onboarding process failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Onboarding process failed: {str(e)}"
        )


if __name__ == "__main__":
    # Initialize database on startup
    try:
        database_service.initialize_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
    
    # Run the application
    uvicorn.run(
        "jobhunter.backend.api:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )