# resume-optimization Specification

## Purpose

Tell the job seeker how well their resume will pass automated screening for the jobs they
match, and produce a rewritten resume aimed at those jobs. Reverse engineered from
`jobhunter/backend/services.py` (`AIService`, `ResumeOptimizerService`) and the
`/resumes/*` routes in `api.py`.

## Requirements

### Requirement: Job title suggestions

The system SHALL suggest up to 3 job titles for a stored resume using the OpenAI chat
model `gpt-4o-mini`.

#### Scenario: Suggestions returned

- **WHEN** a user posts one of their resume names to `/resumes/suggest-job-titles`
- **THEN** the system responds with at most 3 titles and `success` true

#### Scenario: Resume not found

- **WHEN** the resume name does not belong to the user
- **THEN** the system responds 404

#### Scenario: OpenAI key missing

- **WHEN** no `OPENAI_API_KEY` is set
- **THEN** the system responds 500 with the detail "OpenAI API key not configured"

### Requirement: ATS analysis

The system SHALL analyze a stored resume with `gpt-4o-mini` and return an overall score
from 0 to 100, missing keywords, keyword suggestions (current term, suggested term and
reason) and ATS tips.

#### Scenario: Analysis against stored postings

- **WHEN** a user posts a resume name to `/resumes/optimize` and postings are stored
- **THEN** the system analyzes the resume against the top `num_jobs` postings by score (default 20)
- **AND** the response has `analysis_source` "job_database" and `jobs_analyzed` equal to the number used

#### Scenario: No postings stored

- **WHEN** no postings match
- **THEN** the system analyzes the resume from the model's general knowledge and the response has `analysis_source` "ai_general"

#### Scenario: Resume not found or key missing

- **WHEN** the resume is not the user's, or no `OPENAI_API_KEY` is set
- **THEN** the system responds 200 with `success` false, a score of 0 and a message that says why

### Requirement: Analysis filters

The system SHALL narrow the postings used for analysis by the same filters as the job
listing: minimum score, location, remote flag, company, title, job type, and minimum and
maximum salary.

#### Scenario: Remote roles only

- **WHEN** a user requests analysis with `is_remote` true
- **THEN** only postings marked remote are used

### Requirement: Rewritten resume

The system SHALL generate a rewritten resume as HTML from a stored resume and a set of
analysis results using the OpenAI chat model `gpt-4o`, and SHALL store that HTML with the
resume.

#### Scenario: Rewrite generated

- **WHEN** a user posts a resume name and analysis results to `/resumes/generate-optimized`
- **THEN** the system responds with `html_content` and `success` true, and the HTML is stored for that resume

#### Scenario: Generation fails

- **WHEN** the model call fails or returns nothing
- **THEN** the system responds 500 with the detail "Failed to generate optimized resume"

### Requirement: Word download

The system SHALL return the stored rewrite as a `.docx` file named
`<resume name without extension>_optimized.docx`.

#### Scenario: Download

- **WHEN** a user posts a resume name to `/resumes/download-word` and a rewrite is stored
- **THEN** the system streams a Word document

#### Scenario: No rewrite yet

- **WHEN** no rewrite is stored for that resume
- **THEN** the system responds 404 and tells the user to generate the resume first
