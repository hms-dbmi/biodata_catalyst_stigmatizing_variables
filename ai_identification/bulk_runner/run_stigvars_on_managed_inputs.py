#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import os
import re
import subprocess
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

PLACEHOLDER = "{dataset_id}"

# Where the vars.tsv files live, per --source.
SOURCES = {
    "legacy": "s3://avillach-73-bdcatalyst-etl/dictionary/{dataset_id}/vars.tsv",
    "in-boundary": "s3://bdc-etl-data-d0d6191/data/dictionary/dictionary/{dataset_id}/vars.tsv",
}
DEFAULT_SOURCE = "legacy"

# A dataset id becomes an S3 key segment and a local directory name, so it must
# be a plain token: no path separators, no leading dot, no whitespace.
DATASET_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")

THIS_DIR = Path(__file__).resolve().parent
AI_ID_DIR = THIS_DIR.parent
STIG_ID_AI = AI_ID_DIR / "stig_id_ai.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run stig_id_ai.py against vars.tsv files pulled from S3 (the legacy 73 bucket "
                    "by default). Provide either --input-csv (one row per study) or "
                    "--study-identifier (single study)."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--input-csv",
        help='Path to a CSV with a "Study Identifier" column (e.g. "BDC Managed Inputs.csv").',
    )
    group.add_argument(
        "--study-identifier",
        help="Single study identifier (datasetId), e.g. phs004526.",
    )
    parser.add_argument(
        "--source",
        choices=sorted(SOURCES),
        default=DEFAULT_SOURCE,
        help="Where to read vars.tsv from (default: %(default)s). "
             + "; ".join(f"{name}: {uri}" for name, uri in sorted(SOURCES.items())),
    )
    parser.add_argument(
        "--vars-uri",
        metavar="TEMPLATE",
        help="s3://bucket/key template containing {dataset_id} exactly once; overrides --source.",
    )
    return parser.parse_args()


def parse_vars_template(template: str) -> tuple[str, str]:
    """Validate an s3://bucket/key template and return (bucket, key_template)."""
    if template.count(PLACEHOLDER) != 1:
        raise ValueError(f"vars URI template must contain {PLACEHOLDER} exactly once: {template!r}")
    prefix = "s3://"
    if not template.startswith(prefix):
        raise ValueError(f"vars URI template must use the s3:// scheme: {template!r}")
    bucket, _, key = template[len(prefix):].partition("/")
    if not bucket or PLACEHOLDER in bucket:
        raise ValueError(f"vars URI template has an empty or templated bucket: {template!r}")
    if not key or PLACEHOLDER not in key:
        raise ValueError(f"vars URI template needs a key containing {PLACEHOLDER}: {template!r}")
    return bucket, key


def resolve_vars_template(source: str, vars_uri: str | None) -> tuple[str, str]:
    """Return (bucket, key_template) for the chosen --source / --vars-uri."""
    return parse_vars_template(vars_uri if vars_uri else SOURCES[source])


def validate_dataset_id(dataset_id: str) -> None:
    if not DATASET_ID_RE.fullmatch(dataset_id):
        raise ValueError(f"invalid dataset id: {dataset_id!r}")


def iter_dataset_ids(args: argparse.Namespace):
    if args.study_identifier:
        yield args.study_identifier.strip()
        return

    required = ("Study Identifier", "Data is ready to process", "Data Processed")
    with open(args.input_csv, "r", encoding="utf-8", newline="") as fin:
        reader = csv.DictReader(fin)
        missing = [c for c in required if c not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(f"Input CSV is missing required column(s): {', '.join(missing)}")
        for row in reader:
            dataset_id = (row.get("Study Identifier") or "").strip()
            ready = (row.get("Data is ready to process") or "").strip().lower()
            processed = (row.get("Data Processed") or "").strip().lower()
            if not dataset_id or ready != "yes" or processed != "no":
                continue
            yield dataset_id


def download_vars_tsv(s3_client, bucket: str, key_template: str, dataset_id: str, dest_dir: Path) -> Path | None:
    key = key_template.replace(PLACEHOLDER, dataset_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / "vars.tsv"
    try:
        s3_client.download_file(bucket, key, str(dest_path))
    except ClientError as exc:
        print(f"  skip {dataset_id}: s3://{bucket}/{key} -> {exc.response['Error'].get('Code', 'Error')}", file=sys.stderr)
        return None
    return dest_path


def run_stig_id_ai(vars_path: Path, dataset_id: str) -> bool:
    output_path = vars_path.with_name("vars_FLAGGED.tsv")
    cmd = [
        sys.executable,
        str(STIG_ID_AI),
        "--input", str(vars_path),
        "--output", str(output_path),
        "--no-header",
        "--num-columns", "6",
    ]
    # stig_id_ai.py appends to ../stigmatizing_terms/conceptsToRemove.txt, so run it from ai_identification/.
    result = subprocess.run(cmd, cwd=AI_ID_DIR)
    if result.returncode != 0:
        print(f"  stig_id_ai.py failed for {dataset_id} (exit {result.returncode})", file=sys.stderr)
        return False
    return True


def main() -> int:
    args = parse_args()

    try:
        bucket, key_template = resolve_vars_template(args.source, args.vars_uri)
    except ValueError as exc:
        raise SystemExit(f"error: {exc}")
    if args.study_identifier:
        try:
            validate_dataset_id(args.study_identifier.strip())
        except ValueError as exc:
            raise SystemExit(f"error: {exc}")

    origin = "--vars-uri" if args.vars_uri else f"--source {args.source}"
    print(f"vars.tsv source ({origin}): s3://{bucket}/{key_template}")

    s3_client = boto3.client("s3")

    processed = 0
    skipped = 0
    for dataset_id in iter_dataset_ids(args):
        try:
            validate_dataset_id(dataset_id)
        except ValueError as exc:
            print(f"  skip: {exc}", file=sys.stderr)
            skipped += 1
            continue
        print(f"[{dataset_id}] downloading vars.tsv")
        study_dir = THIS_DIR / dataset_id
        vars_path = download_vars_tsv(s3_client, bucket, key_template, dataset_id, study_dir)
        if vars_path is None:
            skipped += 1
            continue

        print(f"[{dataset_id}] running stig_id_ai.py")
        if run_stig_id_ai(vars_path, dataset_id):
            processed += 1
        else:
            skipped += 1

    print(f"done: processed={processed}, skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
