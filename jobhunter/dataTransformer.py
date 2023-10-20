import logging
from typing import List

from tqdm import tqdm
from pathlib import Path

from jobhunter import config
from jobhunter.extract_salary import extract_salary
from jobhunter.extract_text_from_site import get_text_in_url
from jobhunter.FileHandler import FileHandler
from jobhunter.text_similarity import text_similarity

logging.basicConfig(level=config.LOGGING_LEVEL)


class DataTransformer:
    def __init__(self, raw_path: str, processed_path: str, resume_path: str, data: List[dict]):
        self.resume_path = resume_path
        self.data = data
        self.file_handler = FileHandler(
            raw_path=raw_path, processed_path=processed_path
        )

    def delete_json_keys(self, *keys):
        for item in self.data:
            for key in keys:
                if key in item:
                    del item[key]

    def drop_variables(self):
        self.delete_json_keys("job_url", "company_name", "company_url")

    def remove_duplicates(self):
        tuples = [tuple(d.items()) for d in self.data]
        unique_tuples = set(tuples)
        self.data = [dict(t) for t in unique_tuples]

    def rename_keys(self, key_map):
        for item in self.data:
            for old_key, new_key in key_map.items():
                if old_key in item:
                    item[new_key] = item.pop(old_key)

    def convert_keys_to_lowercase(self, *keys):
        for item in self.data:
            for key in keys:
                if key in item:
                    item[key] = item[key].lower()

    def add_description_to_json_list(self):
        logging.info("gathering jobs from the web")
        for item in tqdm(self.data):
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

    def extract_salaries(self):
        for item in self.data:
            description = item.get("description")
            salary_low, salary_high = extract_salary(description)
            item["salary_low"] = (
                float(salary_low) if salary_low is not None else None
            )
            item["salary_high"] = (
                float(salary_high) if salary_high is not None else None
            )

    def compute_resume_similarity(self, resume_text):
        for item in tqdm(self.data):
            description = item.get("description")
            similarity = text_similarity(description, resume_text)
            item["resume_similarity"] = (
                float(similarity) if similarity is not None else None
            )

    def transform(self):
        key_map = {
            "linkedin_job_url_cleaned": "job_url",
            "job_title": "title",
            "job_location": "location",
            "posted_date": "date",
            "normalized_company_name": "company",
            "linkedin_company_url_cleaned": "company_url",
        }

        self.drop_variables()
        self.remove_duplicates()
        self.rename_keys(key_map)
        self.convert_keys_to_lowercase("title", "location", "company")
        self.add_description_to_json_list()
        self.extract_salaries()

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


if __name__ == "__main__":
    CWD_PATH = Path(os.getcwd())
    RAW_DATA_PATH = Path(f"{CWD_PATH}/temp/data/raw").resolve()
    PROCESSED_DATA_PATH = Path(f"{CWD_PATH}/temp/data/processed").resolve()
    RESUME_PATH = Path(f"{CWD_PATH}/temp/resumes/resume.txt").resolve()

    data = FileHandler.import_job_data_from_dir(dirpath="temp/data/raw")

    transformer = DataTransformer(
        raw_path=RAW_DATA_PATH,
        processed_path=PROCESSED_DATA_PATH,
        resume_path=RESUME_PATH,
        data=data,
    )

    transformer.transform()
