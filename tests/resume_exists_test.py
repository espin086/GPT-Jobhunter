import os
import sys

# Add the directory containing the extract_salary module to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_resume_file_exists():
    """
    Checks to see if the example resume exist, code should not run if this
    text does not exist
    """
    file_path = "../jobhunter/temp/resumes/resume.txt"
    assert os.path.isfile(file_path), f"File {file_path} not found"
