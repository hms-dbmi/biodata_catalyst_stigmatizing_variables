# bulk_runner

Bulk-runs `stig_id_ai.py` against `vars.tsv` files pulled from the 73 bucket
(`s3://avillach-73-bdcatalyst-etl/`) for one or more studies. Flagged concept
paths are appended to `conceptsToRemove.txt`.

## Prerequisites

**AWS credentials** must be exported in the shell:

```sh
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=...
```

**Python dependencies**: `boto3`, `pandas`, `numpy`

```sh
make install
```

## Quick Start

Run the full pipeline — fetches `Managed_Inputs.csv` from S3, classifies every
ready study, and prints a commit message:

```sh
make all
```

Process a single study:

```sh
make run-study STUDY=phs004526
```

## Make Goals

Run `make help` for a summary, or see the table below:

| Goal | Description |
| --- | --- |
| `all` | Clean, fetch inputs, run the classifier, and print a commit message (default) |
| `install` | Install Python dependencies |
| `fetch` | Download `Managed_Inputs.csv` from S3 |
| `run` | Run classifier against all ready studies in `Managed_Inputs.csv` |
| `run-study` | Run classifier for a single study (`STUDY=` required) |
| `commit-msg` | Print a copy-pasteable commit message summarizing the last run |
| `clean` | Remove downloaded study dirs (`phs*/`) and `Managed_Inputs.csv` |
| `help` | Show available goals |

## Manual Usage

For cases where Make is not available or finer control is needed.

### CSV mode (multiple studies)

```sh
python3 run_stigvars_on_managed_inputs.py --input-csv "Managed_Inputs.csv"
```

Only rows where **Data is ready to process** is `Yes` and **Data Processed** is
`No` are processed.

### Single-study mode

```sh
python3 run_stigvars_on_managed_inputs.py --study-identifier phs004526
```

No filtering is applied; the given study is always processed.

### Direct `stig_id_ai.py` invocation

If you already have a local `vars.tsv`, you can skip S3 and call the classifier
directly from the `ai_identification/` directory:

```sh
python3 stig_id_ai.py --input vars.tsv --output vars_FLAGGED.tsv --no-header --num-columns 6
```

## CSV Format

`Managed_Inputs.csv` is pulled from
`s3://avillach-73-bdcatalyst-etl/general/resources/Managed_Inputs.csv`.

The following columns are required (extra columns are ignored):

| Column | Used for |
| --- | --- |
| `Study Identifier` | `datasetId` — used as the S3 path segment and local directory name |
| `Data is ready to process` | Filter: row is processed only when this equals `Yes` |
| `Data Processed` | Filter: row is processed only when this equals `No` |

Matching is case-insensitive and trims surrounding whitespace.

## Outputs

| File | Description |
| --- | --- |
| `./{study}/vars.tsv` | Raw dictionary file downloaded from S3 |
| `./{study}/vars_FLAGGED.tsv` | Three-column TSV: `concept_path`, `is_stigmatizing`, `Category` |
| `../stigmatizing_terms/conceptsToRemove.txt` | Canonical output — flagged concept paths appended here (deduplicated) |

Studies whose `vars.tsv` is missing in S3 are skipped and reported to stderr.
A summary (`done: processed=…, skipped=…`) is printed at the end.
Re-running a study is safe — `conceptsToRemove.txt` will not gain duplicate entries.

## Completing the Process

After the run, commit the updated `conceptsToRemove.txt` to the `main` branch.
Use `make commit-msg` to generate a summary for the commit message.
