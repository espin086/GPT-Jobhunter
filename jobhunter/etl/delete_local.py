import os

FILE_PATH='/Users/jjespinoza/Documents/jobhunter'

def delete_files(dir_path):

    for root, dirs, files in os.walk(dir_path):
        for filename in files:
            file_path = os.path.join(root, filename)
            try:
                os.remove(file_path)
                print(f"Deleted file: {file_path}")
            except OSError as e:
                print(f"Error deleting file: {file_path} - {e}")

def run():
    delete_files(dir_path=f"{FILE_PATH}/data/raw")
    delete_files(dir_path=f"{FILE_PATH}/data/processed")

if __name__ == "__main__":
    run()
