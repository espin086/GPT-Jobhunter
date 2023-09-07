SRC_DIR := $(shell pwd)/jobhunter/src

setup:
	python3 -m venv jobhunter
	. jobhunter/bin/activate && pip install -r requirements.txt
	source jobhunter/bin/activate

test:
	cd $(SRC_DIR) && pytest