import os
from typing import List

import numpy as np
import openai
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")

load_dotenv(dotenv_path)


# Get the API key from the environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")


def generate_gpt_embedding(text):
    """
    This function generates a GPT-3 embedding for the input text.

    Args:
        text (str): The text to generate an embedding for.

    Returns:
        list: A list of GPT-3 embeddings for the input text.
    """
    model = "text-embedding-ada-002"
    text = text.replace("\n", " ")
    return openai.Embedding.create(input=[text], model=model)["data"][0]["embedding"]


if __name__ == "__main__":
    print(generate_gpt_embedding("I like to eat pizza"))
