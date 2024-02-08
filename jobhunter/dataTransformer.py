"""Transforms the raw data into a format that is ready for analysis."""

import concurrent.futures
import logging
from pathlib import Path
from typing import List

from tqdm import tqdm

from jobhunter import config
from jobhunter.extract_salary import extract_salary
from jobhunter.extract_text_from_site import get_text_in_url
from jobhunter.FileHandler import FileHandler
from jobhunter.text_similarity import text_similarity

logging.basicConfig(level=config.LOGGING_LEVEL)

class DataTransformer:
    """Transforms the raw data into a format that is ready for analysis."""

    def __init__(
        self, raw_path: str, processed_path: str, resume_path: str, data: List[dict]
    ):
        self.resume_path = resume_path
        self.data = data
        self.file_handler = FileHandler(
            raw_path=raw_path, processed_path=processed_path
        )

    def delete_json_keys(self, *keys):
        """Deletes the specified keys from the json data."""
        for item in self.data:
            for key in keys:
                if key in item:
                    del item[key]

    def drop_variables(self):
        """Drops the variables that are not needed for analysis."""
        self.delete_json_keys("job_url", "company_name", "company_url")

    def remove_duplicates(self):
        """Removes duplicate entries from the json data."""
        tuples = [tuple(d.items()) for d in self.data]
        unique_tuples = set(tuples)
        self.data = [dict(t) for t in unique_tuples]

    def rename_keys(self, key_map):
        """Renames the keys in the json data."""
        for item in self.data:
            for old_key, new_key in key_map.items():
                if old_key in item:
                    item[new_key] = item.pop(old_key)

    def convert_keys_to_lowercase(self, *keys):
        """Converts the specified keys to lowercase."""
        for item in self.data:
            for key in keys:
                if key in item:
                    item[key] = item[key].lower()

    def compute_resume_similarity(self, resume_text):
        """Computes the similarity between the job description and the resume."""
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []
            for item in self.data:
                description = item.get("description")
                future = executor.submit(text_similarity, description, resume_text)
                futures.append((item, future))

            for item, future in futures:
                similarity = future.result()
                item["resume_similarity"] = (
                    float(similarity) if isinstance(similarity, (float, int)) else None
                )

    def transform(self):
        """Transforms the raw data into a format that is ready for analysis."""

        key_map = {
            'job_posted_at_datetime_utc': 'date',
            'job_title': 'title',
            'employer_name': 'company',
            'employer_logo': 'company_logo',
            'employer_website': 'company_url',
            'employer_company_type': 'company_type',
            'job_employment_type': 'job_type',
            'job_is_remote': 'job_is_remote',
            'job_offer_expiration_datetime_utc': 'job_offer_expiration_date',
            'job_min_salary': 'salary_low',
            'job_max_salary': 'salary_high',
            'job_salary_currency': 'salary_currency',
            'job_salary_period': 'salary_period',
            'job_benfits': 'job_benfits',
            'job_city': 'city',
            'job_state': 'state',
            'job_country': 'country',
            'apply_options': 'apply_options',
            'job_required_skills': 'required_skills',
            'job_required_experience': 'required_experience',
            'job_required_education': 'required_education',
            'job_description': 'description',
            'job_highlights': 'highlights'
        }

        self.drop_variables()
        self.remove_duplicates()
        self.rename_keys(key_map)
        self.convert_keys_to_lowercase("title", "location", "company")

        if Path(self.resume_path).exists():
            resume = self.file_handler.read_resume_text(
                resume_file_path=self.resume_path
            )
            self.compute_resume_similarity(resume_text=resume)

        self.file_handler.save_data_list(
            data_list=self.data,
            source="linkedinjobs",
            sink=self.file_handler.processed_path,
        )


class Main:
    def __init__(self):
        self.file_handler = FileHandler()
        self.data = self.file_handler.import_job_data_from_dir(
            dirpath=config.RAW_DATA_PATH
        )

        self.transformer = DataTransformer(
            raw_path=str(config.RAW_DATA_PATH),
            processed_path=str(config.PROCESSED_DATA_PATH),
            resume_path=str(config.RESUME_PATH),
            data=self.data,
            file_handler=self.file_handler,
        )

    def run(self):
        self.transformer.transform()


if __name__ == "__main__":
    main = Main()
    main.run()