# Benchmark History

This page records benchmark scores by implementation stage. The full answer
list and raw trace are generated locally and intentionally not committed.

All rows use the same 2,309-entry local benchmark answer list.

Duration is wall-clock time for the reproducible benchmark command that
generates that stage's summary. Runs were re-measured locally on 2026-07-07
because the original stage records kept timestamps, not elapsed time.
The current generated benchmark reports also include an internal benchmark
duration that excludes final JSON/Markdown writing. When `--compare-baseline`
is used, the internal duration includes both the selected strategy pass and the
baseline comparison pass.

| Stage | Commit | Total duration | Avg duration / word | Strategy | Solved | Failed | Success rate | Avg attempts (solved) | Avg attempts (all) |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|
| Reproducible baseline | `111c9b2` | 00:03:35.401 | 0.093287s | `candidate-first` | 2,121 | 188 | 91.86% | 4.328147 | 4.545691 |
| Adaptive trap-risk exploration | `2a8d29a` | 00:07:42.932 | 0.200490s | `adaptive-exploration` | 2,227 | 82 | 96.45% | 4.416255 | 4.508012 |
| Small-set split quality | `a0a2f23` | 00:15:44.304 | 0.408966s | `split-quality` | 2,271 | 38 | 98.35% | 4.256715 | 4.301862 |

## Stage Notes

### Reproducible Baseline

Commit: `111c9b2 test: add reproducible wordle benchmark`

Total duration: 00:03:35.401

Average duration per word: 0.093287s

Changes:

- Added reproducible benchmark scripts.
- Generated local answer input from an external archive, but kept the full answer
  list and raw trace ignored/untracked.
- Used strict candidate-first selection: choose the top candidate whenever one
  is available.

Observed behavior:

- Success rate was 91.86%.
- Most failures were near misses caused by small candidate clusters, repeated
  letters, and shared patterns such as `_ower`, `_atch`, and `-er`.

### Adaptive Trap-Risk Exploration

Commit: `2a8d29a test: refine adaptive wordle benchmark analysis`

Total duration: 00:07:42.932

Average duration per word: 0.200490s

Changes:

- Added `adaptive-exploration`.
- When the candidate set was small, remaining candidates exceeded remaining
  rounds, and at least 3 green positions were known, the benchmark used an
  exploration recommendation to split trap patterns.
- Added safeguards so the final round and fully enumerable candidate sets use
  actual candidates instead of non-answer exploration guesses.
- Added tracked diagnostics and baseline comparison fields to the summary.

Observed behavior:

- Success rate improved from 91.86% to 96.45%.
- Failures dropped from 188 to 82.
- The improvement confirmed that the original candidate-first approach wasted
  guesses in small shared-template clusters.

### Small-Set Split Quality

Commit: `a0a2f23 test: add split-quality wordle benchmark strategy`

Total duration: 00:15:44.304

Average duration per word: 0.408966s

Changes:

- Added `split-quality` for candidate sets of at most 20 words.
- Uses the current candidate set as the answer hypothesis pool.
- Evaluates candidate and exploration guesses by simulated Wordle feedback
  partitions.
- Sorts by worst-case remaining candidates, expected remaining candidates,
  singleton buckets, duplicate-count probing, candidate preference, and stable
  order.
- Uses full-dictionary exploration candidates for split evaluation, while still
  forcing actual candidates when the remaining candidates can be enumerated in
  the remaining rounds.
- Added dictionary coverage diagnostics.

Observed behavior:

- Success rate improved from 96.45% to 98.35%.
- Failures dropped from 82 to 38.
- 9 benchmark answers are missing from the solver dictionary; those 9 failures
  are dictionary coverage failures rather than strategy failures.

## Current Interpretation

The current strict strategy solves 2,271 of 2,309 benchmark entries. Of the 38
failures, 9 are not present in `data/five_letter_words.txt`, leaving 29 failures
against answers that are representable by the solver dictionary.

A separate coverage-adjusted local run with `--include-missing-answers` solved
2,280 of 2,309 entries, failed 29, and took 00:13:25.843 internal benchmark
duration (0.349001s/word). This run adds the 9 missing benchmark answers to the
in-memory dictionary and is not the strict tracked benchmark.

The next useful work is likely dictionary coverage and local-only diagnostics
for the remaining hard clusters, rather than more one-step scoring tweaks.
