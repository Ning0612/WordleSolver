# Wordle Solver Benchmark

## Dataset

- Answer list: `data/wordle_answers.txt` (generated locally; not committed)
- Raw trace: `data/benchmark/coverage_adjusted/wordle_benchmark_raw.jsonl` (generated locally; not committed)
- Summary JSON: `data/benchmark/coverage_adjusted/wordle_benchmark_summary.json`

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
| Dataset size | 2309 |
| Dictionary mode | coverage-adjusted |
| Strategy | split-quality |
| Solved | 2280 |
| Failed | 29 |
| Success rate | 98.74% |
| Average attempts (solved) | 4.259649 |
| Median attempts (solved) | 4.0 |
| Average attempts (all) | 4.294067 |
| Benchmark duration | 00:13:25.843 |
| Avg duration per word | 0.349001 |

## Distribution

- `1`: 0
- `2`: 31
- `3`: 304
- `4`: 1101
- `5`: 730
- `6`: 114
- `7`: 29

## Dictionary Coverage

- Answers not in dictionary: `9`
- Failed answers not in dictionary: `0`
- Dictionary mode: `coverage-adjusted`
- Include missing answers: `True`
- Base dictionary size: `15921`
- Benchmark dictionary size: `15930`

## Baseline Comparison

| Strategy | Solved | Failed | Success rate |
|---|---:|---:|---:|
| candidate-first | 2131 | 178 | 92.29% |
| split-quality | 2280 | 29 | 98.74% |

- Rescued from baseline: `156`
- Regressed to failure: `7`
- Net solved delta: `149`


## Failure Cases

| answer | guesses | rounds |
|---|---|---:|
| fixer | cares, tiver, liner, bider, hiper, mixer | 6 |
| homer | cares, tiver, foder, honer, hoker, holer | 6 |
| power | cares, tiver, foder, honer, bower, jower | 6 |
| poker | cares, tiver, foder, honer, bower, moper | 6 |
| aging | cares, donia, ligan, whipt, aking, axing | 6 |
| queer | cares, tiver, foder, huger, puler, buyer | 6 |
| ruler | cares, tiver, foder, huger, puler, euler | 6 |
| joker | cares, tiver, foder, honer, bower, moper | 6 |
| amass | cares, plats, khans, quads, ogams, amaas | 6 |
| jelly | cares, boite, wendy, kelpy, felly, gelly | 6 |
| lower | cares, tiver, foder, honer, bower, jower | 6 |
| sneer | cares, soter, sider, whelp, skeer, smeer | 6 |
| wager | cares, taver, lager, reefy, jager, pager | 6 |
| wider | cares, tiver, liner, bider, hider, mider | 6 |
| wight | cares, bolty, pight, hadnt, fight, might | 6 |
| piper | cares, tiver, liner, bider, hiper, wiper | 6 |
| riper | cares, tiver, liner, bider, hiper, wiper | 6 |
| navel | cares, paled, hamel, begat, favel, javel | 6 |
| maker | cares, taver, lager, waker, baker, daker | 6 |
| ninny | cares, bolty, dingy, kaphs, finny, jinny | 6 |
