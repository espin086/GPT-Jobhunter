"""
FastAPI backend application for GPT Job Hunter.
"""

import logging
from datetime import datetime
from typing import List, Optional
import os

from fastapi import FastAPI, HTTPException, status, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from jobhunter.backend.models import (
    JobSearchRequest, JobSearchResponse,
    ResumeUploadRequest, ResumeResponse, ResumeListResponse, ResumeContentResponse,
    JobFilterRequest, JobListResponse,
    SimilarityUpdateRequest, SimilarityUpdateResponse,
    ErrorResponse, HealthResponse
)
from jobhunter.backend.services import (
    JobSearchService, ResumeService, JobDataService, DatabaseService
)

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


# Startup event handler
@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup."""
    try:
        database_service.initialize_database()
        logger.info("Database initialized successfully on startup")
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


# Resume management endpoints
@app.post("/resumes/upload", response_model=ResumeResponse)
async def upload_resume(request: ResumeUploadRequest):
    """
    Upload a resume to the database.
    
    The resume content should be provided as plain text.
    """
    try:
        success = resume_service.upload_resume(request)
        
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
async def upload_resume_file(file: UploadFile = File(...)):
    """
    Upload a resume file (PDF or TXT).
    
    Accepts PDF and TXT files and extracts text content.
    """
    try:
        # Validate file type
        if file.content_type not in ["application/pdf", "text/plain"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF and TXT files are supported"
            )
        
        # Extract text content
        content = ""
        if file.content_type == "text/plain":
            content_bytes = await file.read()
            content = content_bytes.decode("utf-8")
        elif file.content_type == "application/pdf":
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
                            
            except ImportError:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="PDF processing not available - pdfplumber not installed"
                )
        
        if not content.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No text content could be extracted from the file"
            )
        
        # Upload to database
        request = ResumeUploadRequest(filename=file.filename, content=content)
        success = resume_service.upload_resume(request)
        
        return ResumeResponse(
            resume_name=file.filename,
            success=success,
            message=f"Resume '{file.filename}' uploaded successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File upload failed: {str(e)}"
        )


@app.get("/resumes", response_model=ResumeListResponse)
async def get_resumes():
    """Get list of all uploaded resumes."""
    try:
        resumes = resume_service.get_resumes()
        return ResumeListResponse(resumes=resumes)
    except Exception as e:
        logger.error(f"Failed to get resumes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get resumes: {str(e)}"
        )


@app.get("/resumes/{resume_name}", response_model=ResumeContentResponse)
async def get_resume_content(resume_name: str):
    """Get content of a specific resume."""
    try:
        content = resume_service.get_resume_content(resume_name)
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
async def update_resume(resume_name: str, request: ResumeUploadRequest):
    """Update content of an existing resume."""
    try:
        success = resume_service.update_resume(resume_name, request.content)
        
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
async def delete_resume(resume_name: str):
    """Delete a resume."""
    try:
        success = resume_service.delete_resume(resume_name)
        
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


# Similarity scoring endpoints
@app.post("/similarity/update", response_model=SimilarityUpdateResponse)
async def update_similarity_scores(request: SimilarityUpdateRequest):
    """
    Update similarity scores for all jobs against a specific resume.
    
    This calculates embeddings and similarity scores between the specified
    resume and all jobs in the database.
    """
    try:
        success, jobs_updated = job_data_service.update_similarity_scores(request.resume_name)
        
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