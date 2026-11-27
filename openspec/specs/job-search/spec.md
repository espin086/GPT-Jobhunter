# job-search Specification

## Purpose

Bring job postings into the system from an outside source and prepare them for scoring.
Search is the only way postings are added. Reverse engineered from `jobhunter/extract.py`,
`dataTransformer.py`, `load.py`, `FileHandler.py`, `SQLiteHandler.py`, `config.py` and
`services.py` (`JobSearchService`).

## Requirements

### Requirement: Search by job title

The system SHALL accept a list of job titles with an optional country (default `us`), date
range (default `all`) and location, and SHALL run extract, transform and load for them in
one blocking request.

#### Scenario: Search finds postings

- **WHEN** a client posts job titles to `/jobs/search` and the source returns postings
- **THEN** the system responds with `total_jobs_found` equal to the number of postings the source returned and `success` true

#### Scenario: Search finds nothing

- **WHEN** the source returns no postings for any title
- **THEN** the system responds with `total_jobs_found` 0, `success` false and the message "No jobs found"

#### Scenario: No token needed

- **WHEN** a client posts to `/jobs/search` without an Authorization header
- **THEN** the system runs the search

### Requirement: JSearch as the source

The system SHALL fetch postings from the JSearch API on RapidAPI using `RAPID_API_KEY`,
with the query "`<title>` jobs in `<location>`", requesting up to 3 pages per title.

#### Scenario: Key missing

- **WHEN** a search runs and `RAPID_API_KEY` is not set
- **THEN** the system responds 500 with a detail that says the key is missing

#### Scenario: Location left empty

- **WHEN** a search gives no location and the country is one of `us`, `uk`, `ca`, `au`, `de`, `fr`, `es`, `it`
- **THEN** the system uses that country's name as the location

### Requirement: Pacing and retry

The system SHALL wait 2 seconds before each request to the source and SHALL retry a 429
response up to 3 times with a wait that starts at 2 seconds and is capped at 60 seconds.

#### Scenario: Rate limit clears

- **WHEN** the source answers 429 and then succeeds within 3 retries
- **THEN** the search continues with that page's postings

#### Scenario: Rate limit persists

- **WHEN** the source answers 429 on every retry
- **THEN** the system logs the rate limit, stops fetching pages for that title, and counts the title as having no postings
- **AND** if no title returned postings, the response is `total_jobs_found` 0 with the message "No jobs found", not an error status

### Requirement: Fallback to a simpler title

The system SHALL retry a title that returned nothing with more general terms: the title
with its seniority words removed, then a domain word found in the title, stopping at the
first term that returns postings.

#### Scenario: Senior title returns nothing

- **WHEN** "Principal Machine Learning Engineer" returns no postings
- **THEN** the system searches "machine learning engineer" before giving up on that title

### Requirement: Staged files

The system SHALL write each fetched posting as a JSON file under
`jobhunter/temp/data/raw/` and each cleaned posting under `jobhunter/temp/data/processed/`.
The search route SHALL NOT delete these files.

#### Scenario: Second search

- **WHEN** a second search runs on an instance that has raw files from an earlier search
- **THEN** the transform step reads the earlier files as well as the new ones

### Requirement: Field mapping

The system SHALL keep the source fields listed in `config.SELECTED_KEYS`, rename them to
the stored column names, and flatten list-valued fields to text.

#### Scenario: Posting transformed

- **WHEN** a raw posting has `job_title`, `employer_name` and `job_description`
- **THEN** the processed posting has `title`, `company` and `description`

### Requirement: One row per company and title

The system SHALL identify a posting by the string `"<company> - <title>"` and SHALL skip a
posting whose key is already stored.

#### Scenario: Posting seen before

- **WHEN** a search returns a posting with the same company and title as a stored one
- **THEN** the stored row is left as it is and no second row is added

### Requirement: Embedding on load

The system SHALL embed each new posting's title and description, cut at 8,000 characters,
with OpenAI `text-embedding-3-small` in batches of up to 100, and store the vector with the
posting. A posting SHALL still be stored when its embedding fails.

#### Scenario: OpenAI key missing or rejected

- **WHEN** new postings are loaded and no usable `OPENAI_API_KEY` is set
- **THEN** the postings are stored with no embedding and the search still reports success
