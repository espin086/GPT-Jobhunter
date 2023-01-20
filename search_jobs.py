import requests
import json


def search_linkedin_jobs(search_term, location, page=1):
    """
    1. It's taking in a search term and a location
    2. It's making a request to the linkedin jobs api
    3. It's returning the json object that the api returns
    """
    
    url = "https://linkedin-jobs-search.p.rapidapi.com/"
    payload = {
    	"search_terms": search_term,
    	"location": location,
    	"page": "1"
    }
    headers = {
    	"content-type": "application/json",
    	"X-RapidAPI-Key": "6f6bd1d225msh190d9617fc8a770p12307cjsn64b205138508",
    	"X-RapidAPI-Host": "linkedin-jobs-search.p.rapidapi.com"
    }
    
    response = requests.request("POST", url, json=payload, headers=headers)
    json_object = json.loads(response.text)
    return json_object
    

def main():
    results = search_linkedin_jobs(search_term="Director of Machine Learning", location = "Los Angeles", page=1)
    return results
    
main()
    



