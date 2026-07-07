# Wordle Solver Benchmark

## Dataset

- Answer list: `data/wordle_answers.txt` (generated locally; not committed)
- Raw trace: `data/benchmark/wordle_benchmark_raw.jsonl` (generated locally; not committed)
- Summary JSON: `data/benchmark/wordle_benchmark_summary.json`

## Reproducibility

1. Build the answer list:

```bash
.\.venv\bin\python.exe scripts\build_wordle_answers.py --source-repo <path-to-wordle-answers> --output data\wordle_answers.txt
```

2. Run the benchmark:

```bash
.\.venv\bin\python.exe scripts\benchmark_wordle.py --answers data\wordle_answers.txt --output-dir data\benchmark --report docs\benchmark.md
```

## Summary

| Metric | Value |
|---|---:|
| Dataset size | 2309 |
| Solved | 2121 |
| Failed | 188 |
| Success rate | 91.86% |
| Average attempts (solved) | 4.328147 |
| Median attempts (solved) | 4 |
| Average attempts (all) | 4.545691 |

## Distribution

- `1`: 0
- `2`: 33
- `3`: 378
- `4`: 846
- `5`: 588
- `6`: 276
- `7`: 188

## Failure Cases

| answer | guesses | rounds |
|---|---|---:|
| sissy | cares, soily, sinky, sixty, sippy, sibby | 6 |
| marry | cares, bardy, marly, marty, marvy, maray | 6 |
| staff | cares, shant, stail, staup, stagy, staab | 6 |
| paper | cares, taver, lager, waker, hayer, japer | 6 |
| crazy | cares, chark, craig, crawl, crany, crapy | 6 |
| linen | cares, toled, gimel, lifen, liken, liven | 6 |
| booby | cares, bolty, boody, booky, boomy, boozy | 6 |
| stout | cares, soily, shout, skout, snout, spout | 6 |
| crass | cares, crabs, crags, crams, craps, craws | 6 |
| start | cares, spart, skart, slart, smart, swart | 6 |
| goner | cares, tiver, foder, honer, boner, moner | 6 |
| gamma | cares, manly, tambo, damia, hamza, pampa | 6 |
| hatch | cares, macho, latch, batch, datch, gatch | 6 |
| tweed | cares, toled, tined, tubed, typed, tewed | 6 |
| jaunt | cares, manly, baton, daunt, gaunt, haunt | 6 |
| finer | cares, tiver, liner, diner, piner, miner | 6 |
| surer | cares, sired, strew, sorel, syren, sfree | 6 |
| craze | cares, crane, craie, crake, crape, crate | 6 |
| skill | cares, soily, shilf, stilb, spill, swill | 6 |
| dodge | cares, boite, molge, podge, fodge, hodge | 6 |
