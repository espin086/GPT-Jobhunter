# Runbook 01: run GPT Job Hunter on your machine for development

**Goal:** the backend and the frontend running locally with auto-reload, so a code change
shows up without a restart. Time: about 10 minutes, most of it the dependency install.
Prerequisites: Python 3.11 or 3.12, and the keys from [runbook 03](03-api-keys-and-secrets.md).

Read the warning in step 3 before the first `make dev`. It deletes the local database.

## 1. Install

With Poetry, which the Makefile uses:

```bash
make install            # installs Poetry if it is missing, then the dependencies
```

Or with pip, into a virtual environment:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -e . pytest
```

## 2. Configure

```bash
cp .env.example .env
openssl rand -hex 32    # paste the output as JWT_SECRET_KEY in .env
```

Fill in `OPENAI_API_KEY` and `RAPID_API_KEY`. Accounts, resume upload and the tracker work
without them. Search needs the RapidAPI key and scoring needs the OpenAI key.

## 3. Start

| Command | Database | Use it when |
|---|---|---|
| `make dev` | **Deleted on every start**, along with the staging files | You want a clean slate each run |
| The two commands below | Kept between runs | You want your account, resumes and postings to survive a restart |

`make dev` runs `rm -f jobhunter/all_jobs.db` before it starts the two processes. Every
account, resume, posting and tracker entry on this machine goes with it. Back the file up
first ([runbook 06](06-database-backup-and-reset.md)) or use the commands below.

To keep data, start each process in its own terminal:

```bash
# terminal 1: backend
set -a; . ./.env; set +a
poetry run uvicorn jobhunter.backend.api:app --host 0.0.0.0 --port 8000 --reload

# terminal 2: frontend
BACKEND_URL=http://localhost:8000 poetry run streamlit run jobhunter/frontend/streamlit_app.py --server.port=8501
```

With the pip install, replace `poetry run` with `.venv/bin/python -m`.

## 4. Check it

```bash
curl -s http://localhost:8000/health
# {"status":"healthy","timestamp":"...","version":"1.0.0"}

curl -s http://localhost:8000/stats
# {"total_jobs":0,"total_resumes":0,"jobs_with_embeddings":0,"jobs_with_similarity_scores":0,"database_path":"..."}
```

Then open <http://localhost:8501>, register an account and upload a resume. The API
reference is at <http://localhost:8000/docs>.

## 5. Stop

```bash
make stop
```

`make stop` kills every process listening on ports 8000 and 8501, not only this app's, and
it also stops and removes the Docker container named `gpt-jobhunter` if one exists. If you
run the Docker deployment on the same machine, read
[runbook 02](02-deploy-with-docker.md) before using it.

## Other commands

| Command | What it does | Note |
|---|---|---|
| `make test` | Runs `pytest tests/ -v` | Fails at collection without `RAPID_API_KEY`; see [CONTRIBUTING.md](../../CONTRIBUTING.md) for the keyless command |
| `make format` | `black` and `isort --profile black` on `jobhunter/` | Neither tool is in `pyproject.toml`; install them first with `poetry run pip install black isort` |
| `make coverage` | `pytest --cov` | Needs `pytest-cov`, also not in `pyproject.toml` |
| `make openapi` | Rewrites `openapi.json` from the running code | Run it after changing a route or a model |
| `make clean` | Removes caches and coverage output | Does not touch the database |

## If it fails

| Symptom | Likely cause | Fix |
|---|---|---|
| `make dev` prints that `.env` is missing | No `.env` in the repository root | Step 2 |
| `Address already in use` | An earlier run still holds port 8000 or 8501 | `make stop`, or `lsof -ti:8000` to see what holds it |
| Frontend says it cannot connect to the backend | Backend not up yet, or `BACKEND_URL` points elsewhere | Check step 4's health call; restart the frontend with `BACKEND_URL` set |
| `ModuleNotFoundError: No module named 'config'` | A bare import inside the package | Use `from jobhunter import config`; the package runs as `jobhunter.*` |
| Account gone after a restart | `make dev` deleted the database | Expected; use the two-terminal start |
| Python 3.13 fails to install | `pyproject.toml` requires `>=3.11,<3.13` | Use 3.11 or 3.12 |
