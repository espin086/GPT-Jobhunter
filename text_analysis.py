"""
This module provides a TextAnalyzer class that performs text analysis using a RapidAPI service. 
The class takes a string of text as input and provides methods to extract entities, determine sentiment, and detect personal information. 
The analyzed results are returned in a dictionary.
"""


import requests
import os
import json
import argparse
import pprint

pp = pprint.PrettyPrinter(indent=4)

class TextAnalyzer:
    """
    This class takes a string of text as input and uses the RapidAPI service to extract entities and sentiment.

    Attributes:
    text (str): The text input to be analyzed.
    
    Methods:
    extract_entities(): Extracts entities such as persons, organizations, and locations from the text.
    get_sentiment(): Determines the sentiment of the text, such as positive, negative, or neutral.
    """
    
    def __init__(self, text):
        self.text = text
        self.entities = None
        self.sentiment = None
        self.pii = None
        
        
    pass
    
    def extract_entities(self):
        """
        Makes a call to the RapidAPI entity extraction service to extract entities such as persons, organizations, and locations from the text.
        
        Returns:
        dict: A dictionary containing the extracted entities.
        """
        url = "https://text-entities-api.p.rapidapi.com/"
        querystring = {"text":self.text}
        payload = {
        	"key1": "value",
        	"key2": "value"
        }
        headers = {
        	"content-type": "application/json",
        	"X-RapidAPI-Key": os.environ.get('API_KEY_RAPIDAPI'),
        	"X-RapidAPI-Host": "text-entities-api.p.rapidapi.com"
        }
        
        response = requests.request("POST", url, json=payload, headers=headers, params=querystring)

        return response.json()
    
    
    def find_pii(self):
        """
        Use a text detection API to identify personal information in the given text.
        
        :return: A dictionary containing the results of the personal information detection.
        """
        url = "https://personal-info-detector.p.rapidapi.com/"

        querystring = {"text":self.text}
        
        payload = {
        	"key1": "value",
        	"key2": "value"
        }
        headers = {
        	"content-type": "application/json",
        	"X-RapidAPI-Key":  os.environ.get('API_KEY_RAPIDAPI'),
        	"X-RapidAPI-Host": "personal-info-detector.p.rapidapi.com"
        }
        
        response = requests.request("POST", url, json=payload, headers=headers, params=querystring)
        
        
        
        return response.json()
        
        
    def analyze(self):
        """
        Analyzes the text in the object and returns a dictionary containing the results of entity extraction, PII detection, and sentiment analysis.
        
        Returns:
            dict: a dictionary containing the analyzed results with keys:
                - "text": the input text
                - "entities": the results of entity extraction
                - "pii": the results of PII detection
        """
        result = {
            "entities":self.extract_entities(),
            "pii":self.find_pii(),
        }
        return result
        

def main(text):
    
    analysis = TextAnalyzer(text=text)
    result = analysis.analyze()
    
    entities = result['entities']['sentiment ']['Entities']
    pii = result['pii']['result ']['Entities']
    
    result = {'entities': entities, 'pii': pii}
    
    return result


if __name__ == "__main__":
        
    parser = argparse.ArgumentParser(description="This analysis text including key entities and sentiment.")
    parser.add_argument('text', metavar='text', type=str, help='one long text string to analyze')
    args = parser.parse_args()

    text = args.text.encode('utf-8')

    
    result = main(text)
    
    pp.pprint(result)
