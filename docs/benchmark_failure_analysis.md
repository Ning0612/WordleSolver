# Benchmark Failure Analysis

For the stage-by-stage benchmark score history, see
[`benchmark_history.md`](benchmark_history.md).

## Baseline

The original benchmark used a strict candidate-first strategy: always choose the
top candidate recommendation when candidates are available, and use exploration
only when no candidate recommendation exists.

Full strict dictionary run on 2,309 answer entries:

| Strategy | Solved | Failed | Success rate | Avg completed rounds | Avg all rounds |
|---|---:|---:|---:|---:|---:|
| candidate-first | 2,121 | 188 | 91.86% | 4.328147 | 4.545691 |
| adaptive-exploration | 2,227 | 82 | 96.45% | 4.416255 | 4.508012 |
| split-quality | 2,271 | 38 | 98.35% | 4.256715 | 4.301862 |

Current diagnostic modes:

| Mode | Candidate answer pool | Solved | Failed | Success rate | Avg completed rounds | Avg all rounds | Internal duration |
|---|---|---:|---:|---:|---:|---:|---:|
| Strict dictionary | Public dictionary | 2,271 | 38 | 98.35% | 4.256715 | 4.301862 | 00:13:25.133 |
| Coverage-adjusted | Public dictionary plus 9 local missing answers | 2,280 | 29 | 98.74% | 4.259649 | 4.294067 | 00:13:25.843 |
| Answer-prior local | Generated local answer list | 2,309 | 0 | 100.00% | 3.542659 | 3.542659 | 00:07:20.284 |

The current strict split-quality report records 00:13:25.133 internal benchmark
duration, or 0.348693 seconds per answer entry. A separate coverage-adjusted
local run with missing benchmark answers added to the in-memory dictionary
solves 2,280 entries, fails 29, and records 00:13:25.843 internal duration
(0.349001 seconds per entry).

An answer-prior local run that uses the generated local answer list as the
candidate answer pool solves all 2,309 entries in 00:07:20.284 internal duration
(0.190682 seconds per entry). This is diagnostic evidence, not the strict
public benchmark, because the answer list remains generated locally and
uncommitted.

## Implemented Strategy

`split-quality` keeps candidate-first behavior while the candidate set is large.
When the current candidate set has at most 20 words, it evaluates possible
guesses by simulated Wordle feedback partitions over the current candidates:

- Minimize worst-case remaining candidates.
- Then minimize expected remaining candidates.
- Then maximize singleton buckets.
- Then prefer guesses that probe duplicate-count ambiguity.
- Then prefer actual candidates and stable dictionary order.

When the remaining candidate count is small enough to enumerate within the
remaining rounds, the strategy only chooses actual candidates. This prevents
information-only exploration from wasting a round when straightforward candidate
enumeration can still solve the puzzle.

## Observed Impact

Against the original 188 failed answers:

- 157 previously failed answers are solved by the split-quality strategy.
- 7 previously solved answers regress to failure.
- Net improvement is 150 additional solved answers.
- Overall failures drop from 188 to 38.

The split-quality run improves 664 answers by attempt count and worsens 338 by
attempt count. It optimizes solve rate first; average solved attempts also
improves from 4.328147 to 4.256715.

## Remaining Failure Patterns

The 38 remaining failures include 9 answers that are not present in the solver
dictionary. Those are not solvable by the current dictionary-backed strategy.
Among all 38 failures, duplicate-letter cases are still visible but no longer
dominate the result:

| Duplicate extra letters in answer | Failed count |
|---|---:|
| 0 | 19 |
| 1 | 16 |
| 2 | 3 |

Last-round candidate counts show many failures are still near misses:

| Last candidate count | Failed count |
|---|---:|
| 3 | 12 |
| 2 | 8 |
| 5 | 5 |
| 1 | 4 |
| 12 | 3 |

The most common suffix among failures is `er` with 19 cases. This suggests the
remaining failures are still concentrated in shared-structure ambiguity where a
one-step split-quality choice may not be enough, especially when the answer is
missing from the solver dictionary or the cluster needs deeper lookahead.

The answer-prior local run removes these failures, which indicates the dominant
root cause is not split-quality's feedback partitioning. The stricter dictionary
candidate pool includes many legal guess words that are unlikely answers, and
those obscure candidates outrank common answer words in the final 2-5 candidate
endgame.

## Optimization Plan

1. Improve dictionary coverage.
   The benchmark has 9 answer entries missing from `data/five_letter_words.txt`.
   `--include-missing-answers` now supports a separate coverage-adjusted local
   run without committing the full answer list or raw trace.

2. Add local-only candidate diagnostics.
   `--diagnostics-dir data/benchmark/diagnostics` records candidate sets and
   choices for small-candidate rounds into an ignored local JSONL file.

3. Separate answer candidates from dictionary-only guesses.
   The current dictionary contains many valid guess words that are unlikely
   answer words. The local `--answer-candidate-pool benchmark` run confirms this
   direction by solving all entries. The production-safe version should use a
   public answer-prior file or frequency prior rather than committing the local
   benchmark answer list.

4. Evaluate deeper search for the final hard clusters.
   Remaining failures such as `_ower` and `_o_er` patterns may need a limited
   two-ply lookahead rather than one-step minimax.

## Review / Verification Workflow

Future benchmark strategy changes should be checked by independent Codex
sub-agents before finalizing:

- Reviewer: inspect implementation, benchmark claims, documentation wording, and
  data-publication risk.
- Verifier: rerun targeted validation, confirm generated answer lists and raw
  traces remain untracked, and compare benchmark summary/report consistency.
