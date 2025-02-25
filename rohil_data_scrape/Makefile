.PHONY: run run_scraper run_detector
FILE=prompts.txt

run_scraper:
	ifndef FILE
		@echo "Usage: make run FILE=<prompt-file.txt>"
		@exit 1
	endif
		python3 scraper.py "$(FILE)"

run_detector:
	python3 llm_detector.py