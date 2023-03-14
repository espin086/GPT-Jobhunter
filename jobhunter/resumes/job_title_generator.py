
""" Example of using module 
python3 job_title_generator.py --resume_file ../resumes/resume.txt
"""

import argparse
from jobhunter.jobhunter.utils.openai_models import generate_completion


def get_top_job_titles(resume_text):
    prompt = f"What are the top 10 popular job titles for someone with this resume:\n{resume_text}\n1."
    message = generate_completion("text-davinci-003", prompt, 0.7, 1000)
    job_titles = [title.split(".")[1].strip() if "." in title else title.strip() for title in message.split("\n") if title.strip()]
    return job_titles

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a text completion.")
    parser.add_argument(
        "--resume_file",
        type=str,
        required=True,
        help="The path to the file containing the resume.",
    )
    args = parser.parse_args()

    with open(args.resume_file, "r") as f:
        resume_text = f.read()

    job_titles = get_top_job_titles(resume_text)
    print("-"*30)
    print("Top Job Titles Based on GPT Analysis of Your Resume:")
    print("-"*30)
    for i, title in enumerate(job_titles[:10]):
        print(f"{title}") 