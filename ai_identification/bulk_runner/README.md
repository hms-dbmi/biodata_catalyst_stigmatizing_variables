# bulk_runner

Bulk-runs `ai_identification/stig_id_ai.py` against `vars.tsv` files pulled from
the 73 bucket (`s3://avillach-73-bdcatalyst-etl/`) for one or more studies.

For each study it:

1. Downloads `s3://avillach-73-bdcatalyst-etl/dictionary/{Study Identifier}/vars.tsv`
   to `./{Study Identifier}/vars.tsv`.
2. Runs `stig_id_ai.py --no-header --num-columns 6` against that file, producing
   `./{Study Identifier}/vars_FLAGGED.tsv`.
3. Appends every flagged `concept_path` to
   `../stigmatizing_terms/conceptsToRemove.txt` (handled by `stig_id_ai.py`).

## Prerequisites

Export AWS credentials in the shell before running:

```sh
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=...
```

Python deps: `boto3`, `pandas` (used by `stig_id_ai.py`).

## Usage

The script takes either a CSV of studies or a single study identifier (mutually
exclusive, one is required).

### CSV mode

```sh
python3 run_stigvars_on_managed_inputs.py --input-csv "BDC Managed Inputs.csv"
```

Only rows where `Data is ready to process` is `Yes` **and** `Data Processed` is
`No` are processed.

#### Expected CSV columns

The CSV's first row must be a header. The following columns are required (other
columns are ignored, so `BDC Managed Inputs.csv` works as-is):

| Column                      | Used for                                                  |
| --------------------------- | --------------------------------------------------------- |
| `Study Identifier`          | `datasetId` — used as the S3 path segment and local dir.  |
| `Data is ready to process`  | Filter: row is processed only when this equals `Yes`.     |
| `Data Processed`            | Filter: row is processed only when this equals `No`.      |

Matching on the filter columns is case-insensitive and trims surrounding whitespace.

### Single-study mode

```sh
python3 run_stigvars_on_managed_inputs.py --study-identifier phs004526
```

No filtering is applied; the given study is always processed.

## Outputs

- `./{Study Identifier}/vars.tsv` — raw file pulled from S3.
- `./{Study Identifier}/vars_FLAGGED.tsv` — three-column TSV
  (`concept_path`, `is_stigmatizing`, `Category`) produced by `stig_id_ai.py`.
- `../stigmatizing_terms/conceptsToRemove.txt` — appended with the flagged
  `concept_path`s from each study.

Studies whose `vars.tsv` is missing in S3 are skipped and reported in stderr;
the run continues with the remaining studies. A summary
(`done: processed=…, skipped=…`) is printed at the end.
