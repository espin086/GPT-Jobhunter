# Runbook 04: job search and JSearch rate limits

**Goal:** run a search that loads postings, know how much quota it spent, and recover when
JSearch answers 429. Search is the only way postings enter the system, and it is the step
that spends a metered, monthly allowance. Time: 1 to 5 minutes per search.
Prerequisite: `RAPID_API_KEY` set ([runbook 03](03-api-keys-and-secrets.md)).

## What one search costs

| Quantity | Value | Where it is set |
|---|---|---|
| Requests per job title | Up to 3 (one per page) | `PAGES` in `jobhunter/config.py` |
| Extra requests | A retry with a simpler title when the first returns nothing | `extract.py` |
| Pause before each request | 2 seconds | `DELAY_BETWEEN_REQUESTS` in `extract.py` |
| Retries on 429 | 3, waiting from 2 up to 60 seconds | `MAX_RETRIES`, `INITIAL_BACKOFF`, `MAX_BACKOFF` in `extract.py` |

So five titles spend about 15 requests and take at least 30 seconds before any embedding
work. Onboarding searches the 3 titles the model suggests, about 9 requests. Compare that
with the monthly limit of your RapidAPI plan before searching a long list.

## Run a search

From the UI: open the Job Matches tab, enter titles, pick country, date range and location,
and search.

From the command line (this route takes no token):

```bash
curl -s -X POST http://localhost:8000/jobs/search \
  -H 'content-type: application/json' \
  -d '{"job_titles": ["Data Engineer"], "country": "us", "date_posted": "all", "location": ""}'
# {"total_jobs_found": <n>, "message": "Successfully found <n> jobs", "success": true}
```

`date_posted` is passed to JSearch as is; `all` is the default. An empty `location`
becomes the country's name for `us`, `uk`, `ca`, `au`, `de`, `fr`, `es` and `it`.

The request blocks until extract, transform, embedding and load have all finished.

## Check it

```bash
curl -s http://localhost:8000/stats
```

- `total_jobs` went up by the number of postings that were new. `total_jobs_found` in the
  search response counts everything JSearch returned, including postings already stored,
  so the two numbers differ.
- `jobs_with_embeddings` equals `total_jobs`. If it is lower, the OpenAI call failed;
  see [runbook 05](05-embeddings-and-scores.md).

A search does not update match scores. Score from the UI, or:

```bash
curl -s -X POST http://localhost:8000/similarity/update \
  -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' \
  -d '{"resume_name": "<your resume name>"}'
```

## If it fails

| Symptom | Likely cause | Fix |
|---|---|---|
| 500, "RAPID_API_KEY is missing" | Key not in the backend's environment | [Runbook 03](03-api-keys-and-secrets.md), then restart the backend |
| `total_jobs_found` is 0, "No jobs found", and the backend log shows "429" or "Rate limit exceeded" | Plan limit or per-second limit reached, and 3 retries did not clear it. The API reports this as "no jobs", not as an error; only the log names the rate limit | Wait, then search fewer titles. Check usage on the RapidAPI dashboard. Lower `PAGES` to 1 to cut each title to one request |
| `total_jobs_found` is 0, "No jobs found", and no 429 in the log | The title and location matched nothing, including the simpler retry | Use a plainer title and set `date_posted` to `all` |
| 401 or 403 from JSearch in the backend log | Key wrong, or not subscribed to JSearch | Re-copy the key; confirm the subscription on RapidAPI |
| Search works but the list shows old postings first | Results are ordered by score, then date, and new postings have no score yet | Update scores |
| The same posting never appears twice | Postings are keyed on `"<company> - <title>"` | Expected; see [ADR 0004](../decisions/0004-jsearch-as-the-job-source-with-file-staged-etl.md) |
| Searches get slower over time | The API path never clears `jobhunter/temp/data/raw` and `processed`, and each search re-reads all of it | Stop the backend, delete the JSON files in those two folders, start it again. Stored postings are in the database and are not affected |
| The request times out in the browser | Many titles, each with a 2 second pause per page | Search fewer titles per request |

[Issue #165 (Handle Jobs API Rate Limit Gracefully)](https://github.com/espin086/GPT-Jobhunter/issues/165)
tracks replacing the retry loop with a circuit breaker.
