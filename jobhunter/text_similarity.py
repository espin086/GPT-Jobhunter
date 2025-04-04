"""
This code calculates the similarity between two documents
"""

import argparse
import logging
import pprint
import random  # Import random module for setting a seed
import time
from typing import Dict, List, Union

import nltk
import numpy as np
# from gensim.models.doc2vec import Doc2Vec, TaggedDocument # Removed gensim import
from nltk.corpus import stopwords
from sklearn.metrics.pairwise import cosine_similarity

from jobhunter.textAnalysis import generate_gpt_embedding

# Set a seed for reproducibility
random.seed(42)

logging.basicConfig(level=logging.INFO)

nltk.download("stopwords", quiet=True)
nltk.download("punkt", quiet=True)
stop_words = set(stopwords.words("english"))

# Flag removed, always use OpenAI
# USE_OPENAI_EMBEDDINGS = True 

# --- Doc2Vec functions removed ---
# def preprocess_text(text: str):
#     ...
#
# def generate_doc2vec(sentences):
#     ...
# --- End Doc2Vec functions removed ---

def text_similarity(text1: str, text2: str) -> Union[float, Dict]:
    """
    This function calculates the similarity between two pieces of text using OpenAI embeddings with cosine similarity.
    
    Args:
    text1 (str): The first piece of text for comparison.
    text2 (str): The second piece of text for comparison.

    Returns:
    float or dict: A similarity score between 0 and 1, or a dictionary with error information.
    """
    # Initialize logger inside the function
    logger = logging.getLogger(__name__) 
    try:
        # Always use OpenAI embeddings
        logging.info("Calculating similarity using OpenAI embeddings")
        
        # Generate embeddings for both texts
        # The generate_gpt_embedding function already has rate limiting protection
        text1_embedding = generate_gpt_embedding(text1)
        
        # Add a small delay between calls to reduce chance of rate limiting
        time.sleep(0.5)
        
        text2_embedding = generate_gpt_embedding(text2)
        
        # Check if embeddings are valid (not zero vectors from errors)
        if not text1_embedding or all(v == 0.0 for v in text1_embedding):
            logger.warning("Failed to generate embedding for text1, cannot calculate similarity.")
            return 0.0
        if not text2_embedding or all(v == 0.0 for v in text2_embedding):
            logger.warning("Failed to generate embedding for text2, cannot calculate similarity.")
            return 0.0
        
        # Calculate cosine similarity between the two embeddings
        similarity_score = cosine_similarity([text1_embedding], [text2_embedding])[0][0]
        
        logging.info(f"OpenAI embedding similarity calculated: {similarity_score:.4f}")
        return similarity_score
            
    except Exception as e:
        logger.error(f"An error occurred while calculating text similarity: {e}")
        # Return a default value (0.0) instead of raising an exception to avoid breaking the application
        return 0.0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="takes the similarity of two texts")

    parser.add_argument("text1", metavar="text1", type=str, help="the first text")
    parser.add_argument("text2", metavar="text2", type=str, help="the second text")

    args = parser.parse_args()

    result = text_similarity(text1=args.text1, text2=args.text2)
    print(result)
