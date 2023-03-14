import os

FILE_PATH='/Users/jjespinoza/Documents/jobhunter'


def main():
    os.system(f"/usr/bin/python3 {FILE_PATH}/jobhunter/etl/pipeline.py")
    os.system(f"/usr/bin/python3 {FILE_PATH}/database_reports/get_latest_jobs.py")

if __name__ == "__main__":
    main()




