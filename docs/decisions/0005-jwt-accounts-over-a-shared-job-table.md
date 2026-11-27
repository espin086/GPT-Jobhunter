# 0005. Accounts with JWT bearer tokens over a shared job table

**Status:** accepted · **In the code since:** 2025-12-13 · **Recorded:** 2026-11-27

## Context

Once the backend became an HTTP API ([ADR 0002](0002-fastapi-backend-and-streamlit-frontend.md)),
anyone who could reach it could read and replace the one stored resume. The roadmap also
lists use by groups such as bootcamp cohorts, which needs each person's resumes and
applications kept apart. No reason for the specific design was written down; the tradeoffs
below are read from the code.

## Decision

1. Users register with an email, a username and a password of at least 8 characters.
   The password is hashed with SHA-256 and then bcrypt, so passwords longer than bcrypt's
   72-byte limit are not silently cut.
2. Login returns a JWT signed with HS256 and `JWT_SECRET_KEY`, valid for
   `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` (default 1440, which is 24 hours). The user id is in
   the `sub` claim.
3. Protected routes take the token as `Authorization: Bearer <token>` through the
   `get_current_user` dependency. Tokens are not stored on the server.
4. `resumes` and `job_tracking` carry a `user_id` and are unique per user. Every query on
   them filters by the caller's id.
5. `jobs_new` is shared: one copy of each posting for all users.
6. Password reset issues a single-use token valid for 30 minutes.

## Options considered

| Option | Why not |
|---|---|
| No accounts, one user per install | Simplest, and what the app did before. Leaves the API open to anyone on the network |
| Server-side sessions | Allows real logout and revocation, but adds a session table and a lookup on every request |
| A hosted identity provider | Email delivery, reset and MFA handled elsewhere, at the cost of an outside account for a self-hosted tool |
| Postings stored per user | Makes scores and dismissals private, but stores and embeds the same posting once per user |

## Consequences

- **Isolation holds for resumes and tracking.** `tests/test_user_isolation.py` covers it.
- **Scores and dismissals are not per user.** `resume_similarity` and `hidden` are columns
  on the shared posting row. Two users on one instance overwrite each other's ranking, and
  a posting one user passes on is hidden for everyone. This is the largest gap between the
  account model and the data model.
- **Several routes are still open:** `/jobs/search`, `/jobs`, `/jobs/count`, `/stats` and
  `/initialize` take no token.
- **Logout is client-side.** `/auth/logout` does not revoke anything; a copied token works
  until it expires.
- **The signing key has a default.** If `JWT_SECRET_KEY` is unset the code signs with a
  fixed string that is in the source. An instance run that way accepts forged tokens.
  [Runbook 03](../runbooks/03-api-keys-and-secrets.md) makes setting it a required step.
- **Logs carry secrets.** Token fragments, token payloads, the first characters of the
  signing key and full reset tokens are written to the backend log.
- **Reset needs the operator.** No email is sent. See
  [runbook 07](../runbooks/07-accounts-and-password-reset.md).

## Revisit when

A second person uses the same instance (scores must move to a per-user table first), the
app is exposed beyond localhost, or email delivery is added.
