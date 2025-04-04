import pytest
import os
from jobhunter import text_similarity
from unittest.mock import patch, Mock

# Define test data
text1 = "This is the first text."
text2 = "This is the second text."


# Test text_similarity function
def test_text_similarity_direct():
    """
    Test the text_similarity function with actual OpenAI API calls.
    
    Note: This test will be skipped if the OPENAI_API_KEY environment variable is not set.
    """
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY environment variable not set - skipping test requiring API access")
        
    # Call the function directly
    similarity_score = text_similarity.text_similarity(text1, text2)
    
    # Check that we get a valid similarity score
    assert similarity_score is not None
    assert isinstance(similarity_score, (float))
    
    # The score should be between 0 and 1 for cosine similarity
    assert 0 <= similarity_score <= 1


# Test text_similarity function with mocking
@patch('jobhunter.text_similarity.generate_gpt_embedding')
def test_text_similarity_mocked(mock_generate_embedding):
    """
    Test the text_similarity function with mocked embeddings.
    
    This test mocks the generate_gpt_embedding function to return predictable vectors, 
    so we can test the similarity calculation logic without calling the OpenAI API.
    """
    # Configure the mock to return predefined embeddings for our test texts
    # Using small vectors for simplicity, the actual ones are 1536-dimensional
    mock_generate_embedding.side_effect = [
        [0.1, 0.2, 0.3],  # First text embedding
        [0.2, 0.2, 0.3]   # Second text embedding
    ]
    
    # Call the function
    similarity_score = text_similarity.text_similarity(text1, text2)
    
    # Make sure our mock was called twice (once for each text)
    assert mock_generate_embedding.call_count == 2
    
    # Check the result is a float
    assert isinstance(similarity_score, float)
    
    # The exact value will depend on the cosine similarity between our mocked vectors
    # For vectors [0.1, 0.2, 0.3] and [0.2, 0.2, 0.3], the cosine similarity should be close to:
    # 0.9723055853282465
    assert similarity_score == pytest.approx(0.9723055853282465, abs=1e-5)
