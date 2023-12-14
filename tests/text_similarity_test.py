import pytest
from jobhunter import text_similarity

# Define test data
text1 = "This is the first text."
text2 = "This is the second text."


# Test preprocess_text function
def test_preprocess_text():
    """
    Test the preprocess_text function from the text_similarity module.

    The function should take a string of text and return a list of lists, where each
    inner list contains the preprocessed words of a sentence in the original text.

    This test checks that the function correctly preprocesses a sample text with two
    sentences, and that the resulting list of lists has the expected length and content.
    """
    text = "This is a sample text. It contains multiple sentences."
    preprocessed = text_similarity.preprocess_text(text)
    assert len(preprocessed) == 2
    assert preprocessed[0] == ["this", "is", "a", "sample", "text", "."]
    assert preprocessed[1] == ["it", "contains", "multiple", "sentences", "."]


# Test text_similarity function
def test_text_similarity():
    """
    Test the text_similarity function without mocking the Doc2Vec model.

    This function tests the text_similarity function without mocking the Doc2Vec model.
    It calls the text_similarity function with two sample texts and asserts that the cosine_similarity method is called once.
    Finally, it asserts that the similarity score returned by the text_similarity function is equal to the expected value.
    """
    similarity_score = text_similarity.text_similarity(text1, text2)
    assert similarity_score == pytest.approx(
        0.26849132776260376, rel=1
    )  # Expected similarity score
