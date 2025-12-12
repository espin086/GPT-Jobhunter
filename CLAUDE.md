# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Commands

### Development Workflow
```bash
# Start local development (backend + frontend with auto-reload)
make dev

# Stop all services (local and Docker)
make stop

# Run tests (database, dataTransformer, and full suite if API keys present)
make test

# Run a single test file
poetry run pytest tests/test_database.py -v

# Run a specific test
poetry run pytest tests/test_database.py::test_db_file_creation -v
```

### Production Deployment
```bash
# Build and run with Docker
make prod

# Docker operations
make docker-build    # Build image only
make docker-run      # Run container only
make docker-clean    # Remove containers and images
```

### Other Common Commands
```bash
# Code formatting
make format

# Test coverage
make coverage

# Clean temporary files
make clean

# Rebuild AI embeddings (requires OpenAI API key)
make rebuild-embeddings

# Generate OpenAPI specification
make openapi
```

## Architecture Overview

### Decoupled Backend-Frontend Architecture

The application is split into two services that communicate via REST API:

1. **FastAPI Backend** (`jobhunter/backend/`)
   - Port: 8000
   - Handles business logic, database operations, AI embeddings, job search
   - API docs available at http://localhost:8000/docs

2. **Streamlit Frontend** (`jobhunter/frontend/`)
   - Port: 8501
   - User interface that consumes backend API
   - Connects to backend via BACKEND_URL environment variable

### Core Data Flow

```
1. Job Search Flow:
   extract.py → search_jobs() → RapidAPI JSearch
   → raw JSON → dataTransformer.py → processed JSON
   → load.py → SQLiteHandler.py → all_jobs.db

2. Resume Matching Flow:
   Resume upload → textAnalysis.py → OpenAI embeddings
   → Job descriptions → OpenAI embeddings
   → SQLiteHandler.py → cosine similarity calculation
   → resume_similarity scores in database
```

### Critical Components

**config.py**: Central configuration with:
- File paths (RAW_DATA_PATH, PROCESSED_DATA_PATH, RESUME_PATH)
- Database tables (jobs_new, resumes, applications)
- Job position templates
- API endpoints

**backend/services.py**: Service layer wrapping business logic:
- `JobSearchService`: Orchestrates job search (extract → transform → load)
- `ResumeService`: Resume CRUD operations and text extraction
- `JobDataService`: Job filtering and querying
- `DatabaseService`: Database initialization and stats

**textAnalysis.py**: AI/ML operations:
- `generate_gpt_embedding()`: Single text → OpenAI embedding
- `generate_gpt_embeddings_batch()`: Batch embeddings for efficiency
- Rate limiting and retry logic for OpenAI API

**SQLiteHandler.py**: Database layer:
- `create_db_if_not_there()`: Schema initialization
- `check_and_upload_to_db()`: Upsert job data
- `save_text_to_db()`: Store resume text
- `update_similarity_in_db()`: Update resume_similarity scores
- Batch operations for performance

**dataTransformer.py**: ETL transformations:
- `drop_variables()`: Remove unused API fields
- `rename_keys()`: Map API fields to database schema
- `compute_resume_similarity()`: Calculate similarity scores using embeddings

### Import Structure

All imports within the `jobhunter` package MUST use package-absolute imports:

```python
# Correct
from jobhunter import config
from jobhunter.FileHandler import FileHandler
from jobhunter.SQLiteHandler import check_and_upload_to_db

# Incorrect (will fail)
import config
from FileHandler import FileHandler
```

This is critical because the application runs as a package in both local dev and Docker.

### Database Schema

Primary table: `jobs_new`
- `embeddings`: TEXT (JSON-serialized array of floats from OpenAI)
- `resume_similarity`: REAL (cosine similarity score 0.0-1.0)
- `primary_key`: TEXT UNIQUE (company + title composite key)

The `resumes` table stores:
- `resume_name`: TEXT UNIQUE
- `resume_text`: TEXT

### Environment Variables

Required for full functionality:
- `OPENAI_API_KEY`: For embeddings and similarity scoring
- `RAPID_API_KEY`: For job search API (JSearch)
- `BACKEND_URL`: Frontend's backend connection (default: http://localhost:8000)

### Testing Strategy

Tests are organized by module:
- `test_database.py`: Database operations (no API keys needed)
- `dataTransformer_test.py`: Data transformations (no API keys needed)
- `test_embedding.py`: OpenAI embedding operations (requires OPENAI_API_KEY)
- `search_jobs_test.py`: Job search (requires RAPID_API_KEY)

The Makefile's `make test` runs core tests first, then full suite if API keys are present.

### Application Startup

On `make dev`, the backend must:
1. Initialize database tables (`@app.on_event("startup")` in api.py)
2. Create directory structure (config.py does this on import)
3. Wait for backend health before frontend queries

The health check endpoint (`/health`) verifies database connectivity before returning 200 OK.

### AI Embeddings Performance

- Batch processing: Use `generate_gpt_embeddings_batch()` for multiple texts
- Batch size: 100 texts per API call (OPENAI_EMBEDDING_BATCH_SIZE)
- Rate limiting: Built-in exponential backoff with MAX_RETRIES=5
- Similarity calculation: CPU-bound, uses concurrent.futures with MAX_SIMILARITY_WORKERS=8

### Common Pitfalls

1. **Import errors**: Always use `from jobhunter import X`, never relative imports
2. **Database initialization**: Backend must initialize tables on startup, not just when explicitly called
3. **SQL query construction**: When building dynamic WHERE clauses, use proper parameterization
4. **NoneType errors**: Check cursor.fetchone() for None before indexing
5. **Path handling**: Use pathlib.Path and config.py paths, never hardcoded strings
