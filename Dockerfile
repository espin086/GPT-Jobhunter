# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables to prevent interactive prompts during package installations
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    POETRY_VERSION=1.8.5 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false

# Add poetry to PATH
ENV PATH="$POETRY_HOME/bin:$PATH"

# Add the project root to PYTHONPATH
ENV PYTHONPATH=/app

# Install system dependencies required for Poetry and some Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl build-essential poppler-utils && \
    rm -rf /var/lib/apt/lists/*

# Install poetry
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    poetry --version

# Set the working directory in the container
WORKDIR /app

# Copy only the necessary files for installing dependencies first
# This leverages Docker build caching
COPY pyproject.toml poetry.lock* ./

# Install project dependencies (excluding development dependencies)
RUN poetry install --no-interaction --no-ansi --only main

# IMPORTANT: Environment Variables
# We do NOT copy .env files into the image for security reasons.
# Instead, pass environment variables when running the container:
# docker run -d --env-file .env [other options] gpt-jobhunter:latest
# 
# Required environment variables:
# - RAPID_API_KEY
# - OPENAI_API_KEY

# First create all necessary directories with appropriate permissions
# This ensures we can write to these directories at runtime
RUN mkdir -p /app/jobhunter/temp/data/raw /app/jobhunter/temp/data/processed && \
    chmod -R 777 /app/jobhunter/temp

# COPY only specific required directories and files, not the entire context
# This way we can be more selective about what goes into the image
COPY jobhunter/*.py /app/jobhunter/
COPY jobhunter/templates/ /app/jobhunter/templates/
COPY README.md LICENSE* ./

# Expose the port the app runs on
EXPOSE 8501

# Command to run the application
CMD ["streamlit", "run", "jobhunter/main.py", "--server.address=0.0.0.0", "--server.port=8501"]

# Example for a simple Python script:
# CMD ["python", "your_script_name.py"]

