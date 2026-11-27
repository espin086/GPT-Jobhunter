# Runbook 07: accounts and password reset

**Goal:** help a user who cannot sign in, and turn an account off or remove it. The app
sends no email, so a user who forgets a password is locked out until the operator reads a
reset token from the backend log and passes it on. Time: about 5 minutes.
Prerequisite: access to the backend log and, for the SQL steps, the database file
([runbook 06](06-database-backup-and-reset.md)).

## How accounts work

- Registration takes an email, a username of 2 to 50 characters and a password of at least
  8 characters. Email and username are each unique.
- Login accepts the username or the email and returns a token valid for 24 hours by default.
- The frontend keeps the token in the browser session. Closing the tab signs the user out
  of the UI; the token itself stays valid until it expires.
- There are no roles. Every account has the same rights, and there is no admin screen.

## Reset a password

1. The user (or you) asks for a reset:

```bash
curl -s -X POST http://localhost:8000/auth/password-reset-request \
  -H 'content-type: application/json' -d '{"email": "<the account email>"}'
# {"success":true,"message":"If the email exists, a reset link has been sent"}
```

   The answer is the same whether or not the email exists. No link is sent.

2. Read the token from the backend log. Local: the terminal running the backend. Docker:

```bash
docker exec gpt-jobhunter grep "Password reset token generated" /var/log/supervisor/backend.err.log | tail -n 1
```

   The line ends with `for <email>: <token>`. No such line means no account has that email.

3. Give the token to the user over a channel you trust, or set the password yourself. The
   token works once and expires 30 minutes after step 1.

```bash
curl -s -X POST http://localhost:8000/auth/password-reset-confirm \
  -H 'content-type: application/json' \
  -d '{"token": "<token>", "new_password": "<at least 8 characters>"}'
```

4. Check it: sign in with the new password.

```bash
curl -s -X POST http://localhost:8000/auth/login \
  -H 'content-type: application/json' \
  -d '{"username_or_email": "<email>", "password": "<new password>"}' | jq '.user.username'
```

Because the token sits in the log in full, anyone who can read the log can reset any
account. Limit who can read it.

## Turn an account off

```bash
sqlite3 jobhunter/all_jobs.db "UPDATE users SET is_active = 0 WHERE email = '<email>';"
```

The change applies on the next request; no restart is needed. Calls with that user's token
get 403 "Inactive user account". Set `is_active = 1` to turn it back on.

## Remove an account and its data

Back up first. Foreign keys are not enforced by the app, so delete the dependent rows
yourself, in this order:

```bash
sqlite3 jobhunter/all_jobs.db "
  DELETE FROM job_tracking          WHERE user_id = (SELECT id FROM users WHERE email = '<email>');
  DELETE FROM resumes               WHERE user_id = (SELECT id FROM users WHERE email = '<email>');
  DELETE FROM password_reset_tokens WHERE user_id = (SELECT id FROM users WHERE email = '<email>');
  DELETE FROM users                 WHERE email = '<email>';"
```

Postings are shared and stay. The user's resume text was also sent to OpenAI when it was
scored or analyzed; deleting the row here does not recall it.

## Sign everyone out

Change `JWT_SECRET_KEY` and restart the backend ([runbook 03](03-api-keys-and-secrets.md)).
Every existing token stops working. Do this if a token or the log has leaked. There is no
way to revoke one user's token alone.

## If it fails

| Symptom | Likely cause | Fix |
|---|---|---|
| Register answers 400 | Email or username already taken | Use another, or reset the existing account |
| Register answers 422 | Password under 8 characters, username under 2, or the email is not valid | Fix the input |
| Login answers 401 with the right password | Wrong account; username and email are separate fields at registration | Try the other identifier |
| Reset confirm fails | Token older than 30 minutes, already used, or copied with extra characters | Request a new one |
| No "token generated" line in the log | No account with that email, or the log level is above INFO | Check the email with the SQL in [runbook 06](06-database-backup-and-reset.md) |
| 401 on every call for all users | `JWT_SECRET_KEY` changed or was unset at restart | Users log in again; set the key in `.env` |
| 403 "Inactive user account" | `is_active` is 0 | Turn it back on |
