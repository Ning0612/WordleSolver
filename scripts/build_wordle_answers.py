#!/usr/bin/env python3
"""
Build a reproducible Wordle answer list from a local archive checkout.

The script scans a repository containing one answer file per day and writes a
normalized list of answers, one per line, in chronological order.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


ANSWER_PATTERN = re.compile(r"^[a-z]{5}$")


def collect_answers(source_root: Path) -> list[str]:
    if not source_root.exists():
        raise FileNotFoundError(f"Source repository not found: {source_root}")

    answers: list[str] = []
    seen: set[str] = set()

    for path in sorted(source_root.rglob("*")):
        if not path.is_file():
            continue

        try:
            text = path.read_text(encoding="utf-8").strip().lower()
        except UnicodeDecodeError:
            continue

        if not ANSWER_PATTERN.fullmatch(text):
            continue

        if text in seen:
            raise ValueError(f"Duplicate answer detected in source archive: {text}")

        seen.add(text)
        answers.append(text)

    if not answers:
        raise ValueError(f"No answers found under {source_root}")

    return answers


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a Wordle answer list.")
    parser.add_argument(
        "--source-repo",
        required=True,
        help="Path to a checkout of the answer archive repository.",
    )
    parser.add_argument(
        "--output",
        default="data/wordle_answers.txt",
        help="Output path for the normalized answer list.",
    )
    args = parser.parse_args()

    source_root = Path(args.source_repo)
    output_path = Path(args.output)

    answers = collect_answers(source_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(answers) + "\n", encoding="utf-8")

    print(f"Wrote {len(answers)} answers to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
