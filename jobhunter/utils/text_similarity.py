import logging
import argparse
import pprint
import nltk
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


logging.basicConfig(level=logging.INFO)
pp = pprint.PrettyPrinter(indent=4)

nltk.download('stopwords')
nltk.download('punkt')
stop_words = set(stopwords.words('english'))


def preprocess_text(text):
    """
    This function preprocesses the input text by converting to lower case, removing stop words and punctuation, and 
    tokenizing the text.

    Args:
    text (str): The text to preprocess.

    Returns:
    str: The preprocessed text.
    """
    tokens = nltk.word_tokenize(text.lower())
    words = [word for word in tokens if word.isalnum() and word not in stop_words]
    return ' '.join(words)


def text_similarity(text1, text2):
    """
    This function calculates the similarity between two pieces of text using the cosine similarity between their
    preprocessed representations. It takes in two strings, text1 and text2, as input and returns a dictionary
    containing the similarity score.

    Args:
    text1 (str): The first piece of text for comparison.
    text2 (str): The second piece of text for comparison.

    Returns:
    dict: A dictionary containing the similarity score between the two texts as a key-value pair where key is
    'similarity' and value is a float between 0 and 1.

    Raises:
    Exception: If an exception is encountered during the API request, it is logged as an error.
    """
    try:
        text1_preprocessed = preprocess_text(text1)
        text2_preprocessed = preprocess_text(text2)

        vectorizer = TfidfVectorizer()
        vectors = vectorizer.fit_transform([text1_preprocessed, text2_preprocessed])
        similarity_score = cosine_similarity(vectors)[0][1]

        similarity = {}
        similarity["similarity"] = similarity_score
        logging.info("Text similarity calculated")

        return float(similarity_score)
    except Exception as e:
        logging.error(f"An error occurred while calculating the text similarity: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="takes the similarity of two texts")

    parser.add_argument("text1", metavar="text1", type=str, help="the first text")
    parser.add_argument("text2", metavar="text2", type=str, help="the second text")

    args = parser.parse_args()

    result = text_similarity(text1=args.text1, text2=args.text2)

    pp.pprint(result)
