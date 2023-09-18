SRC_DIR := $(shell pwd)/jobhunter/src


virtualenv: 
	python3 -m venv jobhunter-venv
	echo "RUN THIS!!!: source jobhunter-venv/bin/activate"

setup:
	pip install -r requirements.txt

test: setup
	# the -k command makes it so it only looks at python files not folders
	cd $(SRC_DIR) && coverage run -m pytest 
	cd $(SRC_DIR) && coverage report 
	cd $(SRC_DIR) && coverage html -d coverage_html

run: test
	streamlit run $(SRC_DIR)/main.py