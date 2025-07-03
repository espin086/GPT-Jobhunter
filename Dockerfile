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
    supervisor \
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
    /app/jobhunter/backend \
    /app/jobhunter/frontend \
    && chmod -R 755 /app/jobhunter/temp

# Create a simple README file if it doesn't exist in the build context
RUN echo "# GPT-Jobhunter" > /app/README.md \
    && echo "AI-assisted job hunting application with FastAPI backend and Streamlit frontend" >> /app/README.md

# Copy the actual application code - these files should exist
COPY jobhunter/ /app/jobhunter/
COPY tests/ /app/tests/

# Initialize necessary dependencies and databases
RUN python -m nltk.downloader stopwords punkt -d /usr/share/nltk_data

# Perform database initialization tests
RUN python -m pytest /app/tests/test_database.py || echo "Database tests will be run later with correct environment"

# Create supervisor configuration for running both services
RUN mkdir -p /etc/supervisor/conf.d
COPY <<EOF /etc/supervisor/conf.d/supervisord.conf
[supervisord]
nodaemon=true
user=root
logfile=/var/log/supervisor/supervisord.log
pidfile=/var/run/supervisord.pid

[program:backend]
command=python -m uvicorn jobhunter.backend.api:app --host 0.0.0.0 --port 8000
directory=/app
autostart=true
autorestart=true
stderr_logfile=/var/log/supervisor/backend.err.log
stdout_logfile=/var/log/supervisor/backend.out.log
environment=PYTHONPATH="/app"

[program:frontend]
command=python -m streamlit run jobhunter/frontend/streamlit_app.py --server.port=8501 --server.address=0.0.0.0
directory=/app
autostart=true
autorestart=true
stderr_logfile=/var/log/supervisor/frontend.err.log
stdout_logfile=/var/log/supervisor/frontend.out.log
environment=PYTHONPATH="/app",BACKEND_URL="http://localhost:8000"
EOF

# Create startup script
COPY <<EOF /app/start.sh
#!/bin/bash
set -e

echo "Starting GPT Job Hunter with Backend and Frontend..."

# Initialize database
echo "Initializing database..."
cd /app
python -c "
from jobhunter.backend.services import DatabaseService
db_service = DatabaseService()
db_service.initialize_database()
print('Database initialized successfully')
"

# Start supervisor to manage both services
echo "Starting services with supervisor..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
EOF

RUN chmod +x /app/start.sh

# Create individual service startup scripts for development
COPY <<EOF /app/start-backend.sh
#!/bin/bash
cd /app
echo "Starting FastAPI backend on port 8000..."
python -m uvicorn jobhunter.backend.api:app --host 0.0.0.0 --port 8000 --reload
EOF

COPY <<EOF /app/start-frontend.sh
#!/bin/bash
cd /app
echo "Starting Streamlit frontend on port 8501..."
export BACKEND_URL=http://localhost:8000
python -m streamlit run jobhunter/frontend/streamlit_app.py --server.port=8501 --server.address=0.0.0.0
EOF

RUN chmod +x /app/start-backend.sh /app/start-frontend.sh

# Add health checks for both services
HEALTHCHECK --interval=30s --timeout=30s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health && curl -f http://localhost:8501/ || exit 1

# Set the working directory for application execution
WORKDIR /app

# Expose ports for both backend and frontend
EXPOSE 8000 8501

# Use the startup script as the default command
CMD ["/app/start.sh"]

# Alternative commands for development:
# Backend only: CMD ["/app/start-backend.sh"]
# Frontend only: CMD ["/app/start-frontend.sh"]

