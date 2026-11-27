# accounts-and-auth Specification

## Purpose

Let a person create an account, sign in, and prove who they are on later requests, so that
resumes and tracked applications belong to one user. Reverse engineered from
`jobhunter/backend/api.py`, `auth_service.py`, `services.py` (`AuthService`) and
`jobhunter/AuthHandler.py`.

## Requirements

### Requirement: Account registration

The system SHALL create an account from an email address, a username of 2 to 50 characters
and a password of at least 8 characters, and SHALL store the password only as a bcrypt hash
of its SHA-256 digest.

#### Scenario: New account

- **WHEN** a client posts a valid email, username and password to `/auth/register`
- **THEN** the system responds 201 with the user's id, email, username, full name, `is_active` true and creation time
- **AND** the response contains no password or hash

#### Scenario: Email already registered

- **WHEN** a client registers with an email that an existing account uses
- **THEN** the system responds 400 with the detail "Email already registered"

#### Scenario: Input fails validation

- **WHEN** a client registers with a password shorter than 8 characters, a username shorter than 2 characters, or a malformed email
- **THEN** the system responds 422 and creates no account

### Requirement: Sign-in with username or email

The system SHALL accept either the username or the email in the `username_or_email` field
together with the password, and SHALL return a signed access token on success.

#### Scenario: Correct credentials

- **WHEN** a client posts a matching identifier and password to `/auth/login`
- **THEN** the system responds 200 with `access_token`, `token_type` "bearer" and the user record
- **AND** the system records the time as the account's `last_login`

#### Scenario: Wrong credentials

- **WHEN** a client posts an unknown identifier or a wrong password
- **THEN** the system responds 401

### Requirement: Access tokens

The system SHALL issue access tokens as JWTs signed with HS256 and the `JWT_SECRET_KEY`
setting, carrying the user id in the `sub` claim and expiring after
`JWT_ACCESS_TOKEN_EXPIRE_MINUTES` minutes, which defaults to 1440. The system SHALL NOT
keep tokens on the server.

#### Scenario: Signing key changed

- **WHEN** the backend restarts with a different `JWT_SECRET_KEY`
- **THEN** every token issued before the restart is rejected with 401

#### Scenario: Signing key not configured

- **WHEN** the backend starts with no `JWT_SECRET_KEY` in its environment
- **THEN** the system signs and verifies tokens with a fixed default string from the source code

### Requirement: Protected routes

The system SHALL require an `Authorization: Bearer <token>` header on every resume,
tracker, similarity, optimization and onboarding route, and on `/auth/me` and
`/auth/logout`.

#### Scenario: No token

- **WHEN** a client calls a protected route without an Authorization header
- **THEN** the system responds 401

#### Scenario: Valid token

- **WHEN** a client calls a protected route with a token that verifies and whose user exists and is active
- **THEN** the system runs the request as that user

#### Scenario: Inactive account

- **WHEN** a client calls a protected route with a valid token for an account whose `is_active` is 0
- **THEN** the system responds 403 with the detail "Inactive user account"

### Requirement: Logout

The system SHALL answer `/auth/logout` with success for an authenticated user and SHALL
leave the token valid until it expires.

#### Scenario: Token used after logout

- **WHEN** a client logs out and then calls a protected route with the same token
- **THEN** the system serves the request

### Requirement: Password reset

The system SHALL issue a single-use reset token that expires 30 minutes after it is
requested, SHALL write that token to the backend log, and SHALL send no email.

#### Scenario: Reset requested

- **WHEN** a client posts an email to `/auth/password-reset-request`
- **THEN** the system responds 200 with the same message whether or not an account has that email
- **AND** if an account has that email, a log line records the token

#### Scenario: Reset confirmed

- **WHEN** a client posts an unused, unexpired token and a new password of at least 8 characters to `/auth/password-reset-confirm`
- **THEN** the system responds 200, the new password signs in, and the old password is rejected

#### Scenario: Token reused or expired

- **WHEN** a client posts a token that was already used or is older than 30 minutes
- **THEN** the system responds 400 with the detail "Invalid or expired reset token"
