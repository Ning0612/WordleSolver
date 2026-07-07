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

## Summary

| Metric | Value |
|---|---:|
| Dataset size | 2309 |
| Strategy | split-quality |
| Solved | 2271 |
| Failed | 38 |
| Success rate | 98.35% |
| Average attempts (solved) | 4.256715 |
| Median attempts (solved) | 4 |
| Average attempts (all) | 4.301862 |

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
