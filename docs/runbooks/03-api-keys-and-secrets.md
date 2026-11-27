# Runbook 03: API keys and secrets

**Goal:** a `.env` file with the three secrets the app needs, and a safe way to replace
any of them. Without the first two the app starts but finds no jobs and scores every one
at zero. Without the third, anyone can forge a login. Time: about 10 minutes.

## What goes in `.env`

| Variable | Needed for | If it is missing |
|---|---|---|
| `RAPID_API_KEY` | Job search (JSearch) | `/jobs/search` answers 500, "RAPID_API_KEY is missing" |
| `OPENAI_API_KEY` | Embeddings, job title suggestions, resume analysis and rewriting | Postings load without vectors, every score is 0.0, and the UI shows no error |
| `JWT_SECRET_KEY` | Signing login tokens | The code signs with a default string that is in the source, so tokens can be forged |
| `JWT_ALGORITHM` | Optional, default `HS256` | |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Optional, default `1440` (24 hours) | |
| `BACKEND_URL` | Frontend only, default `http://localhost:8000` | |

`.env` is in `.gitignore` and `.dockerignore`. Do not commit it, paste it into an issue, or
bake it into an image. Use `.env.example` as the template; `.env-template` is an older copy
without the JWT lines.

## 1. Get the keys

1. **OpenAI:** create a key at <https://platform.openai.com/api-keys>. The account needs
   billing enabled; embeddings are a paid API.
2. **RapidAPI:** subscribe to JSearch at
   <https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch> and copy the `X-RapidAPI-Key`
   value. Check the request limit of the plan you pick; one search spends about three
   requests per job title ([runbook 04](04-job-search-and-rate-limits.md)).
3. **JWT secret:** generate one. Do not invent it.

```bash
openssl rand -hex 32
```

## 2. Write `.env`

```bash
cp .env.example .env
```

```
RAPID_API_KEY=<from RapidAPI>
OPENAI_API_KEY=<from OpenAI>
JWT_SECRET_KEY=<64 hex characters from openssl>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

No quotes and no spaces around `=`.

## 3. Check it

Start the backend ([runbook 01](01-local-development.md)), then:

```bash
grep -c "fallback-secret-key" .env          # must print 0
curl -s http://localhost:8000/health        # "status":"healthy"
```

Sign in through the UI, run one search with one job title, then:

```bash
curl -s http://localhost:8000/stats
```

`total_jobs` above zero proves the RapidAPI key. `jobs_with_embeddings` equal to
`total_jobs` proves the OpenAI key.

## Replacing a secret

| Secret | Steps | Effect |
|---|---|---|
| `RAPID_API_KEY` | Edit `.env`, restart the backend | None on stored data |
| `OPENAI_API_KEY` | Edit `.env`, restart the backend | None on stored vectors. Postings loaded while the old key was failing have no vector; fill them with [runbook 05](05-embeddings-and-scores.md) |
| `JWT_SECRET_KEY` | Edit `.env`, restart the backend | Every user is signed out and must log in again. Do this at once if the key or the backend log may have been seen by someone else |

In Docker, a restart does not re-read `.env`. The container has to be created again, which
removes the database unless you back it up first ([runbook 02](02-deploy-with-docker.md)).

## If it fails

| Symptom | Likely cause | Fix |
|---|---|---|
| Every score is 0% | OpenAI key missing, rejected, or out of quota | [Runbook 05](05-embeddings-and-scores.md) |
| A real OpenAI key is treated as missing | `textAnalysis._is_placeholder_key` rejects any key that does not start with `sk-`, is shorter than 20 characters, or contains one of the words `your`, `api`, `key`, `here`, `demo`, `example`, `sample`, `test`, `placeholder`, `enter`, `insert`, `provide` anywhere in it, in any letter case | Create a new key until it passes, or fix the check in code. A random key can contain `api` or `key` by chance |
| 401 on every call after a restart | `JWT_SECRET_KEY` changed, so old tokens no longer verify | Log in again |
| 429 from JSearch | Plan limit reached | [Runbook 04](04-job-search-and-rate-limits.md) |
| Keys set in `.env` but the container does not see them | Container was started before the edit | Recreate it, [runbook 02](02-deploy-with-docker.md) |

## What the logs contain

The backend log is sensitive. At INFO level it records the first and last characters of
each login token, the decoded token payload, the first 10 characters of `JWT_SECRET_KEY`,
masked API keys, and every password reset token in full. Treat a copy of the log like a
copy of `.env`, and cut those lines out before pasting a log into an issue.
