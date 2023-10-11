import datetime
import json
import logging
import os
import re
import sys
from typing import List

import config
from extract_salary import extract_salary
from extract_text_from_site import get_text_in_url
from text_similarity import text_similarity
from tqdm import tqdm
from FileHandler import FileHandler

logging.basicConfig(level=config.LOGGING_LEVEL)

file_handler = FileHandler(
    raw_path="temp/data/raw", processed_path="temp/data/processed"
)


def delete_json_keys(json_obj, *keys):
    """
    Deletes the specified keys from a JSON object."""
    # Loop through the keys to delete and remove them from the JSON object
    for key in keys:
        if key in json_obj:
            del json_obj[key]

    # Return the updated JSON object
    return json_obj


def drop_variables(raw_data):
    """This function drops the variables that are not needed for the analysis."""
    clean_data = []
    for job in raw_data:
        clean_data.append(
            delete_json_keys(job, "job_url", "company_name", "company_url")
        )
    return clean_data


def remove_duplicates(raw_data):
    """
    Remove duplicate dictionaries from a list of dictionaries."""
    tuples = [tuple(d.items()) for d in raw_data]
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
    """Converts the values of the specified keys to lowercase."""
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
    logging.info("gathering jobs from the web")
    for item in tqdm(json_list):
        job_url = item.get("job_url")
        if job_url:
            try:
                description = get_text_in_url(job_url)
                item["description"] = description
            except Exception as e:
                logging.warning(f"Failed to get description for job {job_url}: {e}")
                item["description"] = ""
        else:
            item["description"] = ""

    return json_list


def extract_salaries(json_list):
    """
    Extracts salaries from the 'description' field of each JSON in the list.
    """
    # Create a new list to store the modified JSON dictionaries
    new_json_list = []

    for json_dict in json_list:
        # Extract the description from the current dictionary
        description = json_dict["description"]

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
        json_dict["salary_low"] = salary_low
        json_dict["salary_high"] = salary_high

        # Add the modified dictionary to the new list
        new_json_list.append(json_dict)

    return new_json_list


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
    for json_obj in tqdm(json_list):
        description = json_obj.get("description")
        similarity = text_similarity(description, resume_text)
        if similarity is not None:
            similarity = float(similarity)
        else:
            similarity = None
        json_obj["resume_similarity"] = similarity
        new_json_list.append(json_obj)
    return new_json_list


# ----------main----------
def transform():
    """
    This function transforms the raw data into a format that is ready for analysis.
    """
    resume = file_handler.read_resume_text(resume_file_path="temp/resumes/resume.txt")
    data = file_handler.import_job_data_from_dir(dirpath="temp/" + "data/raw")
    data = drop_variables(raw_data=data)
    data = remove_duplicates(raw_data=data)
    key_map = {
        "linkedin_job_url_cleaned": "job_url",
        "job_title": "title",
        "job_location": "location",
        "posted_date": "date",
        "normalized_company_name": "company",
        "linkedin_company_url_cleaned": "company_url",
    }
    data = rename_keys(json_list=data, key_map=key_map)
    data = convert_keys_to_lowercase(data, "title", "location", "company")
    data = add_description_to_json_list(json_list=data)
    data = extract_salaries(json_list=data)
    data = compute_resume_similarity(json_list=data, resume_text=resume)

    file_handler.save_data_list(
        data_list=data, source="linkedinjobs", sink=file_handler.processed_path
    )

    return None


if __name__ == "__main__":
    transform()
