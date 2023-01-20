
GPT3_cover_letter = """I am writing to express my interest in the position of Research Data Scientist at Cedars-Sinai. With my professional background in Computer Science and experience in Cloud Computing technologies, I am confident that I possess the necessary skills and qualifications for this role.

I have a strong understanding of data analysis and machine learning best practices, and I have extensive experience programming with R and Python, as well as proficiency in SQL. I have worked with large, complex, and incomplete sources in the past and have the problem-solving mentality needed to research and resolve data issues.

As a Research Data Scientist, I am eager to put my research and analytical skills to use in order to make strategic data-related decisions. I am also excited to create database-to-deployment pipelines for models and develop innovative algorithms and analytical methods.

I am confident that I can be an incredible asset to the Cedars-Sinai team, and I look forward to the opportunity of discussing my skills and qualifications in further detail. Thank you for your time and consideration."""


def dm_generator(name, cover_letter, job_link):
    dm = """
Hello {0}!,

{1}

Here is the job link: {2}

Schedule a call with me here: https://bit.ly/3BlU1yf

Read my resume here: https://bit.ly/3gRXxcA

Thank You

JJ Espinoza
    """.format(name, cover_letter, job_link)
    
    return dm
    

link = "https://www.linkedin.com/jobs/view/research-data-scientist-at-cedars-sinai-3279217657/?refId=bK4ig5h4jIXEaM9tiFAaMw%3D%3D&trackingId=vMaWCfAlABV9VgNochDQWg%3D%3D&position=10&pageNum=0&trk=public_jobs_jserp-result_search-card"


dm = dm_generator(
    name="Ralph", 
    cover_letter = GPT3_cover_letter,
    job_link=link
    )
    
print(dm)

print("Open Linkedin Recruiter Search Here: {0}".format("https://www.linkedin.com/search/results/people/?geoUrn=%5B%2290000049%22%5D&keywords=recruiter&network=%5B%22F%22%5D&origin=FACETED_SEARCH&sid=UwU"))
