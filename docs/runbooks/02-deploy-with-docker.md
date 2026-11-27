# Runbook 02: deploy with Docker

**Goal:** the app running in one container that restarts by itself, and no data lost when
you update or stop it. The second half matters most: the container has no persistent
volume, so the commands that stop or rebuild it also delete every account, resume and
posting. Time: about 10 minutes for the first build.
Prerequisites: Docker, and a `.env` from [runbook 03](03-api-keys-and-secrets.md) with
`JWT_SECRET_KEY` set.

This runbook was written from the `Dockerfile`, the `Makefile` and `docker-compose.yml` on
2026-11-27. The image could not be built on the machine it was written on, because the pull
of `python:3.11-slim` timed out twice, so these steps have not been run end to end. The
backend calls in "Check it" were run against a local, non-Docker backend.

## What you get

| Piece | Value |
|---|---|
| Image | `gpt-jobhunter:latest`, from `python:3.11-slim` |
| Container | `gpt-jobhunter`, `--restart unless-stopped` |
| Processes | `uvicorn` on 8000 and `streamlit` on 8501, both under supervisord |
| Database | `/app/jobhunter/all_jobs.db`, inside the container, no volume |
| Logs | `/var/log/supervisor/` inside the container |
| Secrets | Read from `.env` with `--env-file` when the container is created |

## Deploy

```bash
make prod
```

It runs two targets:

1. `make docker-build` removes the old image, builds a new one, and checks that `.env` is
   not inside it.
2. `make docker-run` **removes any existing `gpt-jobhunter` container**, then starts a new
   one with both ports published.

On a first deploy there is nothing to lose. On every later deploy, do the backup below
first.

## Check it

```bash
docker ps --filter name=gpt-jobhunter        # STATUS should reach "healthy"
curl -s http://localhost:8000/health         # {"status":"healthy",...}
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8501/   # 200
```

Then open <http://localhost:8501> and register.

## Back up before you stop, update or clean

These commands remove the container, and the database with it:

| Command | Removes the container |
|---|---|
| `make prod` | Yes, then starts a new empty one |
| `make docker-run` | Yes, then starts a new empty one |
| `make stop` | Yes |
| `make docker-clean` | Yes, and the image |
| `docker restart gpt-jobhunter` | No. Data is kept |

Copy the database out first:

```bash
docker cp gpt-jobhunter:/app/jobhunter/all_jobs.db ./all_jobs.backup.db
```

## Update to a new version without losing data

```bash
git pull
docker cp gpt-jobhunter:/app/jobhunter/all_jobs.db ./all_jobs.backup.db   # 1. back up
make prod                                                                  # 2. rebuild and replace
docker cp ./all_jobs.backup.db gpt-jobhunter:/app/jobhunter/all_jobs.db   # 3. put the data back
docker restart gpt-jobhunter                                               # 4. reopen the file
```

Then run "Check it" again and sign in with an existing account to confirm the data came
back. New columns are added at startup by the backend, so an older database file is
brought forward when the container restarts.

## Read the logs

supervisord sends each program's output to a file, so the app's log lines are not in
`docker logs gpt-jobhunter`. Read the files:

```bash
docker exec gpt-jobhunter tail -n 100 /var/log/supervisor/backend.err.log
docker exec gpt-jobhunter tail -n 100 /var/log/supervisor/frontend.out.log
```

The backend log contains token fragments and password reset tokens
([runbook 03](03-api-keys-and-secrets.md)). Do not share it unedited.

## Change a secret

`docker restart` does not re-read `.env`. Edit `.env`, back up the database, run
`make docker-run`, restore the database, then `docker restart gpt-jobhunter`.

## About `docker-compose.yml`

The Compose file in the repository is not the same deployment as `make prod`, and as
written it is not safe to rely on:

- It does not pass `JWT_SECRET_KEY`, so tokens are signed with the default string from the
  source.
- It mounts `./all_jobs.db` to `/app/all_jobs.db`, but the app writes to
  `/app/jobhunter/all_jobs.db`. The mount persists nothing, and if `./all_jobs.db` does not
  exist on the host Docker creates a directory with that name.

Use `make prod` until the Compose file is corrected.

## Before exposing it beyond your own machine

The defaults suit a laptop. On a shared or public host, each of these is open today
([Known gaps](../architecture/c4.md#known-gaps)):

- Port 8000 serves `/jobs/search`, `/jobs`, `/stats` and `/initialize` without a token.
  Publish only 8501, or put both behind a proxy that requires sign-in.
- CORS allows every origin.
- Scores and dismissed postings are shared by all accounts.
- There is no TLS. Terminate it in a reverse proxy.

## If it fails

| Symptom | Likely cause | Fix |
|---|---|---|
| `make docker-build` stops with a `.env` message | No `.env` in the repository root | [Runbook 03](03-api-keys-and-secrets.md) |
| Build fails pulling `python:3.11-slim` | Registry not reachable | Check the network and `docker pull python:3.11-slim`, then retry |
| Container exits at once | Table creation failed in `/app/start.sh` | `docker logs gpt-jobhunter` shows the Python error |
| STATUS stays "unhealthy" | One of the two ports is not answering; the health check needs both | Read both log files above |
| Port already allocated | A local `make dev` holds 8000 or 8501 | Stop the local processes, then `make docker-run` |
| All accounts gone after an update | The container was replaced without a restore | Restore from your last `all_jobs.backup.db` |
| Searches fail with a key error though `.env` is right | Container created before `.env` was edited | "Change a secret" above |
