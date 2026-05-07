#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

BUCKET = "avillach-73-bdcatalyst-etl"
VARS_KEY_TEMPLATE = "dictionary/{dataset_id}/vars.tsv"

THIS_DIR = Path(__file__).resolve().parent
AI_ID_DIR = THIS_DIR.parent
STIG_ID_AI = AI_ID_DIR / "stig_id_ai.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run stig_id_ai.py against vars.tsv files pulled from the 73 bucket. "
                    "Provide either --input-csv (one row per study) or --study-identifier (single study)."
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
    return parser.parse_args()


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


def download_vars_tsv(s3_client, dataset_id: str, dest_dir: Path) -> Path | None:
    key = VARS_KEY_TEMPLATE.format(dataset_id=dataset_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / "vars.tsv"
    try:
        s3_client.download_file(BUCKET, key, str(dest_path))
    except ClientError as exc:
        print(f"  skip {dataset_id}: s3://{BUCKET}/{key} -> {exc.response['Error'].get('Code', 'Error')}", file=sys.stderr)
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

    s3_client = boto3.client("s3")

    processed = 0
    skipped = 0
    for dataset_id in iter_dataset_ids(args):
        print(f"[{dataset_id}] downloading vars.tsv")
        study_dir = THIS_DIR / dataset_id
        vars_path = download_vars_tsv(s3_client, dataset_id, study_dir)
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
