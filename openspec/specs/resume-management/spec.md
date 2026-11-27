# resume-management Specification

## Purpose

Store the text of one or more resumes for each user, so that postings can be scored against
them and the optimizer can analyze and rewrite them. Reverse engineered from
`jobhunter/backend/api.py`, `services.py` (`ResumeService`) and `jobhunter/SQLiteHandler.py`.

## Requirements

### Requirement: Upload a resume as text

The system SHALL store a resume from a filename and its text content under the
authenticated user.

#### Scenario: First upload

- **WHEN** a user posts a filename and content to `/resumes/upload`
- **THEN** the system stores the resume and responds with `resume_name`, `success` true and a confirmation message

#### Scenario: Same name uploaded again

- **WHEN** a user uploads a resume whose name they already used
- **THEN** the system replaces the stored text and keeps a single resume with that name

### Requirement: Upload a resume as a file

The system SHALL accept a file upload of content type `application/pdf` or `text/plain`,
extract its text, and store it under the file's name.

#### Scenario: PDF upload

- **WHEN** a user posts a PDF to `/resumes/upload-file`
- **THEN** the system extracts the text of every page and stores it as a resume

#### Scenario: Unsupported file type

- **WHEN** a user posts a file of any other content type
- **THEN** the system responds 400 with the detail "Only PDF and TXT files are supported"

#### Scenario: No extractable text

- **WHEN** a user posts a file from which no text can be extracted
- **THEN** the system responds 400 and stores nothing

### Requirement: List, read, replace and delete

The system SHALL let a user list the names of their resumes, read one by name, replace its
text, and delete it.

#### Scenario: List

- **WHEN** a user calls `GET /resumes`
- **THEN** the system returns the names of that user's resumes

#### Scenario: Read a missing resume

- **WHEN** a user calls `GET /resumes/{resume_name}` for a name they do not have
- **THEN** the system responds 404

### Requirement: Resumes are private to their owner

The system SHALL scope every resume operation to the authenticated user and SHALL treat
resume names as unique per user, not across users.

#### Scenario: Two users, same resume name

- **WHEN** two users each upload a resume named `resume.pdf`
- **THEN** each user's list shows one `resume.pdf` and each reads back their own text

#### Scenario: Reading another user's resume

- **WHEN** a user requests a resume name that exists only under another user
- **THEN** the system responds 404

### Requirement: Stored rewrite

The system SHALL keep at most one generated rewrite per resume, as HTML, alongside the
resume text.

#### Scenario: Rewrite generated twice

- **WHEN** an optimized version is generated for a resume that already has one
- **THEN** the stored HTML is replaced
