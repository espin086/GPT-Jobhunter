# Runbook 05: embeddings and match scores

**Goal:** every stored posting has a vector and a score that reflects your current resume.
When this breaks, the app still runs and shows 0% on every posting with no error, so the
user sees a product that does not work and no reason why. Time: 5 minutes to diagnose,
longer to rebuild a large table.
Prerequisite: `OPENAI_API_KEY` set ([runbook 03](03-api-keys-and-secrets.md)).

## How a score is made

1. When a posting is first loaded, its title and description (cut at 8,000 characters) are
   sent to OpenAI `text-embedding-3-small`, in batches of up to 100. The 1,536-number
   vector is stored in `jobs_new.embeddings` as JSON text.
2. When scores are updated, the resume is embedded the same way, compared with every
   stored vector by cosine similarity, and the result (0.0 to 1.0) is written to
   `jobs_new.resume_similarity`.

Scores are updated only by `POST /similarity/update` (the UI calls it) and by onboarding.
Uploading a new resume or running a search does not rescore.

## Diagnose

```bash
curl -s http://localhost:8000/stats
```

| What you see | Meaning | Go to |
|---|---|---|
| `total_jobs` is 0 | Nothing to score | [Runbook 04](04-job-search-and-rate-limits.md) |
| `jobs_with_embeddings` below `total_jobs` | Some postings were loaded while the OpenAI call was failing | "Fill missing vectors" |
| `jobs_with_embeddings` equals `total_jobs`, `jobs_with_similarity_scores` is 0 | Vectors are fine; scoring has not run or the resume could not be embedded | "Rescore" |
| All three match and the UI still shows 0% | The UI is filtering, or another account rescored | "Scores changed by themselves" below |

The same check in SQL, with the backend stopped or running:

```bash
sqlite3 jobhunter/all_jobs.db "
  SELECT COUNT(*)                                    AS jobs,
         SUM(embeddings IS NOT NULL)                 AS with_vector,
         SUM(resume_similarity > 0)                  AS with_score,
         ROUND(MAX(resume_similarity), 3)            AS best
  FROM jobs_new;"
```

## Rescore

From the UI, pick the resume and update scores. From the command line:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H 'content-type: application/json' \
  -d '{"username_or_email": "<you>", "password": "<password>"}' | jq -r .access_token)

curl -s -X POST http://localhost:8000/similarity/update \
  -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' \
  -d '{"resume_name": "<resume name as listed by GET /resumes>"}'
```

A response of `{"success": false, "message": "Failed to update similarity scores", ...}`
with HTTP 200 means the resume could not be embedded. That is almost always the OpenAI
key: missing, rejected by the placeholder check, or out of quota. The backend log has the
exact line.

## Fill missing vectors

```bash
make rebuild-embeddings
```

It shows a masked copy of the OpenAI key, asks for confirmation, then runs
`python -m jobhunter.rebuild_embeddings`, which re-embeds stored postings and writes the
vectors back. It calls OpenAI once per batch for the whole table, so on a large table it
costs time and money in proportion to the number of postings.

The script's second half, which is meant to rescore every resume, calls
`fetch_resumes_from_db()` without a user id and stops with a `TypeError`. The vectors are
already saved by then. Rescore afterwards with the step above.

In Docker, run it inside the container:

```bash
docker exec -it gpt-jobhunter python -m jobhunter.rebuild_embeddings
```

## Check it

Run the `/stats` call again. `jobs_with_embeddings` should equal `total_jobs`, and after a
rescore `jobs_with_similarity_scores` should be close to it. Then:

```bash
curl -s "http://localhost:8000/jobs?limit=5" | jq '.jobs[] | {title, company, resume_similarity}'
```

The five postings come back highest score first.

## If it fails

| Symptom | Likely cause | Fix |
|---|---|---|
| Every score is 0.0 after a rescore | The resume came back as a zero vector | Fix the OpenAI key ([runbook 03](03-api-keys-and-secrets.md)), then rescore |
| Log says the key "is a placeholder value" for a real key | The placeholder check rejected it | See the key table in [runbook 03](03-api-keys-and-secrets.md) |
| Rate limit errors from OpenAI in the log | Too many requests for the account's tier | The code retries 5 times with backoff; wait and run again |
| Scores changed by themselves | Another account rescored. `resume_similarity` is one shared column | Rescore with your resume. See [ADR 0005](../decisions/0005-jwt-accounts-over-a-shared-job-table.md) |
| A long posting scores oddly | Only the first 8,000 characters are embedded | Expected |
| Scores after switching embedding model make no sense | Old and new vectors are mixed | `make rebuild-embeddings`, then rescore |
| `make rebuild-embeddings` ends with `TypeError: fetch_resumes_from_db()` | Known defect in the rescoring half | Vectors are saved; rescore by hand |
