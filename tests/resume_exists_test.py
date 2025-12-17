import os
import sys
import pytest

from jobhunter import config

# Add the directory containing the extract_salary module to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


IN_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"


@pytest.mark.skipif(
    IN_GITHUB_ACTIONS,
    reason="Skipping in Github actions because no resumes should be loaded, test works locally with make test command",
)
def test_resume_file_exists():
    """
    Checks to see if the example resume exist. If it doesn't, create a test one.
    """
    file_path = config.RESUME_PATH

    # If resume doesn't exist, create a test one
    if not os.path.isfile(file_path):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            f.write("Test Resume\n\nJohn Doe\nSoftware Engineer\nExperience: 5 years\nSkills: Python, JavaScript, React")
        print(f"Created test resume at {file_path}")

    assert os.path.isfile(file_path), f"File {file_path} could not be created or found"
