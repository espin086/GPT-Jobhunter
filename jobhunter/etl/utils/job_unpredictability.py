import argparse
import logging
import re
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import gensim.downloader as api
from gensim.models import KeyedVectors

# Download NLTK data
import nltk

nltk.download("punkt")
nltk.download("stopwords")
nltk.download("wordnet")

# Load FastText model
fasttext_model = KeyedVectors.load_word2vec_format(
    "wiki-news-300d-1M.vec", binary=False
)

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Create argument parser
parser = argparse.ArgumentParser(
    description="Read in a text file that contains a job description and use machine learning to identify keywords that means that the job will be unpredictable in terms of tasks and duties."
)
parser.add_argument(
    "--file", help="Path to the text file containing the job description"
)

# Define unpredictability words
unpredictability_words = [
    "dynamic",
    "fast-paced",
    "unpredictable",
    "ever-changing",
    "fluid",
    "adaptable",
    "flexible",
    "changeable",
    "variable",
    "unstable",
    "unsteady",
    "unreliable",
    "erratic",
    "unsystematic",
    "unstructured",
    "uncontrolled",
    "unregular",
    "unceasing",
    "unending",
    "unfailing",
    "uninterrupted",
    "unceasing",
    "unabating",
    "unflagging",
    "unremitting",
    "unstoppable",
    "unstinting",
    "unabated",
    "uninterruptedly",
    "unceasingly",
]


# Find similar words using FastText
def get_similar_words(words, topn=10):
    similar_words = set()
    for word in words:
        try:
            for similar_word, _ in fasttext_model.most_similar(word, topn=topn):
                similar_words.add(similar_word)
        except KeyError:
            pass
    return similar_words


# Get similar words for unpredictability words
unpredictability_words = list(get_similar_words(unpredictability_words))


def calculate_unpredictability_index(text):
    """Calculate the index of unpredictability in a given text.

    Args:
        text (str): The text to analyze.

    Returns:
        float: The index of unpredictability.
    """
    # Tokenize the text
    tokens = word_tokenize(text)

    # Remove stopwords
    stop_words = set(stopwords.words("english"))
    filtered_tokens = [t for t in tokens if t.lower() not in stop_words]

    # Lemmatize tokens
    lemmatizer = WordNetLemmatizer()
    lemmatized_tokens = [lemmatizer.lemmatize(t) for t in filtered_tokens]

    # Find all words related to unpredictability
    unpredictability_words_found = [
        t for t in lemmatized_tokens if t.lower() in unpredictability_words
    ]
    # Calculate the index of unpredictability
    unpredictability_index = len(unpredictability_words_found) / len(lemmatized_tokens)

    return unpredictability_index


def main():
    args = parser.parse_args()
    file_path = args.file
    # Read in the text file
    with open(file_path, "r") as f:
        text = f.read()

    # Calculate the index of unpredictability
    unpredictability_index = calculate_unpredictability_index(text)

    # Log the index
    logging.info("The index of unpredictability is: {}".format(unpredictability_index))


if name == "main":
    main()
