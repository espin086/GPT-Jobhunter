# Contributing

This guide gets a change from an idea to a merged pull request without a round of avoidable
review comments. It applies to everyone the same way: outside contributors, the maintainer,
and coding agents. The maintainer merges; nobody else does.

New to the code? Start with [QUICKSTART.md](QUICKSTART.md), then the
[architecture page](docs/architecture/c4.md).

## The path: issue, branch, pull request

1. **Issue first.** Find the issue your change closes, or open one. Look for
   [`good first issue` and `help wanted`](https://github.com/espin086/GPT-Jobhunter/issues).
   An issue says what is wrong or missing, why it matters, and how we will know it is done.
   Two or three sentences are enough for a small fix. Comment on it to say you are taking it.
2. **Branch from `main`, named for the issue.** `fix/165-rate-limit-backoff`,
   `feat/164-salary-estimate`, `docs/170-postgres-notes`. From the issue page, "Create a
   branch" does this for you, or run `gh issue develop <number> --checkout`. Outside
   contributors: fork first, then branch in the fork.
3. **Make the change with its tests.** One coherent commit per piece of work, with a
   message in the form `type(scope): summary`, for example
   `fix(extract): stop retrying after the third 429`.
4. **Run the checks below.**
5. **Open the pull request into `main`.** The body starts with the problem and who it
   affects, then what changed and how you tested it, and contains `Closes #<number>` so the
   issue closes on merge. `Refs #12` or a bare `#12` does not link it.
6. **Review.** Fix findings in new commits; do not rewrite reviewed history. The
   maintainer merges when the checks pass.

Never commit to `main` directly.

## Set up

```bash
git clone https://github.com/<you>/GPT-Jobhunter.git
cd GPT-Jobhunter
make install
cp .env.example .env      # fill in per docs/runbooks/03-api-keys-and-secrets.md
```

Python 3.11 or 3.12. [Runbook 01](docs/runbooks/01-local-development.md) covers running the
app and the one thing to know first: `make dev` deletes the local database on every start.

## Checks to run before you push

### Tests

```bash
# No API keys needed. 70 tests on 2026-11-27.
poetry run pytest tests/ --ignore=tests/search_jobs_test.py --ignore=tests/test_embedding.py

# Everything. Needs RAPID_API_KEY and OPENAI_API_KEY in .env, and spends real quota.
make test
```

| Test file | Covers | Needs a key |
|---|---|---|
| `test_authentication.py`, `test_password_reset.py` | Register, login, tokens, reset | No |
| `test_user_isolation.py` | One user cannot read another's resumes or tracker | No |
| `test_database.py`, `dataTransformer_test.py`, `FileHandler_test.py`, `extract_salary_test.py` | Schema, transforms, staging files | No |
| `test_resume_optimizer.py` | Optimizer service with OpenAI mocked | No |
| `text_similarity_test.py`, `resume_exists_test.py` | Similarity with the embedding call mocked; the live cases skip themselves without a key | No |
| `test_embedding.py` | Real embedding calls; fails without the key | `OPENAI_API_KEY` |
| `search_jobs_test.py` | Real JSearch call; fails at import without the key | `RAPID_API_KEY` |

A change to behavior comes with a test that fails without it. A bug fix comes with a test
that reproduces the bug. Tests that need a network call belong with the keyed files, not
the keyless ones, so the keyless command stays runnable by anyone.

### Format

```bash
poetry run pip install black isort     # once; they are not in pyproject.toml yet
make format                            # black, then isort --profile black, on jobhunter/
```

### Imports

Inside the package always import from the package: `from jobhunter import config`, never
`import config`. The app runs as `jobhunter.*` locally and in Docker, and a bare import
fails in one of the two.

### API contract

If you add or change a route or a model in `jobhunter/backend/`, run `make openapi` and
commit the updated `openapi.json`.

## Keep the docs true

A change is not done until the page that describes it is right.

| If you change | Update |
|---|---|
| A route, a table, a service, or how processes are deployed | [docs/architecture/c4.md](docs/architecture/c4.md), including the Known gaps table when you close one |
| A decision recorded in an ADR (the database, the job source, auth, the matching method, the container layout) | Add a new record under [docs/decisions/](docs/decisions/README.md) that supersedes the old one |
| A `make` target, an environment variable, a port, a file path | The [runbook](docs/runbooks/) that uses it, plus `.env.example` for a new variable |
| Setup steps | [QUICKSTART.md](QUICKSTART.md) and [INSTALLATION.md](INSTALLATION.md) |

Commands in a runbook are ones somebody ran. If you could not run a step, say so in the
runbook.

## What CI does today

`.github/workflows/python_application.yml` runs on pushes and pull requests to `main`. It
sets up Python 3.10, installs `flake8 pytest pylint black isort`, looks for a
`requirements.txt`, runs `black` and `isort`, then `pytest` from inside `tests/`.

The project needs Python 3.11 and has no `requirements.txt`, so the app's dependencies are
never installed there. The last two runs on `main` (2026-07-22) failed. Until the workflow
is fixed, a red check on your pull request is expected: paste the output of the keyless
test command into the pull request body so the reviewer has evidence. Fixing the workflow
is a welcome contribution.

## What not to put in an issue, a commit or a pull request

- API keys, `.env` files, or a `JWT_SECRET_KEY`.
- Backend logs as they are. They contain token fragments and password reset tokens; see
  [runbook 03](docs/runbooks/03-api-keys-and-secrets.md).
- Database files (`*.db`). They hold emails, password hashes and resume text.
- A real resume. Use an invented one in tests and examples.

If you find a security problem, do not post the details in a public issue. Contact the
maintainer through their GitHub profile first.

## Review checklist

The reviewer checks, and you can check first:

- The pull request closes an issue and its scope matches that issue.
- New behavior has a test, and the keyless tests pass.
- No secret, log or database file is in the diff.
- Queries on `resumes` and `job_tracking` filter by the caller's `user_id`.
- SQL uses `?` parameters, never string formatting with user input.
- Docs in the table above are updated.

## Need help?

Open an issue with the `question` label, or start a thread in
[Discussions](https://github.com/espin086/GPT-Jobhunter/discussions).
