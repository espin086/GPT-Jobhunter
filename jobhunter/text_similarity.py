"""
This code calculates the similarity between two documents
"""

import argparse
import logging
import pprint
import random  # Import random module for setting a seed

import nltk
from gensim.models.doc2vec import Doc2Vec, TaggedDocument
from nltk.corpus import stopwords
from sklearn.metrics.pairwise import cosine_similarity
from typing import Dict

# Set a seed for reproducibility
random.seed(42)

logging.basicConfig(level=logging.INFO)
pp = pprint.PrettyPrinter(indent=4)

nltk.download("stopwords")
nltk.download("punkt")
stop_words = set(stopwords.words("english"))


def preprocess_text(text: str):
    """
    This function preprocesses the input text by converting to lower case, removing stop words and punctuation, and
    tokenizing the text into sentences.

    Args:
    text (str): The text to preprocess.

    Returns:
    list: A list of sentences in the preprocessed text.
    """
    sentences = nltk.sent_tokenize(text.lower())
    return [
        nltk.word_tokenize(sentence)
        for sentence in sentences
        if sentence not in stop_words
    ]


def generate_doc2vec(sentences):
    """
    This function generates doc2vec vectors for each sentence in the input list.

    Args:
    sentences (list): A list of sentences.

    Returns:
    list: A list of doc2vec vectors for each sentence.
    """
    documents = [TaggedDocument(doc, [i]) for i, doc in enumerate(sentences)]
    model = Doc2Vec(
        documents,
        vector_size=100,
        min_alpha=0.025,
        window=5,
        min_count=1,
        workers=4,
        dm=0,
    )
    return [model.infer_vector(doc) for doc in documents]


def text_similarity(text1: str, text2: str) -> Dict:
    """
    This function calculates the similarity between two pieces of text using the cosine similarity between their
    doc2vec representations. It takes in two strings, text1 and text2, as input and returns a dictionary
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

        documents = [
            TaggedDocument(doc, [i])
            for i, doc in enumerate(text1_preprocessed + text2_preprocessed)
        ]
        model = Doc2Vec(
            documents, vector_size=50, window=2, min_count=1, workers=4, epochs=100
        )
        text1_vec = model.infer_vector(text1_preprocessed[0])
        text2_vec = model.infer_vector(text2_preprocessed[0])
        similarity_score = cosine_similarity([text1_vec], [text2_vec])[0][0]

        similarity = {}
        similarity["similarity"] = similarity_score
        logging.info("Text similarity calculated")

        return similarity_score
    except Exception as e:
        logging.error(f"An error occurred while calculating the text similarity: {e}")
        return {
            "error": f"An error occurred while calculating the text similarity: {e}"
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="takes the similarity of two texts")

    parser.add_argument("text1", metavar="text1", type=str, help="the first text")
    parser.add_argument("text2", metavar="text2", type=str, help="the second text")

    args = parser.parse_args()

    result = text_similarity(text1=args.text1, text2=args.text2)
    print(result)
