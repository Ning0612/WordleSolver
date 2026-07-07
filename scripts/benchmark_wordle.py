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
import time
from collections import Counter
from dataclasses import asdict, dataclass
from functools import lru_cache
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
SPLIT_QUALITY_THRESHOLD = 20


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "n/a"
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{secs:06.3f}"


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


@dataclass
class DiagnosticWriter:
    path: Path

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("w", encoding="utf-8", newline="\n")

    def write(self, record: dict) -> None:
        self._fh.write(json.dumps(record, ensure_ascii=False))
        self._fh.write("\n")

    def close(self) -> None:
        self._fh.close()


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


@lru_cache(maxsize=None)
def feedback_key(guess: str, answer: str) -> tuple[str, ...]:
    return tuple(color.value for color in simulate_feedback(guess, answer))


def duplicate_probe_score(guess: str, candidates: list[str]) -> int:
    varying_letters = set()
    for letter in "abcdefghijklmnopqrstuvwxyz":
        counts = {candidate.count(letter) for candidate in candidates}
        if len(counts) > 1:
            varying_letters.add(letter)

    if not varying_letters:
        return 0

    unique_hits = sum(1 for letter in set(guess) if letter in varying_letters)
    repeated_hits = sum(guess.count(letter) - 1 for letter in varying_letters if guess.count(letter) > 1)
    return unique_hits * 2 + repeated_hits


def split_quality_choice(
    recommendations: dict[str, list[tuple[str, float]]],
    candidates: list[str],
    full_dictionary: list[str],
    round_number: int,
    max_rounds: int,
    constraint: Constraint,
) -> GuessChoice | None:
    if len(candidates) > SPLIT_QUALITY_THRESHOLD:
        return None

    rounds_remaining = max_rounds - round_number + 1
    candidate_rank = {word: rank for rank, word in enumerate(candidates)}
    candidate_words = list(candidates)

    if rounds_remaining <= 2 or len(candidates) <= rounds_remaining:
        guess_pool = [(word, "candidate", candidate_rank[word]) for word in candidate_words]
    else:
        exploration_words = [
            word
            for word in full_dictionary
            if word not in candidate_rank
        ]
        guess_pool = [(word, "candidate", candidate_rank[word]) for word in candidate_words]
        guess_pool.extend(
            (word, "exploration", len(candidate_words) + rank)
            for rank, word in enumerate(exploration_words)
        )

    if not guess_pool:
        return None

    best: tuple[tuple[float, ...], GuessChoice] | None = None
    for word, category, rank in guess_pool:
        buckets: Counter[tuple[str, ...]] = Counter()
        best_worst = best[0][0] if best is not None else None
        abandoned = False
        for answer in candidates:
            key = feedback_key(word, answer)
            buckets[key] += 1
            if best_worst is not None and buckets[key] > best_worst:
                abandoned = True
                break
        if abandoned:
            continue

        worst_case = max(buckets.values())
        expected_remaining = sum(size * size for size in buckets.values()) / len(candidates)
        singleton_buckets = sum(1 for size in buckets.values() if size == 1)
        solved_now = 1 if word in candidate_rank else 0
        duplicate_score = duplicate_probe_score(word, candidates)
        split_count = len(buckets)

        sort_key = (
            worst_case,
            expected_remaining,
            -singleton_buckets,
            -duplicate_score,
            -solved_now,
            -split_count,
            0 if category == "candidate" else 1,
            rank,
        )
        choice = GuessChoice(
            word=word,
            category=category,
            reason=f"split-quality:w{worst_case}:d{duplicate_score}",
        )
        if best is None or sort_key < best[0]:
            best = (sort_key, choice)

    return best[1] if best else None


def select_guess(
    recommendations: dict[str, list[tuple[str, float]]],
    fallback_pool: list[str],
    candidates: list[str],
    full_dictionary: list[str],
    constraint: Constraint,
    round_number: int,
    max_rounds: int,
    strategy: str,
) -> GuessChoice:
    if strategy == "split-quality":
        split_choice = split_quality_choice(
            recommendations=recommendations,
            candidates=candidates,
            full_dictionary=full_dictionary,
            round_number=round_number,
            max_rounds=max_rounds,
            constraint=constraint,
        )
        if split_choice is not None:
            return split_choice

    if strategy in {"adaptive-exploration", "split-quality"}:
        rounds_remaining = max_rounds - round_number + 1
        should_explore = (
            rounds_remaining > 1
            and len(candidates) > rounds_remaining
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
    diagnostic_writer: DiagnosticWriter | None = None,
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
            full_dictionary=word_list,
            constraint=active_constraint,
            round_number=round_number,
            max_rounds=max_rounds,
            strategy=strategy,
        )
        guess = choice.word
        guesses.append(guess)

        if diagnostic_writer is not None and len(candidates) <= SPLIT_QUALITY_THRESHOLD:
            diagnostic_writer.write(
                {
                    "answer": answer,
                    "round": round_number,
                    "strategy": strategy,
                    "candidate_count": len(candidates),
                    "candidates": candidates,
                    "choice": asdict(choice),
                    "top_candidates": recommendations["candidates"][:5],
                    "top_explorations": recommendations["explorations"][:5],
                }
            )

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


def duplicate_extra_count(word: str) -> int:
    counts = Counter(word)
    return sum(count - 1 for count in counts.values() if count > 1)


def failure_template(result: GameResult) -> str:
    last_round = result.rounds[-1]
    return "".join(
        letter if color == "green" else "_"
        for letter, color in zip(last_round.guess, last_round.feedback)
    )


def summarize_results(results: list[GameResult], max_rounds: int, strategy: str) -> dict:
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


def build_diagnostics(results: list[GameResult]) -> dict:
    failed = [r for r in results if not r.solved]
    choice_counts = Counter(choice for r in results for choice in (round.choice for round in r.rounds))

    return {
        "choice_counts": dict(sorted(choice_counts.items())),
        "trap_risk_games_solved": sum(
            r.solved and any(round.choice == "exploration:trap-risk" for round in r.rounds)
            for r in results
        ),
        "trap_risk_games_failed": sum(
            (not r.solved) and any(round.choice == "exploration:trap-risk" for round in r.rounds)
            for r in results
        ),
        "failure_duplicate_extra_letters": {
            str(key): value
            for key, value in sorted(Counter(duplicate_extra_count(r.answer) for r in failed).items())
        },
        "failure_last_candidate_count_top": {
            str(key): value
            for key, value in Counter(r.rounds[-1].candidate_count for r in failed).most_common(10)
        },
        "failure_template_top": dict(Counter(failure_template(r) for r in failed).most_common(10)),
        "failure_suffix2_top": dict(Counter(r.answer[3:] for r in failed).most_common(10)),
    }


def build_strategy_comparison(
    current_results: list[GameResult],
    baseline_results: list[GameResult],
    max_rounds: int,
) -> dict:
    current_by_answer = {result.answer: result for result in current_results}
    baseline_by_answer = {result.answer: result for result in baseline_results}

    rescued = [
        answer
        for answer, baseline in baseline_by_answer.items()
        if not baseline.solved and current_by_answer[answer].solved
    ]
    regressed_to_failure = [
        answer
        for answer, baseline in baseline_by_answer.items()
        if baseline.solved and not current_by_answer[answer].solved
    ]
    improved_attempts = [
        answer
        for answer, baseline in baseline_by_answer.items()
        if current_by_answer[answer].attempts < baseline.attempts
    ]
    worsened_attempts = [
        answer
        for answer, baseline in baseline_by_answer.items()
        if current_by_answer[answer].attempts > baseline.attempts
    ]

    baseline_summary = summarize_results(baseline_results, max_rounds, "candidate-first")
    baseline_summary.pop("failure_cases", None)

    return {
        "baseline": baseline_summary,
        "rescued_from_baseline": len(rescued),
        "regressed_to_failure": len(regressed_to_failure),
        "net_solved_delta": len(rescued) - len(regressed_to_failure),
        "improved_attempts": len(improved_attempts),
        "worsened_attempts": len(worsened_attempts),
    }


def aggregate_results(
    results: list[GameResult],
    max_rounds: int,
    strategy: str,
    baseline_results: list[GameResult] | None = None,
    dictionary_coverage: dict | None = None,
    duration_seconds: float | None = None,
) -> dict:
    summary = summarize_results(results, max_rounds, strategy)
    if duration_seconds is not None:
        summary["benchmark_duration_seconds"] = round(duration_seconds, 3)
        summary["avg_duration_seconds_per_word"] = round(duration_seconds / len(results), 6) if results else None
    summary["diagnostics"] = build_diagnostics(results)
    if dictionary_coverage is not None:
        summary["dictionary_coverage"] = dictionary_coverage
    if baseline_results is not None:
        summary["comparison"] = build_strategy_comparison(results, baseline_results, max_rounds)
    return summary


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
            ("Dictionary mode", summary.get("dictionary_coverage", {}).get("dictionary_mode", "strict")),
            ("Strategy", summary["strategy"]),
            ("Solved", summary["solved"]),
            ("Failed", summary["failed"]),
            ("Success rate", f'{summary["success_rate"] * 100:.2f}%'),
            ("Average attempts (solved)", summary["average_attempts_solved"]),
            ("Median attempts (solved)", summary["median_attempts_solved"]),
            ("Average attempts (all)", summary["average_attempts_all"]),
            ("Benchmark duration", format_duration(summary.get("benchmark_duration_seconds"))),
            ("Avg duration per word", summary.get("avg_duration_seconds_per_word", "n/a")),
        ]
    )

    dist_lines = "\n".join(f"- `{k}`: {v}" for k, v in summary["distribution"].items())
    coverage = summary.get("dictionary_coverage", {})
    coverage_lines = "\n".join(
        f"- {label}: `{value}`"
        for label, value in [
            ("Answers not in dictionary", coverage.get("answers_not_in_dictionary", "n/a")),
            ("Failed answers not in dictionary", coverage.get("failed_answers_not_in_dictionary", "n/a")),
            ("Dictionary mode", coverage.get("dictionary_mode", "n/a")),
            ("Include missing answers", coverage.get("include_missing_answers", "n/a")),
            ("Base dictionary size", coverage.get("base_dictionary_size", "n/a")),
            ("Benchmark dictionary size", coverage.get("benchmark_dictionary_size", "n/a")),
        ]
    )
    comparison = summary.get("comparison", {})
    baseline = comparison.get("baseline", {})
    if baseline:
        comparison_lines = f"""| Strategy | Solved | Failed | Success rate |
|---|---:|---:|---:|
| {baseline["strategy"]} | {baseline["solved"]} | {baseline["failed"]} | {baseline["success_rate"] * 100:.2f}% |
| {summary["strategy"]} | {summary["solved"]} | {summary["failed"]} | {summary["success_rate"] * 100:.2f}% |

- Rescued from baseline: `{comparison["rescued_from_baseline"]}`
- Regressed to failure: `{comparison["regressed_to_failure"]}`
- Net solved delta: `{comparison["net_solved_delta"]}`
"""
    else:
        comparison_lines = "No baseline comparison was requested."

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

1. Activate the project virtual environment.

2. Build the answer list:

```bash
python scripts/build_wordle_answers.py --source-repo <path-to-wordle-answers> --output data/wordle_answers.txt
```

3. Run the benchmark:

```bash
python scripts/benchmark_wordle.py --answers data/wordle_answers.txt --strategy split-quality --compare-baseline --output-dir data/benchmark --report docs/benchmark.md
```

Coverage-adjusted local runs must use a separate output directory because they
add missing benchmark answers to the in-memory dictionary:

```bash
python scripts/benchmark_wordle.py --answers data/wordle_answers.txt --strategy split-quality --compare-baseline --include-missing-answers --output-dir data/benchmark/coverage_adjusted --report data/benchmark/coverage_adjusted/benchmark.md --diagnostics-dir data/benchmark/diagnostics
```

Benchmark duration excludes final JSON/Markdown writing. When
`--compare-baseline` is used, it includes both the selected strategy pass and
the baseline comparison pass.

## Summary

| Metric | Value |
|---|---:|
{rows}

## Distribution

{dist_lines}

## Dictionary Coverage

{coverage_lines}

## Baseline Comparison

{comparison_lines}

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
    parser.add_argument(
        "--report",
        default=None,
        help="Markdown report path. Defaults to docs/benchmark.md for the default output dir, otherwise <output-dir>/benchmark.md.",
    )
    parser.add_argument("--max-rounds", type=int, default=MAX_ROUNDS_DEFAULT)
    parser.add_argument("--limit", type=int, default=0, help="Optional cap on the number of answers to benchmark.")
    parser.add_argument(
        "--include-missing-answers",
        action="store_true",
        help="Coverage-adjusted local run: add benchmark answers missing from the dictionary to the in-memory word list.",
    )
    parser.add_argument(
        "--diagnostics-dir",
        default=None,
        help="Optional local-only directory for small-candidate diagnostic JSONL output.",
    )
    parser.add_argument(
        "--strategy",
        choices=("candidate-first", "adaptive-exploration", "split-quality"),
        default="split-quality",
        help="Guess selection strategy for candidate/exploration recommendations.",
    )
    parser.add_argument(
        "--compare-baseline",
        action="store_true",
        help="Also run candidate-first and include aggregate comparison metrics.",
    )
    args = parser.parse_args()

    answers_path = ROOT / args.answers if not Path(args.answers).is_absolute() else Path(args.answers)
    dictionary_path = ROOT / args.dictionary if not Path(args.dictionary).is_absolute() else Path(args.dictionary)
    output_dir = ROOT / args.output_dir if not Path(args.output_dir).is_absolute() else Path(args.output_dir)
    if args.report is None:
        report_path = ROOT / "docs" / "benchmark.md" if args.output_dir == "data/benchmark" else output_dir / "benchmark.md"
    else:
        report_path = ROOT / args.report if not Path(args.report).is_absolute() else Path(args.report)
    default_output_dir = ROOT / "data" / "benchmark"
    default_report_path = ROOT / "docs" / "benchmark.md"
    if args.include_missing_answers and (
        output_dir.resolve() == default_output_dir.resolve()
        or report_path.resolve() == default_report_path.resolve()
    ):
        parser.error(
            "--include-missing-answers is a coverage-adjusted local run; "
            "use a separate --output-dir and --report instead of overwriting strict benchmark artifacts."
        )

    answer_list = load_answers(answers_path)
    if args.limit and args.limit > 0:
        answer_list = answer_list[:args.limit]
        print(f"Limiting benchmark to first {len(answer_list)} answers")

    base_word_list = get_word_list(dictionary_path)
    base_dictionary_set = set(base_word_list)
    missing_answers = set(answer_list) - base_dictionary_set
    word_list = sorted(base_dictionary_set | missing_answers) if args.include_missing_answers else base_word_list
    stats = LetterStats(word_list)
    recommender = WordRecommender(word_list, stats)

    diagnostic_writer = None
    if args.diagnostics_dir is not None:
        diagnostics_dir = ROOT / args.diagnostics_dir if not Path(args.diagnostics_dir).is_absolute() else Path(args.diagnostics_dir)
        benchmark_dir = ROOT / "data" / "benchmark"
        if is_relative_to(diagnostics_dir, ROOT):
            try:
                diagnostics_parts = diagnostics_dir.resolve().relative_to(benchmark_dir.resolve()).parts
            except ValueError:
                diagnostics_parts = ()
            if "diagnostics" not in diagnostics_parts:
                parser.error(
                    "--diagnostics-dir writes answer/candidate traces; repo-local diagnostics must be under "
                    "data/benchmark/.../diagnostics so generated JSONL remains ignored."
                )
        diagnostic_writer = DiagnosticWriter(diagnostics_dir / "wordle_small_set_diagnostics.jsonl")

    benchmark_start = time.perf_counter()
    results: list[GameResult] = []
    try:
        for index, answer in enumerate(answer_list, start=1):
            result = run_game(answer, word_list, recommender, args.max_rounds, args.strategy, diagnostic_writer)
            results.append(result)
            if index % 100 == 0:
                print(f"Processed {index}/{len(answer_list)} answers")
    finally:
        if diagnostic_writer is not None:
            diagnostic_writer.close()

    baseline_results = None
    if args.compare_baseline and args.strategy != "candidate-first":
        baseline_results = []
        for index, answer in enumerate(answer_list, start=1):
            result = run_game(answer, word_list, recommender, args.max_rounds, "candidate-first")
            baseline_results.append(result)
            if index % 100 == 0:
                print(f"Processed baseline {index}/{len(answer_list)} answers")
    benchmark_duration_seconds = time.perf_counter() - benchmark_start

    failed_answers = {result.answer for result in results if not result.solved}
    dictionary_coverage = {
        "answers_not_in_dictionary": len(missing_answers),
        "failed_answers_not_in_dictionary": len(missing_answers & failed_answers),
        "dictionary_mode": "coverage-adjusted" if args.include_missing_answers else "strict",
        "include_missing_answers": args.include_missing_answers,
        "benchmark_dictionary_size": len(word_list),
        "base_dictionary_size": len(base_word_list),
    }

    summary = aggregate_results(
        results,
        args.max_rounds,
        args.strategy,
        baseline_results,
        dictionary_coverage,
        benchmark_duration_seconds,
    )
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
