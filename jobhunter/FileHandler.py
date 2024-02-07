"""
This code handles all of the local file movements for the project

"""

import datetime
import json
import logging
import os
import pprint
from pathlib import Path

import config


class FileHandler:
    """This class handles all of the local file movements for the project"""

    def __init__(self, raw_path, processed_path):
        """Initialize the class with the raw and processed paths"""
        self.raw_path = raw_path
        self.processed_path = processed_path
        self.pp = pprint.PrettyPrinter(indent=4)

        self.setup_logging()
        self.create_data_folders_if_not_exists()

    @staticmethod
    def setup_logging():
        """Setup logging configuration"""
        logging.basicConfig(
            level=config.LOGGING_LEVEL,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )

    def create_data_folders_if_not_exists(self):
        """
        Creates the data folders if they don't exist.
        """
        try:
            os.makedirs(self.raw_path, exist_ok=True)
            os.makedirs(self.processed_path, exist_ok=True)
            logging.info("Created data folders successfully.")

        except Exception as e:
            logging.error("An error occurred while creating data folders: %s", str(e))

    def load_json_files(self, directory):
        """This function loads all JSON files from a directory and returns a list of JSON objects."""
        logging.info("Loading JSON files from %s", directory)
        json_list = []
        for filename in os.listdir(directory):
            if filename.endswith(".json"):
                filepath = os.path.join(directory, filename)
                try:
                    with open(filepath, encoding="utf-8") as f:
                        json_obj = json.load(f)
                        json_list.append(json_obj)
                    logging.info("Successfully loaded %s", filename)
                except Exception as e:
                    logging.error("Failed to load %s: %s", filename, e)
        return json_list

    def read_resume_text(self, resume_file_path):
        """
        Read the text content of a resume file.

        Args:
            resume_file_path: The path to the resume file.

        Returns:
            The text content of the resume file.
        """
        try:
            with open(resume_file_path, "r", encoding="utf-8") as f:
                resume_text = f.read()
            return resume_text
        except FileNotFoundError as exc:
            logging.error("Resume file not found at path: %s", resume_file_path)
            raise FileNotFoundError(
                "Resume file not found at path: {}".format(resume_file_path)
            ) from exc
        except Exception as e:
            logging.error(
                f"Error reading resume file at path %s: %s", resume_file_path, e
            )
        return None

    def import_job_data_from_dir(
        self, dirpath, required_keys=None, filename_starts_with=None
    ):
        """
        This function imports the job data from the directory specified in the argument.
        """
        if required_keys is None:
            required_keys = [
                "job_url",
                "linkedin_job_url_cleaned",
                "company_name",
                "company_url",
                "linkedin_company_url_cleaned",
                "job_title",
                "job_location",
                "posted_date",
                "normalized_company_name",
            ]

        if filename_starts_with is None:
            filename_starts_with = (
                config.FILENAMES
            )  # Adjust to class property if needed

        data_list = [
            json.load(open(os.path.join(dirpath, filename), encoding="utf-8"))
            for filename in os.listdir(dirpath)
            if filename.startswith(filename_starts_with) and filename.endswith(".json")
        ]

        valid_data_list = [
            data for data in data_list if all(key in data for key in required_keys)
        ]

        invalid_files = set(os.listdir(dirpath)) - set(
            os.path.join(dirpath, data.get("filename", "")) for data in valid_data_list
        )

        for filename in invalid_files:
            logging.warning(
                "WARNING: raw data schema does not conform in file %s", filename
            )

        logging.info("INFO: Imported data list: %s", valid_data_list)
        return valid_data_list

    def delete_files(self, dir_path):
        """Delete files in a directory."""
        logging.info(f"Starting to delete files in directory: {dir_path}")

        for root, dirs, files in os.walk(dir_path):
            for filename in files:
                file_path = os.path.join(root, filename)
                try:
                    os.remove(file_path)
                    print(f"Deleted file: {file_path}")
                    logging.info(f"Successfully deleted file: {file_path}")
                except OSError as e:
                    print(f"Error deleting file: {file_path} - {e}")
                    logging.error(f"Error deleting file: {file_path} - {e}")

        logging.info(f"Completed deleting files in directory: {dir_path}")

    def delete_local(self):
        """Delete local files"""
        logging.info("Starting 'delete_local' function.")

        for dir_path in [self.raw_path, self.processed_path]:
            try:
                self.delete_files(dir_path=dir_path)
                logging.info(f"Successfully deleted files in '{dir_path}'")
            except Exception as e:
                logging.error(f"Failed to delete files in '{dir_path}': {e}")

        logging.info("Finished delete local files function.")

    def save_data(self, data, source, sink):
        """
        Saves a dictionary to a JSON file locally in the specified sink directory.
        """
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
            file_path = os.path.join(sink, f"{source}-{timestamp}.json")

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f)

            logging.info("Saved job successfully.")
            logging.debug("Saved data to %s", file_path)

        except Exception as e:
            logging.error("An error occurred while saving data: %s", str(e))

    def save_data_list(self, data_list, source, sink):
        """
        Saves a list of dictionaries to individual JSON files locally in the specified sink directory.
        """
        required_keys = [
            "job_url",
            "title",
            "company_url",
            "location",
            "date",
            "company",
            "description",
            "salary_low",
            "salary_high",
            "resume_similarity",
        ]

        for i, data in enumerate(data_list):
            # Check if the data contains all the required keys
            if all(key in data for key in required_keys):
                # Using the existing save_data method to store each dictionary
                self.save_data(data, "{}-{}".format(source, i + 1), sink)
            else:
                missing_keys = [key for key in required_keys if key not in data]
                logging.warning(
                    "Data item %s is missing required keys: %s",
                    i + 1,
                    ", ".join(missing_keys),
                )


if __name__ == "__main__":
    logging.info("Application started.")
    # You can change these paths as needed when creating an instance
    file_handler = FileHandler(
        raw_path="temp/data/raw", processed_path="temp/data/processed"
    )
    file_handler.delete_local()
    logging.info("Application finished.")
