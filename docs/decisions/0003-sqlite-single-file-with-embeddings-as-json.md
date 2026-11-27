# 0003. One SQLite file, embeddings stored as JSON text, scoring by full scan

**Status:** accepted, under review in [issue #170 (PostgreSQL Migration)](https://github.com/espin086/GPT-Jobhunter/issues/170) · **In the code since:** 2023-09-06 · **Recorded:** 2026-11-27

## Context

The app started as a tool one person runs on a laptop. It needed to keep postings between
runs and nothing else: no server to install, no account to create, no connection string.
No reason for the choice was written down at the time; the tradeoffs below are read from
the code.

## Decision

1. All durable data is in one SQLite file, `jobhunter/all_jobs.db`, opened with the
   standard-library `sqlite3` module. Each function opens and closes its own connection.
2. A posting's embedding is stored in `jobs_new.embeddings` as a JSON array in a TEXT column.
3. Scoring reads every posting's vector, parses the JSON, and computes cosine similarity in
   Python on 8 threads. There is no vector index.
4. The schema is created at backend startup with `CREATE TABLE IF NOT EXISTS`. Columns
   added later are applied with `ALTER TABLE` in the same startup code. There is no
   migration tool and no schema version.

## Options considered

| Option | Why not |
|---|---|
| PostgreSQL | Concurrent writers and real migrations, at the cost of a database server for every user of a laptop tool. Issue #170 proposes this, with SQLAlchemy and Alembic, PostgreSQL 15 in Docker. It was written before accounts existed and keeps the schema as it is, so it would not by itself add a vector index or per-user scores |
| PostgreSQL with the pgvector extension | Adds indexed nearest-neighbor search on top of the row above. Not proposed anywhere yet |
| SQLite with a vector extension | Keeps the single file and adds an index, but needs a native extension installed on every platform |
| Embeddings in a separate file (NumPy, Parquet) | Faster to load, but a second store to keep in step with the rows |

## Consequences

- **Setup:** nothing to install. A new clone has a working database on first start.
- **Backup and reset:** copy or delete one file. See
  [runbook 06](../runbooks/06-database-backup-and-reset.md).
- **Scale:** each scoring run parses every stored vector. At 1,536 floats per posting that
  is tens of kilobytes of JSON each, so the time grows in a straight line with the table.
  It has not been measured at 10,000 postings or more.
- **Concurrency:** SQLite allows one writer at a time. Two users searching at once can hit
  "database is locked".
- **Shared columns:** `resume_similarity` and `hidden` sit on the shared posting row, so
  they hold one value for all users. See
  [ADR 0005](0005-jwt-accounts-over-a-shared-job-table.md).
- **Deployment:** the file lives next to the code. In Docker that is the container's
  writable layer, which is removed with the container.
- **Schema drift:** the `jobs_new` table is defined in two places
  (`SQLiteHandler.create_db_if_not_there` and `DatabaseService.initialize_database`) that
  already differ on `UNIQUE` and `DEFAULT`. Whichever runs first on an empty file wins.

## Revisit when

More than one person uses the same instance at the same time, the posting table passes the
size where a scoring run takes longer than a user will wait, or scores need to be kept per
resume. Issue #170 is where that discussion is open.
