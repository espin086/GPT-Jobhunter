# Quick start

This page takes you from a fresh clone to a ranked list of jobs scored against your own
resume, on your own machine, in about 15 minutes. It is the shortest path that works;
[INSTALLATION.md](INSTALLATION.md) has the long form and the
[runbooks](docs/runbooks/01-local-development.md) cover running it day to day.

## Before you start

| You need | Why | Where |
|---|---|---|
| Python 3.11 or 3.12 | `pyproject.toml` requires `>=3.11,<3.13` | <https://www.python.org/downloads/> |
| An OpenAI API key | Scores each job against your resume and rewrites the resume | <https://platform.openai.com/api-keys> (paid API) |
| A RapidAPI key subscribed to JSearch | The source of job postings | <https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch> |

Your resume text and the job postings are sent to OpenAI, and your search terms to
JSearch. Accounts, resumes and tracked jobs are stored only on your machine.

## 1. Get the code

```bash
git clone https://github.com/espin086/GPT-Jobhunter.git
cd GPT-Jobhunter
```

## 2. Add your keys

```bash
cp .env.example .env
openssl rand -hex 32        # copy the output
```

Open `.env` and set three values:

```
RAPID_API_KEY=<your RapidAPI key>
OPENAI_API_KEY=<your OpenAI key>
JWT_SECRET_KEY=<the openssl output>
```

`JWT_SECRET_KEY` signs your login. Do not leave the placeholder in.

## 3. Install and start

```bash
make install    # installs Poetry if needed, then the dependencies
make dev        # starts the backend on 8000 and the frontend on 8501
```

`make dev` begins from an empty database every time it starts. That is fine for a first
look. To keep your account and jobs between runs, start the two processes the way
[runbook 01](docs/runbooks/01-local-development.md) shows.

No Poetry? This works too:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -e .
set -a; . ./.env; set +a
.venv/bin/python -m uvicorn jobhunter.backend.api:app --port 8000 &
BACKEND_URL=http://localhost:8000 .venv/bin/python -m streamlit run jobhunter/frontend/streamlit_app.py --server.port=8501
```

## 4. Check that it is up

```bash
curl -s http://localhost:8000/health
# {"status":"healthy","timestamp":"...","version":"1.0.0"}
```

## 5. Use it

1. Open <http://localhost:8501>.
2. Choose **Register**, create an account, and sign in.
3. Upload your resume as a PDF or a text file.
4. Onboarding runs by itself: it suggests three job titles, searches them, scores every
   posting against your resume and analyzes the resume. This takes a minute or two and
   spends about 9 JSearch requests.
5. Open **Job Matches** for the ranked list, **Resume Optimizer** for the ATS score and
   the rewritten resume, and **Job Tracker** to move saved jobs through
   Apply, HR Screen, 1st Round, 2nd Round and Rejected.

## 6. Stop

```bash
make stop
```

## No keys yet?

The app still starts. Accounts, resume upload and the tracker work. Search answers
"RAPID_API_KEY is missing" and every match score stays at 0% until both keys are set.

## Where to go next

| I want to | Read |
|---|---|
| Keep my data between restarts | [Runbook 01: local development](docs/runbooks/01-local-development.md) |
| Run it in Docker | [Runbook 02: deploy with Docker](docs/runbooks/02-deploy-with-docker.md) |
| Fix 0% scores | [Runbook 05: embeddings and match scores](docs/runbooks/05-embeddings-and-scores.md) |
| Understand how it fits together | [Architecture (C4 diagrams)](docs/architecture/c4.md) |
| Know why it was built this way | [Architecture decision records](docs/decisions/README.md) |
| Call the API directly | <http://localhost:8000/docs> while it runs, or `openapi.json` |
| Change the code | [CONTRIBUTING.md](CONTRIBUTING.md) |
