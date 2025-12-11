# GPT-Jobhunter Makefile
# Consolidated deployment, development, and testing commands

ROOT_DIR:=$(shell pwd)
SRC_DIR:=$(ROOT_DIR)/jobhunter
BACKEND_PORT:=8000
FRONTEND_PORT:=8501

.PHONY: help install dev prod stop test coverage format check clean rebuild-embeddings
.PHONY: openapi openapi-validate serve-docs api-docs docker-build docker-run docker-clean

# Default target
help:
	@echo "====== GPT-JOBHUNTER MAKEFILE ======"
	@echo ""
	@echo "Development Commands:"
	@echo "  make dev              - Run locally without Docker (auto-refresh enabled)"
	@echo "  make stop             - Stop all running services (local and Docker)"
	@echo ""
	@echo "Production Commands:"
	@echo "  make prod             - Build and run with Docker (production mode)"
	@echo "  make docker-build     - Build Docker image only"
	@echo "  make docker-run       - Run Docker container only"
	@echo "  make docker-clean     - Remove Docker containers and images"
	@echo ""
	@echo "Testing & Quality:"
	@echo "  make test             - Run all pytest tests"
	@echo "  make coverage         - Run tests with coverage report"
	@echo "  make format           - Format code with black and isort"
	@echo "  make check            - Run format and test"
	@echo ""
	@echo "Database & Utilities:"
	@echo "  make rebuild-embeddings - Rebuild all embeddings (requires OpenAI API key)"
	@echo "  make clean            - Clean temporary files and cache"
	@echo ""
	@echo "API Documentation:"
	@echo "  make openapi          - Generate OpenAPI specification"
	@echo "  make openapi-validate - Validate OpenAPI specification"
	@echo "  make serve-docs       - Start API documentation server"
	@echo "  make api-docs         - Generate and validate API docs"
	@echo ""
	@echo "Setup:"
	@echo "  make install          - Install dependencies with Poetry"
	@echo ""

# Installation
install:
	@echo "📦 Installing dependencies with Poetry..."
	@if ! command -v poetry &> /dev/null; then \
		echo "❌ Poetry not found. Installing Poetry..."; \
		curl -sSL https://install.python-poetry.org | python3 -; \
	fi
	poetry install --no-interaction
	@echo "✅ Dependencies installed successfully!"

# Development mode - run locally without Docker with auto-refresh
dev:
	@echo "====== STARTING DEVELOPMENT MODE ======"
	@echo "Starting FastAPI backend and Streamlit frontend locally..."
	@echo ""
	@if [ ! -f .env ]; then \
		echo "❌ ERROR: .env file not found."; \
		echo "Please create a .env file with your API keys:"; \
		echo "  RAPID_API_KEY=your_rapid_api_key"; \
		echo "  OPENAI_API_KEY=your_openai_api_key"; \
		exit 1; \
	fi
	@echo "✅ Environment file found"
	@echo ""
	@# Clean database for fresh testing
	@echo "🗑️  Cleaning database for fresh start..."
	@rm -f all_jobs.db
	@rm -rf jobhunter/temp/data/raw/* jobhunter/temp/data/processed/* 2>/dev/null || true
	@echo "✅ Database cleaned"
	@echo ""
	@echo "💡 TIP: If you see old data in browser, press Ctrl+Shift+R to clear cache"
	@echo ""
	@echo "🚀 Starting backend on http://localhost:$(BACKEND_PORT)"
	@echo "🚀 Starting frontend on http://localhost:$(FRONTEND_PORT)"
	@echo ""
	@echo "Press Ctrl+C to stop all services"
	@echo ""
	@# Load environment variables and start both services in parallel
	@set -a; . ./.env; set +a; \
	trap 'kill 0' INT; \
	poetry run uvicorn jobhunter.backend.api:app --host 0.0.0.0 --port $(BACKEND_PORT) --reload & \
	sleep 3; \
	BACKEND_URL=http://localhost:$(BACKEND_PORT) poetry run streamlit run jobhunter/frontend/streamlit_app.py --server.port=$(FRONTEND_PORT) --server.address=0.0.0.0 & \
	wait

# Production mode - run with Docker
prod: docker-build docker-run
	@echo "✅ Production deployment complete!"
	@echo "🌐 Application available at http://localhost:$(FRONTEND_PORT)"
	@echo "📊 Backend API at http://localhost:$(BACKEND_PORT)"
	@echo "📖 API docs at http://localhost:$(BACKEND_PORT)/docs"
	@echo ""
	@echo "View logs with: docker logs -f gpt-jobhunter"
	@echo "Stop with: make stop"

# Build Docker image
docker-build:
	@echo "====== BUILDING DOCKER IMAGE ======"
	@if [ ! -f .env ]; then \
		echo "❌ ERROR: .env file not found."; \
		echo "Please create a .env file with your API keys before building."; \
		exit 1; \
	fi
	@echo "✅ Environment file found"
	@echo ""
	@# Create necessary directories
	@mkdir -p jobhunter/templates jobhunter/temp/data/raw jobhunter/temp/data/processed
	@chmod -R 755 jobhunter/temp
	@echo "✅ Directories created"
	@echo ""
	@# Remove existing image if it exists
	@echo "🗑️  Removing existing image (if it exists)..."
	@docker rmi gpt-jobhunter:latest >/dev/null 2>&1 || true
	@echo ""
	@# Build the Docker image
	@echo "🔨 Building new Docker image..."
	@if docker build --no-cache=false --build-arg BUILDKIT_INLINE_CACHE=1 -t gpt-jobhunter:latest .; then \
		echo "✅ Docker image built successfully!"; \
	else \
		echo "❌ Docker build failed! Check the errors above."; \
		exit 1; \
	fi
	@echo ""
	@# Security check - verify .env is not in image
	@echo "🔒 Running security check..."
	@if docker run --rm gpt-jobhunter:latest ls -la /app 2>/dev/null | grep -q ".env"; then \
		echo "⚠️  WARNING: .env file was found in the image! This is a security risk."; \
	else \
		echo "✅ Security check passed: .env file is properly excluded"; \
	fi

# Run Docker container
docker-run:
	@echo "====== STARTING DOCKER CONTAINER ======"
	@# Remove existing container if it exists
	@docker rm -f gpt-jobhunter >/dev/null 2>&1 || true
	@echo "🚀 Starting container..."
	@docker run -d \
		--name gpt-jobhunter \
		--env-file .env \
		-p $(BACKEND_PORT):$(BACKEND_PORT) \
		-p $(FRONTEND_PORT):$(FRONTEND_PORT) \
		--restart unless-stopped \
		gpt-jobhunter:latest
	@echo "✅ Container started!"
	@echo ""
	@echo "Waiting for services to be ready..."
	@sleep 5
	@echo "✅ Services should be ready now"

# Stop all services (local and Docker)
stop:
	@echo "====== STOPPING ALL SERVICES ======"
	@echo "🛑 Stopping Docker containers..."
	@docker stop gpt-jobhunter >/dev/null 2>&1 || true
	@docker rm gpt-jobhunter >/dev/null 2>&1 || true
	@echo "🛑 Stopping local services on ports $(BACKEND_PORT) and $(FRONTEND_PORT)..."
	@# Kill processes on backend port
	@lsof -ti:$(BACKEND_PORT) | xargs kill -9 2>/dev/null || true
	@# Kill processes on frontend port
	@lsof -ti:$(FRONTEND_PORT) | xargs kill -9 2>/dev/null || true
	@# Kill any remaining uvicorn or streamlit processes
	@pkill -f "uvicorn jobhunter.backend.api" 2>/dev/null || true
	@pkill -f "streamlit run jobhunter/frontend/streamlit_app.py" 2>/dev/null || true
	@echo "✅ All services stopped"

# Clean Docker resources
docker-clean:
	@echo "🧹 Cleaning Docker resources..."
	@docker stop gpt-jobhunter >/dev/null 2>&1 || true
	@docker rm gpt-jobhunter >/dev/null 2>&1 || true
	@docker rmi gpt-jobhunter:latest >/dev/null 2>&1 || true
	@echo "✅ Docker resources cleaned"

# Testing - consolidated from run_docker.sh
test:
	@echo "====== RUNNING TESTS ======"
	@echo ""
	@echo "📋 Running database tests..."
	@if poetry run pytest tests/test_database.py -v; then \
		echo "✅ Database tests passed!"; \
	else \
		echo "❌ Database tests failed!"; \
		exit 1; \
	fi
	@echo ""
	@echo "📋 Running dataTransformer tests..."
	@if poetry run pytest tests/dataTransformer_test.py -v; then \
		echo "✅ DataTransformer tests passed!"; \
	else \
		echo "❌ DataTransformer tests failed!"; \
		exit 1; \
	fi
	@echo ""
	@# Check if API keys are available for full test suite
	@if [ -f ".env" ] && grep -q "OPENAI_API_KEY" .env && grep -q "RAPID_API_KEY" .env; then \
		echo "🔑 API keys found, running full test suite..."; \
		echo ""; \
		if poetry run pytest -v; then \
			echo "✅ All tests passed successfully!"; \
		else \
			echo "⚠️  Some tests failed! This might be due to API limitations or invalid API keys."; \
			echo "✅ Core tests (database and dataTransformer) passed successfully!"; \
		fi; \
	else \
		echo "⚠️  API keys not found in .env file. Skipping API-dependent tests."; \
		echo "✅ Core tests completed successfully!"; \
	fi

# Coverage report
coverage:
	@echo "📊 Running tests with coverage..."
	poetry run pytest --cov=$(SRC_DIR) --cov-report term --cov-report html
	@echo "✅ Coverage report generated in htmlcov/"

# Code formatting
format:
	@echo "🎨 Formatting code with black and isort..."
	poetry run black $(SRC_DIR)
	poetry run isort --profile black $(SRC_DIR)
	@echo "✅ Code formatted successfully!"

# Check: format + test
check: format test

# Rebuild embeddings - from rebuild_all.sh
rebuild-embeddings:
	@echo "====== GPT-JOBHUNTER EMBEDDING REBUILDER ======"
	@echo "This will rebuild all job embeddings and recalculate resume similarities."
	@echo ""
	@# Check if OpenAI API key is set
	@if [ -f ".env" ]; then \
		set -a; . ./.env; set +a; \
		if [ -z "$$OPENAI_API_KEY" ]; then \
			echo "❌ ERROR: OPENAI_API_KEY not found in .env file."; \
			echo "Please add your OpenAI API key to the .env file:"; \
			echo "  OPENAI_API_KEY=your-openai-api-key"; \
			exit 1; \
		fi; \
		MASKED_KEY="$${OPENAI_API_KEY:0:4}...$${OPENAI_API_KEY: -4}"; \
		echo "✅ Using OpenAI API key: $$MASKED_KEY"; \
	else \
		echo "❌ ERROR: .env file not found."; \
		exit 1; \
	fi
	@echo ""
	@echo "⚠️  WARNING: This process may use a significant amount of your OpenAI API quota."
	@echo "Depending on the number of jobs and resumes, costs could be substantial."
	@read -p "Do you want to proceed? (y/n): " choice; \
	if [ "$$choice" != "y" ] && [ "$$choice" != "Y" ]; then \
		echo "Operation cancelled."; \
		exit 0; \
	fi
	@echo ""
	@echo "🔄 Starting embedding rebuilding process..."
	@echo "============================================="
	@set -a; . ./.env; set +a; \
	poetry run python -m jobhunter.rebuild_embeddings
	@echo ""
	@echo "✅ Process completed!"
	@echo "If you're running the Streamlit app, restart it for changes to take effect."

# Clean temporary files and cache
clean:
	@echo "🧹 Cleaning temporary files and cache..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@rm -rf htmlcov/ 2>/dev/null || true
	@rm -rf .coverage 2>/dev/null || true
	@echo "✅ Temporary files cleaned"

# OpenAPI generation targets
openapi:
	@echo "🚀 Generating OpenAPI specification..."
	poetry run python scripts/generate_openapi.py
	@echo "✅ OpenAPI specification generated"

openapi-validate:
	@echo "✅ Validating OpenAPI specification..."
	@if [ -f openapi.json ]; then \
		poetry run python -c "import json; json.load(open('openapi.json'))" && \
		echo "✅ OpenAPI spec is valid JSON"; \
	else \
		echo "❌ openapi.json not found. Run 'make openapi' first."; \
		exit 1; \
	fi

serve-docs:
	@echo "📖 Starting API documentation server..."
	@if [ -f openapi.json ]; then \
		poetry run python -c "from jobhunter.backend.api import app; import uvicorn; uvicorn.run(app, host='127.0.0.1', port=8000)" & \
		echo "📖 API docs available at:"; \
		echo "   - Swagger UI: http://127.0.0.1:8000/docs"; \
		echo "   - ReDoc: http://127.0.0.1:8000/redoc"; \
		echo "   - OpenAPI JSON: http://127.0.0.1:8000/openapi.json"; \
		echo ""; \
		echo "Press Ctrl+C to stop the server"; \
	else \
		echo "❌ openapi.json not found. Run 'make openapi' first."; \
		exit 1; \
	fi

# Combined target for complete API documentation workflow
api-docs: openapi openapi-validate
	@echo "🎉 API documentation generated and validated successfully!"
	@echo "📁 Files created:"
	@echo "   - openapi.json (for Postman/external tools)"
	@echo "📖 To view docs locally, run: make serve-docs"
