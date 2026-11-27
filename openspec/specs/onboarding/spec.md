# onboarding Specification

## Purpose

Take a new user from an uploaded resume to a ranked job list and an ATS analysis in one
request, so the first screen they see has results on it. Reverse engineered from
`jobhunter/backend/services.py` (`OnboardingService`) and `/onboarding/process` in `api.py`.

## Requirements

### Requirement: Four steps in order

The system SHALL run these steps for a named resume in this order: suggest job titles,
search those titles, score postings against the resume, analyze the resume against the
top 20 postings.

#### Scenario: Full run

- **WHEN** a user posts one of their resume names to `/onboarding/process` with both API keys configured
- **THEN** the response lists four step results named `job_title_suggestions`, `job_search`, `similarity_calculation` and `resume_optimization`
- **AND** it carries the suggested titles, the number of postings found, the number with a score, and the optimization score

### Requirement: Each step reports for itself

The system SHALL record a success flag and a message for every step, and SHALL continue to
the later steps when an earlier one fails.

#### Scenario: Title suggestion fails

- **WHEN** the title suggestion step fails
- **THEN** its step result has `success` false and the remaining steps are still attempted and reported

### Requirement: Overall result follows the search

The system SHALL report the run as successful when the job search step succeeded,
whatever the other steps returned.

#### Scenario: Search succeeds, analysis fails

- **WHEN** postings are found and the analysis step fails
- **THEN** the response has `success` true and the `resume_optimization` step has `success` false

#### Scenario: Search finds nothing

- **WHEN** the search step finds no postings
- **THEN** the response has `success` false

### Requirement: Analysis results are returned in full

The system SHALL include the analysis output (score, missing keywords, keyword suggestions,
tips, number of postings analyzed and analysis source) in the `resume_optimization` step's
data when that step succeeds.

#### Scenario: Analysis succeeds

- **WHEN** the analysis step succeeds
- **THEN** the frontend can show the ATS results from the onboarding response without a second request
