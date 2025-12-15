"""
Service layer for FastAPI backend that wraps existing business logic.
"""

import logging
import sqlite3
from typing import List, Optional, Tuple, Dict
import pandas as pd
from pathlib import Path
import os

from jobhunter import config
from jobhunter.extract import extract
from jobhunter.dataTransformer import DataTransformer
from jobhunter.load import load
from jobhunter.FileHandler import FileHandler
from jobhunter.SQLiteHandler import (
    save_text_to_db,
    fetch_resumes_from_db,
    get_resume_text,
    update_resume_in_db,
    delete_resume_in_db,
    update_similarity_in_db,
    check_and_upload_to_db
)
from jobhunter.backend.models import (
    JobData,
    JobFilterRequest,
    JobSearchRequest,
    ResumeUploadRequest,
    KeywordSuggestion,
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    TokenResponse,
    OnboardingStepResult,
    OnboardingResponse
)

logger = logging.getLogger(__name__)


class JobSearchService:
    """Service for job search operations."""
    
    def __init__(self):
        self.file_handler = FileHandler(
            raw_path=config.RAW_DATA_PATH, 
            processed_path=config.PROCESSED_DATA_PATH
        )
    
    def search_jobs(self, request: JobSearchRequest) -> int:
        """
        Search for jobs and return total count found.

        Args:
            request: Job search request parameters

        Returns:
            Total number of jobs found
        """
        try:
            logger.info(f"Starting job search for: {request.job_titles}")

            # Run the extract pipeline
            total_jobs = extract(
                POSITIONS=request.job_titles,
                country=request.country,
                date_posted=request.date_posted,
                location=request.location
            )

            if total_jobs > 0:
                # Transform the data
                logger.info("Transforming job data...")
                transformer = DataTransformer(
                    raw_path=str(config.RAW_DATA_PATH),
                    processed_path=str(config.PROCESSED_DATA_PATH),
                    resume_path=str(config.RESUME_PATH),
                    data=self.file_handler.import_job_data_from_dir(dirpath=config.RAW_DATA_PATH),
                )
                transformer.transform()

                # Load to database
                logger.info("Loading job data to database...")
                load()

                # Auto-calculate similarity scores if a resume exists
                try:
                    resumes = fetch_resumes_from_db()
                    if resumes:
                        # Use the first resume for similarity calculation
                        resume_name = resumes[0]
                        logger.info(f"Auto-calculating similarity scores using resume: {resume_name}")
                        update_similarity_in_db(resume_name)
                        logger.info("Similarity scores calculated successfully")
                except Exception as similarity_error:
                    logger.warning(f"Could not auto-calculate similarity scores: {similarity_error}")
                    # Don't fail the job search if similarity calculation fails

                logger.info(f"Job search completed successfully. Found {total_jobs} jobs.")

            return total_jobs

        except Exception as e:
            logger.error(f"Error in job search: {e}", exc_info=True)
            raise


class ResumeService:
    """Service for resume management operations."""
    
    def upload_resume(self, request: ResumeUploadRequest, user_id: int) -> bool:
        """
        Upload a resume to the database.

        Args:
            request: Resume upload request
            user_id: ID of the user uploading the resume

        Returns:
            True if successful
        """
        try:
            save_text_to_db(request.filename, request.content, user_id)
            logger.info(f"Resume '{request.filename}' uploaded successfully for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error uploading resume: {e}", exc_info=True)
            raise
    
    def get_resumes(self, user_id: int) -> List[str]:
        """
        Get list of resumes for a specific user.

        Args:
            user_id: ID of the user whose resumes to fetch

        Returns:
            List of resume names owned by the user
        """
        try:
            return fetch_resumes_from_db(user_id)
        except Exception as e:
            logger.error(f"Error fetching resumes: {e}", exc_info=True)
            raise
    
    def get_resume_content(self, resume_name: str, user_id: int) -> Optional[str]:
        """
        Get resume content by name with user ownership verification.

        Args:
            resume_name: Name of the resume
            user_id: ID of the user who owns the resume

        Returns:
            Resume content or None if not found or not owned by user
        """
        try:
            return get_resume_text(resume_name, user_id)
        except Exception as e:
            logger.error(f"Error fetching resume content: {e}", exc_info=True)
            raise
    
    def update_resume(self, resume_name: str, content: str, user_id: int) -> bool:
        """
        Update resume content with user ownership verification.

        Args:
            resume_name: Name of the resume
            content: New content
            user_id: ID of the user who owns the resume

        Returns:
            True if successful, False if resume not found or not owned by user
        """
        try:
            result = update_resume_in_db(resume_name, content, user_id)
            if result:
                logger.info(f"Resume '{resume_name}' updated successfully for user {user_id}")
            else:
                logger.warning(f"Resume '{resume_name}' not found or not owned by user {user_id}")
            return result
        except Exception as e:
            logger.error(f"Error updating resume: {e}", exc_info=True)
            raise
    
    def delete_resume(self, resume_name: str, user_id: int) -> bool:
        """
        Delete a resume with user ownership verification.

        Args:
            resume_name: Name of the resume
            user_id: ID of the user who owns the resume

        Returns:
            True if successful, False if resume not found or not owned by user
        """
        try:
            result = delete_resume_in_db(resume_name, user_id)
            if result:
                logger.info(f"Resume '{resume_name}' deleted successfully for user {user_id}")
            else:
                logger.warning(f"Resume '{resume_name}' not found or not owned by user {user_id}")
            return result
        except Exception as e:
            logger.error(f"Error deleting resume: {e}", exc_info=True)
            raise


class JobDataService:
    """Service for job data operations."""
    
    def get_jobs(self, filter_request: JobFilterRequest) -> Tuple[List[JobData], int]:
        """
        Get filtered jobs from database.
        
        Args:
            filter_request: Job filter parameters
            
        Returns:
            Tuple of (job list, total count)
        """
        try:
            conn = sqlite3.connect(config.DATABASE)
            
            # Build the base query - exclude hidden jobs and already-tracked jobs
            base_query = """
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
                WHERE (hidden IS NULL OR hidden = 0)
                AND id NOT IN (SELECT job_id FROM job_tracking)
            """
            
            params = []
            
            # Add filters
            if filter_request.min_similarity is not None:
                base_query += " AND resume_similarity >= ?"
                params.append(filter_request.min_similarity)
            
            if filter_request.company:
                base_query += " AND company LIKE ?"
                params.append(f"%{filter_request.company}%")
            
            if filter_request.title:
                base_query += " AND title LIKE ?"
                params.append(f"%{filter_request.title}%")
            
            if filter_request.location:
                base_query += " AND (city LIKE ? OR state LIKE ? OR country LIKE ?)"
                params.extend([f"%{filter_request.location}%"] * 3)
            
            if filter_request.job_type:
                base_query += " AND job_type LIKE ?"
                params.append(f"%{filter_request.job_type}%")
            
            if filter_request.is_remote is not None:
                remote_value = "Yes" if filter_request.is_remote else "No"
                base_query += " AND job_is_remote = ?"
                params.append(remote_value)
            
            if filter_request.min_salary is not None:
                base_query += " AND salary_low >= ?"
                params.append(filter_request.min_salary)
            
            if filter_request.max_salary is not None:
                base_query += " AND salary_high <= ?"
                params.append(filter_request.max_salary)
            
            # Get total count - build a proper count query
            # Extract the WHERE clause from base_query
            where_clause_start = base_query.find("WHERE")
            if where_clause_start != -1:
                where_clause = base_query[where_clause_start:]
                # Remove any ORDER BY or LIMIT if present (shouldn't be at this point though)
                where_clause = where_clause.split("ORDER BY")[0].split("LIMIT")[0].strip()
                count_query = f"SELECT COUNT(*) FROM jobs_new {where_clause}"
            else:
                count_query = "SELECT COUNT(*) FROM jobs_new"

            cursor = conn.cursor()
            cursor.execute(count_query, params)
            result = cursor.fetchone()
            total_count = result[0] if result else 0
            
            # Add ordering and pagination
            base_query += " ORDER BY resume_similarity DESC, date DESC"
            base_query += " LIMIT ? OFFSET ?"
            params.extend([filter_request.limit, filter_request.offset])
            
            # Execute main query
            df = pd.read_sql(base_query, conn, params=params)
            conn.close()
            
            # Clean data: handle NaN and Infinity values
            # Replace NaN and Infinity values in numeric columns
            numeric_columns = ['resume_similarity', 'salary_low', 'salary_high']
            for col in numeric_columns:
                if col in df.columns:
                    # Replace NaN and Infinity with None for salary fields
                    if col in ['salary_low', 'salary_high']:
                        df[col] = df[col].replace([float('inf'), float('-inf')], None)
                        df[col] = df[col].where(pd.notna(df[col]), None)
                    # Replace NaN and Infinity with 0 for resume_similarity
                    elif col == 'resume_similarity':
                        df[col] = df[col].replace([float('inf'), float('-inf')], 0.0)
                        df[col] = df[col].fillna(0.0)
            
            # Convert to JobData models
            jobs = []
            for _, row in df.iterrows():
                job_data = JobData(**row.to_dict())
                jobs.append(job_data)
            
            return jobs, total_count
            
        except Exception as e:
            logger.error(f"Error fetching jobs: {e}", exc_info=True)
            raise
    
    def update_similarity_scores(self, resume_name: str, user_id: int = None) -> Tuple[bool, int]:
        """
        Update similarity scores for all jobs against a resume.

        Args:
            resume_name: Name of the resume to calculate similarities against
            user_id: ID of the user who owns the resume

        Returns:
            Tuple of (success, number of jobs updated)
        """
        try:
            success = update_similarity_in_db(resume_name, user_id)
            
            if success:
                # Get count of jobs that were updated
                conn = sqlite3.connect(config.DATABASE)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM jobs_new WHERE resume_similarity > 0")
                count = cursor.fetchone()[0]
                conn.close()
                
                logger.info(f"Successfully updated similarity scores for {count} jobs")
                return True, count
            else:
                return False, 0
                
        except Exception as e:
            logger.error(f"Error updating similarity scores: {e}", exc_info=True)
            raise


class DatabaseService:
    """Service for database operations."""
    
    def initialize_database(self) -> bool:
        """
        Initialize the database with required tables.
        
        Returns:
            True if successful
        """
        try:
            # Use the existing initialization function
            conn = sqlite3.connect(config.DATABASE)
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
                    resume_name TEXT NOT NULL,
                    resume_text TEXT,
                    user_id INTEGER NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    UNIQUE(user_id, resume_name)
                )
            ''')

            # Create job_tracking table for Kanban board with user isolation
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS job_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'apply',
                    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    date_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT,
                    user_id INTEGER NOT NULL,
                    FOREIGN KEY (job_id) REFERENCES jobs_new(id),
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    UNIQUE(user_id, job_id)
                )
            ''')

            # Add hidden column to jobs_new if it doesn't exist
            try:
                cursor.execute("ALTER TABLE jobs_new ADD COLUMN hidden INTEGER DEFAULT 0")
            except:
                pass  # Column already exists

            conn.commit()
            conn.close()
            logger.info("Database initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}", exc_info=True)
            raise
    
    def get_database_stats(self) -> dict:
        """
        Get database statistics.
        
        Returns:
            Dictionary with database stats
        """
        try:
            conn = sqlite3.connect(config.DATABASE)
            cursor = conn.cursor()
            
            # Get job count
            cursor.execute("SELECT COUNT(*) FROM jobs_new")
            job_count = cursor.fetchone()[0]
            
            # Get resume count
            cursor.execute("SELECT COUNT(*) FROM resumes")
            resume_count = cursor.fetchone()[0]
            
            # Get jobs with embeddings count
            cursor.execute("SELECT COUNT(*) FROM jobs_new WHERE embeddings IS NOT NULL")
            jobs_with_embeddings = cursor.fetchone()[0]
            
            # Get jobs with similarity scores count
            cursor.execute("SELECT COUNT(*) FROM jobs_new WHERE resume_similarity > 0")
            jobs_with_similarity = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                "total_jobs": job_count,
                "total_resumes": resume_count,
                "jobs_with_embeddings": jobs_with_embeddings,
                "jobs_with_similarity_scores": jobs_with_similarity,
                "database_path": str(Path(config.DATABASE).absolute())
            }

        except Exception as e:
            logger.error(f"Error getting database stats: {e}", exc_info=True)
            raise


class AIService:
    """Service for AI-powered features."""

    def suggest_job_titles(self, resume_name: str, user_id: int) -> Tuple[bool, List[str], str]:
        """
        Analyze resume and suggest 3 optimal job titles using OpenAI.

        Args:
            resume_name: Name of the resume to analyze
            user_id: ID of the user who owns the resume

        Returns:
            Tuple of (success, list of job titles, message)
        """
        try:
            # Get resume text with user verification
            resume_text = get_resume_text(resume_name, user_id)
            if not resume_text:
                return False, [], f"Resume '{resume_name}' not found"

            # Check if OpenAI API key is available
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.warning("OpenAI API key not found, cannot generate suggestions")
                return False, [], "OpenAI API key not configured"

            # Use OpenAI to analyze resume and suggest job titles
            from openai import OpenAI
            client = OpenAI(api_key=api_key)

            prompt = f"""Analyze this resume and suggest exactly 3 job titles that:
1. Match the candidate's experience and skills
2. Are high-paying roles (typically $100K+)
3. Are in-demand positions with high job posting volume
4. Use standard job market terminology (e.g., "Senior Software Engineer" not "Code Ninja")

Resume:
{resume_text[:3000]}

Return ONLY the 3 job titles, one per line, with no numbering, bullets, or explanations.
Example format:
Senior Software Engineer
Machine Learning Engineer
Technical Lead"""

            logger.info(f"Requesting job title suggestions for resume: {resume_name}")

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert career advisor and recruiter who understands job market trends and compensation."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=150
            )

            suggestions_text = response.choices[0].message.content.strip()
            suggestions = [title.strip() for title in suggestions_text.split('\n') if title.strip()]

            # Ensure we have exactly 3 suggestions
            if len(suggestions) < 3:
                logger.warning(f"Only got {len(suggestions)} suggestions, padding with defaults")
                defaults = ["Senior Software Engineer", "Data Scientist", "Product Manager"]
                suggestions.extend(defaults[len(suggestions):3])
            suggestions = suggestions[:3]

            logger.info(f"Generated suggestions: {suggestions}")
            return True, suggestions, f"Generated {len(suggestions)} job title suggestions"

        except Exception as e:
            logger.error(f"Error generating job title suggestions: {e}", exc_info=True)
            return False, [], f"Failed to generate suggestions: {str(e)}"


class JobTrackingService:
    """Service for job application tracking (Kanban board)."""

    def save_job(self, job_id: int, user_id: int) -> Tuple[bool, str]:
        """
        Save a job to tracking board for a specific user (starts in 'apply' status).

        Args:
            job_id: ID of the job to save
            user_id: ID of the user saving the job

        Returns:
            Tuple of (success, message)
        """
        try:
            conn = sqlite3.connect(config.DATABASE)
            cursor = conn.cursor()

            # Check if job exists
            cursor.execute("SELECT id FROM jobs_new WHERE id = ?", (job_id,))
            if not cursor.fetchone():
                conn.close()
                return False, "Job not found"

            # Insert or ignore if already tracked by this user
            cursor.execute('''
                INSERT OR IGNORE INTO job_tracking (job_id, user_id, status)
                VALUES (?, ?, 'apply')
            ''', (job_id, user_id))

            conn.commit()
            conn.close()

            logger.info(f"Job {job_id} saved to tracking board for user {user_id}")
            return True, "Job saved successfully"

        except Exception as e:
            logger.error(f"Error saving job: {e}", exc_info=True)
            return False, f"Failed to save job: {str(e)}"

    def pass_job(self, job_id: int, user_id: int) -> Tuple[bool, str]:
        """
        Mark a job as hidden/passed.

        Note: This marks the job as hidden in the shared jobs_new table.
        In the future, this could be made user-specific by creating a separate
        hidden_jobs table with user_id.

        Args:
            job_id: ID of the job to hide
            user_id: ID of the user (for logging purposes)

        Returns:
            Tuple of (success, message)
        """
        try:
            conn = sqlite3.connect(config.DATABASE)
            cursor = conn.cursor()

            # Update hidden flag (affects all users currently)
            cursor.execute("UPDATE jobs_new SET hidden = 1 WHERE id = ?", (job_id,))

            conn.commit()
            conn.close()

            logger.info(f"Job {job_id} marked as hidden by user {user_id}")
            return True, "Job marked as not interested"

        except Exception as e:
            logger.error(f"Error marking job as hidden: {e}", exc_info=True)
            return False, f"Failed to hide job: {str(e)}"

    def get_tracked_jobs(self, user_id: int) -> Dict[str, List[Dict]]:
        """
        Get all tracked jobs for a specific user organized by status (for Kanban board).

        Args:
            user_id: ID of the user whose tracked jobs to fetch

        Returns:
            Dictionary with status as keys and lists of jobs as values
        """
        try:
            conn = sqlite3.connect(config.DATABASE)

            query = '''
                SELECT
                    jt.id as tracking_id,
                    jt.job_id,
                    jt.status,
                    jt.date_added,
                    jt.date_updated,
                    jt.notes,
                    j.title,
                    j.company,
                    j.city,
                    j.state,
                    j.job_is_remote,
                    j.salary_low,
                    j.salary_high,
                    j.job_apply_link,
                    j.resume_similarity,
                    j.date as posted_date
                FROM job_tracking jt
                JOIN jobs_new j ON jt.job_id = j.id
                WHERE jt.user_id = ?
                ORDER BY jt.date_updated DESC
            '''

            df = pd.read_sql(query, conn, params=(user_id,))
            conn.close()

            # Replace NaN/Infinity with None for JSON serialization
            import math
            df = df.replace([float('inf'), float('-inf')], None)
            df = df.where(pd.notna(df), None)

            # Organize by status
            statuses = ['apply', 'hr_screen', 'round_1', 'round_2', 'rejected']
            result = {status: [] for status in statuses}

            for _, row in df.iterrows():
                job_dict = row.to_dict()

                # Double-check: replace any remaining NaN values with None
                for key, value in job_dict.items():
                    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                        job_dict[key] = None

                status = job_dict.get('status', 'apply')
                if status in result:
                    result[status].append(job_dict)

            return result

        except Exception as e:
            logger.error(f"Error getting tracked jobs: {e}", exc_info=True)
            return {status: [] for status in ['apply', 'hr_screen', 'round_1', 'round_2', 'rejected']}

    def update_job_status(self, job_id: int, new_status: str, user_id: int) -> Tuple[bool, str]:
        """
        Update the status of a tracked job with user ownership verification (for moving between Kanban columns).

        Args:
            job_id: ID of the job
            new_status: New status (apply, hr_screen, round_1, round_2, rejected)
            user_id: ID of the user who owns this tracking entry

        Returns:
            Tuple of (success, message)
        """
        try:
            valid_statuses = ['apply', 'hr_screen', 'round_1', 'round_2', 'rejected']
            if new_status not in valid_statuses:
                return False, f"Invalid status. Must be one of: {', '.join(valid_statuses)}"

            conn = sqlite3.connect(config.DATABASE)
            cursor = conn.cursor()

            # Update status and timestamp with user ownership check
            cursor.execute('''
                UPDATE job_tracking
                SET status = ?, date_updated = CURRENT_TIMESTAMP
                WHERE job_id = ? AND user_id = ?
            ''', (new_status, job_id, user_id))

            if cursor.rowcount == 0:
                conn.close()
                return False, "Job not found in tracking or not owned by user"

            conn.commit()
            conn.close()

            logger.info(f"Job {job_id} status updated to {new_status} for user {user_id}")
            return True, f"Job moved to {new_status}"

        except Exception as e:
            logger.error(f"Error updating job status: {e}", exc_info=True)
            return False, f"Failed to update status: {str(e)}"

    def remove_from_tracking(self, job_id: int, user_id: int) -> Tuple[bool, str]:
        """
        Remove a job from tracking board with user ownership verification.

        Args:
            job_id: ID of the job to remove
            user_id: ID of the user who owns this tracking entry

        Returns:
            Tuple of (success, message)
        """
        try:
            conn = sqlite3.connect(config.DATABASE)
            cursor = conn.cursor()

            cursor.execute("DELETE FROM job_tracking WHERE job_id = ? AND user_id = ?", (job_id, user_id))

            if cursor.rowcount == 0:
                conn.close()
                return False, "Job not found in tracking or not owned by user"

            conn.commit()
            conn.close()

            logger.info(f"Job {job_id} removed from tracking for user {user_id}")
            return True, "Job removed from tracking"

        except Exception as e:
            logger.error(f"Error removing job from tracking: {e}", exc_info=True)
            return False, f"Failed to remove job: {str(e)}"


class ResumeOptimizerService:
    """Service for resume optimization and ATS keyword analysis."""

    def get_top_similar_jobs(self, num_jobs: int = 20) -> List[Dict]:
        """
        Get top N jobs by similarity score.

        Args:
            num_jobs: Number of jobs to retrieve

        Returns:
            List of job dictionaries with descriptions and required skills
        """
        try:
            conn = sqlite3.connect(config.DATABASE)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT title, company, resume_similarity, description, required_skills
                FROM jobs_new
                WHERE resume_similarity > 0
                AND description IS NOT NULL
                AND description != ''
                ORDER BY resume_similarity DESC
                LIMIT ?
            ''', (num_jobs,))

            jobs = cursor.fetchall()
            conn.close()

            return [
                {
                    "title": job[0],
                    "company": job[1],
                    "similarity": job[2],
                    "description": job[3] or "",
                    "required_skills": job[4] or ""
                }
                for job in jobs
            ]

        except Exception as e:
            logger.error(f"Error fetching top similar jobs: {e}", exc_info=True)
            return []

    def get_job_count(self) -> int:
        """Get total count of jobs with similarity scores."""
        try:
            conn = sqlite3.connect(config.DATABASE)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM jobs_new WHERE resume_similarity > 0")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            logger.error(f"Error getting job count: {e}", exc_info=True)
            return 0

    def optimize_resume(self, resume_name: str, num_jobs: int = 20, user_id: int = None) -> Dict:
        """
        Analyze resume against top similar jobs and provide optimization suggestions.

        If jobs exist in the database, analyzes against those jobs.
        If no jobs exist, uses AI's general knowledge for optimization.

        Args:
            resume_name: Name of the resume to analyze
            num_jobs: Number of top similar jobs to analyze
            user_id: ID of the user who owns the resume

        Returns:
            Dictionary with optimization results
        """
        try:
            # Get resume text with user verification
            resume_text = get_resume_text(resume_name, user_id)
            if not resume_text:
                return {
                    "success": False,
                    "missing_keywords": [],
                    "keyword_suggestions": [],
                    "ats_tips": [],
                    "overall_score": 0,
                    "message": f"Resume '{resume_name}' not found",
                    "jobs_analyzed": 0,
                    "analysis_source": "none"
                }

            # Check if OpenAI API key is available
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.warning("OpenAI API key not found, cannot perform optimization")
                return {
                    "success": False,
                    "missing_keywords": [],
                    "keyword_suggestions": [],
                    "ats_tips": [],
                    "overall_score": 0,
                    "message": "OpenAI API key not configured",
                    "jobs_analyzed": 0,
                    "analysis_source": "none"
                }

            # Get top similar jobs
            top_jobs = self.get_top_similar_jobs(num_jobs)
            jobs_analyzed = len(top_jobs)

            # Determine analysis source
            if jobs_analyzed > 0:
                analysis_source = "job_database"
                # Build job context from database
                job_context = self._build_job_context(top_jobs)
                prompt = self._build_job_based_prompt(resume_text, job_context, jobs_analyzed)
            else:
                analysis_source = "ai_general"
                prompt = self._build_general_prompt(resume_text)

            # Call OpenAI for analysis
            result = self._call_openai_for_analysis(prompt, api_key)

            if result:
                result["success"] = True
                result["jobs_analyzed"] = jobs_analyzed
                result["analysis_source"] = analysis_source
                result["message"] = (
                    f"Analyzed resume against {jobs_analyzed} similar jobs from your search"
                    if jobs_analyzed > 0
                    else "Analyzed resume using AI's general knowledge of job market trends"
                )
                return result
            else:
                return {
                    "success": False,
                    "missing_keywords": [],
                    "keyword_suggestions": [],
                    "ats_tips": [],
                    "overall_score": 0,
                    "message": "Failed to generate optimization suggestions",
                    "jobs_analyzed": jobs_analyzed,
                    "analysis_source": analysis_source
                }

        except Exception as e:
            logger.error(f"Error optimizing resume: {e}", exc_info=True)
            return {
                "success": False,
                "missing_keywords": [],
                "keyword_suggestions": [],
                "ats_tips": [],
                "overall_score": 0,
                "message": f"Error during optimization: {str(e)}",
                "jobs_analyzed": 0,
                "analysis_source": "none"
            }

    def _build_job_context(self, jobs: List[Dict]) -> str:
        """Build a context string from job descriptions and skills."""
        context_parts = []
        for i, job in enumerate(jobs[:10], 1):  # Limit to top 10 for context
            context_parts.append(f"""
Job {i}: {job['title']} at {job['company']} (Match: {int(job['similarity'] * 100)}%)
Required Skills: {job['required_skills']}
Description excerpt: {job['description'][:500]}...
""")
        return "\n".join(context_parts)

    def _build_job_based_prompt(self, resume_text: str, job_context: str, num_jobs: int) -> str:
        """Build the prompt for job-based analysis."""
        return f"""You are an expert ATS (Applicant Tracking System) optimization specialist and career coach.

Analyze this resume against the following {num_jobs} job postings that the candidate is most likely to apply to.

RESUME:
{resume_text[:4000]}

TARGET JOBS:
{job_context}

Based on this analysis, provide optimization recommendations in the following JSON format:
{{
    "missing_keywords": ["keyword1", "keyword2", ...],
    "keyword_suggestions": [
        {{"current": "word in resume", "suggested": "better alternative", "reason": "explanation"}},
        ...
    ],
    "ats_tips": ["tip1", "tip2", ...],
    "overall_score": 75
}}

Guidelines:
1. MISSING_KEYWORDS: List 8-12 important technical keywords/skills that appear frequently in the target jobs but are completely missing from the resume. Focus on:
   - Technical skills (programming languages, frameworks, tools)
   - Industry-specific terms
   - Certifications or methodologies
   - Prioritize keywords that appear in multiple job listings

2. KEYWORD_SUGGESTIONS: Provide 5-8 suggestions for improving existing keywords:
   - Identify words in the resume that could be replaced with more ATS-friendly synonyms
   - Suggest industry-standard terminology instead of informal terms
   - Recommend adding context or specificity to vague terms
   - Each suggestion should include the current word, suggested improvement, and reason

3. ATS_TIPS: Provide 4-6 specific, actionable tips that are DIRECTLY based on THIS resume's actual content:
   - First, identify what sections ALREADY EXIST in this resume (e.g., if there's a Skills section, don't recommend adding one)
   - Provide SPECIFIC examples from the resume text when making recommendations
   - For quantification: Point to SPECIFIC bullet points that lack metrics and show examples of ones that do it well
   - For formatting: Reference actual formatting issues you observe, not generic advice
   - For keywords: Reference specific job descriptions from the target jobs and where in the resume to add them
   - Each tip must include a concrete example or reference to specific resume content
   - Focus on actionable improvements, not generic best practices that may already be followed

4. OVERALL_SCORE: Rate the resume's current ATS compatibility from 0-100 based on:
   - Keyword match percentage with target jobs
   - Formatting compatibility
   - Content structure

Return ONLY valid JSON, no additional text."""

    def _build_general_prompt(self, resume_text: str) -> str:
        """Build the prompt for general AI-based analysis (when no jobs in database)."""
        return f"""You are an expert ATS (Applicant Tracking System) optimization specialist and career coach.

Analyze this resume and provide optimization recommendations based on current job market trends and best practices.

RESUME:
{resume_text[:4000]}

Since the user hasn't searched for specific jobs yet, analyze based on:
1. The apparent career field/industry from the resume
2. Current job market trends for similar roles
3. Common ATS requirements and best practices
4. Industry-standard terminology and keywords

Provide recommendations in the following JSON format:
{{
    "missing_keywords": ["keyword1", "keyword2", ...],
    "keyword_suggestions": [
        {{"current": "word in resume", "suggested": "better alternative", "reason": "explanation"}},
        ...
    ],
    "ats_tips": ["tip1", "tip2", ...],
    "overall_score": 75
}}

Guidelines:
1. MISSING_KEYWORDS: List 8-12 important keywords commonly expected in the candidate's apparent field that are missing from the resume.

2. KEYWORD_SUGGESTIONS: Provide 5-8 suggestions for improving existing keywords with more ATS-friendly or industry-standard alternatives.

3. ATS_TIPS: Provide 4-6 specific, actionable tips that are DIRECTLY based on THIS resume's actual content:
   - First, identify what sections ALREADY EXIST in this resume (e.g., if there's a Skills section, don't recommend adding one)
   - Provide SPECIFIC examples from the resume text when making recommendations
   - For quantification: Point to SPECIFIC bullet points that lack metrics and show examples of ones that do it well
   - For formatting: Reference actual formatting issues you observe, not generic advice
   - Each tip must include a concrete example or reference to specific resume content
   - Focus on actionable improvements, not generic best practices that may already be followed
   - Include one tip suggesting they search for specific jobs to get more targeted keyword recommendations

4. OVERALL_SCORE: Rate the resume's current ATS compatibility from 0-100.

Return ONLY valid JSON, no additional text."""

    def _call_openai_for_analysis(self, prompt: str, api_key: str) -> Optional[Dict]:
        """Call OpenAI API for resume analysis."""
        try:
            from openai import OpenAI
            import json

            client = OpenAI(api_key=api_key)

            logger.info("Requesting resume optimization analysis from OpenAI")

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert ATS optimization specialist. Always respond with valid JSON only."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )

            response_text = response.choices[0].message.content.strip()

            # Clean up response if it contains markdown code blocks
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                # Remove first and last lines (```json and ```)
                response_text = "\n".join(lines[1:-1])

            # Parse JSON response
            result = json.loads(response_text)

            # Validate and convert keyword_suggestions to proper format
            keyword_suggestions = []
            for suggestion in result.get("keyword_suggestions", []):
                if isinstance(suggestion, dict):
                    keyword_suggestions.append(KeywordSuggestion(
                        current=suggestion.get("current", ""),
                        suggested=suggestion.get("suggested", ""),
                        reason=suggestion.get("reason", "")
                    ))

            return {
                "missing_keywords": result.get("missing_keywords", []),
                "keyword_suggestions": keyword_suggestions,
                "ats_tips": result.get("ats_tips", []),
                "overall_score": result.get("overall_score", 50)
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response as JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Error calling OpenAI for analysis: {e}", exc_info=True)
            return None

class AuthService:
    """Service for authentication operations."""
    
    def register_user(self, request: UserRegisterRequest) -> Tuple[bool, str, Optional[UserResponse]]:
        """
        Register a new user.
        
        Args:
            request: User registration request
            
        Returns:
            Tuple of (success, message, user_response)
        """
        try:
            from jobhunter.AuthHandler import create_user, get_user_by_email, get_user_by_username
            
            # Check if email already exists
            existing_email = get_user_by_email(email=request.email)
            if existing_email:
                logger.warning(f"Registration failed - email already exists: {request.email}")
                return False, "Email already registered", None
            
            # Check if username already exists
            existing_username = get_user_by_username(username=request.username)
            if existing_username:
                logger.warning(f"Registration failed - username already exists: {request.username}")
                return False, "Username already taken", None
            
            # Create user
            user_id = create_user(
                email=request.email,
                username=request.username,
                password=request.password,
                full_name=request.full_name
            )
            
            # Get the created user
            from jobhunter.AuthHandler import get_user_by_id
            user_data = get_user_by_id(user_id=user_id)
            
            if not user_data:
                logger.error(f"User created but not found: {user_id}")
                return False, "User created but could not retrieve details", None
            
            # Convert to UserResponse
            from datetime import datetime
            user_response = UserResponse(
                id=user_data['id'],
                email=user_data['email'],
                username=user_data['username'],
                full_name=user_data.get('full_name'),
                is_active=bool(user_data['is_active']),
                created_at=datetime.fromisoformat(user_data['created_at']) if user_data.get('created_at') else datetime.now(),
                last_login=datetime.fromisoformat(user_data['last_login']) if user_data.get('last_login') else None
            )
            
            logger.info(f"User registered successfully: {request.username}")
            return True, "User registered successfully", user_response
            
        except Exception as e:
            logger.error(f"Error registering user: {e}", exc_info=True)
            return False, f"Registration failed: {str(e)}", None
    
    def login_user(self, request: UserLoginRequest) -> Tuple[bool, str, Optional[TokenResponse]]:
        """
        Authenticate user and return JWT token.
        
        Args:
            request: User login request
            
        Returns:
            Tuple of (success, message, token_response)
        """
        try:
            from jobhunter.AuthHandler import (
                get_user_by_email,
                get_user_by_username,
                verify_password,
                update_last_login
            )
            from jobhunter.backend.auth_service import create_access_token
            from datetime import datetime
            
            # Try to find user by email or username
            user_data = None
            if "@" in request.username_or_email:
                # Looks like an email
                user_data = get_user_by_email(email=request.username_or_email)
            else:
                # Looks like a username
                user_data = get_user_by_username(username=request.username_or_email)
            
            # If not found, try the other way
            if not user_data:
                if "@" in request.username_or_email:
                    user_data = get_user_by_username(username=request.username_or_email)
                else:
                    user_data = get_user_by_email(email=request.username_or_email)
            
            if not user_data:
                logger.warning(f"Login failed - user not found: {request.username_or_email}")
                return False, "Invalid credentials", None
            
            # Check if user is active
            if not user_data.get('is_active'):
                logger.warning(f"Login failed - inactive account: {user_data['username']}")
                return False, "Account is inactive", None
            
            # Verify password
            if not verify_password(request.password, user_data['hashed_password']):
                logger.warning(f"Login failed - incorrect password for: {user_data['username']}")
                return False, "Invalid credentials", None
            
            # Update last login
            update_last_login(user_id=user_data['id'])
            
            # Create JWT token (sub must be a string per JWT spec)
            access_token = create_access_token(data={"sub": str(user_data['id'])})
            
            # Convert to UserResponse
            user_response = UserResponse(
                id=user_data['id'],
                email=user_data['email'],
                username=user_data['username'],
                full_name=user_data.get('full_name'),
                is_active=bool(user_data['is_active']),
                created_at=datetime.fromisoformat(user_data['created_at']) if user_data.get('created_at') else datetime.now(),
                last_login=datetime.now()  # Just updated
            )
            
            token_response = TokenResponse(
                access_token=access_token,
                token_type="bearer",
                user=user_response
            )
            
            logger.info(f"User logged in successfully: {user_data['username']}")
            return True, "Login successful", token_response
            
        except Exception as e:
            logger.error(f"Error during login: {e}", exc_info=True)
            return False, f"Login failed: {str(e)}", None
    
    def request_password_reset(self, email: str) -> Tuple[bool, str]:
        """
        Generate password reset token for user.
        
        Args:
            email: User's email address
            
        Returns:
            Tuple of (success, message)
        """
        try:
            from jobhunter.AuthHandler import get_user_by_email, create_password_reset_token
            
            # Find user by email
            user_data = get_user_by_email(email=email)
            
            if not user_data:
                # For security, don't reveal if email exists
                logger.info(f"Password reset requested for non-existent email: {email}")
                return True, "If the email exists, a reset link has been sent"
            
            # Generate reset token
            token = create_password_reset_token(user_id=user_data['id'])
            
            # In a real application, you would send this token via email
            # For now, we'll just log it (for development/testing)
            logger.info(f"Password reset token generated for {email}: {token}")
            logger.warning("NOTE: In production, this token should be sent via email, not logged!")
            
            return True, "If the email exists, a reset link has been sent"
            
        except Exception as e:
            logger.error(f"Error requesting password reset: {e}", exc_info=True)
            return False, f"Failed to process password reset request: {str(e)}"
    
    def reset_password(self, token: str, new_password: str) -> Tuple[bool, str]:
        """
        Reset user password using reset token.
        
        Args:
            token: Password reset token
            new_password: New password to set
            
        Returns:
            Tuple of (success, message)
        """
        try:
            from jobhunter.AuthHandler import reset_password as reset_pwd
            
            success = reset_pwd(token=token, new_password=new_password)
            
            if success:
                logger.info("Password reset successful")
                return True, "Password reset successful"
            else:
                logger.warning("Password reset failed - invalid or expired token")
                return False, "Invalid or expired reset token"
                
        except Exception as e:
            logger.error(f"Error resetting password: {e}", exc_info=True)
            return False, f"Failed to reset password: {str(e)}"


class OnboardingService:
    """Service for automated user onboarding workflow."""

    def __init__(self):
        self.ai_service = AIService()
        self.job_search_service = JobSearchService()
        self.job_data_service = JobDataService()
        self.resume_optimizer_service = ResumeOptimizerService()

    def process_onboarding(self, resume_name: str, user_id: int) -> OnboardingResponse:
        """
        Run the complete onboarding workflow for a resume.

        Steps:
        1. Get AI job title suggestions
        2. Run smart search with suggested titles
        3. Update similarity scores
        4. Run resume optimizer

        Args:
            resume_name: Name of the resume to process
            user_id: ID of the user who owns the resume

        Returns:
            OnboardingResponse with results from all steps
        """
        steps = []
        job_titles_suggested = []
        total_jobs_found = 0
        jobs_with_similarity = 0
        optimization_score = 0
        overall_success = True

        # Step 1: Get AI job title suggestions
        logger.info(f"Onboarding Step 1: Getting job title suggestions for {resume_name}")
        try:
            success, suggestions, message = self.ai_service.suggest_job_titles(resume_name, user_id)
            job_titles_suggested = suggestions if success else []

            steps.append(OnboardingStepResult(
                step_name="job_title_suggestions",
                success=success,
                message=message,
                data={"suggestions": job_titles_suggested} if success else None
            ))

            if not success:
                logger.warning(f"Onboarding Step 1 failed: {message}")
                # Continue with default job titles if suggestions fail
                job_titles_suggested = ["Software Engineer", "Data Analyst", "Product Manager"]

        except Exception as e:
            logger.error(f"Onboarding Step 1 error: {e}", exc_info=True)
            steps.append(OnboardingStepResult(
                step_name="job_title_suggestions",
                success=False,
                message=f"Error: {str(e)}",
                data=None
            ))
            job_titles_suggested = ["Software Engineer", "Data Analyst", "Product Manager"]

        # Step 2: Run smart search with suggested titles
        logger.info(f"Onboarding Step 2: Searching for jobs with titles: {job_titles_suggested}")
        try:
            request = JobSearchRequest(
                job_titles=job_titles_suggested,
                country="us",
                date_posted="all",
                location=""
            )
            total_jobs_found = self.job_search_service.search_jobs(request)

            steps.append(OnboardingStepResult(
                step_name="job_search",
                success=total_jobs_found > 0,
                message=f"Found {total_jobs_found} jobs" if total_jobs_found > 0 else "No jobs found",
                data={"total_jobs": total_jobs_found, "job_titles_searched": job_titles_suggested}
            ))

            if total_jobs_found == 0:
                logger.warning("Onboarding Step 2: No jobs found")

        except Exception as e:
            logger.error(f"Onboarding Step 2 error: {e}", exc_info=True)
            steps.append(OnboardingStepResult(
                step_name="job_search",
                success=False,
                message=f"Error: {str(e)}",
                data=None
            ))
            overall_success = False

        # Step 3: Update similarity scores
        logger.info(f"Onboarding Step 3: Calculating similarity scores")
        try:
            success, jobs_updated = self.job_data_service.update_similarity_scores(resume_name, user_id)
            jobs_with_similarity = jobs_updated

            steps.append(OnboardingStepResult(
                step_name="similarity_calculation",
                success=success,
                message=f"Calculated similarity for {jobs_updated} jobs" if success else "Failed to calculate similarity",
                data={"jobs_updated": jobs_updated} if success else None
            ))

            if not success:
                logger.warning("Onboarding Step 3: Similarity calculation failed")

        except Exception as e:
            logger.error(f"Onboarding Step 3 error: {e}", exc_info=True)
            steps.append(OnboardingStepResult(
                step_name="similarity_calculation",
                success=False,
                message=f"Error: {str(e)}",
                data=None
            ))

        # Step 4: Run resume optimizer
        logger.info(f"Onboarding Step 4: Running resume optimizer")
        try:
            optimizer_result = self.resume_optimizer_service.optimize_resume(
                resume_name=resume_name,
                num_jobs=20,
                user_id=user_id
            )
            optimization_success = optimizer_result.get("success", False)
            optimization_score = optimizer_result.get("overall_score", 0)

            steps.append(OnboardingStepResult(
                step_name="resume_optimization",
                success=optimization_success,
                message=optimizer_result.get("message", ""),
                data={
                    "overall_score": optimization_score,
                    "missing_keywords_count": len(optimizer_result.get("missing_keywords", [])),
                    "tips_count": len(optimizer_result.get("ats_tips", []))
                } if optimization_success else None
            ))

            if not optimization_success:
                logger.warning(f"Onboarding Step 4 failed: {optimizer_result.get('message')}")

        except Exception as e:
            logger.error(f"Onboarding Step 4 error: {e}", exc_info=True)
            steps.append(OnboardingStepResult(
                step_name="resume_optimization",
                success=False,
                message=f"Error: {str(e)}",
                data=None
            ))

        # Determine overall success (at least job search and similarity should succeed)
        critical_steps_succeeded = any(
            s.step_name == "job_search" and s.success for s in steps
        )

        logger.info(f"Onboarding completed. Jobs found: {total_jobs_found}, "
                   f"Similarity updated: {jobs_with_similarity}, Score: {optimization_score}")

        return OnboardingResponse(
            success=critical_steps_succeeded,
            message=self._build_summary_message(steps, total_jobs_found, optimization_score),
            steps=steps,
            job_titles_suggested=job_titles_suggested,
            total_jobs_found=total_jobs_found,
            jobs_with_similarity=jobs_with_similarity,
            optimization_score=optimization_score
        )

    def _build_summary_message(self, steps: List[OnboardingStepResult],
                               total_jobs: int, score: int) -> str:
        """Build a human-readable summary message."""
        successful_steps = sum(1 for s in steps if s.success)
        total_steps = len(steps)

        if successful_steps == total_steps:
            return f"Onboarding complete! Found {total_jobs} jobs and your resume scored {score}/100."
        elif successful_steps > 0:
            return f"Onboarding partially complete ({successful_steps}/{total_steps} steps). Found {total_jobs} jobs."
        else:
            return "Onboarding encountered issues. Please check your API keys and try again."
