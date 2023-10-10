import logging
import os
import pprint

import config

# Initialize pretty printer and logging
pp = pprint.PrettyPrinter(indent=4)
logging.basicConfig(
    level=config.LOGGING_LEVEL, format="%(asctime)s - %(levelname)s - %(message)s"
)


def delete_files(dir_path):
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


def delete_local():
    logging.info("Starting 'run' function.")

    try:
        delete_files(dir_path=f"temp/data/raw")
        logging.info("Successfully deleted files in 'temp/data/raw'")
    except Exception as e:
        logging.error(f"Failed to delete files in 'temp/data/raw': {e}")

    try:
        delete_files(dir_path=f"temp/data/processed")
        logging.info("Successfully deleted files in 'temp/data/processed'")
    except Exception as e:
        logging.error(f"Failed to delete files in 'temp/data/processed': {e}")

    logging.info("Finished delete local files function.")


if __name__ == "__main__":
    logging.info("Application started.")
    delete_local()
    logging.info("Application finished.")
