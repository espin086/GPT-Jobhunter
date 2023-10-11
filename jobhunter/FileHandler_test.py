import json
import os
import sys

import pytest

# Add the path to the FileHandler module to the system path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import the FileHandler module
import FileHandler


@pytest.fixture
def file_handler_instance():
    """Provides a FileHandler instance for testing"""
    return FileHandler.FileHandler(
        raw_path="temp/test/data/raw", processed_path="temp/test/data/processed"
    )


def test_setup_logging(file_handler_instance):
    """Test logging setup"""
    assert file_handler_instance.setup_logging() is None  # Should have no return


def test_create_data_folders_if_not_exists(file_handler_instance):
    """Test the creation of data folders if they don't exist"""
    file_handler_instance.create_data_folders_if_not_exists()

    assert os.path.exists(file_handler_instance.raw_path)
    assert os.path.exists(file_handler_instance.processed_path)


def test_read_resume_text(file_handler_instance):
    """Test reading of resume text from a file"""
    test_text = "This is a test resume."
    with open(f"{file_handler_instance.raw_path}/test_resume.txt", "w") as f:
        f.write(test_text)

    result = file_handler_instance.read_resume_text(
        f"{file_handler_instance.raw_path}/test_resume.txt"
    )

    assert result == test_text


def test_delete_files(file_handler_instance):
    """Test deletion of files in a directory"""
    with open(f"{file_handler_instance.raw_path}/test_delete.txt", "w") as f:
        f.write("This is a test for delete.")

    file_handler_instance.delete_files(file_handler_instance.raw_path)

    assert not os.path.exists(f"{file_handler_instance.raw_path}/test_delete.txt")
