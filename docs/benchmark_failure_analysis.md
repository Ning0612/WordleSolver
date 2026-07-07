# Benchmark Failure Analysis

## Baseline

The original benchmark used a strict candidate-first strategy: always choose the
top candidate recommendation when candidates are available, and use exploration
only when no candidate recommendation exists.

Full run on 2,309 answer entries:

| Strategy | Solved | Failed | Success rate |
|---|---:|---:|---:|
| candidate-first | 2,121 | 188 | 91.86% |
| adaptive-exploration | 2,227 | 82 | 96.45% |
| split-quality | 2,271 | 38 | 98.35% |

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

## Optimization Plan

1. Improve dictionary coverage.
   The benchmark has 9 answer entries missing from `data/five_letter_words.txt`.
   Add a legal way to include benchmark-only answer words locally, or document
   coverage-adjusted metrics separately from strict dictionary-backed metrics.

2. Add local-only candidate diagnostics.
   The current trace records candidate counts, but not the candidate set. A
   local-only diagnostic mode can record candidates and split partitions for the
   remaining 14 solvable failures without committing answer data.

3. Separate answer candidates from dictionary-only guesses.
   The current dictionary contains many valid guess words that are unlikely
   answer words. Keeping a local, uncommitted answer list for benchmarking while
   using a public answer-prior file or frequency prior would reduce guesses such
   as obscure dictionary-only words.

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
