import argparse
import logging
import os
import sqlite3
import pandas as pd
from extract import extract
from dataTransformer import DataTransformer
from FileHandler import FileHandler
from load import load
from config import PROCESSED_DATA_PATH, RAW_DATA_PATH, RESUME_PATH

logging.basicConfig(level=logging.INFO)


file_handler = FileHandler(raw_path=RAW_DATA_PATH, processed_path=PROCESSED_DATA_PATH)


def run_search(job_titles):
    steps = [
        lambda: extract(job_titles),
        lambda: DataTransformer(
            raw_path=RAW_DATA_PATH,
            processed_path=PROCESSED_DATA_PATH,
            resume_path=RESUME_PATH,
            data=file_handler.import_job_data_from_dir(dirpath=RAW_DATA_PATH),
        ).transform(),
        load,
    ]

    for step in steps:
        step()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run job search")
    parser.add_argument(
        "job_titles", type=str, help="Job titles to search for (comma-separated)"
    )
    args = parser.parse_args()

    job_titles = [title.strip() for title in args.job_titles.split(",")]
    run_search(job_titles)
    file_handler.delete_local()
