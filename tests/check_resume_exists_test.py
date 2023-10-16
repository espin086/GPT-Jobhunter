import os
import sys

# Add the directory containing search_linkedin_jobs.py to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_resume_exists():
    """
    Checks if a file exists.
    """
    file_path = (
        "../jobhunter/temp/resumes/resume.txt"  # Replace with the actual file path
    )

    assert os.path.exists(file_path), f"File does not exist: {file_path}"
