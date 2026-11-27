# job-tracking Specification

## Purpose

Let the job seeker keep the postings they intend to act on and move each one through the
stages of an application, on a board with one column per stage. Reverse engineered from
`jobhunter/backend/services.py` (`JobTrackingService`) and the `/jobs/*` tracking routes
in `api.py`.

## Requirements

### Requirement: Save a posting

The system SHALL add a stored posting to the authenticated user's tracker in the `apply`
stage.

#### Scenario: Saved

- **WHEN** a user posts a stored posting's id to `/jobs/save`
- **THEN** a tracker entry is created for that user with status `apply` and the response has `success` true

#### Scenario: Saved twice

- **WHEN** a user saves a posting they already track
- **THEN** the system keeps the one existing entry, leaves its status unchanged, and responds with `success` true

#### Scenario: Unknown posting

- **WHEN** a user saves an id that matches no posting
- **THEN** the system responds 200 with `success` false and the message "Job not found"

### Requirement: Five stages

The system SHALL allow exactly these statuses: `apply`, `hr_screen`, `round_1`, `round_2`
and `rejected`.

#### Scenario: Move to the next stage

- **WHEN** a user puts a valid status to `/jobs/tracked/{job_id}/status` for a posting they track
- **THEN** the entry's status and update time change

#### Scenario: Invalid status

- **WHEN** a user sends a status outside the five
- **THEN** the system responds with `success` false and lists the valid statuses

#### Scenario: Path and body disagree

- **WHEN** the job id in the path differs from the job id in the body
- **THEN** the system responds 400

### Requirement: Board view

The system SHALL return the user's tracked postings grouped under the five statuses, each
with the posting's fields and the entry's status, added time, updated time and notes, most
recently updated first.

#### Scenario: Empty tracker

- **WHEN** a user with no tracked postings calls `GET /jobs/tracked`
- **THEN** the system returns five empty lists

### Requirement: Tracker entries are private to their owner

The system SHALL scope tracker reads and status changes to the authenticated user.

#### Scenario: Changing another user's entry

- **WHEN** a user sends a status change for a posting that only another user tracks
- **THEN** the system responds with `success` false and changes nothing

### Requirement: Pass on a posting

The system SHALL mark a posting hidden when a user passes on it. The mark is stored on the
shared posting.

#### Scenario: Passed

- **WHEN** a user posts a posting's id to `/jobs/pass`
- **THEN** the posting is hidden from the job listing for every user
