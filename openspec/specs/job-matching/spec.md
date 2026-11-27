# job-matching Specification

## Purpose

Turn stored postings into a ranked list for one resume, so the job seeker reads the best
fits first. Reverse engineered from `jobhunter/SQLiteHandler.py`
(`update_similarity_in_db`), `textAnalysis.py`, and `services.py` (`JobDataService`).

## Requirements

### Requirement: Score postings against a resume

The system SHALL, on request, embed the named resume, compute the cosine similarity
between it and every stored posting's embedding, and store the result on the posting as a
number between 0.0 and 1.0.

#### Scenario: Scores updated

- **WHEN** a user posts one of their resume names to `/similarity/update`
- **THEN** every posting with an embedding gets a new `resume_similarity`
- **AND** the response reports `success` true and how many postings have a score above zero

#### Scenario: Posting without an embedding

- **WHEN** a posting has no stored embedding
- **THEN** its score is set to 0.0

#### Scenario: Resume cannot be embedded

- **WHEN** the resume is not found, or OpenAI returns no usable vector for it
- **THEN** the system responds 200 with `success` false and changes no scores

### Requirement: One score per posting

The system SHALL store a single `resume_similarity` value on each posting, shared by all
users and all resumes.

#### Scenario: Second user scores

- **WHEN** user A scores postings and then user B scores postings with a different resume
- **THEN** the listing shows user B's scores to both users

### Requirement: Scores change only on request

The system SHALL update scores only through `/similarity/update` and the onboarding run.
Uploading a resume or running a search SHALL leave existing scores as they are.

#### Scenario: New postings after a search

- **WHEN** a search adds postings and no score update follows
- **THEN** the new postings have a score of 0

### Requirement: Ranked listing

The system SHALL return postings ordered by score from highest to lowest and then by date
from newest to oldest, with `limit` (default 100) and `offset` paging and the total count
of matches.

#### Scenario: Listing

- **WHEN** a client calls `GET /jobs?limit=5`
- **THEN** the system returns at most 5 postings, highest score first, and `total_count` for the whole filtered set

#### Scenario: No token needed

- **WHEN** a client calls `GET /jobs` or `GET /jobs/count` without an Authorization header
- **THEN** the system answers

### Requirement: Filters

The system SHALL filter the listing and the count by minimum score, company, title,
location (matched against city, state or country), job type, remote flag, minimum salary
and maximum salary. Text filters SHALL match as substrings.

#### Scenario: Location filter

- **WHEN** a client lists postings with `location=Texas`
- **THEN** only postings whose city, state or country contains "Texas" are returned

### Requirement: Dismissed and tracked postings leave the listing

The system SHALL leave out of the listing every posting marked hidden and every posting
that any user has saved to a tracker.

#### Scenario: Another user saved the posting

- **WHEN** user A saves a posting to their tracker
- **THEN** the posting no longer appears in the listing for user B
