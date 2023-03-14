.PHONY: setup test format lint all

all: setup test format lint

setup:
	pip3 install --editable .
	/usr/bin/python3 /Users/jjespinoza/Documents/jobhunter/jobhunter/etl/pipeline.py

test:
	pytest
	coverage run -m pytest

format:
	black .

lint:
	pylint --output-format=colorized  jobhunter/
