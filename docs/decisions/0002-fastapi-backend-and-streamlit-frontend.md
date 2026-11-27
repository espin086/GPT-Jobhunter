# 0002. A FastAPI backend and a Streamlit frontend that talk over REST

**Status:** accepted · **In the code since:** 2025-07-02 · **Recorded:** 2026-11-27

## Context

Until July 2025 the whole application was one Streamlit script, `jobhunter/main.py`. The
search pipeline, the database calls and the screens ran in one process, so the matching
logic could only be exercised by clicking through the UI, and nothing else could call it.

## Decision

1. The backend is a FastAPI app (`jobhunter/backend/`, port 8000). It owns business logic,
   the pipeline, embeddings, accounts and the database.
2. The frontend is a Streamlit app (`jobhunter/frontend/streamlit_app.py`, port 8501). It
   holds no business logic and reaches the backend only through `BACKEND_URL`.
3. The contract between them is the OpenAPI schema FastAPI generates, saved as
   `openapi.json` by `make openapi`.

The README states the reason: "Separating them means the matching engine can be tested,
deployed, and scaled independently of the UI."

## Options considered

| Option | Why not |
|---|---|
| Keep the single Streamlit app | No API for tests or other clients; every rerun of the script re-enters pipeline code |
| FastAPI with a JavaScript frontend | A better UI ceiling, at the cost of a second language and build chain for a project maintained in Python |
| Streamlit calling the service classes in-process | Keeps one process but loses the HTTP contract, per-request auth and the generated API docs |

## Consequences

- **Testing:** routes and services can be tested without a browser. `tests/` does this for
  auth, user isolation, the database and the optimizer.
- **Two processes to run:** `make dev` starts both; the container runs both under
  supervisord ([ADR 0006](0006-one-container-two-processes.md)).
- **Auth became necessary:** an HTTP API that anyone on the network can reach needs
  accounts, which led to [ADR 0005](0005-jwt-accounts-over-a-shared-job-table.md).
- **The split is not complete.** `SQLiteHandler.py` and `textAnalysis.py` still import
  Streamlit and call `st.error`, so the backend depends on the frontend's library. The old
  `jobhunter/main.py` is still in the repository and still started by the devcontainer.
- **Long requests:** a search or an onboarding run is one blocking HTTP call that can take
  minutes. The frontend waits on it; there is no job queue.

## Revisit when

A second client needs the API (a browser extension is on the roadmap), or searches become
long enough that a blocking request times out and a background job is needed.
