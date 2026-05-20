PYTHON       ?= python3
MANAGED_CSV  := Managed_Inputs.csv
S3_CSV_URI   := s3://avillach-73-bdcatalyst-etl/general/resources/Managed_Inputs.csv
RUNNER       := run_stigvars_on_managed_inputs.py

.DEFAULT_GOAL := help

.PHONY: all install fetch run run-study commit-msg clean help

all: clean fetch run commit-msg  ## Clean, fetch inputs, run the classifier, and print a commit message

install:  ## Install Python dependencies
	$(PYTHON) -m pip install boto3 pandas numpy

fetch:  ## Download Managed_Inputs.csv from S3 (always re-downloads)
	aws s3 cp $(S3_CSV_URI) $(MANAGED_CSV)

run: $(MANAGED_CSV)  ## Run classifier against all ready studies in Managed_Inputs.csv
	$(PYTHON) $(RUNNER) --input-csv $(MANAGED_CSV)

run-study:  ## Run classifier for a single study: make run-study STUDY=phs004526
ifndef STUDY
	$(error STUDY is not set. Usage: make run-study STUDY=phs004526)
endif
	$(PYTHON) $(RUNNER) --study-identifier $(STUDY)

commit-msg:  ## Print a copy-pasteable commit message summarizing the last run
	@$(PYTHON) _commit_msg.py $(MANAGED_CSV)

clean:  ## Remove downloaded study dirs and Managed_Inputs.csv
	rm -rf phs* $(MANAGED_CSV)

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'
