ROOT_DIR:=$(shell pwd)
SRC_DIR:=$(ROOT_DIR)/jobhunter

virtualenv:
	cp .env-template .env
	conda create --name jobhunter python=3.11
	conda activate jobhunter

.PHONY: install test lint format openapi openapi-validate serve-docs

install:
	conda create --name jobhunter python=3.10 && \
	eval "$(conda shell.bash hook)" && \
	conda activate jobhunter && \
	pip install -r requirements.txt

format:
	python3 -m black $(SRC_DIR)
	python3 -m isort --profile black $(SRC_DIR)

test:
	pytest $(ROOT_DIR)/tests/

coverage:
	python3 -m pytest --cov=$(SRC_DIR) --cov-report term --cov-report html

check: format test

run:
	streamlit run $(SRC_DIR)/main.py

# OpenAPI generation targets
openapi:
	@echo "🚀 Generating OpenAPI specification..."
	python3 scripts/generate_openapi.py

openapi-validate:
	@echo "✅ Validating OpenAPI specification..."
	@if [ -f openapi.json ]; then \
		python3 -c "import json; json.load(open('openapi.json'))" && \
		echo "✅ OpenAPI spec is valid JSON"; \
	else \
		echo "❌ openapi.json not found. Run 'make openapi' first."; \
		exit 1; \
	fi

serve-docs:
	@echo "📖 Starting API documentation server..."
	@if [ -f openapi.json ]; then \
		python3 -c "from jobhunter.backend.api import app; import uvicorn; uvicorn.run(app, host='127.0.0.1', port=8000)" & \
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
