#!/usr/bin/env python3
"""
Stigmatizing variable flagger

This script reproduces the heuristic rule-based flagging used in the chat:
- reads a CSV or TSV file
- scans all columns in each row
- appends two columns:
    is_stigmatizing  -> TRUE / FALSE
    Category         -> stigmatizing category name or blank

It is designed to work on large files by streaming row-by-row instead of loading
all data into memory.

Examples
--------
CSV with header:
    python stigmatizing_flagger.py \
        --input adult_vars_v5.csv \
        --output adult_vars_v5_with_stigmatizing.csv

TSV with header:
    python stigmatizing_flagger.py \
        --input ehr_vars.tsv \
        --output ehr_vars_with_stigmatizing.tsv

Headerless TSV with 6 columns:
    python stigmatizing_flagger.py \
        --input recover_vars.tsv \
        --output recover_vars_with_stigmatizing.tsv \
        --no-header \
        --num-columns 6

Optional gzip output:
    python stigmatizing_flagger.py \
        --input recover_vars.tsv \
        --output recover_vars_with_stigmatizing.tsv.gz \
        --no-header \
        --num-columns 6
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import os
import re
import sys
from typing import Iterable, List, Sequence, Tuple
import pandas as pd
pd.set_option('display.max_colwidth', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)

import numpy as np
import shutil


# Allow very large fields.
try:
    csv.field_size_limit(sys.maxsize)
except OverflowError:
    csv.field_size_limit(2**31 - 1)


# -----------------------------
# Keyword sets
# -----------------------------

IDENT = [
    "participant id", "participant_id", "subject id", "study id", "mrn",
    "medical record number", "name", "first name", "last name", "initials",
    "address", "email", "phone", "contact", "date of birth", "dob", "date",
    "time", "datetime", "timestamp", "zip code", "zipcode", "city",
    "birthplace", "photograph", "photo", "audio", "specimen", "barcode",
    "identifier", "family id", "hospitalization", "death date", "place of birth",
]

MH_VERY_STRICT = [
    "agoraphobia", "phobia", "panic disorder", "generalized anxiety disorder",
    "social anxiety disorder", "anxiety", "panic", "gad",
    "major depressive disorder", "mdd", "depression", "depressive", "mood disorder",
    "bipolar i disorder", "bipolar ii disorder", "bipolar", "mania", "manic",
    "cyclothymic", "psychosis", "psychotic", "schizophrenia",
    "schizophreniform", "schizoaffective", "antisocial personality disorder",
    "personality disorder", "binge eating disorder", "binge-eating disorder",
    "binge eating", "eating disorder", "anorexia", "bulimia", "ptsd",
    "post traumatic stress disorder", "post-traumatic stress disorder",
    "post traumatic stress", "suicide", "suicidality", "suicidal",
    "suicide behavior disorder", "suicide behaviour disorder", "self harm",
    "self-harm", "self injury", "self-injury", "attempt", "mental health",
    "psychiatric", "psychiatrist", "psychology", "psychological", "diagnosis",
    "diagnosed", "primary diagnosis", "no primary diagnosis", "remission",
    "therapy", "counseling", "counselling", "antidepressant", "antipsychotic",
    "ssri", "snri", "mood stabilizer", "lithium", "inpatient",
    "psychiatric hospitalization", "involuntary commitment", "mood", "stress",
    "sleep", "insomnia", "fatigue", "tired", "appetite", "eat more", "eat less",
    "happy", "sad", "lonely",
]

SEX_STRICT = [
    "sexual history", "sexual behavior", "sexual behaviour", "sexual activity",
    "intercourse", "coitus", "erectile", "erection", "erections", "impotence",
    "orgasm", "anorgasmia", "libido", "arousal", "ejaculation",
    "premature ejaculation", "semen", "vaginal sex", "anal sex", "oral sex",
    "anal intercourse", "vaginal intercourse", "number of partners",
    "sexual partners", "condom", "contraception", "birth control", "prep",
    "transactional sex", "sex work", "chemsex", "estrogen", "testosterone",
]

DRUGS = [
    "cocaine", "heroin", "methamphetamine", "meth", "mdma", "ecstasy", "lsd",
    "psilocybin", "fentanyl", "ketamine", "illicit drug", "drug use",
    "substance use", "substance use disorder", "sud", "opioid", "oxycodone",
    "hydrocodone", "morphine", "benzodiazepine", "xanax", "alprazolam",
    "clonazepam", "stimulant", "adderall", "ritalin", "methadone",
    "buprenorphine", "suboxone", "rehab", "detox", "12 step", "twelve step",
    "needle", "injection", "drug test", "toxicology", "urine screen",
    "positive screen", "hair test", "alcohol", "alcoholism", "drinking",
    "tobacco", "smoking", "cannabis", "marijuana", "weed",
    "controlled substance", "schedule i", "schedule ii", "schedule iii", "schedule iv",
]

STD = [
    "hiv", "aids", "syphilis", "gonorrhea", "chlamydia", "hpv", "herpes",
    "sti", "std", "antiviral", "antiretroviral", "prep",
    "postexposure prophylaxis", "pep", "std screen", "std test", "sti screen",
    "sti test", "contact tracing", "partner notification", "cervical biopsy",
    "pap smear with hpv", "infertility due to chlamydia",
]

INTEL = [
    "iq", "cognitive", "memory", "processing speed", "aptitude", "sat", "gre",
    "lsat", "gmat", "adhd", "dyslexia", "dyscalculia", "learning disability",
    "iep", "special education", "gpa", "class rank", "remedial", "tutoring",
    "dementia", "neurodegenerative", "cognitive decline", "ability to pay bills",
    "financial concerns", "homelessness", "self reported intelligence",
]

LEGAL = [
    "citizenship", "naturalization", "visa", "residency", "asylum", "refugee",
    "undocumented", "deport", "arrest", "charge", "conviction", "incarceration",
    "parole", "probation", "court record", "work authorization", "work permit",
    "green card", "denied housing", "denied employment", "marital status",
    "married", "divorced",
]


# Pad phrases once for cheap substring search.
PADDED_IDENT = [f" {x.lower()} " for x in IDENT]
PADDED_MH = [f" {x.lower()} " for x in MH_VERY_STRICT]
PADDED_SEX = [f" {x.lower()} " for x in SEX_STRICT]
PADDED_DRUGS = [f" {x.lower()} " for x in DRUGS]
PADDED_STD = [f" {x.lower()} " for x in STD]
PADDED_INTEL = [f" {x.lower()} " for x in INTEL]
PADDED_LEGAL = [f" {x.lower()} " for x in LEGAL]


# -----------------------------
# Helpers
# -----------------------------

_NON_ALNUM_RE = re.compile(r"[^a-z0-9\s]+")
_SPACE_RE = re.compile(r"\s+")


def normalize_text(parts: Iterable[str | None]) -> str:
    """Normalize row text for boundary-ish substring matching."""
    s = " ".join("" if p is None else str(p) for p in parts).lower()
    s = s.replace("_", " ").replace("-", " ")
    s = _NON_ALNUM_RE.sub(" ", s)
    s = _SPACE_RE.sub(" ", s).strip()
    return f" {s} "


def has_any(text: str, terms: Sequence[str]) -> bool:
    return any(term in text for term in terms)


def classify_row(text: str) -> Tuple[str, str]:
    """Return (is_stigmatizing, category) using the same priority used in the chat."""
    if has_any(text, PADDED_IDENT):
        return "TRUE", "Stigmatizing Identifiers"
    if has_any(text, PADDED_MH):
        return "TRUE", "Mental Health Diagnoses / History / Treatment"
    if has_any(text, PADDED_SEX):
        return "TRUE", "Sexual History"
    if has_any(text, PADDED_DRUGS):
        return "TRUE", "Illicit Drug Use History"
    if has_any(text, PADDED_STD):
        return "TRUE", "Sexually Transmitted Disease Diagnoses / History / Treatment"
    if has_any(text, PADDED_INTEL):
        return "TRUE", "Intellectual Achievement / Ability / Educational Attainment"
    if has_any(text, PADDED_LEGAL):
        return "TRUE", "Direct or Surrogate Identifiers of Legal Status"
    return "FALSE", ""


def infer_delimiter(path: str) -> str:
    lowered = path.lower()
    if lowered.endswith(".tsv") or lowered.endswith(".tsv.gz"):
        return "\t"
    return ","


def open_maybe_gzip(path: str, mode: str):
    if path.lower().endswith(".gz"):
        return gzip.open(path, mode, encoding="utf-8", newline="")
    return open(path, mode, encoding="utf-8", newline="")


def write_with_header(
    input_path: str,
    output_path: str,
    delimiter: str,
    progress_every: int,
) -> None:
    with open_maybe_gzip(input_path, "rt") as fin, open_maybe_gzip(output_path, "wt") as fout:
        reader = csv.DictReader(fin, delimiter=delimiter)
        if not reader.fieldnames:
            raise ValueError("Could not detect header row. Use --no-header for headerless files.")
        fieldnames = list(reader.fieldnames) + ["is_stigmatizing", "Category"]
        writer = csv.DictWriter(fout, fieldnames=fieldnames, delimiter=delimiter)
        writer.writeheader()

        row_count = 0
        for row in reader:
            text = normalize_text(row.values())
            row["is_stigmatizing"], row["Category"] = classify_row(text)
            writer.writerow(row)
            row_count += 1
            if progress_every and row_count % progress_every == 0:
                print(f"processed {row_count:,} rows", file=sys.stderr)

        print(f"finished {row_count:,} rows", file=sys.stderr)


def write_no_header(
    input_path: str,
    output_path: str,
    delimiter: str,
    num_columns: int | None,
    progress_every: int,
    concept_path_index: int = 0,  # 0-based index
) -> None:
    with open_maybe_gzip(input_path, "rt") as fin, open_maybe_gzip(output_path, "wt") as fout:
        reader = csv.reader(fin, delimiter=delimiter)
        writer = csv.writer(fout, delimiter=delimiter)

        first_row = next(reader, None)
        if first_row is None:
            raise ValueError("Input file is empty.")

        writer.writerow(["concept_path", "is_stigmatizing", "Category"])

        def emit_row(values: List[str]) -> None:
            if concept_path_index >= len(values):
                concept_path = ""
            else:
                concept_path = values[concept_path_index]

            text = normalize_text(values)
            is_stig, cat = classify_row(text)
            
            writer.writerow([concept_path, is_stig, cat])

        emit_row(first_row)
        row_count = 1

        for row in reader:
            emit_row(row)
            row_count += 1
            if progress_every and row_count % progress_every == 0:
                print(f"processed {row_count:,} rows", file=sys.stderr)

        print(f"finished {row_count:,} rows", file=sys.stderr)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Flag stigmatizing variables in CSV/TSV files.")
    parser.add_argument("--input", required=True, help="Input CSV/TSV path. .gz is supported.")
    parser.add_argument("--output", required=True, help="Output CSV/TSV path. .gz is supported.")
    parser.add_argument(
        "--delimiter",
        choices=["csv", "tsv"],
        help="Override delimiter detection. Default: infer from filename.",
    )
    parser.add_argument(
        "--no-header",
        action="store_true",
        help="Treat the input as headerless and write generic column_1...column_n headers.",
    )
    parser.add_argument(
        "--num-columns",
        type=int,
        default=None,
        help="Expected number of columns for headerless files. Defaults to the first row width.",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=50000,
        help="Print progress every N rows to stderr. Use 0 to disable.",
    )
    return parser.parse_args()


def update_conceptstoRemove(output_path: str):
    print(f"Updating conceptsToRemove.txt")

    #original_concepts = pd.read_csv('../stigmatizing_terms/conceptsToRemove.txt', sep=" ", header=None)
    #original_concepts.columns = ["concept_path"]

    full_stig_id = pd.read_table(output_path, dtype={"concept_path" : "string","is_stigmatizing" : "string","category" : "string"})

    new_stig_ids = full_stig_id.loc[full_stig_id['is_stigmatizing'] == "TRUE", 'concept_path']


    new_stig_ids.to_csv('new_concepts.txt', index=False, header=False)

    with open('new_concepts.txt', 'r') as f_src, open('../stigmatizing_terms/conceptsToRemove.txt', 'a') as f_dest:
        shutil.copyfileobj(f_src, f_dest)

    return 0


def main() -> int:
    args = parse_args()

    if args.delimiter == "csv":
        delimiter = ","
    elif args.delimiter == "tsv":
        delimiter = "\t"
    else:
        delimiter = infer_delimiter(args.input)

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)

    if args.no_header:
        write_no_header(
            input_path=args.input,
            output_path=args.output,
            delimiter=delimiter,
            num_columns=args.num_columns,
            progress_every=args.progress_every,
            concept_path_index=3,
        )
    else:
        write_with_header(
            input_path=args.input,
            output_path=args.output,
            delimiter=delimiter,
            progress_every=args.progress_every,
        )

    print(f"Wrote: {args.output}")

    update_conceptstoRemove(
        output_path=args.output
        )

    print("Updated local conceptsToRemove.txt")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

