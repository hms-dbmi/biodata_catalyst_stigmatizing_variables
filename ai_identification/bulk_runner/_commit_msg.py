#!/usr/bin/env python3
"""Print a copy-pasteable commit message summarizing the last stigvar run.

Usage:
    python3 _commit_msg.py [Managed_Inputs.csv]

If Managed_Inputs.csv is provided, only vars_FLAGGED.tsv files newer than it
are included (i.e. produced in the current run). If omitted, all local
phs*/vars_FLAGGED.tsv files are summarized.
"""
from __future__ import annotations

import glob
import os
import sys
from collections import Counter
from pathlib import Path


def parse_flagged(path: str) -> tuple[int, list[str]]:
    """Return (flagged_count, top_categories) for a vars_FLAGGED.tsv file."""
    count = 0
    categories: Counter = Counter()
    with open(path, encoding="utf-8") as f:
        for line in f:
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 2:
                continue
            stigmatizing = cols[1].strip()
            if stigmatizing not in ("TRUE", "FALSE"):
                continue  # skip header rows or malformed lines
            if stigmatizing == "TRUE":
                count += 1
                if len(cols) >= 3 and cols[2].strip():
                    categories[cols[2].strip()] += 1
    top = [cat for cat, _ in categories.most_common(3)]
    return count, top


def main() -> None:
    ref_mtime: float | None = None
    if len(sys.argv) > 1:
        csv_path = Path(sys.argv[1])
        if csv_path.exists():
            ref_mtime = csv_path.stat().st_mtime

    flagged_files = sorted(glob.glob("phs*/vars_FLAGGED.tsv"))

    if ref_mtime is not None:
        flagged_files = [f for f in flagged_files if os.path.getmtime(f) > ref_mtime]

    results: list[tuple[str, int, list[str]]] = []
    for path in flagged_files:
        study = Path(path).parent.name
        count, top_cats = parse_flagged(path)
        if count > 0:
            results.append((study, count, top_cats))

    if not results:
        print("No studies with flagged concepts from the last run.")
        return

    n = len(results)
    total = sum(c for _, c, _ in results)

    study_word = "study" if n == 1 else "studies"
    concept_word = "concept" if total == 1 else "concepts"

    print(f"Add stigmatizing variable flags: {n} {study_word}, {total} {concept_word} flagged")
    print()
    print("Studies processed:")
    width = max(len(study) for study, _, _ in results)
    for study, count, top_cats in results:
        cat_str = f" ({', '.join(top_cats)})" if top_cats else ""
        c_word = "concept" if count == 1 else "concepts"
        print(f"  - {study:<{width}}: {count:>3} {c_word} flagged{cat_str}")
    print()
    print("Updates stigmatizing_terms/conceptsToRemove.txt")


if __name__ == "__main__":
    main()
