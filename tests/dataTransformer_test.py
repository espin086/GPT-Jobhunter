import pytest
import os

# Import the `shutil` module
import shutil
from jobhunter.config import PROCESSED_DATA_PATH
from jobhunter.dataTransformer import DataTransformer
from jobhunter import FileHandler


sample_data = [
    {
        "linkedin_job_url_cleaned": "url1",
        "job_title": "Software Engineer",
        "job_location": "San Francisco, CA",
        "posted_date": "2023-01-15",
        "normalized_company_name": "Tech Corp",
        "linkedin_company_url_cleaned": "company_url1",
        "job_url": "job_url1",
        "company_name": "Tech Corp",
        "company_url": "company_url1",
        "description": "Tech Corp is seeking a talented Software Engineer to join our team in San Francisco, CA. As a Software Engineer, you will be responsible for designing and developing high-quality software solutions, collaborating with cross-functional teams, and ensuring the scalability and performance of our applications.",
    },
    {
        "linkedin_job_url_cleaned": "url2",
        "job_title": "Data Scientist",
        "job_location": "New York, NY",
        "posted_date": "2023-01-20",
        "normalized_company_name": "Data Insights, Inc.",
        "linkedin_company_url_cleaned": "company_url2",
        "job_url": "job_url2",
        "company_name": "Data Insights, Inc.",
        "company_url": "company_url2",
        "description": "Data Insights, Inc. is looking for an experienced Data Scientist to join our analytics team in New York, NY. As a Data Scientist, you will work on complex data analysis projects, develop predictive models, and provide data-driven insights to help our clients make informed decisions.",
    },
    {
        "linkedin_job_url_cleaned": "url3",
        "job_title": "Product Manager",
        "job_location": "Seattle, WA",
        "posted_date": "2023-01-25",
        "normalized_company_name": "InnovateTech",
        "linkedin_company_url_cleaned": "company_url3",
        "job_url": "job_url3",
        "company_name": "InnovateTech",
        "company_url": "company_url3",
        "description": "InnovateTech is seeking a passionate Product Manager to lead our product development efforts in Seattle, WA. As a Product Manager, you will define product roadmaps, gather customer feedback, and collaborate with engineering teams to deliver innovative solutions to the market.",
    },
    # Add more realistic data entries as needed for testing
]


@pytest.fixture
def data_transformer_instance(tmpdir):
    """Provides a DataTransformer instance for testing."""
    raw_path = str(tmpdir.mkdir("raw_data"))
    processed_path = str(tmpdir.mkdir("processed_data"))
    resume_path = str(tmpdir.join("resume.txt"))

    with open(resume_path, "w") as resume_file:
        resume_file.write("Sample resume content")

    return DataTransformer(raw_path, processed_path, resume_path, sample_data.copy())


def test_drop_variables(data_transformer_instance):
    """Test if the drop_variables method removes specified keys from data."""
    data_transformer_instance.drop_variables()
    for item in data_transformer_instance.data:
        assert "job_url" not in item
        assert "company_name" not in item
        assert "company_url" not in item


def test_remove_duplicates(data_transformer_instance):
    """Test if the remove_duplicates method removes duplicate entries from data."""
    data_transformer_instance.remove_duplicates()
    assert len(data_transformer_instance.data) == 3  # No duplicates in the sample data


def test_rename_keys(data_transformer_instance):
    """Test if the rename_keys method renames keys in data."""
    data_transformer_instance.rename_keys({"job_title": "new_title"})
    for item in data_transformer_instance.data:
        assert "job_title" not in item
        assert "new_title" in item


def test_extract_salaries(data_transformer_instance):
    """Test if the extract_salaries method correctly extracts salary information."""
    data_transformer_instance.extract_salaries()
    for item in data_transformer_instance.data:
        assert "salary_low" in item
        assert "salary_high" in item
        assert (
            isinstance(item["salary_low"], (float, int)) or item["salary_low"] is None
        )
        assert (
            isinstance(item["salary_high"], (float, int)) or item["salary_high"] is None
        )


def test_compute_resume_similarity(data_transformer_instance):
    """Test if the compute_resume_similarity method correctly computes resume similarity."""
    resume_text = "Sample resume content"
    data_transformer_instance.compute_resume_similarity(resume_text)
    for item in data_transformer_instance.data:
        assert "resume_similarity" in item
        assert (
            isinstance(item["resume_similarity"], (float, int))
            or item["resume_similarity"] is None
        )


def test_transform(data_transformer_instance, tmpdir, request):
    """Test if the transform method correctly transforms and saves data."""

    # Create a unique directory name based on the test function name
    test_name = request.node.name
    processed_data_dir = tmpdir.mkdir(f"processed_data_{test_name}")

    # Update the processed_path in the data transformer instance
    data_transformer_instance.file_handler.processed_path = str(processed_data_dir)

    # Check if the directory exists, and if not, create it
    if not os.path.exists(data_transformer_instance.file_handler.processed_path):
        os.makedirs(data_transformer_instance.file_handler.processed_path)

    # Perform the transformation
    data_transformer_instance.transform()

    # Load the processed data from the temporary directory
    processed_data = data_transformer_instance.file_handler.import_job_data_from_dir(
        data_transformer_instance.file_handler.processed_path
    )

    # Ensure that the number of items in the processed data matches the input data
    assert len(data_transformer_instance.data) == 3

    # You can add additional assertions to validate the transformed data as needed
    for item in processed_data:
        assert "title" in item
        assert "location" in item
        assert "date" in item
        assert "company" in item
        assert "description" in item
        assert "salary_low" in item
        assert "salary_high" in item
        assert "resume_similarity" in item
