
SRC_DIR:=$(shell pwd)/src

virtualenv: 
	python3 -m venv jobhunter-venv
	echo "RUN THIS!!!: source jobhunter-venv/bin/activate"

.PHONY: install test lint format

install:
	python -m pip install --upgrade pip
	pip install flake8 pytest pylint black isort
	if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

format:
	black src
	isort src/*.py

test:
	pytest src


run: 
	streamlit run $(SRC_DIR)/main.py

