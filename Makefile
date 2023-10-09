
SRC_DIR:=$(shell pwd)/src

virtualenv: 
	python3 -m venv jobhunter-venv
	echo "RUN THIS!!!: source jobhunter-venv/bin/activate"

install:
	pip install -r requirements.txt

test: install
    # the -k command makes it so it only looks at python files not folders
	cd $(SRC_DIR) && coverage run -m pytest 
	cd $(SRC_DIR) && coverage report 
	cd $(SRC_DIR) && coverage html -d coverage_html

run: 
	streamlit run $(SRC_DIR)/main.py

