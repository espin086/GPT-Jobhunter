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
    KeywordSuggestion
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
    
    def upload_resume(self, request: ResumeUploadRequest) -> bool:
        """
        Upload a resume to the database.
        
        Args:
            request: Resume upload request
            
        Returns:
            True if successful
        """
        try:
            save_text_to_db(request.filename, request.content)
            logger.info(f"Resume '{request.filename}' uploaded successfully")
            return True
        except Exception as e:
            logger.error(f"Error uploading resume: {e}", exc_info=True)
            raise
    
    def get_resumes(self) -> List[str]:
        """
        Get list of all resumes.
        
        Returns:
            List of resume names
        """
        try:
            return fetch_resumes_from_db()
        except Exception as e:
            logger.error(f"Error fetching resumes: {e}", exc_info=True)
            raise
    
    def get_resume_content(self, resume_name: str) -> Optional[str]:
        """
        Get resume content by name.
        
        Args:
            resume_name: Name of the resume
            
        Returns:
            Resume content or None if not found
        """
        try:
            return get_resume_text(resume_name)
        except Exception as e:
            logger.error(f"Error fetching resume content: {e}", exc_info=True)
            raise
    
    def update_resume(self, resume_name: str, content: str) -> bool:
        """
        Update resume content.
        
        Args:
            resume_name: Name of the resume
            content: New content
            
        Returns:
            True if successful
        """
        try:
            update_resume_in_db(resume_name, content)
            logger.info(f"Resume '{resume_name}' updated successfully")
            return True
        except Exception as e:
            logger.error(f"Error updating resume: {e}", exc_info=True)
            raise
    
    def delete_resume(self, resume_name: str) -> bool:
        """
        Delete a resume.
        
        Args:
            resume_name: Name of the resume
            
        Returns:
            True if successful
        """
        try:
            delete_resume_in_db(resume_name)
            logger.info(f"Resume '{resume_name}' deleted successfully")
            return True
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
    
    def update_similarity_scores(self, resume_name: str) -> Tuple[bool, int]:
        """
        Update similarity scores for all jobs against a resume.
        
        Args:
            resume_name: Name of the resume to calculate similarities against
            
        Returns:
            Tuple of (success, number of jobs updated)
        """
        try:
            success = update_similarity_in_db(resume_name)
            
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
                    resume_name TEXT UNIQUE,
                    resume_text TEXT
                )
            ''')

            # Create job_tracking table for Kanban board
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS job_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'apply',
                    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    date_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT,
                    FOREIGN KEY (job_id) REFERENCES jobs_new(id),
                    UNIQUE(job_id)
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

    def suggest_job_titles(self, resume_name: str) -> Tuple[bool, List[str], str]:
        """
        Analyze resume and suggest 3 optimal job titles using OpenAI.

        Args:
            resume_name: Name of the resume to analyze

        Returns:
            Tuple of (success, list of job titles, message)
        """
        try:
            # Get resume text
            resume_text = get_resume_text(resume_name)
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

    def save_job(self, job_id: int) -> Tuple[bool, str]:
        """
        Save a job to tracking board (starts in 'apply' status).

        Args:
            job_id: ID of the job to save

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

            # Insert or ignore if already tracked
            cursor.execute('''
                INSERT OR IGNORE INTO job_tracking (job_id, status)
                VALUES (?, 'apply')
            ''', (job_id,))

            conn.commit()
            conn.close()

            logger.info(f"Job {job_id} saved to tracking board")
            return True, "Job saved successfully"

        except Exception as e:
            logger.error(f"Error saving job: {e}", exc_info=True)
            return False, f"Failed to save job: {str(e)}"

    def pass_job(self, job_id: int) -> Tuple[bool, str]:
        """
        Mark a job as hidden/passed.

        Args:
            job_id: ID of the job to hide

        Returns:
            Tuple of (success, message)
        """
        try:
            conn = sqlite3.connect(config.DATABASE)
            cursor = conn.cursor()

            # Update hidden flag
            cursor.execute("UPDATE jobs_new SET hidden = 1 WHERE id = ?", (job_id,))

            conn.commit()
            conn.close()

            logger.info(f"Job {job_id} marked as hidden")
            return True, "Job marked as not interested"

        except Exception as e:
            logger.error(f"Error marking job as hidden: {e}", exc_info=True)
            return False, f"Failed to hide job: {str(e)}"

    def get_tracked_jobs(self) -> Dict[str, List[Dict]]:
        """
        Get all tracked jobs organized by status (for Kanban board).

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
                ORDER BY jt.date_updated DESC
            '''

            df = pd.read_sql(query, conn)
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

    def update_job_status(self, job_id: int, new_status: str) -> Tuple[bool, str]:
        """
        Update the status of a tracked job (for moving between Kanban columns).

        Args:
            job_id: ID of the job
            new_status: New status (apply, hr_screen, round_1, round_2, rejected)

        Returns:
            Tuple of (success, message)
        """
        try:
            valid_statuses = ['apply', 'hr_screen', 'round_1', 'round_2', 'rejected']
            if new_status not in valid_statuses:
                return False, f"Invalid status. Must be one of: {', '.join(valid_statuses)}"

            conn = sqlite3.connect(config.DATABASE)
            cursor = conn.cursor()

            # Update status and timestamp
            cursor.execute('''
                UPDATE job_tracking
                SET status = ?, date_updated = CURRENT_TIMESTAMP
                WHERE job_id = ?
            ''', (new_status, job_id))

            if cursor.rowcount == 0:
                conn.close()
                return False, "Job not found in tracking"

            conn.commit()
            conn.close()

            logger.info(f"Job {job_id} status updated to {new_status}")
            return True, f"Job moved to {new_status}"

        except Exception as e:
            logger.error(f"Error updating job status: {e}", exc_info=True)
            return False, f"Failed to update status: {str(e)}"

    def remove_from_tracking(self, job_id: int) -> Tuple[bool, str]:
        """
        Remove a job from tracking board.

        Args:
            job_id: ID of the job to remove

        Returns:
            Tuple of (success, message)
        """
        try:
            conn = sqlite3.connect(config.DATABASE)
            cursor = conn.cursor()

            cursor.execute("DELETE FROM job_tracking WHERE job_id = ?", (job_id,))

            conn.commit()
            conn.close()

            logger.info(f"Job {job_id} removed from tracking")
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

    def optimize_resume(self, resume_name: str, num_jobs: int = 20) -> Dict:
        """
        Analyze resume against top similar jobs and provide optimization suggestions.

        If jobs exist in the database, analyzes against those jobs.
        If no jobs exist, uses AI's general knowledge for optimization.

        Args:
            resume_name: Name of the resume to analyze
            num_jobs: Number of top similar jobs to analyze

        Returns:
            Dictionary with optimization results
        """
        try:
            # Get resume text
            resume_text = get_resume_text(resume_name)
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

3. ATS_TIPS: Provide 4-6 specific, actionable tips for optimizing this resume for ATS systems:
   - Formatting recommendations
   - Section organization
   - Keyword placement strategies
   - Quantification opportunities

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

3. ATS_TIPS: Provide 4-6 specific, actionable tips for ATS optimization, including a tip to search for specific jobs to get more targeted recommendations.

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