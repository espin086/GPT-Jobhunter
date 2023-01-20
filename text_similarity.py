import requests
import json


def text_similarity(text1, text2):
    url = "https://twinword-text-similarity-v1.p.rapidapi.com/similarity/"
    
    payload = "text1={0}&text2={1}".format(text1,text2)
    headers = {
    	"content-type": "application/x-www-form-urlencoded",
    	"X-RapidAPI-Key": "6f6bd1d225msh190d9617fc8a770p12307cjsn64b205138508",
    	"X-RapidAPI-Host": "twinword-text-similarity-v1.p.rapidapi.com"
    }
    
    response = requests.request("POST", url, data=payload, headers=headers)
    json_object = json.loads(response.text)
    
    similarity={}
    
    similarity['similarity'] = json_object['similarity']
    
    return similarity
