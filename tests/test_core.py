import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from benchmark_wordle import split_quality_choice  # noqa: E402
from constraints import Constraint, FeedbackColor, FeedbackRound  # noqa: E402
from solver import filter_candidates  # noqa: E402


class ConstraintTests(unittest.TestCase):
    def test_duplicate_feedback_sets_exact_count_and_excluded_positions(self):
        round_ = FeedbackRound(
            guess="speed",
            feedback=[
                FeedbackColor.GRAY,
                FeedbackColor.GRAY,
                FeedbackColor.YELLOW,
                FeedbackColor.GRAY,
                FeedbackColor.GRAY,
            ],
        )

        constraint = round_.to_constraint()

        self.assertEqual(constraint.letter_counts["e"], (1, 1))
        self.assertEqual(constraint.yellows["e"], {2, 3})
        self.assertEqual(
            filter_candidates(
                ["creep", "ember", "enter", "venom", "plumb", "steel", "below", "melon"],
                constraint,
            ),
            ["venom", "below", "melon"],
        )

    def test_filter_candidates_applies_green_yellow_and_gray_constraints(self):
        constraint = Constraint(
            greens={0: "c"},
            yellows={"r": {1}, "a": {2}},
            letter_counts={"c": (1, None), "r": (1, None), "a": (1, None), "n": (0, 0), "e": (0, 0)},
        )

        self.assertEqual(
            filter_candidates(["crane", "carby", "cairn", "cigar", "trace"], constraint),
            ["carby", "cigar"],
        )


class StrategyTests(unittest.TestCase):
    def test_split_quality_prefers_guess_that_splits_small_candidate_set(self):
        candidates = ["booby", "boozy"]
        full_dictionary = ["booby", "boozy", "ferry", "merry"]
        recommendations = {
            "candidates": [("booby", 100.0), ("boozy", 90.0)],
            "explorations": [("ferry", 10.0), ("merry", 9.0)],
        }

        choice = split_quality_choice(
            recommendations=recommendations,
            candidates=candidates,
            full_dictionary=full_dictionary,
            round_number=3,
            max_rounds=6,
            constraint=Constraint(),
        )

        self.assertIsNotNone(choice)
        self.assertIn(choice.word, candidates)
        self.assertTrue(choice.reason.startswith("split-quality:"))


class BenchmarkSmokeTests(unittest.TestCase):
    def test_benchmark_runs_with_public_safe_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            answers_path = tmp_path / "answers.txt"
            output_dir = tmp_path / "benchmark"
            report_path = tmp_path / "benchmark.md"
            answers_path.write_text("cigar\nrebut\nawake\n", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "benchmark_wordle.py"),
                    "--answers",
                    str(answers_path),
                    "--strategy",
                    "split-quality",
                    "--limit",
                    "3",
                    "--output-dir",
                    str(output_dir),
                    "--report",
                    str(report_path),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=True,
            )

            self.assertIn('"dataset_size": 3', result.stdout)
            summary = json.loads((output_dir / "wordle_benchmark_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["dataset_size"], 3)
            self.assertEqual(summary["strategy"], "split-quality")
            self.assertEqual(summary["dictionary_coverage"]["answers_not_in_dictionary"], 0)
            self.assertTrue((output_dir / "wordle_benchmark_raw.jsonl").exists())
            self.assertTrue(report_path.exists())


if __name__ == "__main__":
    unittest.main()
