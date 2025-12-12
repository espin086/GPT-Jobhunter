# 📦 GPT Job Hunter - Installation Guide

Complete installation and setup instructions for GPT Job Hunter.

---

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start (Recommended)](#quick-start-recommended)
- [Installation Methods](#installation-methods)
  - [Method 1: Using Make (Easiest)](#method-1-using-make-easiest)
  - [Method 2: Docker Compose](#method-2-docker-compose)
  - [Method 3: Manual Setup](#method-3-manual-setup)
- [Configuration](#configuration)
- [API Keys Setup](#api-keys-setup)
- [Verification](#verification)
- [Development Setup](#development-setup)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

- **Operating System**: macOS, Linux, or Windows (with WSL2)
- **Python**: 3.11 or 3.12
- **Memory**: Minimum 4GB RAM (8GB recommended)
- **Disk Space**: At least 2GB free space

### Required Software

**Option 1: Using Make (Recommended)**
- Python 3.11+
- Poetry (Python package manager)
- Make

**Option 2: Using Docker**
- Docker Desktop (includes Docker Compose)
- No Python installation needed

**Option 3: Manual Setup**
- Python 3.11+
- pip or Poetry

---

## Quick Start (Recommended)

### 1. Clone the Repository

```bash
git clone https://github.com/espin086/GPT-Jobhunter.git
cd GPT-Jobhunter
```

### 2. Set Up API Keys

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your API keys
nano .env  # or use your preferred editor
```

Add these keys to `.env`:
```bash
OPENAI_API_KEY=sk-your-openai-key-here
RAPID_API_KEY=your-rapidapi-key-here
```

**Where to get API keys:**
- OpenAI: https://platform.openai.com/api-keys
- RapidAPI (JSearch): https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch

### 3. Install Dependencies

```bash
# Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
poetry install
```

### 4. Start the Application

```bash
make dev
```

This single command:
- ✅ Starts the FastAPI backend (port 8000)
- ✅ Starts the Streamlit frontend (port 8501)
- ✅ Initializes the database
- ✅ Enables auto-reload for development

### 5. Access the Application

- **Frontend (Streamlit)**: http://localhost:8501
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **API ReDoc**: http://localhost:8000/redoc

---

## Installation Methods

### Method 1: Using Make (Easiest)

The Makefile provides convenient commands for all common tasks.

#### Available Commands

```bash
# Development (local, auto-reload)
make dev              # Start both backend and frontend

# Production (Docker)
make prod             # Build and run with Docker

# Testing
make test             # Run the test suite
make coverage         # Run tests with coverage report

# Docker Management
make docker-build     # Build Docker image only
make docker-run       # Run Docker container only
make docker-clean     # Remove Docker containers and images

# Maintenance
make stop             # Stop all services (local and Docker)
make clean            # Clean temporary files and cache
make format           # Format code with Black
make rebuild-embeddings  # Rebuild AI embeddings (requires OpenAI key)

# Documentation
make help             # Show all available commands
```

#### Development Workflow

```bash
# Start developing
make dev

# In another terminal, run tests
make test

# When done
make stop
```

---

### Method 2: Docker Compose

Best for production deployment or if you don't want to install Python locally.

#### Setup

```bash
# 1. Clone repository
git clone https://github.com/espin086/GPT-Jobhunter.git
cd GPT-Jobhunter

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 3. Build and start
docker-compose up -d

# 4. View logs
docker-compose logs -f

# 5. Stop services
docker-compose down
```

#### Docker Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f backend    # Backend logs
docker-compose logs -f frontend   # Frontend logs

# Restart services
docker-compose restart

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build

# Clean everything (including volumes)
docker-compose down -v
```

---

### Method 3: Manual Setup

For advanced users who want full control.

#### Step 1: Install Python Dependencies

**Using Poetry (Recommended):**

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

**Using pip:**

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt  # If you have requirements.txt
# or
pip install fastapi uvicorn streamlit pandas openai python-dotenv pydantic
```

#### Step 2: Set Up Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your API keys
nano .env
```

#### Step 3: Initialize Database

```bash
poetry run python -c "from jobhunter.backend.services import DatabaseService; DatabaseService().initialize_database()"
```

#### Step 4: Start Backend

```bash
# Terminal 1: Start FastAPI backend
poetry run uvicorn jobhunter.backend.api:app --host 0.0.0.0 --port 8000 --reload
```

#### Step 5: Start Frontend

```bash
# Terminal 2: Start Streamlit frontend
export BACKEND_URL=http://localhost:8000  # On Windows: set BACKEND_URL=http://localhost:8000
poetry run streamlit run jobhunter/frontend/streamlit_app.py --server.port 8501
```

---

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Required API Keys
OPENAI_API_KEY=sk-your-openai-api-key
RAPID_API_KEY=your-rapidapi-key

# Optional Configuration
BACKEND_URL=http://localhost:8000  # Frontend's backend URL
DATABASE=all_jobs.db                # Database file name
```

### Database Configuration

The application uses SQLite by default. The database file is created automatically in the project root as `all_jobs.db`.

**Custom database location:**
```python
# Edit jobhunter/config.py
DATABASE = "/path/to/your/custom.db"
```

### Port Configuration

**Change default ports:**

Backend (FastAPI):
```bash
# Start on different port
poetry run uvicorn jobhunter.backend.api:app --port 8080
```

Frontend (Streamlit):
```bash
# Start on different port
poetry run streamlit run jobhunter/frontend/streamlit_app.py --server.port 8502
```

---

## API Keys Setup

### OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Sign in or create an account
3. Click "Create new secret key"
4. Name it (e.g., "GPT-Job-Hunter")
5. Copy the key (starts with `sk-`)
6. Add to `.env` file

**Pricing:**
- Text embeddings: ~$0.02 per 1,000 jobs
- GPT-4 for suggestions: ~$0.01-0.03 per request

### RapidAPI Key (JSearch)

1. Go to https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
2. Sign up for a free account
3. Subscribe to the free plan (1,000 requests/month)
4. Copy your API key
5. Add to `.env` file

**Free tier:**
- 1,000 searches per month
- Perfect for personal use

---

## Verification

### Test Backend

```bash
# Check health endpoint
curl http://localhost:8000/health

# Expected output:
# {"status":"healthy","database":"connected"}
```

### Test Frontend

1. Open http://localhost:8501
2. You should see the GPT Job Hunter interface
3. Try uploading a resume
4. Click "SmartSearch AI ✨"

### Run Test Suite

```bash
# Run all tests
make test

# Run with coverage
make coverage

# Run specific test file
poetry run pytest tests/test_database.py -v

# Run specific test
poetry run pytest tests/test_database.py::test_db_file_creation -v
```

---

## Development Setup

### Project Structure

```
GPT-Jobhunter/
├── jobhunter/              # Main application package
│   ├── backend/            # FastAPI backend
│   │   ├── api.py          # API endpoints
│   │   ├── models.py       # Pydantic models
│   │   └── services.py     # Business logic
│   ├── frontend/           # Streamlit frontend
│   │   └── streamlit_app.py
│   ├── config.py           # Configuration
│   ├── extract.py          # Job extraction
│   ├── dataTransformer.py  # Data transformation
│   ├── SQLiteHandler.py    # Database operations
│   ├── textAnalysis.py     # AI/ML operations
│   └── ...
├── tests/                  # Test suite
├── images/                 # Screenshots
├── Makefile               # Development commands
├── docker-compose.yml     # Docker configuration
├── pyproject.toml         # Poetry dependencies
├── README.md              # Product documentation
├── INSTALLATION.md        # This file
└── CLAUDE.md             # Architecture guide
```

### Development Workflow

```bash
# 1. Create a new branch
git checkout -b feature/my-new-feature

# 2. Start development server
make dev

# 3. Make changes (auto-reload enabled)

# 4. Run tests
make test

# 5. Format code
make format

# 6. Commit and push
git add .
git commit -m "Add new feature"
git push origin feature/my-new-feature
```

### Code Style

The project uses:
- **Black** for Python formatting
- **Pydantic** for data validation
- **Type hints** throughout

Format code:
```bash
make format
```

### Running Services Separately

**Backend only:**
```bash
poetry run uvicorn jobhunter.backend.api:app --reload
```

**Frontend only:**
```bash
export BACKEND_URL=http://localhost:8000
poetry run streamlit run jobhunter/frontend/streamlit_app.py
```

---

## Troubleshooting

### Common Issues

#### 1. Port Already in Use

```bash
# Error: Address already in use
# Solution: Kill process using the port

# Find process
lsof -i :8000  # or :8501

# Kill it
kill -9 <PID>

# Or use make command
make stop
```

#### 2. API Key Errors

```bash
# Error: 401 Unauthorized / Invalid API key

# Check your .env file
cat .env | grep API_KEY

# Verify keys are valid (no extra spaces, quotes, etc.)
# OpenAI keys start with: sk-
# RapidAPI keys are alphanumeric
```

#### 3. Module Not Found

```bash
# Error: ModuleNotFoundError

# Solution: Reinstall dependencies
poetry install

# Or update specific package
poetry update <package-name>
```

#### 4. Database Errors

```bash
# Error: Database locked / table doesn't exist

# Solution: Reinitialize database
rm all_jobs.db
poetry run python -c "from jobhunter.backend.services import DatabaseService; DatabaseService().initialize_database()"
```

#### 5. Docker Issues

```bash
# Container won't start
docker-compose logs backend  # Check logs

# Permission issues
sudo chown -R $USER:$USER .

# Clean restart
docker-compose down -v
docker-compose up -d --build
```

#### 6. Frontend Can't Connect to Backend

```bash
# Error: Connection refused / 500 errors

# 1. Check backend is running
curl http://localhost:8000/health

# 2. Check BACKEND_URL environment variable
echo $BACKEND_URL

# 3. Restart both services
make stop
make dev
```

### Reset Everything

If all else fails, start fresh:

```bash
# 1. Stop all services
make stop
pkill -f uvicorn
pkill -f streamlit

# 2. Clean everything
make clean
rm -rf __pycache__ .pytest_cache .mypy_cache
rm all_jobs.db

# 3. Reinstall
poetry install

# 4. Start fresh
make dev
```

---

## Performance Optimization

### For Large Job Databases

```python
# Increase batch sizes in config.py
OPENAI_EMBEDDING_BATCH_SIZE = 200  # Default: 100
MAX_SIMILARITY_WORKERS = 16        # Default: 8
```

### For Slow API Responses

```bash
# Use more workers
poetry run uvicorn jobhunter.backend.api:app --workers 4
```

---

## Migration from Previous Versions

### From Monolithic Streamlit Version

```bash
# 1. Backup your database
cp all_jobs.db all_jobs.db.backup

# 2. Update dependencies
poetry install

# 3. Initialize new backend
poetry run python -c "from jobhunter.backend.services import DatabaseService; DatabaseService().initialize_database()"

# 4. Start new version
make dev
```

---

## Additional Resources

- **API Documentation**: http://localhost:8000/docs (when running)
- **Architecture Guide**: See [CLAUDE.md](CLAUDE.md)
- **GitHub Issues**: https://github.com/espin086/GPT-Jobhunter/issues
- **Discussions**: https://github.com/espin086/GPT-Jobhunter/discussions

---

## Getting Help

If you're stuck:

1. Check this installation guide
2. Check [Common Issues](#common-issues) above
3. Search [GitHub Issues](https://github.com/espin086/GPT-Jobhunter/issues)
4. Ask in [GitHub Discussions](https://github.com/espin086/GPT-Jobhunter/discussions)
5. Create a new issue with:
   - Your OS and Python version
   - Steps to reproduce the problem
   - Error messages (full output)
   - What you've already tried

---

<div align="center">

**Ready to find your dream job? [Go back to README](README.md)**

</div>
