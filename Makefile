ROOT_DIR:=$(shell pwd)
SRC_DIR:=$(ROOT_DIR)/jobhunter

virtualenv:
	cp .env-template .env
	conda create --name jobhunter python=3.11
	conda activate jobhunter

.PHONY: install test lint format

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
