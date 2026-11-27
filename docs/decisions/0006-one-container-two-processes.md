# 0006. One Docker image that runs both processes under supervisord

**Status:** accepted · **In the code since:** 2025-07-02 · **Recorded:** 2026-11-27

## Context

After the split into a backend and a frontend ([ADR 0002](0002-fastapi-backend-and-streamlit-frontend.md))
there were two processes to ship. The people running this app are job seekers on their own
machines, so the deployment had to stay one command. No reason for the design was written
down; the tradeoffs below are read from the Dockerfile and the Makefile.

## Decision

1. One image, built from `python:3.11-slim`, holds the whole `jobhunter` package.
2. The container's command is `/app/start.sh`, which creates the database tables and then
   starts `supervisord`.
3. `supervisord` runs two programs and restarts either one if it exits: `uvicorn` on port
   8000 and `streamlit` on port 8501. Their output goes to `/var/log/supervisor/`.
4. The frontend reaches the backend at `http://localhost:8000` inside the container.
5. `make prod` builds the image and runs it with `--env-file .env`, both ports published
   and `--restart unless-stopped`. The image's health check requires both ports to answer.
6. `.env` is excluded from the image by `.dockerignore`; `make docker-build` checks for it
   after the build.

## Options considered

| Option | Why not |
|---|---|
| Two containers with Docker Compose | The usual shape: separate logs, restarts and scaling for each service. `docker-compose.yml` has this layout commented out. It is more to explain to a non-technical user |
| A process manager on the host, no Docker | No image to build, but Python and Poetry on every user's machine |
| A platform that builds from the repository | No Docker knowledge needed, but a hosting account and a place for the SQLite file |

## Consequences

- **One command:** `make prod` is the whole deployment.
- **No persistent storage.** The database is written inside the container. `make stop`,
  `make docker-clean` and a repeat of `make prod` remove the container and the data with it.
  [Runbook 02](../runbooks/02-deploy-with-docker.md) puts a backup before each of them.
- **Logs are inside the container,** not in `docker logs`, because supervisord writes each
  program's output to its own file.
- **The two services cannot scale apart,** which gives up one of the stated reasons for
  ADR 0002 until the Compose layout is finished.
- **`docker-compose.yml` is not equivalent to `make prod`.** It does not pass
  `JWT_SECRET_KEY`, and it mounts `./all_jobs.db` to `/app/all_jobs.db`, while the app
  writes to `/app/jobhunter/all_jobs.db`. Data is not persisted by that file as written.
- **The image runs as root** and includes the test suite and build tools.

## Revisit when

The database moves out of the container (issue #170), the app is hosted for more than one
person, or the frontend and backend need different resources.
