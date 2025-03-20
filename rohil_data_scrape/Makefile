.PHONY: run run_scraper run_detector

## Run the scraper with a specified prompt file
run_scraper:
	ifndef FILE
		@echo "Usage: make run_scraper FILE=<prompt-file.txt>"
		@exit 1
	endif
	python3 scraper.py "$(FILE)"

## Run the LLM detector to analyze flagged content
run_detector:
	python3 llm_detector.py

## Run both the scraper and detector sequentially (example combined target)
run: run_scraper run_detector
