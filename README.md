# JobHunter

This module allows you to perform a job analysis on LinkedIn by searching for jobs using a given search term and location, extracting job descriptions from job URLs, and calculating the similarity between a given resume text and a job description.

## Installation

1. Clone this repository using the following command: 

    git clone https://github.com/espin086/jobhunter.git

2. Enter into repository and run the make command

```bash
cd jobhunter
make
```

3. Update the resume.txt file with a text version of your resume. To confirm
your resume has been updated use this command.

```bash
cat jobhunter/jobhunter/resumes/resume.txt
```
4. Update the jobs and locations you'd like to search for jobs in the file called `config.yaml`, here are examples:

```yaml
    positions:
    - "Director Machine Learning"
    - "Vice President Machine Learning"
    
    locations:
    - "remote"
    - "Los Angeles"
```
5. Sign-up for an API key to access the Linkedin data, [go to this link to get API KEY](https://rapidapi.com/jaypat87/api/linkedin-jobs-search).

6. Sign-up for an API key to access the OpenAI and GPT, [go to this link to get API KEY](https://openai.com/blog/openai-api).

7. Update environment variables with your API KEY information with the following commands (mac/linux):
```bash
nano ~/.bash_profile
export RAPID_API_KEY="variable_value"
export OPENAI_ORGANIZATION="variable_value"
export OPENAI_API_KEY="variable_value"
```


```bash
source ~/.bash_profile
```

8. Run `main.py` and watch your job report print to the screen.


## Usage

1. Run a command to collect jobs and calculate similarity scores.

    `python3 jobhunter/main.py`


    You will receive output that looks like this after you run the step above:
```bash
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
```
    

## Contributing to this Project

1. Fork the Repository: First, fork the repository you want to contribute to by clicking the "Fork" button on the project's GitHub page. This will create a copy of the repository in your GitHub account.

2. Clone the Repository: Next, clone the repository to your local machine using the command:
`git clone https://github.com/espin086/jobhunter.git`

3. Create a New Branch: It's always a good idea to create a new branch for your changes to keep them separate from the main branch. You can create a new branch using the command:
`git checkout -b new-branch-name`

Be sure to give your branch a descriptive name that reflects the changes you plan to make.

4. Make Changes: Now you can make the changes you want to the codebase. Be sure to follow any guidelines provided by the project's contributors and to test your changes thoroughly before submitting them.

5. Commit Changes: Once you're satisfied with your changes, you can commit them using the command:

```bash
git add .
git commit -m "description of your changes"
```

Be sure to provide a clear and concise description of your changes in your commit message.

6. Push Changes: Finally, you can push your changes to your forked repository using the command:

`git push origin new-branch-name`

This will create a new branch in your forked repository and push your changes to it.

7. Create a Pull Request: Once you've pushed your changes to your forked repository, you can create a pull request (PR) to merge your changes into the main project's repository. To do this, go to the project's GitHub page, switch to the branch you just pushed your changes to, and click the "New pull request" button.

Be sure to provide a clear and concise description of your changes in your pull request, and explain why they're valuable to the project.

8. Review and Merge: Once your PR is submitted, the project's maintainers will review your changes and may ask for revisions or further changes. If they're satisfied with your changes, they'll merge your changes into the main project's repository.