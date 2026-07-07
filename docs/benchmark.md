# Wordle Solver Benchmark

## Dataset

- Answer list: `data/wordle_answers.txt` (generated locally; not committed)
- Raw trace: `data/benchmark/wordle_benchmark_raw.jsonl` (generated locally; not committed)
- Summary JSON: `data/benchmark/wordle_benchmark_summary.json`

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

## Benchmark Modes

| Mode | Candidate answer pool | Purpose |
|---|---|---|
| Strict dictionary | Public dictionary | Public benchmark for the committed solver dictionary. |
| Coverage-adjusted | Public dictionary plus locally generated missing answers | Separates dictionary coverage failures from strategy failures. |
| Answer-prior local | Locally generated answer list | Diagnostic run for answer-likelihood effects; the answer list remains uncommitted. |

## Summary

| Metric | Value |
|---|---:|
| Dataset size | 2309 |
| Dictionary mode | strict |
| Answer candidate pool | dictionary |
| Strategy | split-quality |
| Solved | 2271 |
| Failed | 38 |
| Success rate | 98.35% |
| Avg completed rounds | 4.256715 |
| Median attempts (solved) | 4 |
| Avg all rounds | 4.301862 |
| Benchmark duration | 00:13:25.133 |
| Avg duration per word | 0.348693 |

## Distribution

- `1`: 0
- `2`: 31
- `3`: 304
- `4`: 1097
- `5`: 729
- `6`: 110
- `7`: 38

## Dictionary Coverage

- Answers not in dictionary: `9`
- Failed answers not in dictionary: `9`
- Dictionary mode: `strict`
- Answer candidate pool: `dictionary`
- Answer candidate pool size: `15921`
- Include missing answers: `False`
- Base dictionary size: `15921`
- Benchmark dictionary size: `15921`

## Baseline Comparison

| Strategy | Solved | Failed | Success rate |
|---|---:|---:|---:|
| candidate-first | 2121 | 188 | 91.86% |
| split-quality | 2271 | 38 | 98.35% |

- Rescued from baseline: `157`
- Regressed to failure: `7`
- Net solved delta: `150`


## Failure Cases

| answer | guesses | rounds |
|---|---|---:|
| fixer | cares, tiver, liner, bider, hiper, mixer | 6 |
| homer | cares, tiver, foder, honer, hoker, holer | 6 |
| power | cares, tiver, foder, honer, bower, jower | 6 |
| poker | cares, tiver, foder, honer, bower, moper | 6 |
| aging | cares, donia, ligan, whipt, aking, axing | 6 |
| queer | cares, tiver, foder, huger, puler, buyer | 6 |
| rehab | cares, drate, reban | 3 |
| ruler | cares, tiver, foder, huger, puler, euler | 6 |
| joker | cares, tiver, foder, honer, bower, moper | 6 |
| geeky | cares, boite, wendy, kelpy, yeuky | 5 |
| amass | cares, plats, khans, quads, ogams, amaas | 6 |
| jelly | cares, boite, wendy, kelpy, felly, gelly | 6 |
| lower | cares, tiver, foder, honer, bower, jower | 6 |
| penne | cares, boite, fudge, helve, neeze | 5 |
| ramen | cares, taver, midgy, ramex, ramee | 5 |
| sneer | cares, soter, sider, whelp, skeer, smeer | 6 |
| wager | cares, taver, lager, reefy, jager, pager | 6 |
| wider | cares, tiver, liner, bider, hider, mider | 6 |
| detox | cares, boite, demot | 3 |
| wight | cares, bolty, pight, hadnt, fight, might | 6 |
