# JobHunter

This module allows you to perform a job analysis on LinkedIn by searching for jobs using a given search term and location, extracting job descriptions from job URLs, and calculating the similarity between a given resume text and a job description.

## Installation

1. Clone this repository using the following command: 

    git clone https://github.com/espin086/jobhunter.git

2. Enter into repository and run the make command

    cd jobhunter
    make

3. Update the resume.txt file with a text version of your resume. To confirm
your resume has been updated use this command.

    cat jobhunter/jobhunter/resumes/resume.txt

4. Update the jobs and locations you'd like to search for jobs in the file called `config.yaml`, here are examples:

    positions:
    - "Director Machine Learning"
    - "Vice President Machine Learning"
    
    locations:
    - "remote"
    - "Los Angeles"

5. Sign-up for an API key to access the Linkedin data, [go to this link to get API KEY](https://rapidapi.com/jaypat87/api/linkedin-jobs-search).

6. Update this file located here:

jobhunter/jobhunter/utils/search_linkedin_jobs.py

Delete this line in the file above:

    import jobhunter.utils.aws_secrets_manager

Add your RapidAPI Key to this dictionary key:

    "X-RapidAPI-Key"

That is all you need to set up JobHunter.

## Usage

1. Run a command to collect jobs and calculate similarity scores.

    `python3 jobhunter/run_linkedin_bot.py`

2. Run code to create a local SQLite Database:

    `python3 jobhunter/jobhunter/utils/database.py`

3. Run code to process, clean, and store the data into a local SQLite database

    `python3 jobhunter/jobhunter/utils/clean_data_loader.py`

4. Run report on latest jobs and their similarity to your resume:

    `python3 jobhunter/jobhunter/utils/get_latest_jobs.py`

    You will receive output that looks like this after you run the step above:

    ------------------------------
    Date: 2023-03-08
    Resume Similarity: 0.087
    Title: head of machine learning
    Company Name: storm3
    Salary Max: 230000
    Job URL: https://www.linkedin.com/jobs/view/head-of-machine-learning-at-storm3-3511291454

    ------------------------------
    Date: 2023-03-08
    Resume Similarity: 0.052
    Title: vice president of analytics
    Company Name: dickclarkproductions
    Salary Max: 180000
    Job URL: https://www.linkedin.com/jobs/view/vice-president-of-analytics-at-dick-clark-productions-3509854976

    ------------------------------
    Date: 2023-03-08
    Resume Similarity: 0.087
    Title: head of machine learning
    Company Name: storm3
    Salary Max: 250000
    Job URL: https://www.linkedin.com/jobs/view/head-of-machine-learning-at-storm3-3511296009

    ------------------------------
    Date: 2023-03-08
    Resume Similarity: 0.087
    Title: head of machine learning
    Company Name: storm3
    Salary Max: 230000
    Job URL: https://www.linkedin.com/jobs/view/head-of-machine-learning-at-storm3-3511291454

    ------------------------------
    Date: 2023-03-08
    Resume Similarity: 0.106
    Title: director of machine learning
    Company Name: cubiq recruitment
    Salary Max: 250000
    Job URL: https://www.linkedin.com/jobs/view/director-of-machine-learning-at-cubiq-recruitment-3511237710

    ------------------------------
    Date: 2023-03-08
    Resume Similarity: 0.146
    Title: vp data, data analytics and data science
    Company Name: honest medical group
    Salary Max: 0
    Job URL: https://www.linkedin.com/jobs/view/vp-data-data-analytics-and-data-science-at-honest-medical-group-3511426579

    ------------------------------
    Date: 2023-03-08
    Resume Similarity: 0.045
    Title: head of robotics
    Company Name: storm5
    Salary Max: 0
    Job URL: https://www.linkedin.com/jobs/view/head-of-robotics-at-storm5-3500657395

    ------------------------------
    Date: 2023-03-08
    Resume Similarity: 0.117
    Title: vice president, analytics engineering
    Company Name: spotter inc
    Salary Max: 600000
    Job URL: https://www.linkedin.com/jobs/view/vice-president-analytics-engineering-at-spotter-3509179835

    ------------------------------
    Date: 2023-03-08
    Resume Similarity: 0.117
    Title: vice president, analytics engineering
    Company Name: spotter inc
    Salary Max: 600000
    Job URL: https://www.linkedin.com/jobs/view/vice-president-analytics-engineering-at-spotter-3509179835

    ------------------------------
