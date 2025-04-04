# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables to prevent interactive prompts during package installations
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    POETRY_VERSION=1.8.3 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false

# Add poetry to PATH
ENV PATH="$POETRY_HOME/bin:$PATH"

# Add the project root to PYTHONPATH
ENV PYTHONPATH=/app

# Install system dependencies required for Poetry and some Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Install poetry
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    poetry --version

# Set the working directory in the container
WORKDIR /app

# Copy only the necessary files for installing dependencies first
# This leverages Docker build caching
COPY pyproject.toml ./
COPY poetry.lock* ./

# Install project dependencies (excluding development dependencies)
RUN poetry install --no-interaction --no-ansi --only main

# Copy the rest of the application code into the container
# Ensure you have a .dockerignore file to exclude unnecessary files (like .git, .venv, __pycache__)
COPY . .

# Expose the port the app runs on (adjust if your app uses a different port, e.g., 8000 for FastAPI)
EXPOSE 8501

# Command to run the application
CMD ["streamlit", "run", "jobhunter/main.py", "--server.address=0.0.0.0", "--server.port=8501"]

# Example for a simple Python script:
# CMD ["python", "your_script_name.py"]

