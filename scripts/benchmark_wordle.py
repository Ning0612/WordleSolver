#!/usr/bin/env python3
"""
Run a reproducible benchmark against the Wordle answer list.

Outputs:
- raw JSONL trace per answer
- summary JSON
- Markdown report for docs/benchmark.md
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from constraints import Constraint, FeedbackColor, FeedbackRound  # noqa: E402
from dictionary import get_word_list  # noqa: E402
from recommender import WordRecommender  # noqa: E402
from solver import filter_candidates  # noqa: E402
from stats import LetterStats  # noqa: E402


MAX_ROUNDS_DEFAULT = 6


@dataclass
class RoundTrace:
    round: int
    guess: str
    choice: str
    feedback: list[str]
    candidate_count: int


@dataclass
class GameResult:
    answer: str
    solved: bool
    attempts: int
    guesses: list[str]
    rounds: list[RoundTrace]


@dataclass(frozen=True)
class GuessChoice:
    word: str
    category: str
    reason: str


def load_answers(path: Path) -> list[str]:
    answers = [line.strip().lower() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not answers:
        raise ValueError(f"No answers found in {path}")
    return answers


def simulate_feedback(guess: str, answer: str) -> list[FeedbackColor]:
    feedback = [FeedbackColor.GRAY] * 5
    answer_pool = list(answer)

    for i, (g, a) in enumerate(zip(guess, answer)):
        if g == a:
            feedback[i] = FeedbackColor.GREEN
            answer_pool[i] = None

    remaining = Counter(ch for ch in answer_pool if ch is not None)
    for i, g in enumerate(guess):
        if feedback[i] == FeedbackColor.GREEN:
            continue
        if remaining[g] > 0:
            feedback[i] = FeedbackColor.YELLOW
            remaining[g] -= 1

    return feedback


def select_guess(
    recommendations: dict[str, list[tuple[str, float]]],
    fallback_pool: list[str],
    candidates: list[str],
    constraint: Constraint,
    round_number: int,
    max_rounds: int,
    strategy: str,
) -> GuessChoice:
    if strategy == "adaptive-exploration":
        rounds_remaining = max_rounds - round_number + 1
        should_explore = (
            len(candidates) > rounds_remaining
            and len(candidates) <= 20
            and len(constraint.greens) >= 3
            and bool(recommendations["explorations"])
        )
        if should_explore:
            return GuessChoice(
                word=recommendations["explorations"][0][0],
                category="exploration",
                reason="trap-risk",
            )

    if recommendations["candidates"]:
        return GuessChoice(
            word=recommendations["candidates"][0][0],
            category="candidate",
            reason="candidate-first",
        )
    if recommendations["explorations"]:
        return GuessChoice(
            word=recommendations["explorations"][0][0],
            category="exploration",
            reason="candidate-empty",
        )

    if fallback_pool:
        return GuessChoice(word=fallback_pool[0], category="fallback", reason="recommendation-empty")

    raise ValueError("No guess candidates available")


def run_game(
    answer: str,
    word_list: list[str],
    recommender: WordRecommender,
    max_rounds: int,
    strategy: str,
) -> GameResult:
    merged_constraint: Constraint | None = None
    candidates = word_list
    guesses: list[str] = []
    rounds: list[RoundTrace] = []

    for round_number in range(1, max_rounds + 1):
        active_constraint = merged_constraint or Constraint()
        recommendations = recommender.recommend(
            candidates=candidates,
            constraint=active_constraint,
            round_number=round_number,
            top_n=5,
        )
        choice = select_guess(
            recommendations=recommendations,
            fallback_pool=candidates,
            candidates=candidates,
            constraint=active_constraint,
            round_number=round_number,
            max_rounds=max_rounds,
            strategy=strategy,
        )
        guess = choice.word
        guesses.append(guess)

        feedback = simulate_feedback(guess, answer)
        round_trace = RoundTrace(
            round=round_number,
            guess=guess,
            choice=f"{choice.category}:{choice.reason}",
            feedback=[color.value for color in feedback],
            candidate_count=len(candidates),
        )
        rounds.append(round_trace)

        if guess == answer:
            return GameResult(
                answer=answer,
                solved=True,
                attempts=round_number,
                guesses=guesses,
                rounds=rounds,
            )

        feedback_round = FeedbackRound(guess=guess, feedback=feedback)
        constraint = feedback_round.to_constraint()
        merged_constraint = constraint if merged_constraint is None else merged_constraint.merge(constraint)
        candidates = filter_candidates(word_list, merged_constraint)
        if not candidates:
            break

    return GameResult(
        answer=answer,
        solved=False,
        attempts=max_rounds + 1,
        guesses=guesses,
        rounds=rounds,
    )


def aggregate_results(results: list[GameResult], max_rounds: int, strategy: str) -> dict:
    total = len(results)
    solved = [r for r in results if r.solved]
    failed = [r for r in results if not r.solved]
    solved_attempts = [r.attempts for r in solved]
    all_attempts = [r.attempts for r in results]

    distribution = Counter(r.attempts if r.solved else max_rounds + 1 for r in results)

    return {
        "strategy": strategy,
        "dataset_size": total,
        "solved": len(solved),
        "failed": len(failed),
        "success_rate": round(len(solved) / total, 6) if total else 0.0,
        "average_attempts_solved": round(statistics.mean(solved_attempts), 6) if solved_attempts else None,
        "median_attempts_solved": statistics.median(solved_attempts) if solved_attempts else None,
        "average_attempts_all": round(statistics.mean(all_attempts), 6) if all_attempts else None,
        "distribution": {str(k): distribution.get(k, 0) for k in range(1, max_rounds + 2)},
        "failure_cases": [
            {
                "answer": r.answer,
                "guesses": r.guesses,
                "rounds": len(r.rounds),
            }
            for r in failed
        ][:20],
    }


def write_jsonl(path: Path, results: Iterable[GameResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for result in results:
            fh.write(json.dumps(asdict(result), ensure_ascii=False))
            fh.write("\n")


def write_summary(path: Path, summary: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def render_markdown(summary: dict, answers_path: Path, raw_path: Path, summary_path: Path) -> str:
    def display_path(path: Path) -> str:
        try:
            return path.relative_to(ROOT).as_posix()
        except ValueError:
            return path.as_posix()

    rows = "\n".join(
        f"| {label} | {value} |"
        for label, value in [
            ("Dataset size", summary["dataset_size"]),
            ("Strategy", summary["strategy"]),
            ("Solved", summary["solved"]),
            ("Failed", summary["failed"]),
            ("Success rate", f'{summary["success_rate"] * 100:.2f}%'),
            ("Average attempts (solved)", summary["average_attempts_solved"]),
            ("Median attempts (solved)", summary["median_attempts_solved"]),
            ("Average attempts (all)", summary["average_attempts_all"]),
        ]
    )

    dist_lines = "\n".join(f"- `{k}`: {v}" for k, v in summary["distribution"].items())

    failures = summary["failure_cases"]
    failure_lines = "\n".join(
        f"| {item['answer']} | {', '.join(item['guesses'])} | {item['rounds']} |"
        for item in failures
    ) or "| - | - | - |"

    return f"""# Wordle Solver Benchmark

## Dataset

- Answer list: `{display_path(answers_path)}` (generated locally; not committed)
- Raw trace: `{display_path(raw_path)}` (generated locally; not committed)
- Summary JSON: `{display_path(summary_path)}`

## Reproducibility

1. Build the answer list:

```bash
.\\.venv\\bin\\python.exe scripts\\build_wordle_answers.py --source-repo <path-to-wordle-answers> --output data\\wordle_answers.txt
```

2. Run the benchmark:

```bash
.\\.venv\\bin\\python.exe scripts\\benchmark_wordle.py --answers data\\wordle_answers.txt --strategy adaptive-exploration --output-dir data\\benchmark --report docs\\benchmark.md
```

## Summary

| Metric | Value |
|---|---:|
{rows}

## Distribution

{dist_lines}

## Failure Cases

| answer | guesses | rounds |
|---|---|---:|
{failure_lines}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Wordle benchmark.")
    parser.add_argument("--answers", default="data/wordle_answers.txt", help="Path to the answer list.")
    parser.add_argument("--dictionary", default="data/five_letter_words.txt", help="Path to the full word dictionary.")
    parser.add_argument("--output-dir", default="data/benchmark", help="Directory for raw benchmark outputs.")
    parser.add_argument("--report", default="docs/benchmark.md", help="Markdown report path.")
    parser.add_argument("--max-rounds", type=int, default=MAX_ROUNDS_DEFAULT)
    parser.add_argument("--limit", type=int, default=0, help="Optional cap on the number of answers to benchmark.")
    parser.add_argument(
        "--strategy",
        choices=("candidate-first", "adaptive-exploration"),
        default="adaptive-exploration",
        help="Guess selection strategy for candidate/exploration recommendations.",
    )
    args = parser.parse_args()

    answers_path = ROOT / args.answers if not Path(args.answers).is_absolute() else Path(args.answers)
    dictionary_path = ROOT / args.dictionary if not Path(args.dictionary).is_absolute() else Path(args.dictionary)
    output_dir = ROOT / args.output_dir if not Path(args.output_dir).is_absolute() else Path(args.output_dir)
    report_path = ROOT / args.report if not Path(args.report).is_absolute() else Path(args.report)

    answer_list = load_answers(answers_path)
    if args.limit and args.limit > 0:
        answer_list = answer_list[:args.limit]
        print(f"Limiting benchmark to first {len(answer_list)} answers")

    word_list = get_word_list(dictionary_path)
    stats = LetterStats(word_list)
    recommender = WordRecommender(word_list, stats)

    results: list[GameResult] = []
    for index, answer in enumerate(answer_list, start=1):
        result = run_game(answer, word_list, recommender, args.max_rounds, args.strategy)
        results.append(result)
        if index % 100 == 0:
            print(f"Processed {index}/{len(answer_list)} answers")

    summary = aggregate_results(results, args.max_rounds, args.strategy)
    raw_path = output_dir / "wordle_benchmark_raw.jsonl"
    summary_path = output_dir / "wordle_benchmark_summary.json"

    write_jsonl(raw_path, results)
    write_summary(summary_path, summary)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_markdown(summary, answers_path, raw_path, summary_path), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Wrote raw trace to {raw_path}")
    print(f"Wrote summary to {summary_path}")
    print(f"Wrote report to {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
