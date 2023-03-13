import json
import os
import time
import re
import numpy as np
import datetime
from pathlib import Path
from typing import List
from jobhunter.utils.extract_text_from_site import get_text_in_url
from jobhunter.utils.text_similarity import text_similarity

def import_job_data_from_dir(dirpath):
    data_list = []
    for filename in os.listdir(dirpath):
        if filename.startswith('linkedinjob') and filename.endswith('.json'):
            filepath = os.path.join(dirpath, filename)
            with open(filepath, 'r') as f:
                try:
                    data = json.load(f)
                    if all(key in data for key in ['job_url', 'linkedin_job_url_cleaned', 'company_name', 'company_url', 'linkedin_company_url_cleaned', 'job_title', 'job_location', 'posted_date', 'normalized_company_name']):
                        data_list.append(data)
                    else:
                        print("WARNING: raw data schema does not conform")
                except ValueError:
                    pass
    return data_list

def delete_json_keys(json_obj, *keys):
    # Loop through the keys to delete and remove them from the JSON object
    for key in keys:
        if key in json_obj:
            del json_obj[key]
    
    # Return the updated JSON object
    return json_obj

def drop_variables(raw_data):
    clean_data = []
    for job in raw_data:
        clean_data.append(delete_json_keys(job, "job_url", "company_name", "company_url"))
    return clean_data

def remove_duplicates(raw_data):
    tuples = [tuple(d.items()) for d in data]
    unique_tuples = set(tuples)
    unique_dicts = [dict(t) for t in unique_tuples]
    return unique_dicts


def rename_keys(json_list, key_map):
    """
    Rename keys in a list of dictionaries based on a key map.

    Args:
        json_list (list): A list of dictionaries.
        key_map (dict): A dictionary mapping old key names to new key names.

    Returns:
        list: A list of dictionaries with renamed keys.
    """
    # Create a new list to hold the renamed dictionaries
    renamed_list = []

    # Iterate over each dictionary in the list
    for dictionary in json_list:
        # Create a new dictionary to hold the renamed key-value pairs
        renamed_dict = {}

        # Iterate over each key-value pair in the dictionary
        for key, value in dictionary.items():
            # If the key is in the key map, rename it and add it to the renamed dictionary
            if key in key_map:
                renamed_dict[key_map[key]] = value
            # Otherwise, add the original key-value pair to the renamed dictionary
            else:
                renamed_dict[key] = value

        # Add the renamed dictionary to the renamed list
        renamed_list.append(renamed_dict)

    # Return the renamed list
    return renamed_list

def convert_keys_to_lowercase(json_list, *keys):
    for obj in json_list:
        for key in keys:
            if key in obj:
                obj[key] = obj[key].lower()
    return json_list


def add_description_to_json_list(json_list):
    """
    A function that loops through a JSON list, gets the value of the key 'job_url'
    from each item in the list, passes it to the function 'get_text_in_url', gets
    the output of the function and saves it to each item in the JSON list as the key
    'description'.
    """
    for item in json_list:
        job_url = item.get('job_url')
        if job_url:
            time.sleep(.25)
            try:
                description = get_text_in_url(job_url)
                item['description'] = description
            except:
                item['description'] = ''

        else:
            item['description'] = ''
            
    return json_list




def extract_salary(text):
    # Match for salaries like "$150,000.00" or "$150,000"
    salary_pattern_1 = r"\$([\d,]+)(?:\.(\d{2}))?"
    # Match for salaries like "$150K"
    salary_pattern_2 = r"\$([\d\.]+)(K)"
    # Match for salaries like "$125K-$150K" or "$150,000 - $350K"
    salary_pattern_3 = r"\$([\d,]+)(?:\.(\d{2}))?\s*(K)?\s*-\s*\$([\d,]+)(?:\.(\d{2}))?(K)?"
    
    # Find a match in the text for each pattern
    match1 = re.search(salary_pattern_1, text)
    match2 = re.search(salary_pattern_2, text)
    match3 = re.search(salary_pattern_3, text)
    
    if match3:
        # For salary ranges like "$125K-$150K" or "$150,000 - $350K"
        salary_low = float(match3.group(1).replace(',', '')) * 1000 if match3.group(3) == 'K' else float(match3.group(1).replace(',', ''))
        salary_high = float(match3.group(4).replace(',', '')) * 1000 if match3.group(6) == 'K' else float(match3.group(4).replace(',', ''))
    elif match2:
        # For salaries like "$150K"
        salary_low = salary_high = float(match2.group(1).replace(',', '')) * 1000
    elif match1:
        # For salaries like "$150,000.00" or "$150,000"
        salary_low = salary_high = float(match1.group(1).replace(',', '') + '.' + match1.group(2) if match1.group(2) else match1.group(1).replace(',', ''))
    else:
        salary_low = salary_high = None
    
    return salary_low, salary_high

def extract_salaries(json_list):
    # Create a new list to store the modified JSON dictionaries
    new_json_list = []
    
    for json_dict in json_list:
        # Extract the description from the current dictionary
        description = json_dict['description']
        
        # Use the extract_salary() function to extract the salary information
        salary_low, salary_high = extract_salary(description)

        if salary_low is not None:
            salary_low = float(salary_low)
        else:
            salary_low = None

        if salary_high is not None:
            salary_high = float(salary_high)
        else:
            salary_high = None
        
        # Add the salary information to the dictionary
        json_dict['salary_low'] = salary_low
        json_dict['salary_high'] = salary_high
        
        # Add the modified dictionary to the new list
        new_json_list.append(json_dict)
    
    return new_json_list


def read_resume_text(resume_file_path):
    """
    Read the text content of a resume file.
    
    Args:
        resume_file_path: The path to the resume file.
        
    Returns:
        The text content of the resume file.
    """
    with open(resume_file_path, 'r') as f:
        resume_text = f.read()
    return resume_text


def compute_resume_similarity(json_list, resume_text):
    """
    Compute the similarity between the resume text and the 'description' field of each JSON in the list.
    
    Args:
        json_list: A list of JSONs, each of which has a 'description' field.
        resume_text: The text content of the resume.
        
    Returns:
        A new list of JSONs, each of which has a 'resume_similarity' field added.
    """
    new_json_list = []
    for json_obj in json_list:
        description = json_obj.get('description')
        similarity = text_similarity(description, resume_text)
        if similarity is not None:
            similarity = float(similarity)
        else:
            similarity = None
        json_obj['resume_similarity'] = similarity
        new_json_list.append(json_obj)
    return new_json_list


def save_raw_data(data, source):
    """
    Saves dictionaries to a JSON file locally in the ../data/raw directory.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
    file_path = os.path.join("..", "data", "processed", f"{source}-{timestamp}.json")
    with open(file_path, "w") as f:
        json.dump(data, f)
    logging.info("Saved data to %s", file_path)
    return None

def save_raw_data_list(data_list, source):
    """
    Saves a list of dictionaries to individual JSON files locally in the ../data/raw directory.
    """
    for i, data in enumerate(data_list):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
        file_path = os.path.join("../../", "data", "processed", f"{source}-{i+1}-{timestamp}.json")
        with open(file_path, "w") as f:
            json.dump(data, f)
        print(f"INFO: saved data to {file_path}")
    return None

#----------main----------
resume = read_resume_text(resume_file_path='../resumes/resume.txt')


data = import_job_data_from_dir(dirpath="../../data/raw")
print(data)
data = drop_variables(raw_data=data)
data = remove_duplicates(raw_data=data)
key_map = {
    'linkedin_job_url_cleaned': 'job_url',
    'job_title': 'title',
    'job_location': 'location',
    'posted_date': 'date',
    'normalized_company_name': 'company',
    'linkedin_company_url_cleaned': 'company_url'
}
data = rename_keys(json_list=data, key_map=key_map)
data = convert_keys_to_lowercase(data, 'title', 'location', 'company')
data = add_description_to_json_list(json_list=data)
data = extract_salaries(json_list=data)
data = compute_resume_similarity(json_list=data, resume_text=resume)
save_raw_data_list(data_list=data, source='linkedinjobs')




