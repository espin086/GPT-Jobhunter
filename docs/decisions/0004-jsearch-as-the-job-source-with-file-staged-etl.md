# 0004. JSearch on RapidAPI as the only job source, loaded through file-staged ETL

**Status:** accepted · **In the code since:** 2023-09-06 · **Recorded:** 2026-11-27

## Context

The app needs current postings from many employers without scraping job boards, which
breaks often and can violate their terms. It also needs to see what the source returned
when a search produces odd results. No reason for the choice of provider was written down;
the tradeoffs below are read from the code.

## Decision

1. Postings come from one source: the JSearch API on RapidAPI
   (`https://jsearch.p.rapidapi.com/search`), authenticated with `RAPID_API_KEY`.
2. A search runs as three steps that hand off through files on disk:
   - **Extract** (`extract.py`): for each title, request up to 3 pages
     (`PAGES` in `config.py`) with the query "`<title>` jobs in `<location>`", and write
     each posting as a JSON file under `jobhunter/temp/data/raw/`.
   - **Transform** (`dataTransformer.py`): read the raw files, keep the fields listed in
     `config.SELECTED_KEYS`, rename them to the database's column names, flatten lists, and
     write the result under `jobhunter/temp/data/processed/`.
   - **Load** (`load.py`, `SQLiteHandler.py`): build the key `"<company> - <title>"`, skip
     keys already stored, embed the new postings, insert them.
3. Calls to JSearch are sequential, with a 2 second pause before each one. A 429 response
   is retried up to 3 times with backoff from 2 to 60 seconds, then the search fails.
4. When a title returns nothing, extract retries with a simpler title (seniority words
   such as "senior" or "principal" removed).

## Options considered

| Option | Why not |
|---|---|
| Scrape job boards directly | No API fee, but fragile and against most boards' terms |
| Several job APIs behind one interface | Better coverage, at the cost of merging and de-duplicating different schemas. Nothing in the code prepares for a second source |
| Pass data between steps in memory | Faster and leaves nothing on disk, but loses the raw response that explains a bad result |

## Consequences

- **Quota:** one search spends about titles × 3 requests, more when the fallback runs.
  Onboarding searches 3 suggested titles, so about 9 requests. The README quotes 1,000
  requests a month on the free tier; that figure is unverified.
- **Speed:** the pause alone puts a floor of about 2 seconds per request under every search.
- **De-duplication is coarse.** The same title at the same company in two cities, or
  reposted next month, is one row. The first one seen is kept.
- **Disk:** the API path never clears the staging folders, so each search re-reads every
  earlier raw file. `make dev` clears them on start and the CLI clears them when it ends.
- **Coverage:** results are whatever JSearch returns for a title and location. The README
  lists US postings as the tested case.
- **One vendor:** if JSearch changes its fields, `SELECTED_KEYS` and the rename map in
  `DataTransformer.transform()` are the two places to update.

## Revisit when

JSearch pricing or limits stop fitting the usage, a second source is needed for coverage,
or the retry behavior in
[issue #165 (Handle Jobs API Rate Limit Gracefully)](https://github.com/espin086/GPT-Jobhunter/issues/165)
is redesigned.
