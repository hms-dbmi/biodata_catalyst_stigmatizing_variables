PYTHON       ?= python3
MANAGED_CSV  := Managed_Inputs.csv
RUNNER       := run_stigvars_on_managed_inputs.py

# SOURCE selects where vars.tsv and Managed_Inputs.csv are read from:
#   legacy       s3://avillach-73-bdcatalyst-etl/        (default)
#   in-boundary  s3://bdc-etl-data-d0d6191/              (dictionary ETL output; Managed_Inputs.csv from the mirror)
# MANAGED_INPUTS_URI overrides the Managed_Inputs.csv location. VARS_URI (an s3://bucket/key
# template containing {dataset_id}) overrides the vars.tsv location chosen by SOURCE.
SOURCE ?= legacy
ifeq ($(SOURCE),legacy)
MANAGED_INPUTS_URI ?= s3://avillach-73-bdcatalyst-etl/general/resources/Managed_Inputs.csv
else ifeq ($(SOURCE),in-boundary)
MANAGED_INPUTS_URI ?= s3://bdc-etl-data-d0d6191/avillach-73-bdcatalyst-etl/general/resources/Managed_Inputs.csv
else
$(error SOURCE must be legacy or in-boundary, got '$(SOURCE)')
endif
RUNNER_OPTS := --source $(SOURCE) $(if $(VARS_URI),--vars-uri '$(VARS_URI)')

.DEFAULT_GOAL := help

.PHONY: all install fetch run run-study commit-msg test clean help

all: clean fetch run commit-msg  ## Clean, fetch inputs, run the classifier, and print a commit message

install:  ## Install Python dependencies
	$(PYTHON) -m pip install boto3 pandas numpy

fetch:  ## Download Managed_Inputs.csv from S3 (always re-downloads)
	aws s3 cp $(MANAGED_INPUTS_URI) $(MANAGED_CSV)

run: $(MANAGED_CSV)  ## Run classifier against all ready studies in Managed_Inputs.csv
	$(PYTHON) $(RUNNER) $(RUNNER_OPTS) --input-csv $(MANAGED_CSV)

run-study:  ## Run classifier for a single study: make run-study STUDY=phs004526
ifndef STUDY
	$(error STUDY is not set. Usage: make run-study STUDY=phs004526)
endif
	$(PYTHON) $(RUNNER) $(RUNNER_OPTS) --study-identifier $(STUDY)

commit-msg:  ## Print a copy-pasteable commit message summarizing the last run
	@$(PYTHON) _commit_msg.py $(MANAGED_CSV)

test:  ## Run the unit tests (no AWS access needed)
	$(PYTHON) -m unittest discover -s tests -v

clean:  ## Remove downloaded study dirs and Managed_Inputs.csv
	rm -rf phs* $(MANAGED_CSV)

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'
