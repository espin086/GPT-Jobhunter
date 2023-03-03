.PHONY: setup test format lint all

all: setup test format

setup:
	pip3 install .

test:
	pytest
	coverage run -m pytest

format:
	black .

lint:
	pylint --output-format=colorized  jobhunter/
