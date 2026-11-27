# Architecture decision records

Each record states one decision that shapes GPT Job Hunter, the options that were not
taken, and what the decision costs. Read the record before changing the part of the system
it covers, so the tradeoff is reopened on purpose and not by accident.

These six were written on 2026-11-27 from the code and the README, after the decisions had
already shipped. Where the reason was written down at the time (the README gives it for
0001 and 0002), the record quotes it. Where it was not, the record says so and the
tradeoffs are a reading of the code, not a memory of the discussion.

To change a decision, add a new record that supersedes the old one. Do not edit an
accepted record except to mark it superseded.

| ADR | Decision | In the code since | Status |
|---|---|---|---|
| [0001](0001-rank-jobs-by-embedding-similarity.md) | Rank postings by cosine similarity of OpenAI embeddings, not keyword overlap | 2023-10-28 | accepted |
| [0002](0002-fastapi-backend-and-streamlit-frontend.md) | A FastAPI backend and a Streamlit frontend that talk over REST | 2025-07-02 | accepted |
| [0003](0003-sqlite-single-file-with-embeddings-as-json.md) | One SQLite file, embeddings stored as JSON text, scoring by full scan | 2023-09-06 | accepted, under review in issue #170 |
| [0004](0004-jsearch-as-the-job-source-with-file-staged-etl.md) | JSearch on RapidAPI as the only job source, loaded through file-staged extract, transform and load | 2023-09-06 | accepted |
| [0005](0005-jwt-accounts-over-a-shared-job-table.md) | Accounts with JWT bearer tokens; resumes and tracking per user over a shared job table | 2025-12-13 | accepted |
| [0006](0006-one-container-two-processes.md) | One Docker image that runs both processes under supervisord | 2025-07-02 | accepted |

Diagrams: [../architecture/c4.md](../architecture/c4.md).

## Writing a new record

Copy the shape of an existing one: Context, Decision, Options considered, Consequences,
Revisit when. Number it with the next free four digits, add a row to the table above, and
link the issue that prompted it. A record is `proposed` until the maintainer merges it.
Prices and limits from a vendor get a source link or the word "unverified".
