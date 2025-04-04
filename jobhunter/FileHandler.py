import datetime
import json
import logging
import os
import pprint
from pathlib import Path

from jobhunter import config

# import config


class FileHandler:
    """This class handles all of the local file movements for the project"""

    def __init__(self, raw_path=None, processed_path=None):
        """
        Initialize the class with the raw and processed paths.
        Uses paths from config.py by default if none provided.
        """
        self.raw_path = raw_path if raw_path else config.RAW_DATA_PATH
        self.processed_path = processed_path if processed_path else config.PROCESSED_DATA_PATH
        self.pp = pprint.PrettyPrinter(indent=4)

        # Convert to Path objects if they aren't already
        if not isinstance(self.raw_path, Path):
            self.raw_path = Path(self.raw_path)
        if not isinstance(self.processed_path, Path):
            self.processed_path = Path(self.processed_path)

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
            self.raw_path.mkdir(parents=True, exist_ok=True)
            self.processed_path.mkdir(parents=True, exist_ok=True)
            logging.info("Created data folders successfully.")

        except Exception as e:
            logging.error("An error occurred while creating data folders: %s", str(e))

    def load_json_files(self, directory):
        """This function loads all JSON files from a directory and returns a list of JSON objects."""
        directory_path = Path(directory)
        logging.info("Loading JSON files from %s", directory_path)
        json_list = []
        
        if not directory_path.exists():
            logging.warning(f"Directory {directory_path} does not exist")
            return json_list
            
        for file_path in directory_path.glob("*.json"):
            try:
                with open(file_path, encoding="utf-8") as f:
                    json_obj = json.load(f)
                    json_list.append(json_obj)
                logging.info("Successfully loaded %s", file_path.name)
            except Exception as e:
                logging.error("Failed to load %s: %s", file_path.name, e)
        return json_list

    def read_resume_text(self, resume_file_path):
        """
        Read the text content of a resume file.

        Args:
            resume_file_path: The path to the resume file.

        Returns:
            The text content of the resume file.
        """
        path = Path(resume_file_path)
        try:
            with open(path, "r", encoding="utf-8") as f:
                resume_text = f.read()
            return resume_text
        except FileNotFoundError as exc:
            logging.error("Resume file not found at path: %s", path)
            raise FileNotFoundError(
                f"Resume file not found at path: {path}"
            ) from exc
        except Exception as e:
            logging.error(
                f"Error reading resume file at path %s: %s", path, e
            )
        return None

    def import_job_data_from_dir(self, dirpath):
        """
        This function imports the job data from the directory specified in the argument.
        """
        dirpath = Path(dirpath)
        filename_starts_with = "jobs"
        selected_keys = config.SELECTED_KEYS

        data_list = []
        if not dirpath.exists():
            logging.warning(f"Directory {dirpath} does not exist")
            return data_list
            
        for file_path in dirpath.glob(f"{filename_starts_with}*.json"):
            try:
                with open(file_path, encoding="utf-8") as file:
                    data = json.load(file)

                    # If selected_keys is provided, filter and add missing keys
                    if selected_keys:
                        filtered_data = {
                            key: data.get(key, None) for key in selected_keys
                        }
                        data_list.append(filtered_data)
                    else:
                        data_list.append(data)
            except Exception as e:
                logging.error(f"Error reading file {file_path}: {str(e)}")

        if not data_list:
            logging.warning(f"No valid job data files found in {dirpath}")
            
        logging.info("Imported %d job data items", len(data_list))
        return data_list

    def delete_files(self, dir_path):
        """Delete files in a directory."""
        dir_path = Path(dir_path)
        logging.info(f"Starting to delete files in directory: {dir_path}")
        
        if not dir_path.exists():
            logging.warning(f"Directory {dir_path} does not exist")
            return

        for file_path in dir_path.glob("**/*"):
            if file_path.is_file():
                try:
                    file_path.unlink()
                    logging.info(f"Successfully deleted file: {file_path}")
                except OSError as e:
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
            sink_path = Path(sink)
            sink_path.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
            file_path = sink_path / f"{source}-{timestamp}.json"

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
            "date",
            "company",
            "company_url",
            "company_type",
            "job_type",
            "job_is_remote",
            "job_apply_link",
            "job_offer_expiration_date",
            "salary_low",
            "salary_high",
            "salary_currency",
            "salary_period",
            "job_benefits",
            "city",
            "state",
            "apply_options",
            "required_skills",
            "required_experience",
            "description",
            "highlights",
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
    # Use config paths by default
    file_handler = FileHandler()
    file_handler.delete_local()
    logging.info("Application finished.")
