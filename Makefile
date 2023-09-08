SRC_DIR := $(shell pwd)/jobhunter/src

setup:
	python3 -m venv jobhunter
	. jobhunter/bin/activate && pip install -r requirements.txt

test: setup
	cd $(SRC_DIR) && coverage run -m pytest
	cd $(SRC_DIR) && coverage report 
	cd $(SRC_DIR) && coverage html -d coverage_html

run: test
	streamlit run $(SRC_DIR)/main.py