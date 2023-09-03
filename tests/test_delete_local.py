from unittest import mock

import pytest

# Import the function under test
from jobhunter.app.utilities.delete_local import delete_files, delete_local


# Test with correct import path
@mock.patch("jobhunter.app.utilities.delete_local.delete_files")
def test_delete_local_with_correct_path(mock_delete_files):
    print("Before calling delete_local")  # Debug print

    delete_local()  # Call the function under test

    print("After calling delete_local")  # Debug print
    print(
        f"Mock delete_files called with: {mock_delete_files.call_args_list}"
    )  # Debug print

    mock_delete_files.assert_has_calls(
        [
            mock.call(dir_path="temp/data/raw"),
            mock.call(dir_path="temp/data/processed"),
        ],
        any_order=True,
    )


# Test with corrected import path (this test should pass now)
@mock.patch("jobhunter.app.utilities.delete_local.delete_files")
def test_delete_local_another_test(mock_delete_files):
    delete_local()  # Call the function under test

    # Check if delete_files was called for each directory
    mock_delete_files.assert_has_calls(
        [
            mock.call(dir_path="temp/data/raw"),
            mock.call(dir_path="temp/data/processed"),
        ],
        any_order=True,
    )
