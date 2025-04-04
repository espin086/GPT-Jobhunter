import json
import logging
import os
import time
import random
from typing import List, Union

import numpy as np
from openai import OpenAI, APIError, RateLimitError  # Correct direct imports
import streamlit as st
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")

load_dotenv(dotenv_path)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)

# Rate limit handling constants
MAX_RETRIES = 5
INITIAL_RETRY_DELAY = 1.0
MAX_RETRY_DELAY = 60.0
# Batch size for synchronous OpenAI calls (adjust as needed)
OPENAI_EMBEDDING_BATCH_SIZE = 100 

def get_openai_api_key():
    """
    Get the OpenAI API key from session state or environment variable
    
    Returns:
        str: The OpenAI API key
    """
    # First check if it's in the session state (set through UI)
    if "openai_api_key" in st.session_state and st.session_state.openai_api_key:
        api_key = st.session_state.openai_api_key
        
        # Check if it's a placeholder or demo key
        if _is_placeholder_key(api_key):
            logger.warning("API key in session state appears to be a placeholder value")
            # Fall back to environment variable
            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key and not _is_placeholder_key(api_key):
                masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
                logger.info(f"Using OpenAI API key from environment variable instead (masked: {masked_key})")
                return api_key
            else:
                logger.error("Both session state and environment variable API keys are invalid")
                return None
        else:
            # Valid key from session state
            masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
            logger.info(f"Using OpenAI API key from session state (masked: {masked_key})")
            return api_key
    
    # Then fall back to environment variable
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        if _is_placeholder_key(api_key):
            logger.error("API key in environment variable appears to be a placeholder value")
            return None
        
        masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***" 
        logger.info(f"Using OpenAI API key from environment variable (masked: {masked_key})")
        return api_key
    else:
        logger.warning("No OpenAI API key found in session state or environment variables")
        return None

def _is_placeholder_key(api_key):
    """Check if the API key appears to be a placeholder or demo value"""
    # Common placeholder texts
    placeholders = [
        "your", "api", "key", "here", "demo", "example", "sample", "test", "placeholder",
        "sk-demo", "sk-test", "enter", "insert", "provide"
    ]
    
    # Convert to lowercase for case-insensitive comparison
    key_lower = api_key.lower()
    
    # Check if key contains placeholder text
    for placeholder in placeholders:
        if placeholder in key_lower:
            return True
            
    # Check if key is too short to be valid
    if len(api_key) < 20:  # OpenAI keys are typically much longer
        return True
        
    # Check format - most OpenAI keys start with "sk-"
    if not key_lower.startswith("sk-"):
        return True
    
    return False

def generate_gpt_embedding(text: str) -> List[float]:
    """
    Generate embeddings for input text using OpenAI's embedding API.
    
    Args:
        text: Input text to generate embeddings for
        
    Returns:
        List of floats representing the embedding vector
    """
    # Get the API key
    api_key = get_openai_api_key()
    
    if not api_key:
        error_msg = "OpenAI API key not found or is a placeholder value. Please provide a valid API key in the settings."
        logger.error(error_msg)
        return [0.0] * 1536  # Return zero embedding to avoid breaking the app
    
    # Initialize the OpenAI client with the API key (new way in v1.0+)
    client = OpenAI(api_key=api_key)
    logger.info("OpenAI client initialized successfully")
    
    # Truncate the text if it's too long (to stay within OpenAI's token limits)
    max_chars = 8000  # Approximate character limit
    if len(text) > max_chars:
        text = text[:max_chars]
        logger.warning(f"Text truncated to {max_chars} characters for embedding generation")
    
    # Setup for retry logic
    retry_count = 0
    retry_delay = INITIAL_RETRY_DELAY
    
    while retry_count <= MAX_RETRIES:
        try:
            # Call the OpenAI API to generate embeddings (using modern API format)
            logger.info(f"Calling OpenAI embeddings API with text of length {len(text)}")
            response = client.embeddings.create(
                input=text, 
                model="text-embedding-3-small"  # Updated to newer model
            )
            
            # Extract the embedding vector from the response
            embedding = response.data[0].embedding
            logger.info(f"Successfully generated embedding of dimension {len(embedding)} for text")
            
            return embedding
            
        except RateLimitError as e:
            retry_count += 1
            
            if retry_count > MAX_RETRIES:
                logger.error(f"Maximum retries reached. Rate limit exceeded: {e}")
                break
                
            # Add jitter to the delay to prevent synchronized retries
            jitter = random.uniform(0, 0.1 * retry_delay)
            wait_time = min(retry_delay + jitter, MAX_RETRY_DELAY)
            
            logger.warning(f"Rate limit exceeded. Retrying in {wait_time:.2f} seconds (retry {retry_count}/{MAX_RETRIES})")
            time.sleep(wait_time)
            
            # Exponential backoff
            retry_delay *= 2
            
        except APIError as e:
            # APIError in newer versions doesn't have a status_code attribute, 
            # check the error message instead for rate limiting clues
            if "429" in str(e) or "rate limit" in str(e).lower() or "too many requests" in str(e).lower():
                retry_count += 1
                
                if retry_count > MAX_RETRIES:
                    logger.error(f"Maximum retries reached. API rate limit exceeded: {e}")
                    break
                    
                # Add jitter to the delay to prevent synchronized retries
                jitter = random.uniform(0, 0.1 * retry_delay)
                wait_time = min(retry_delay + jitter, MAX_RETRY_DELAY)
                
                logger.warning(f"API rate limit exceeded. Retrying in {wait_time:.2f} seconds (retry {retry_count}/{MAX_RETRIES})")
                time.sleep(wait_time)
                
                # Exponential backoff
                retry_delay *= 2
            else:
                logger.error(f"API error: {e}")
                break
                
        except Exception as e:
            logger.error(f"Error getting embedding from OpenAI: {e}")
            masked_key = f"{api_key[:4]}...{api_key[-4:]}" if api_key and len(api_key) > 8 else "API key is empty or too short"
            logger.error(f"API key used (masked): {masked_key}")
            break
    
    # If we've reached here, we've either exceeded retries or encountered a non-retriable error
    logger.warning("Failed to generate embeddings after retries or due to errors. Returning zero vector.")
    # Return a vector with the dimension for the text-embedding-3-small model
    return [0.0] * 1536

def generate_gpt_embeddings_batch(texts: List[str]) -> List[Union[List[float], None]]:
    """
    Generate embeddings for a batch of input texts using OpenAI's embedding API.

    Args:
        texts: A list of input texts to generate embeddings for.

    Returns:
        A list containing embedding vectors (List[float]) for each input text.
        If an embedding for a specific text fails within the batch (or the whole batch fails),
        its corresponding entry in the list might be None or potentially a zero vector,
        depending on error type. Returns an empty list if the initial API key check fails.
    """
    if not texts:
        logger.info("Received empty list for batch embedding. Returning empty list.")
        return []

    api_key = get_openai_api_key()
    if not api_key:
        error_msg = "OpenAI API key not found or invalid. Cannot generate embeddings."
        logger.error(error_msg)
        # Return a list of Nones matching the input size to signal failure for all
        return [None] * len(texts) 

    client = OpenAI(api_key=api_key)
    # logger.info(f"OpenAI client initialized for batch embedding of {len(texts)} texts.")

    # Truncate texts individually if too long
    max_chars = 8000 # Should align with model limits (e.g., text-embedding-3-small has 8191 tokens)
    truncated_texts = []
    for i, text in enumerate(texts):
        if len(text) > max_chars:
            truncated_texts.append(text[:max_chars])
            # logger.warning(f"Text at index {i} truncated to {max_chars} characters for batch embedding.")
        else:
            truncated_texts.append(text)

    retry_count = 0
    retry_delay = INITIAL_RETRY_DELAY

    while retry_count <= MAX_RETRIES:
        try:
            # logger.info(f"Calling OpenAI embeddings API for batch of size {len(truncated_texts)} (Retry {retry_count}) ...")
            response = client.embeddings.create(
                input=truncated_texts, 
                model="text-embedding-3-small" # Use the appropriate model
            )
            
            # Extract embeddings - response.data should be a list of Embedding objects
            # Assuming the order matches the input order as per documentation
            embeddings = [item.embedding for item in response.data]
            logger.info(f"Successfully generated {len(embeddings)} embeddings from batch.")
            
            # Basic validation: Check if the number of embeddings matches the input
            if len(embeddings) != len(texts):
                 logger.error(f"Mismatch in batch embedding results: Expected {len(texts)}, Got {len(embeddings)}. Returning Nones.")
                 return [None] * len(texts)
                 
            return embeddings # Return the list of embedding vectors

        except RateLimitError as e:
            retry_count += 1
            if retry_count > MAX_RETRIES:
                logger.error(f"Maximum retries reached for batch. Rate limit exceeded: {e}")
                break
            jitter = random.uniform(0, 0.1 * retry_delay)
            wait_time = min(retry_delay + jitter, MAX_RETRY_DELAY)
            logger.warning(f"Rate limit exceeded for batch. Retrying in {wait_time:.2f} seconds (retry {retry_count}/{MAX_RETRIES})...")
            time.sleep(wait_time)
            retry_delay *= 2

        except APIError as e:
            # Handle potential API errors, including rate limits disguised as APIError
            if "429" in str(e) or "rate limit" in str(e).lower() or "too many requests" in str(e).lower():
                retry_count += 1
                if retry_count > MAX_RETRIES:
                    logger.error(f"Maximum retries reached for batch. API rate limit error: {e}")
                    break
                jitter = random.uniform(0, 0.1 * retry_delay)
                wait_time = min(retry_delay + jitter, MAX_RETRY_DELAY)
                logger.warning(f"API rate limit error for batch. Retrying in {wait_time:.2f} seconds (retry {retry_count}/{MAX_RETRIES})...")
                time.sleep(wait_time)
                retry_delay *= 2
            else:
                logger.error(f"API error during batch embedding: {e}")
                break # Non-retriable API error for the batch

        except Exception as e:
            logger.error(f"Unexpected error during batch embedding: {e}", exc_info=True)
            break # Non-retriable unexpected error

    # If loop finishes without returning, it means failure after retries or non-retriable error
    logger.error(f"Failed to generate embeddings for batch after {retry_count} retries.")
    # Return a list of Nones matching the input size to indicate failure for all items in this batch
    return [None] * len(texts)


if __name__ == "__main__":
    # Example usage:
    test_texts = [
        "This is the first sentence for batching.",
        "Here is another sentence, slightly longer.",
        "A third one to test the batch call."
    ]
    batch_embeddings = generate_gpt_embeddings_batch(test_texts)
    
    if batch_embeddings:
        print(f"Received {len(batch_embeddings)} embeddings.")
        for i, emb in enumerate(batch_embeddings):
            if emb:
                print(f"Embedding {i+1} length: {len(emb)}")
            else:
                print(f"Embedding {i+1}: Failed")
    else:
        print("Batch embedding failed entirely.")
    
    # Test deprecated single function call
    print("\nTesting single embedding call (via batch function):")
    single_embedding = generate_gpt_embedding("Test single embedding.")
    if single_embedding and any(v != 0.0 for v in single_embedding):
        print(f"Single embedding length: {len(single_embedding)}")
    else:
        print("Single embedding failed or returned zero vector.")
