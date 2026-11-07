# bulk_runner

Bulk-runs `stig_id_ai.py` against `vars.tsv` files pulled from S3 for one or
more studies. By default they come from the legacy 73 bucket
(`s3://avillach-73-bdcatalyst-etl/`); `--source in-boundary` reads the files the
in-boundary dictionary ETL publishes instead (see [Sources](#sources)). Flagged
concept paths are appended to `conceptsToRemove.txt`.

## Prerequisites

**AWS credentials** must be available to the AWS CLI and boto3 through the
usual environment. For the legacy bucket, export them in the shell:

```sh
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=...
```

For the in-boundary bucket, use whatever credentials your in-boundary
environment provides (for example `export AWS_PROFILE=<in-boundary SSO profile>`
after `aws sso login`, or the instance role on a server). The runner does no
credential handling of its own.

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

Against the in-boundary bucket:

```sh
make all SOURCE=in-boundary
make run-study SOURCE=in-boundary STUDY=phsNNNNNN
```

## Sources

`--source` (Make: `SOURCE`) selects where `vars.tsv` is read from. Without it,
behaviour is unchanged (`legacy`).

| Source | `vars.tsv` location | Default `Managed_Inputs.csv` (Make `fetch`) |
| --- | --- | --- |
| `legacy` (default) | `s3://avillach-73-bdcatalyst-etl/dictionary/<phs>/vars.tsv` | `s3://avillach-73-bdcatalyst-etl/general/resources/Managed_Inputs.csv` |
| `in-boundary` | `s3://bdc-etl-data-d0d6191/data/dictionary/dictionary/<phs>/vars.tsv` | `s3://bdc-etl-data-d0d6191/avillach-73-bdcatalyst-etl/general/resources/Managed_Inputs.csv` (mirror of the legacy file) |

The in-boundary `vars.tsv` files are written by the in-boundary dictionary ETL
(`dict-ingest`, step `stigvar-id-files`).

For any other location, pass a template with `--vars-uri` (Make: `VARS_URI`).
It must be an `s3://bucket/key` URI with a non-empty bucket and `{dataset_id}`
exactly once in the key; it overrides `--source`. For example, the legacy-layout
copy inside the in-boundary mirror:

```sh
make run-study STUDY=phsNNNNNN \
  VARS_URI='s3://bdc-etl-data-d0d6191/avillach-73-bdcatalyst-etl/dictionary/{dataset_id}/vars.tsv'
```

Override the `Managed_Inputs.csv` location with `MANAGED_INPUTS_URI=s3://...`.
The runner prints the vars.tsv location it uses when it starts, and validates
the template and each study identifier before making any S3 call.

## Make Goals

Run `make help` for a summary, or see the table below:

| Goal | Description |
| --- | --- |
| `all` | Clean, fetch inputs, run the classifier, and print a commit message (default) |
| `install` | Install Python dependencies |
| `fetch` | Download `Managed_Inputs.csv` from S3 (`MANAGED_INPUTS_URI`, chosen by `SOURCE`) |
| `run` | Run classifier against all ready studies in `Managed_Inputs.csv` |
| `run-study` | Run classifier for a single study (`STUDY=` required) |
| `test` | Run the unit tests (no AWS access needed) |
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

### Choosing the source

```sh
python3 run_stigvars_on_managed_inputs.py --source in-boundary --study-identifier phsNNNNNN
python3 run_stigvars_on_managed_inputs.py --vars-uri 's3://bucket/prefix/{dataset_id}/vars.tsv' --input-csv Managed_Inputs.csv
```

### Direct `stig_id_ai.py` invocation

If you already have a local `vars.tsv`, you can skip S3 and call the classifier
directly from the `ai_identification/` directory:

```sh
python3 stig_id_ai.py --input vars.tsv --output vars_FLAGGED.tsv --no-header --num-columns 6
```

## CSV Format

`Managed_Inputs.csv` is pulled from
`s3://avillach-73-bdcatalyst-etl/general/resources/Managed_Inputs.csv`
(or its in-boundary mirror with `SOURCE=in-boundary`).

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

Studies whose `vars.tsv` is missing in S3, or (in CSV mode) whose identifier is
not a plain token (letters, digits, `.`, `_`, `-`), are skipped and reported to
stderr. An invalid `--study-identifier` stops the run with an error before any S3 call.
A summary (`done: processed=…, skipped=…`) is printed at the end.
Re-running a study is safe — `conceptsToRemove.txt` will not gain duplicate entries.

## Completing the Process

After the run, commit the updated `conceptsToRemove.txt` to the `main` branch.
Use `make commit-msg` to generate a summary for the commit message.

## Tests

```sh
make test
# or, from the repository root:
python3 -m unittest discover -s ai_identification/bulk_runner/tests
```

The tests mock boto3 and never touch AWS.
