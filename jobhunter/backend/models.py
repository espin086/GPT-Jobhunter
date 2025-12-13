"""
Pydantic models for FastAPI backend request/response schemas.
"""

from datetime import datetime
from typing import List, Optional, Union
import math
from pydantic import BaseModel, Field, validator, EmailStr


class JobSearchRequest(BaseModel):
    """Request model for job search."""
    job_titles: List[str] = Field(..., description="List of job titles to search for")
    country: str = Field(default="us", description="Country code for job search")
    date_posted: str = Field(default="all", description="Time frame for job posting")
    location: str = Field(default="", description="Location to search for jobs")


class JobSearchResponse(BaseModel):
    """Response model for job search."""
    total_jobs_found: int = Field(..., description="Total number of jobs found")
    message: str = Field(..., description="Status message")
    success: bool = Field(..., description="Whether the search was successful")


class ResumeUploadRequest(BaseModel):
    """Request model for resume upload."""
    filename: str = Field(..., description="Name of the resume file")
    content: str = Field(..., description="Text content of the resume")


class ResumeResponse(BaseModel):
    """Response model for resume operations."""
    resume_name: str = Field(..., description="Name of the resume")
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Status message")


class ResumeListResponse(BaseModel):
    """Response model for listing resumes."""
    resumes: List[str] = Field(..., description="List of resume names")


class ResumeContentResponse(BaseModel):
    """Response model for resume content."""
    resume_name: str = Field(..., description="Name of the resume")
    content: str = Field(..., description="Resume text content")


class JobFilterRequest(BaseModel):
    """Request model for filtering jobs."""
    resume_name: Optional[str] = Field(None, description="Resume name for similarity filtering")
    min_similarity: Optional[float] = Field(0.0, description="Minimum similarity score")
    company: Optional[str] = Field(None, description="Company name filter")
    title: Optional[str] = Field(None, description="Job title filter")
    location: Optional[str] = Field(None, description="Location filter")
    job_type: Optional[str] = Field(None, description="Job type filter")
    is_remote: Optional[bool] = Field(None, description="Remote job filter")
    min_salary: Optional[float] = Field(None, description="Minimum salary filter")
    max_salary: Optional[float] = Field(None, description="Maximum salary filter")
    limit: int = Field(default=100, description="Maximum number of jobs to return")
    offset: int = Field(default=0, description="Number of jobs to skip")


class JobData(BaseModel):
    """Model for job data."""
    id: Optional[int] = None
    primary_key: Optional[str] = None
    date: Optional[str] = None
    resume_similarity: Optional[float] = 0.0
    title: Optional[str] = None
    company: Optional[str] = None
    company_url: Optional[str] = None
    company_type: Optional[str] = None
    job_type: Optional[str] = None
    job_is_remote: Optional[str] = None
    job_apply_link: Optional[str] = None
    job_offer_expiration_date: Optional[str] = None
    salary_low: Optional[float] = None
    salary_high: Optional[float] = None
    salary_currency: Optional[str] = None
    salary_period: Optional[str] = None
    job_benefits: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    apply_options: Optional[str] = None
    required_skills: Optional[str] = None
    required_experience: Optional[str] = None
    required_education: Optional[str] = None
    description: Optional[str] = None
    highlights: Optional[str] = None

    @validator('resume_similarity', pre=True)
    def validate_resume_similarity(cls, v):
        """Convert NaN/Infinity values to 0.0 for resume_similarity."""
        if v is None:
            return 0.0
        if isinstance(v, (int, float)):
            if math.isnan(v) or math.isinf(v):
                return 0.0
        return v

    @validator('salary_low', 'salary_high', pre=True)
    def validate_salary_fields(cls, v):
        """Convert NaN/Infinity values to None for salary fields."""
        if v is None:
            return None
        if isinstance(v, (int, float)):
            if math.isnan(v) or math.isinf(v):
                return None
        return v


class JobListResponse(BaseModel):
    """Response model for job listings."""
    jobs: List[JobData] = Field(..., description="List of jobs")
    total_count: int = Field(..., description="Total number of jobs matching criteria")
    limit: int = Field(..., description="Applied limit")
    offset: int = Field(..., description="Applied offset")


class SimilarityUpdateRequest(BaseModel):
    """Request model for updating similarity scores."""
    resume_name: str = Field(..., description="Resume name to calculate similarities against")


class SimilarityUpdateResponse(BaseModel):
    """Response model for similarity updates."""
    success: bool = Field(..., description="Whether the update was successful")
    message: str = Field(..., description="Status message")
    jobs_updated: int = Field(..., description="Number of jobs updated")


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(..., description="Current timestamp")
    version: str = Field(..., description="API version")


class JobTitleSuggestionsRequest(BaseModel):
    """Request model for job title suggestions."""
    resume_name: str = Field(..., description="Name of the resume to analyze")


class JobTitleSuggestionsResponse(BaseModel):
    """Response model for job title suggestions."""
    suggestions: List[str] = Field(..., description="List of 3 suggested job titles")
    success: bool = Field(..., description="Whether the suggestion generation was successful")
    message: str = Field(..., description="Status message")


class SaveJobRequest(BaseModel):
    """Request model for saving a job to tracking."""
    job_id: int = Field(..., description="ID of the job to save")


class PassJobRequest(BaseModel):
    """Request model for passing/hiding a job."""
    job_id: int = Field(..., description="ID of the job to pass")


class JobTrackingResponse(BaseModel):
    """Response model for job tracking operations."""
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Status message")


class TrackedJobData(BaseModel):
    """Model for tracked job data with tracking info."""
    # Job details (inherited from JobData)
    id: Optional[int] = None
    primary_key: Optional[str] = None
    date: Optional[str] = None
    resume_similarity: Optional[float] = 0.0
    title: Optional[str] = None
    company: Optional[str] = None
    company_url: Optional[str] = None
    company_type: Optional[str] = None
    job_type: Optional[str] = None
    job_is_remote: Optional[str] = None
    job_apply_link: Optional[str] = None
    job_offer_expiration_date: Optional[str] = None
    salary_low: Optional[float] = None
    salary_high: Optional[float] = None
    salary_currency: Optional[str] = None
    salary_period: Optional[str] = None
    job_benefits: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    apply_options: Optional[str] = None
    required_skills: Optional[str] = None
    required_experience: Optional[str] = None
    required_education: Optional[str] = None
    description: Optional[str] = None
    highlights: Optional[str] = None
    # Tracking fields
    tracking_id: Optional[int] = None
    job_id: Optional[int] = None  # The actual job ID from jobs_new table
    status: Optional[str] = None
    date_added: Optional[str] = None
    date_updated: Optional[str] = None
    notes: Optional[str] = None


class TrackedJobsResponse(BaseModel):
    """Response model for tracked jobs organized by status."""
    apply: List[TrackedJobData] = Field(default=[], description="Jobs in 'Apply' column")
    hr_screen: List[TrackedJobData] = Field(default=[], description="Jobs in 'HR Phone Screen' column")
    round_1: List[TrackedJobData] = Field(default=[], description="Jobs in '1st Round' column")
    round_2: List[TrackedJobData] = Field(default=[], description="Jobs in '2nd Round' column")
    rejected: List[TrackedJobData] = Field(default=[], description="Jobs in 'Rejected/Ghosted' column")


class UpdateJobStatusRequest(BaseModel):
    """Request model for updating job status."""
    job_id: int = Field(..., description="ID of the job to update")
    new_status: str = Field(..., description="New status (apply, hr_screen, round_1, round_2, rejected)")


# Resume Optimizer Models
class ResumeOptimizeRequest(BaseModel):
    """Request model for resume optimization analysis."""
    resume_name: str = Field(..., description="Name of the resume to analyze")
    num_jobs: Optional[int] = Field(default=20, description="Number of top similar jobs to analyze (default: 20)")


class KeywordSuggestion(BaseModel):
    """Model for a keyword synonym suggestion."""
    current: str = Field(..., description="Current keyword in resume")
    suggested: str = Field(..., description="Suggested alternative or addition")
    reason: str = Field(..., description="Reason for the suggestion")


class ResumeOptimizeResponse(BaseModel):
    """Response model for resume optimization analysis."""
    success: bool = Field(..., description="Whether the analysis was successful")
    missing_keywords: List[str] = Field(default=[], description="Keywords present in jobs but missing from resume")
    keyword_suggestions: List[KeywordSuggestion] = Field(default=[], description="Suggestions for keyword improvements")
    ats_tips: List[str] = Field(default=[], description="ATS optimization tips")
    overall_score: int = Field(default=0, description="Overall ATS compatibility score (0-100)")
    message: str = Field(..., description="Status message or explanation")
    jobs_analyzed: int = Field(default=0, description="Number of jobs analyzed")
    analysis_source: str = Field(default="ai_general", description="Source of analysis: 'job_database' or 'ai_general'")


# ============================================================================
# Authentication Models
# ============================================================================

class UserRegisterRequest(BaseModel):
    """Request model for user registration."""
    email: EmailStr = Field(..., description="User's email address")
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    password: str = Field(..., min_length=8, description="Password (minimum 8 characters)")
    full_name: Optional[str] = Field(None, description="User's full name")


class UserLoginRequest(BaseModel):
    """Request model for user login."""
    username_or_email: str = Field(..., description="Username or email address")
    password: str = Field(..., description="User's password")


class UserResponse(BaseModel):
    """Response model for user information."""
    id: int = Field(..., description="User ID")
    email: str = Field(..., description="User's email")
    username: str = Field(..., description="Username")
    full_name: Optional[str] = Field(None, description="Full name")
    is_active: bool = Field(..., description="Whether the account is active")
    created_at: datetime = Field(..., description="Account creation timestamp")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")


class TokenResponse(BaseModel):
    """Response model for authentication token."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user: UserResponse = Field(..., description="Authenticated user information")


class PasswordResetRequest(BaseModel):
    """Request model for password reset request."""
    email: EmailStr = Field(..., description="Email address of the account")


class PasswordResetConfirm(BaseModel):
    """Request model for confirming password reset."""
    token: str = Field(..., description="Password reset token from email")
    new_password: str = Field(..., min_length=8, description="New password (minimum 8 characters)")


class LogoutResponse(BaseModel):
    """Response model for logout."""
    success: bool = Field(..., description="Whether logout was successful")
    message: str = Field(..., description="Status message")