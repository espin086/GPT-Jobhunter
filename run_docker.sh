#!/bin/bash

# Set error handling and enable verbose logging
set -e
echo "====== GPT-JOBHUNTER DOCKER DEPLOYMENT ======"

# Prepare environment for local tests and Docker
echo "Preparing environment for testing and Docker build..."

# Create necessary directories if they don't exist
mkdir -p jobhunter/templates jobhunter/temp/data/raw jobhunter/temp/data/processed
chmod -R 755 jobhunter/temp

# Create a basic README.md file if it doesn't exist
if [ ! -f "README.md" ]; then
    echo "# GPT-Jobhunter" > README.md
    echo "AI-assisted job hunting application" >> README.md
    echo "Created README.md file"
fi

# Run pytest to validate the codebase before building
echo "Running pytest to validate codebase..."

# Separate database tests (which don't need API keys) from API-dependent tests
echo "Running database tests first..."
if ! poetry run pytest tests/test_database.py -v; then
    echo "❌ Database tests failed! Please fix the database issues before continuing."
    exit 1
else
    echo "✅ Database tests passed successfully!"
fi

echo "Running modified dataTransformer tests..."
if ! poetry run pytest tests/dataTransformer_test.py -v; then
    echo "❌ DataTransformer tests failed! Please fix the issues before continuing."
    exit 1
else
    echo "✅ DataTransformer tests passed successfully!"
fi

# Check if API keys are available for API-dependent tests
if [ -f ".env" ] && grep -q "OPENAI_API_KEY" .env && grep -q "RAPID_API_KEY" .env; then
    echo "API keys found, running full test suite..."
    if ! poetry run pytest; then
        echo "⚠️ Some tests failed! This might be due to API limitations or other issues."
        read -p "Do you want to continue with the Docker build anyway? (y/n): " choice
        if [[ ! "$choice" =~ ^[Yy]$ ]]; then
            echo "Deployment aborted by user."
            exit 1
        fi
    else
        echo "✅ All tests passed successfully!"
    fi
else
    echo "⚠️ API keys not found in .env file. Skipping API-dependent tests."
    echo "You will need API keys for the application to function correctly."
fi

# Remove existing container if it exists
echo "Removing existing container (if it exists)..."
docker rm -f gpt-jobhunter >/dev/null 2>&1 || true

# Remove existing image if it exists
echo "Removing existing image (if it exists)..."
docker rmi gpt-jobhunter:latest >/dev/null 2>&1 || true

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ ERROR: .env file not found. Please create one with your API keys before continuing."
    echo "Example .env file contents:"
    echo "RAPID_API_KEY=your_rapid_api_key"
    echo "OPENAI_API_KEY=your_openai_api_key"
    exit 1
fi

# Check the size of the Docker build context (this shows what will be sent to Docker)
echo "Checking size of Docker build context (should be small if .dockerignore is working)..."
# Use tar to simulate what Docker will send in the build context, but only count the size
tar -czh --exclude-vcs --exclude=.git --exclude-from=.dockerignore . | wc -c | awk '{printf "Build context size: %.2f MB\n", $1/(1024*1024)}'

# Build the Docker image with build cache optimizations
echo "Building new image with optimizations..."
if ! docker build --no-cache=false --build-arg BUILDKIT_INLINE_CACHE=1 -t gpt-jobhunter:latest .; then
    echo "❌ Docker build failed! Check the errors above."
    exit 1
else
    echo "✅ Docker image built successfully!"
fi

# Verify that .env file is not in the image (security check)
echo "Verifying .env file is not in the image (security check)..."
if docker run --rm gpt-jobhunter:latest ls -la /app | grep -q ".env"; then
    echo "⚠️ WARNING: .env file was found in the image! This is a security risk."
    echo "Check your .dockerignore file and ensure it includes .env"
    echo "You may want to rebuild the image after fixing this issue."
    read -p "Do you want to continue anyway? (y/n): " choice
    if [[ ! "$choice" =~ ^[Yy]$ ]]; then
        echo "Deployment aborted by user."
        exit 1
    fi
else
    echo "✅ Security check passed: .env file is properly excluded from the image."
fi

# Verify that temp JSON files are not in the image
echo "Checking if temp directory JSON files were excluded from the image..."
if docker run --rm gpt-jobhunter:latest bash -c 'find /app -path "*/temp/*" -name "*.json" | wc -l' | grep -q "^0$"; then
    echo "✅ No JSON files found in temp directories - .dockerignore is working!"
else
    echo "⚠️ Warning: JSON files found in temp directories in the image. .dockerignore may not be working correctly."
    # List found files for debugging
    docker run --rm gpt-jobhunter:latest bash -c 'find /app -path "*/temp/*" -name "*.json" | head -n 5'
fi

# Verify environment variables can be read from .env file
echo "Checking if environment variables from .env file are valid..."
RAPID_API_KEY=$(grep -E "^RAPID_API_KEY=" .env | cut -d= -f2)
OPENAI_API_KEY=$(grep -E "^OPENAI_API_KEY=" .env | cut -d= -f2)

if [ -z "$RAPID_API_KEY" ]; then
    echo "❌ RAPID_API_KEY not found or empty in .env file"
    exit 1
else
    echo "✅ RAPID_API_KEY found in .env file"
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ OPENAI_API_KEY not found or empty in .env file"
    exit 1
else 
    echo "✅ OPENAI_API_KEY found in .env file"
fi

# Verify environment variables pass correctly to container
echo "Checking if environment variables pass correctly to container..."
echo "RAPID_API_KEY availability test:"
docker run --rm --env-file .env gpt-jobhunter:latest bash -c 'if [ -n "$RAPID_API_KEY" ]; then echo "✅ RAPID_API_KEY is available"; else echo "❌ RAPID_API_KEY is missing"; fi'
echo "OPENAI_API_KEY availability test:"
docker run --rm --env-file .env gpt-jobhunter:latest bash -c 'if [ -n "$OPENAI_API_KEY" ]; then echo "✅ OPENAI_API_KEY is available"; else echo "❌ OPENAI_API_KEY is missing"; fi'

# Perform a direct Python environment check of the API keys
echo "Performing Python environment check of API keys:"
docker run --rm --env-file .env gpt-jobhunter:latest python -c "
import os
print('RAPID_API_KEY from Python:', 'Available' if os.environ.get('RAPID_API_KEY') else 'Missing')
print('OPENAI_API_KEY from Python:', 'Available' if os.environ.get('OPENAI_API_KEY') else 'Missing')
"

# Run the database tests inside the container to ensure the database setup works
echo "Running database tests inside the container..."
if ! docker run --rm --env-file .env gpt-jobhunter:latest python -m pytest /app/tests/test_database.py -v; then
    echo "❌ Database tests failed inside the container! The image may have issues."
    read -p "Tests failed inside the container. Do you want to continue anyway? (y/n): " choice
    if [[ ! "$choice" =~ ^[Yy]$ ]]; then
        echo "Deployment aborted by user."
        exit 1
    fi
    echo "Continuing despite test failures..."
else
    echo "✅ Database tests inside the container passed!"
fi

# Run the container with enhanced options
echo "Starting container..."
docker run -d \
  --name gpt-jobhunter \
  --env-file .env \
  -p 8501:8501 \
  --restart unless-stopped \
  gpt-jobhunter:latest

# OPTIONAL: If you want to persist the database between container restarts, 
# comment out the command above and uncomment the command below.
# This will create a docker volume that persists your data, but starts fresh initially.
# docker run -d --name gpt-jobhunter --env-file .env -p 8501:8501 -v gpt-jobhunter-data:/app/jobhunter/temp gpt-jobhunter:latest

echo "✅ Container started! Access Streamlit at http://localhost:8501"
echo "View logs with: docker logs -f gpt-jobhunter" 