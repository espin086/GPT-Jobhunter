import concurrent.futures
import logging
import time
from pathlib import Path
from typing import Dict, List

# Use the correct import for config within the package
from jobhunter import config
from jobhunter.FileHandler import FileHandler
from jobhunter.text_similarity import text_similarity

# Remove commented out alternative imports
# from config import LOGGING_LEVEL
# from FileHandler import FileHandler
# from text_similarity import text_similarity


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
        self.delete_json_keys(
            "employer_logo",
            "job_publisher",
            "job_id",
            "job_apply_is_direct",
            "job_apply_quality_score",
            "job_posted_at_timestamp",
            "job_latitude",
            "job_longitude",
            "job_google_link",
            "job_offer_expiration_timestamp",
            "job_experience_in_place_of_education",
            "job_job_title",
            "job_posting_language",
            "job_onet_soc",
            "job_onet_job_zone",
            "job_naics_code",
            "job_naics_name",
        )

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

    def concatenate_apply_links(self):
        """Concatenates all apply links from apply_options."""
        for item in self.data:
            apply_options = item.get("apply_options", [])
            apply_links = [
                option.get("apply_link", "") if isinstance(option, dict) else ""
                for option in apply_options
            ]
            concatenated_links = "\n".join(apply_links)
            item["apply_options"] = concatenated_links

    def transform_required_experience(self):
        """Transforms the required_experience dictionary into the desired format."""
        for item in self.data:
            required_experience = item.get("required_experience", {})
            # Check if required_experience is None or not a dictionary
            if required_experience is None or not isinstance(required_experience, dict):
                # Set to empty string or empty object as appropriate
                item["required_experience"] = ""
                continue
                
            formatted_experience = ", \n".join(
                f"{key}: {value}" for key, value in required_experience.items()
            )
            item["required_experience"] = formatted_experience

    def transform_required_education(self):
        """Transforms the required_education dictionary into the desired format."""
        for item in self.data:
            required_education = item.get("required_education", {})
            # Check if required_education is None or not a dictionary
            if required_education is None or not isinstance(required_education, dict):
                # Set to empty string or empty object as appropriate
                item["required_education"] = ""
                continue
                
            formatted_education = ", \n".join(
                f"{key}: {value}" for key, value in required_education.items()
            )
            item["required_education"] = formatted_education

    def transform_highlights(self):
        """
        Transforms the highlights dictionary into the desired format.
        """
        for item in self.data:
            highlights = item.get("highlights", {})
            # Check if highlights is None or not a dictionary
            if highlights is None or not isinstance(highlights, dict):
                # Set to empty string or empty object as appropriate
                item["highlights"] = ""
                continue
                
            formatted_highlights = ", ".join(
                [
                    f"\n{key}:\n {', '.join(values)}"
                    for key, values in highlights.items()
                ]
            )
            item["highlights"] = formatted_highlights

    def transform_job_is_remote(self):
        """
        Transform the 'job_is_remote' field by replacing 1 with 'yes' and 0 with 'no'.
        """
        for entry in self.data:
            if "job_is_remote" in entry:
                entry["job_is_remote"] = (
                    "Remote" if entry["job_is_remote"] == True else "Not Remote"
                )

    def transform_single_skills(self):
        """
        Transform 'required_skills' field from a list to a single string if it has only one item.
        """
        for entry in self.data:
            if "required_skills" in entry and isinstance(
                entry["required_skills"], list
            ):
                skills_list = entry["required_skills"]
                if len(skills_list) == 1:
                    entry["required_skills"] = skills_list[0]
                elif len(skills_list) > 1:
                    entry["required_skills"] = ", \n".join(skills_list)

    def transform_job_benefits(self):
        """
        Transform 'job_benefits' field from a list to a single string if it has only one item.
        """
        for entry in self.data:
            if "job_benefits" in entry and isinstance(entry["job_benefits"], list):
                skills_list = entry["job_benefits"]
                if len(skills_list) == 1:
                    entry["job_benefits"] = skills_list[0]
                elif len(skills_list) > 1:
                    entry["job_benefits"] = ", \n".join(skills_list)

    def compute_resume_similarity(self, resume_text):
        """
        Computes the similarity between the job description and the resume SEQUENTIALLY.
        """
        # Constants for rate limiting (less critical now but keep for potential future use)
        # BATCH_SIZE = 5  # Number of jobs to process in a batch
        # BATCH_DELAY = 10  # Seconds to wait between batches
        
        # Log the total number of jobs to process
        total_jobs = len(self.data)
        logging.info(f"Computing similarity for {total_jobs} jobs sequentially...")
        
        processed_count = 0
        # Process jobs sequentially
        for i, item in enumerate(self.data):
            logging.info(f"Processing job {i+1}/{total_jobs}")
            description = item.get("description")
            if not description:
                item["resume_similarity"] = 0.0
                logging.warning(f"Job {item.get('primary_key', 'Unknown')} has no description, setting similarity to 0")
                continue
                
            try:
                similarity = text_similarity(description, resume_text)
                item["resume_similarity"] = (
                    float(similarity) if isinstance(similarity, (float, int)) else 0.0
                )
                logging.info(f"Computed similarity for job: {item.get('title', 'Unknown')} - {item['resume_similarity']:.2f}")
                processed_count += 1
                # Add a small delay between individual calls to avoid hitting rate limits too fast
                time.sleep(0.5) 
            except Exception as e:
                logging.error(f"Error computing similarity for job {item.get('primary_key', 'Unknown')}: {e}")
                item["resume_similarity"] = 0.0
        
        logging.info(f"Completed similarity computation for {processed_count}/{total_jobs} jobs")

    def transform(self):
        """Transforms the raw data into a format that is ready for analysis."""

        key_map = {
            "job_id": "id",
            "job_posted_at_datetime_utc": "date",
            "job_title": "title",
            "employer_name": "company",
            "job_apply_link": "job_apply_link",
            "employer_logo": "company_logo",
            "employer_website": "company_url",
            "employer_company_type": "company_type",
            "job_employment_type": "job_type",
            "job_is_remote": "job_is_remote",
            "job_offer_expiration_datetime_utc": "job_offer_expiration_date",
            "job_min_salary": "salary_low",
            "job_max_salary": "salary_high",
            "job_salary_currency": "salary_currency",
            "job_salary_period": "salary_period",
            "job_benefits": "job_benefits",
            "job_city": "city",
            "job_state": "state",
            "job_country": "country",
            "apply_options": "apply_options",
            "job_required_skills": "required_skills",
            "job_required_experience": "required_experience",
            "job_required_education": "required_education",
            "job_description": "description",
            "job_highlights": "highlights",
        }

        self.drop_variables()
        self.rename_keys(key_map)
        self.concatenate_apply_links()
        self.transform_required_experience()
        self.transform_required_education()
        self.transform_highlights()
        self.transform_job_is_remote()
        self.transform_single_skills()
        self.transform_job_benefits()

        if Path(self.resume_path).exists():
            resume = self.file_handler.read_resume_text(
                resume_file_path=self.resume_path
            )
            self.compute_resume_similarity(resume_text=resume)

        self.file_handler.save_data_list(
            data_list=self.data,
            source="jobs",
            sink=self.file_handler.processed_path,
        )


class Main:
    def __init__(self):
        # Explicitly import config here
        from jobhunter import config 
        self.file_handler = FileHandler(
            raw_path=config.RAW_DATA_PATH, processed_path=config.PROCESSED_DATA_PATH
        )
        self.data = self.file_handler.import_job_data_from_dir(
            dirpath=config.RAW_DATA_PATH
        )

        self.transformer = DataTransformer(
            raw_path=str(config.RAW_DATA_PATH),
            processed_path=str(config.PROCESSED_DATA_PATH),
            resume_path=str(config.RESUME_PATH),
            data=self.data,
        )

    def run(self):
        self.transformer.transform()


if __name__ == "__main__":
    # Explicitly import config here as well for the main block
    from jobhunter import config 
    main = Main()
    main.run()
