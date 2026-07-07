# Wordle Solver Benchmark

## Dataset

- Answer list: `data/wordle_answers.txt` (generated locally; not committed)
- Raw trace: `data/benchmark/answer_prior/wordle_benchmark_raw.jsonl` (generated locally; not committed)
- Summary JSON: `data/benchmark/answer_prior/wordle_benchmark_summary.json`

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

Answer-prior local runs use the generated local answer list as the candidate
answer pool while keeping the public dictionary available for exploration
guesses:

```bash
python scripts/benchmark_wordle.py --answers data/wordle_answers.txt --strategy split-quality --compare-baseline --include-missing-answers --answer-candidate-pool benchmark --output-dir data/benchmark/answer_prior --report data/benchmark/answer_prior/benchmark.md --diagnostics-dir data/benchmark/answer_prior/diagnostics
```

Benchmark duration excludes final JSON/Markdown writing. When
`--compare-baseline` is used, it includes both the selected strategy pass and
the baseline comparison pass.

## Summary

| Metric | Value |
|---|---:|
| Dataset size | 2309 |
| Dictionary mode | coverage-adjusted |
| Answer candidate pool | benchmark |
| Strategy | split-quality |
| Solved | 2309 |
| Failed | 0 |
| Success rate | 100.00% |
| Average attempts (solved) | 3.542659 |
| Median attempts (solved) | 4 |
| Average attempts (all) | 3.542659 |
| Benchmark duration | 00:07:20.284 |
| Avg duration per word | 0.190682 |

## Distribution

- `1`: 1
- `2`: 99
- `3`: 976
- `4`: 1120
- `5`: 105
- `6`: 8
- `7`: 0

## Dictionary Coverage

- Answers not in dictionary: `9`
- Failed answers not in dictionary: `0`
- Dictionary mode: `coverage-adjusted`
- Answer candidate pool: `benchmark`
- Answer candidate pool size: `2309`
- Include missing answers: `True`
- Base dictionary size: `15921`
- Benchmark dictionary size: `15930`

## Baseline Comparison

| Strategy | Solved | Failed | Success rate |
|---|---:|---:|---:|
| candidate-first | 2292 | 17 | 99.26% |
| split-quality | 2309 | 0 | 100.00% |

- Rescued from baseline: `17`
- Regressed to failure: `0`
- Net solved delta: `17`


## Failure Cases

| answer | guesses | rounds |
|---|---|---:|
| - | - | - |
