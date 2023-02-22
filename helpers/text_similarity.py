"""
This module calculates the similarity between two pieces of text using the Twinword Text Similarity API. It takes in two strings as input and makes a POST request to the API with the provided text. The API returns a json object containing the similarity score between the two texts. The function returns a dictionary containing the similarity score. The module also has a command line interface that takes the two texts as input and prints the similarity score in json format.

To use the module, import it and call the text_similarity function with two strings as arguments. The function returns a dictionary containing the similarity score between the two texts as a key-value pair where key is 'similarity' and value is a float between 0 and 1.

To use the command line interface, run the module as the main program and pass the two texts as command line arguments. The command line interface will print the similarity score in json format.

If an exception is encountered during the API request, the error will be logged.
"""


import requests
import json
import os
import logging
import pprint
import argparse
import aws_secrets_manager

logging.basicConfig(level=logging.INFO)
pp = pprint.PrettyPrinter(indent=4)


def text_similarity(text1, text2):
    """
    This function calculates the similarity between two pieces of text using the Twinword Text Similarity API. It takes in two strings, text1 and text2, as input and makes a POST request to the API with the provided text. The API returns a json object containing the similarity score between the two texts. The function returns a dictionary containing the similarity score.

    Args:
    text1 (str): The first piece of text for comparison.
    text2 (str): The second piece of text for comparison.

    Returns:
    dict: A dictionary containing the similarity score between the two texts as a key-value pair where key is 'similarity' and value is a float between 0 and 1.

    Raises:
    Exception: If an exception is encountered during the API request, it is logged as an error.
    """
    try:
        url = "https://twinword-text-similarity-v1.p.rapidapi.com/similarity/"

        payload = "text1={0}&text2={1}".format(text1, text2)
        headers = {
            "content-type": "application/x-www-form-urlencoded",
            "X-RapidAPI-Key": aws_secrets_manager.get_secret(
                secret_name="rapidapikey", region_name="us-west-1"
            )["rapidapikey"],
            "X-RapidAPI-Host": "twinword-text-similarity-v1.p.rapidapi.com",
        }

        response = requests.request("POST", url, data=payload, headers=headers)
        json_object = json.loads(response.text)

        similarity = {}

        similarity["similarity"] = json_object["similarity"]
        logging.info("Text similarity calculated")

        return similarity
    except Exception as e:
        logging.error(f"An error occured while making the API request:: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="takes the similarity of two texts")

    parser.add_argument("text1", metavar="text1", type=str, help="the first text")
    parser.add_argument("text2", metavar="text2", type=str, help="the second text")

    args = parser.parse_args()

    result = text_similarity(text1=args.text1, text2=args.text1)

    pp.pprint(result)
