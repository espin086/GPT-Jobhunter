# GPT Job Hunter

## What this is

GPT Job Hunter helps one job seeker find postings that fit their resume. It pulls postings
from a job search API, scores each one against the resume with text embeddings, rewrites
the resume for the best matches, and tracks applications on a board. A FastAPI backend
holds all the logic and a Streamlit frontend is the only client today.

## What these specs are

The specs under `openspec/specs/` were reverse engineered from the code at commit `69d202a`
on 2026-11-27. They state what the system does today, so that a future change can say
exactly which behavior it adds, modifies or removes. They are a baseline, not a wish list.

Three consequences of that:

- **A requirement here is observed behavior.** Each one was read from the code, and the
  ones marked in the table below were also exercised against a running backend.
- **Some observed behavior is a defect.** Where the code does something the product should
  not do (scores shared between accounts, routes open without a login), the spec records
  it plainly and the defect is listed in
  [docs/architecture/c4.md](../docs/architecture/c4.md#known-gaps). Fixing one is a change
  that MODIFIES the requirement.
- **Nothing here describes the planned CLI, library, MCP server or PyPI package.** Those
  arrive as changes under `openspec/changes/`.

| Capability | Spec | Exercised on a running backend |
|---|---|---|
| Accounts and sign-in | [accounts-and-auth](specs/accounts-and-auth/spec.md) | Yes |
| Resumes | [resume-management](specs/resume-management/spec.md) | Upload as text, list |
| Job search pipeline | [job-search](specs/job-search/spec.md) | Missing-key path only |
| Match scores and job listing | [job-matching](specs/job-matching/spec.md) | Empty listing, missing-key path |
| Resume analysis and rewriting | [resume-optimization](specs/resume-optimization/spec.md) | No (needs an OpenAI key) |
| Application tracker | [job-tracking](specs/job-tracking/spec.md) | No |
| Onboarding | [onboarding](specs/onboarding/spec.md) | No (needs both keys) |
| Health, setup and deployment | [platform-operations](specs/platform-operations/spec.md) | Health, stats, startup |

## Where things live

| Thing | Path |
|---|---|
| Specs and changes | `openspec/` |
| Architecture diagrams and known gaps | `docs/architecture/c4.md` |
| Architecture decision records | `docs/decisions/` |
| Runbooks | `docs/runbooks/` |
| Backend (routes, services, models) | `jobhunter/backend/` |
| Frontend | `jobhunter/frontend/streamlit_app.py` |
| Search pipeline | `jobhunter/extract.py`, `dataTransformer.py`, `load.py`, `FileHandler.py` |
| Storage and scoring | `jobhunter/SQLiteHandler.py`, `AuthHandler.py`, `textAnalysis.py` |
| API contract | `openapi.json` |
| Tests | `tests/` |

## Rules every change is checked against

1. **One source of logic.** Business logic lives in the backend services. A new surface
   (CLI, MCP server, library call) wraps those services and does not copy them.
2. **User data is scoped to its owner.** Every read or write of a resume or a tracker row
   filters by the caller's user id.
3. **Secrets stay out of the repository, the image and the logs.**
4. **A behavior change comes with a spec delta and a test that names the scenario.**
5. **Tests that call JSearch or OpenAI are kept apart** from tests that need no key, so the
   keyless suite runs anywhere.
6. **Docs move with the code:** the C4 page, the ADRs and the runbooks are updated in the
   same pull request ([CONTRIBUTING.md](../CONTRIBUTING.md)).

## Working with changes

```bash
openspec list --specs                 # the capabilities above
openspec validate --specs --strict    # check the baseline
openspec new change <slug>            # start a change
```

A change folder holds `proposal.md`, `tasks.md` and spec deltas under `specs/`. It is
archived into `openspec/specs/` after the implementation merges.
