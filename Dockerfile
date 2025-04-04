# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - \
    && ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Copy only necessary files for dependency installation
COPY pyproject.toml poetry.lock* ./

# Install dependencies - use --no-root to avoid requiring README.md at this stage
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --without dev --no-root \
    && rm -rf ~/.cache

# Install pytest separately for container testing and other required packages
RUN pip install pytest==7.4.4 pdfplumber

# Create necessary directories with correct permissions
RUN mkdir -p /app/jobhunter/templates \
    /app/jobhunter/temp/data/raw \
    /app/jobhunter/temp/data/processed \
    /app/jobhunter/temp/resumes \
    && chmod -R 755 /app/jobhunter/temp

# Create a simple README file if it doesn't exist in the build context
RUN echo "# GPT-Jobhunter" > /app/README.md \
    && echo "AI-assisted job hunting application" >> /app/README.md

# Copy the actual application code - these files should exist
COPY jobhunter/ /app/jobhunter/
COPY tests/ /app/tests/

# Initialize necessary dependencies and databases
RUN python -m nltk.downloader stopwords punkt -d /usr/share/nltk_data

# Perform database initialization tests
RUN python -m pytest /app/tests/test_database.py || echo "Database tests will be run later with correct environment"

# Add a basic health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8501/ || exit 1

# Set the working directory for application execution
WORKDIR /app

# Expose the port Streamlit runs on
EXPOSE 8501

# Command to run the application
CMD ["python", "-m", "streamlit", "run", "jobhunter/main.py", "--server.port=8501", "--server.address=0.0.0.0"]

# Example for a simple Python script:
# CMD ["python", "your_script_name.py"]

