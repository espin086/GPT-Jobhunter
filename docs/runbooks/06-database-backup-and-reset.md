# Runbook 06: back up, restore, inspect and reset the database

**Goal:** a copy of the data you can restore from, and a clean way to start over. All
durable state is one SQLite file, and two everyday commands (`make dev` and `make prod`)
delete it without asking. Time: under a minute for each task.

| Where the app runs | Database file |
|---|---|
| Local | `jobhunter/all_jobs.db` in the repository (ignored by git) |
| Docker | `/app/jobhunter/all_jobs.db` inside the container |

The path is fixed in `jobhunter/config.py` (`DATABASE`). The `TEST_DATABASE` environment
variable overrides it for part of the code only and exists for the test suite; do not use
it to move the real database.

## Back up

Local, safe while the backend is running:

```bash
sqlite3 jobhunter/all_jobs.db ".backup 'all_jobs.backup.db'"
```

Docker:

```bash
docker cp gpt-jobhunter:/app/jobhunter/all_jobs.db ./all_jobs.backup.db
```

`docker cp` copies the file as it is on disk. Take it when no search is running.

Keep backups outside the repository or under a name git ignores (`*.db` is ignored). A
backup contains every user's email, password hash and resume text. Do not attach one to an
issue or a pull request.

## Check a backup

```bash
sqlite3 all_jobs.backup.db "PRAGMA integrity_check;"      # ok
sqlite3 all_jobs.backup.db "SELECT
  (SELECT COUNT(*) FROM users)        AS users,
  (SELECT COUNT(*) FROM resumes)      AS resumes,
  (SELECT COUNT(*) FROM jobs_new)     AS jobs,
  (SELECT COUNT(*) FROM job_tracking) AS tracked;"
```

## Restore

Local: stop the backend, copy the backup over the file, start the backend.

```bash
make stop
cp all_jobs.backup.db jobhunter/all_jobs.db
```

Start it with the two-terminal commands in [runbook 01](01-local-development.md), not
`make dev`, which would delete the file you just restored.

Docker:

```bash
docker cp ./all_jobs.backup.db gpt-jobhunter:/app/jobhunter/all_jobs.db
docker restart gpt-jobhunter
```

## Inspect

```bash
sqlite3 jobhunter/all_jobs.db ".tables"
# job_tracking  jobs_new  password_reset_tokens  resumes  users

sqlite3 -header -column jobhunter/all_jobs.db \
  "SELECT id, username, email, is_active, last_login FROM users;"

sqlite3 -header -column jobhunter/all_jobs.db \
  "SELECT title, company, ROUND(resume_similarity, 3) AS score
   FROM jobs_new ORDER BY resume_similarity DESC LIMIT 10;"
```

The schema is drawn in [the architecture page](../architecture/c4.md#data-model).

## Reset

Everything, local: back up, stop the backend, remove the file, start again. The tables are
recreated empty at startup.

```bash
make stop
mv jobhunter/all_jobs.db all_jobs.before-reset.db
```

Postings only, keeping accounts and resumes:

```bash
sqlite3 jobhunter/all_jobs.db "DELETE FROM job_tracking; DELETE FROM jobs_new;"
```

Tracker rows point at postings, so they go first. Then clear the staging folders so the
next search does not reload the old postings from disk: delete the `.json` files under
`jobhunter/temp/data/raw/` and `jobhunter/temp/data/processed/`.

## If it fails

| Symptom | Likely cause | Fix |
|---|---|---|
| `database is locked` | A search or scoring run is writing | Wait for it to finish; SQLite allows one writer |
| `no such table: users` | The file was created by something other than the backend's startup | Start the backend once, or `curl -X POST http://localhost:8000/initialize` (creates the job, resume and tracking tables; the account tables are created only at startup) |
| Restore seems to have no effect | The backend still had the old file open, or `make dev` deleted it | Stop first, copy, then start without `make dev` |
| `no such column` after restoring an old backup | The backup predates a column | Restart the backend; startup adds `hidden`, `embeddings` and `optimized_html` when missing |
| Data gone after `make prod` | Container replaced | Restore from the last backup ([runbook 02](02-deploy-with-docker.md)) |
