import pytest
from linkedin_bot import jobs_analysis


@pytest.fixture
def job_analysis_result():
    search_term = "software engineer"
    location = "San Francisco"
    min_salary = 100000
    minsim = 0.7
    return jobs_analysis(search_term, location, min_salary, minsim)


def test_jobs_analysis_returns_list(job_analysis_result):
    assert isinstance(job_analysis_result, list)


def test_jobs_analysis_returns_list_of_dicts(job_analysis_result):
    assert all(isinstance(job, dict) for job in job_analysis_result)


def test_jobs_analysis_returns_valid_job_fields(job_analysis_result):
    for job in job_analysis_result:
        assert all(
            key in job.keys() for key in ["title", "job_url", "job_description", "resume_similarity"]
        )


def test_jobs_analysis_resumes_similarity_score_is_float_between_0_and_1(job_analysis_result):
    for job in job_analysis_result:
        assert isinstance(job["resume_similarity"], float)
        assert 0 <= job["resume_similarity"] <= 1
