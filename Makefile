
SRC_DIR:=$(shell pwd)/jobhunter

virtualenv: 
	python3 -m venv jobhunter-venv
	echo "RUN THIS!!!: source jobhunter-venv/bin/activate"

.PHONY: install test lint format

install:
	python -m pip install --upgrade pip
	pip install flake8 pytest pylint black isort
	pip install -e .

format:
	black $(SRC_DIR)
	isort $(SRC_DIR)/*.py

test:
	cd tests && pytest .

check: install format test

run: 
	streamlit run $(SRC_DIR)/main.py

