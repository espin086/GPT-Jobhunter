from jobhunter.utils.openai_models import generate_completion
import os
from jobhunter.utils import conn
import numpy as np
from typing import Tuple


def summarize_cv(file_path: str) -> str:
    dir_path = os.path.dirname(file_path)
    base_name = os.path.basename(file_path)
    summarized_cv_p = os.path.join(dir_path, 'summaries', base_name)
    if os.path.exists(summarized_cv_p):
        return summarized_cv_p
    with open(file_path, 'r', encoding='cp437') as f_:
        resume_txt = f_.readlines()
    resume_txt = ''.join(resume_txt)
    max_token = 1000
    prompt = f'''
    summarize my CV to one or two paragraphs:
    """{resume_txt[:4000 - max_token]}"""
    '''
    summarized_cv_ = generate_completion(prompt)
    with open(summarized_cv_p, 'w') as f_:
        f_.write(summarized_cv_)
    print('CV summarization Done!')
    return summarized_cv_p


def create_cover_letter(
        summarized_cv_path: str,
        applicant_name: str,
        job_title: str,
        company_name: str,
        job_description: str
):
    with open(summarized_cv_path, 'r') as f_:
        resume_txt = f_.readlines()
    summarized_cv = ''.join(resume_txt)
    prompt = f'''
            Write a cover letter for the position
            at {company_name} about the {job_title}. 
            
            the following is job descrition: """
            {job_description}
            """
            
            the following is part of my CV: """
            {summarized_cv}
            """
            
            Make it professional and engaging. Sign it as {applicant_name}
        '''
    cover_letter = generate_completion(prompt)
    return cover_letter


def load_jobs() -> Tuple[str]:
    c = conn.cursor()
    c.execute(
        'SELECT title, company, description FROM jobs ORDER BY resume_similarity DESC'
    )
    while True:
        job_ = c.fetchone()
        if job_ is None:
            break
        job_desc = (lambda y: y[np.argmax(list(map(lambda x: len(x), y)))])(job_[-1].split('\n'))
        yield job_[0], job_[1], job_desc


if __name__ == '__main__':
    summary_f_p = summarize_cv('jobhunter/resumes/resume_files/jj_resume.txt')
    job_gen = load_jobs()
    job_info = next(job_gen)
    cover_letter = create_cover_letter(
        summary_f_p,
        'JJ',
        *job_info
    )
    print(cover_letter)