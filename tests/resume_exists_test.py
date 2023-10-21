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
    Checks to see if the example resume exist, code should not run if this
    text does not exist
    """
    file_path = config.RESUME_PATH
    assert os.path.isfile(file_path), f"File {file_path} not found"
