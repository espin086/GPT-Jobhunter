# platform-operations Specification

## Purpose

Describe how the system starts, reports its health, stores its data and is packaged, so
that someone running it knows what to expect. Reverse engineered from
`jobhunter/backend/api.py`, `services.py` (`DatabaseService`), `config.py`, the `Makefile`,
the `Dockerfile` and `jobhunter/cli.py`.

## Requirements

### Requirement: Two processes

The system SHALL run as a FastAPI backend on port 8000 and a Streamlit frontend on port
8501, and the frontend SHALL reach the backend only over HTTP at `BACKEND_URL`, which
defaults to `http://localhost:8000`.

#### Scenario: Backend unreachable

- **WHEN** the frontend cannot connect to `BACKEND_URL`
- **THEN** it shows an error that names the URL and performs no operation itself

### Requirement: Tables created at startup

The system SHALL create the `jobs_new`, `resumes`, `job_tracking`, `users` and
`password_reset_tokens` tables when the backend starts if they do not exist, and SHALL add
the `hidden`, `embeddings` and `optimized_html` columns when an older file lacks them.

#### Scenario: First start

- **WHEN** the backend starts with no database file
- **THEN** the file is created with all five tables and the backend serves requests

### Requirement: One SQLite file at a fixed path

The system SHALL keep all durable data in the SQLite file `all_jobs.db` inside the
`jobhunter` package directory.

#### Scenario: File removed

- **WHEN** the file is deleted and the backend restarts
- **THEN** the system starts empty, with no accounts, resumes or postings

### Requirement: Health check

The system SHALL answer `GET /health` without authentication, with status "healthy", a
timestamp and the API version when the database can be read, and with 503 when it cannot.

#### Scenario: Healthy

- **WHEN** a client calls `GET /health` on a running backend
- **THEN** the system responds 200 with `status` "healthy" and `version` "1.0.0"

### Requirement: Statistics

The system SHALL answer `GET /stats` without authentication with the number of postings,
resumes, postings that have an embedding, postings that have a score above zero, and the
database path.

#### Scenario: Empty instance

- **WHEN** a client calls `GET /stats` on a new instance
- **THEN** all four counts are 0

### Requirement: Manual initialization

The system SHALL create the posting, resume and tracker tables on `POST /initialize`
without authentication.

#### Scenario: Initialize

- **WHEN** a client posts to `/initialize`
- **THEN** the system responds with `success` true

### Requirement: Configuration from the environment

The system SHALL read `RAPID_API_KEY`, `OPENAI_API_KEY`, `JWT_SECRET_KEY`, `JWT_ALGORITHM`
and `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` from the process environment, loading a `.env` file
when one is present.

#### Scenario: Starts without API keys

- **WHEN** the backend starts with neither API key set
- **THEN** it starts and serves accounts, resumes and the tracker, and search and scoring report the missing key when called

### Requirement: Published API contract

The system SHALL serve its OpenAPI schema at `/openapi.json` with interactive pages at
`/docs` and `/redoc`, and the repository SHALL carry a copy as `openapi.json`, regenerated
by `make openapi`.

#### Scenario: Docs page

- **WHEN** a client opens `/docs` on a running backend
- **THEN** the interactive API reference is served

### Requirement: Single-container deployment

The system SHALL ship as one Docker image that initializes the database and then runs both
processes under supervisord, publishing ports 8000 and 8501, with a health check that
requires both ports to answer.

#### Scenario: One process exits

- **WHEN** the backend or the frontend process exits inside the container
- **THEN** supervisord starts it again

### Requirement: Local development start

The system SHALL start both processes with auto-reload on `make dev`, after deleting the
local database file and the staged raw and processed files.

#### Scenario: Restart in development

- **WHEN** a developer runs `make dev` a second time
- **THEN** the accounts, resumes and postings from the first run are gone

### Requirement: Command-line search

The system SHALL provide a script, `jobhunter/cli.py`, that takes comma-separated job
titles, runs extract, transform and load for them, and then deletes the staged files.

#### Scenario: Search from the command line

- **WHEN** a user runs `python -m jobhunter.cli "Data Engineer, ML Engineer"` with `RAPID_API_KEY` set
- **THEN** postings for both titles are loaded into the database

#### Scenario: Installed console command

- **WHEN** a user installs the package and runs the `jobhunter` command that `pyproject.toml` declares
- **THEN** it fails with an ImportError, because the declared entry point `jobhunter.cli:main` does not exist
