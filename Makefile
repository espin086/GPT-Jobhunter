ROOT_DIR:=$(shell pwd)
SRC_DIR:=$(ROOT_DIR)/jobhunter

virtualenv:
	cp .env-template .env
	python3 -m venv jobhunter-venv
	echo "RUN THIS!!!: source jobhunter-venv/bin/activate"

.PHONY: install test lint format

install:
	python -m pip install --upgrade pip
	python3 -m pip install -e .

format:
	python3 -m black $(SRC_DIR)
	python3 -m isort --profile black $(SRC_DIR)

test:
	pytest $(ROOT_DIR)/tests/

coverage:
	python3 -m pytest --cov=$(SRC_DIR) --cov-report term --cov-report html

check: install format test

run:
	streamlit run $(SRC_DIR)/main.py
