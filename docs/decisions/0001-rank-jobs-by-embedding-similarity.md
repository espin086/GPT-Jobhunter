# 0001. Rank postings by cosine similarity of OpenAI embeddings

**Status:** accepted · **In the code since:** 2023-10-28 · **Recorded:** 2026-11-27

## Context

The product's promise is one number per posting: how well this job fits this resume. A
resume and a posting rarely use the same words for the same skill. The README gives the
example of "led a cross-functional engineering team" against "managed engineers across
departments", which share no keywords. A score built on shared words would rank that pair
low and send the job seeker past a good match.

## Decision

1. Every posting is embedded once, when it is first loaded, from its title and description.
2. The resume is embedded each time scores are updated.
3. The score is the cosine similarity of the two vectors, stored as `resume_similarity`
   between 0.0 and 1.0 and shown as a percentage.
4. The embedding model is OpenAI `text-embedding-3-small` (since 2025-04-03), called from
   `jobhunter/textAnalysis.py` in batches of up to 100 texts, with input cut at 8,000
   characters and up to 5 retries with backoff.

## Options considered

| Option | Why not |
|---|---|
| Keyword or TF-IDF overlap | Misses matches that are phrased differently, which is the case the product exists for. This reason is the one the README gives |
| A local embedding model | No per-call cost and no text leaving the machine, but a model download and slower scoring on a laptop. Not recorded as considered; `gensim` settings left in `config.py` suggest an earlier local approach |
| An LLM judging each pair | A reasoned score per posting, at a chat-model call per posting per resume. Too slow and too costly for hundreds of postings |

## Consequences

- **Cost:** one embedding call per new posting and one per scoring run for the resume.
  The README quotes about USD 0.02 per 1,000 postings; that figure is unverified.
- **Privacy:** resume text and posting text are sent to OpenAI. There is no offline mode.
- **Failure mode:** with a missing or rejected key the code returns zero vectors and every
  score is 0.0, with no error in the UI. [Runbook 05](../runbooks/05-embeddings-and-scores.md)
  covers the diagnosis.
- **Lock-in:** vectors from two models cannot be compared. Changing the model means
  re-embedding every stored posting with `make rebuild-embeddings`.
- **Meaning of the number:** cosine similarity of general-purpose embeddings is a ranking
  signal. It has not been calibrated against interview or offer outcomes, so 80% does not
  mean an 80% chance of anything.

## Revisit when

Scores stop separating good postings from poor ones for a real resume, OpenAI retires the
model, or a user needs resume text to stay on the machine.
