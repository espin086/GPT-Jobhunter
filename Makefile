SRC_DIR := $(shell pwd)/jobhunter/src

setup:
	python3 -m venv jobhunter
	. jobhunter/bin/activate && pip install -r requirements.txt
	source jobhunter/bin/activate

test:
	cd $(SRC_DIR) && coverage run -m pytest
	cd $(SRC_DIR) && coverage report 
	cd $(SRC_DIR) && coverage html -d coverage_html