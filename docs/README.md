# Documentation

GPT Job Hunter scores job postings against a resume and rewrites the resume for the best
matches. These pages tell you how to run it, how it is built, and why it is built that way.
Pick the row that matches what you are trying to do.

| I want to | Read |
|---|---|
| Try it in 15 minutes | [QUICKSTART.md](../QUICKSTART.md) |
| See every install option | [INSTALLATION.md](../INSTALLATION.md) |
| Understand the system | [architecture/c4.md](architecture/c4.md): context, containers, components, deployment, data model, run sequences, known gaps |
| Know why a design choice was made | [decisions/](decisions/README.md): six architecture decision records |
| Run or fix it | [runbooks/](#runbooks) below |
| Change the code | [CONTRIBUTING.md](../CONTRIBUTING.md) |
| Call the API | `openapi.json` in the repository root, or `http://localhost:8000/docs` while the backend runs |

## Runbooks

Each runbook has a goal, the steps, a check that proves it worked, and a table of failures
with their fixes.

| Runbook | Use it when |
|---|---|
| [01 Local development](runbooks/01-local-development.md) | Running the app on your machine, and keeping your data while you do |
| [02 Deploy with Docker](runbooks/02-deploy-with-docker.md) | Running the container, updating it, reading its logs |
| [03 API keys and secrets](runbooks/03-api-keys-and-secrets.md) | Setting up `.env`, replacing a key |
| [04 Job search and rate limits](runbooks/04-job-search-and-rate-limits.md) | A search fails, returns nothing, or JSearch answers 429 |
| [05 Embeddings and match scores](runbooks/05-embeddings-and-scores.md) | Every job shows 0%, or scores look wrong |
| [06 Database backup and reset](runbooks/06-database-backup-and-reset.md) | Before any update, and when starting over |
| [07 Accounts and password reset](runbooks/07-accounts-and-password-reset.md) | A user cannot sign in, or an account must be turned off |

## Other files in this folder

`conf.py`, `index.rst`, `jobhunter.rst`, `modules.rst`, `Makefile` and `make.bat` are a
Sphinx setup from 2023 that generates API reference pages from docstrings. It predates the
backend and frontend split and does not list `jobhunter.backend` or `jobhunter.frontend`.
The Markdown pages above are the maintained documentation.
