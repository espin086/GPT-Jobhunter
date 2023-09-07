from search_linkedin_jobs import search_linkedin_jobs


def test_search_linkedin_jobs():
    """
    This is a test function for search_linkedin_jobs().
    """
    search_term = "Software Engineer"
    location = "United States"
    page = 1
    result = search_linkedin_jobs(search_term, location, page)
    print(result)
    assert result is not None
