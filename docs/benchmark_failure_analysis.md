# Benchmark Failure Analysis

## Baseline

The original benchmark used a strict candidate-first strategy: always choose the
top candidate recommendation when candidates are available, and use exploration
only when no candidate recommendation exists.

Full run on 2,309 answer entries:

| Strategy | Solved | Failed | Success rate |
|---|---:|---:|---:|
| candidate-first | 2,121 | 188 | 91.86% |
| adaptive-exploration | 2,183 | 126 | 94.54% |

## Implemented Strategy

`adaptive-exploration` keeps candidate-first behavior for normal rounds, but
switches to the top exploration recommendation when all of these are true:

- Remaining candidates exceed remaining rounds.
- Candidate count is at most 20.
- At least 3 green positions are already known.
- An exploration recommendation is available.

This targets common Wordle trap patterns where candidates share most positions
and candidate-first play burns one guess per remaining option.

## Observed Impact

Against the original 188 failed answers:

- 106 previously failed answers are solved by the adaptive strategy.
- 44 previously solved answers regress to failure.
- Net improvement is 62 additional solved answers.
- Overall failures drop from 188 to 126.

The adaptive run used `exploration:trap-risk` 1,067 times across the full
benchmark. It appeared in 610 solved games and 112 failed games.

## Remaining Failure Patterns

The 126 remaining failures still show heavy concentration in ambiguity and
duplicate-letter cases:

| Duplicate extra letters in answer | Failed count |
|---|---:|
| 0 | 42 |
| 1 | 68 |
| 2 | 15 |
| 3 | 1 |

Last-round candidate counts show many failures are still near misses:

| Last candidate count | Failed count |
|---|---:|
| 2 | 58 |
| 3 | 31 |
| 4 | 15 |
| 5 | 11 |

The most common suffix among failures is `er` with 31 cases. These are often
hard because many dictionary words share the same discovered structure while the
current scorer still ranks candidates and exploration words by heuristic score,
not by expected split quality.

## Optimization Plan

1. Add split-quality scoring for trap-risk rounds.
   For each exploration recommendation, simulate feedback against the current
   candidate set and choose the word with the lowest worst-case remaining
   candidates. Limit this to small candidate sets so runtime stays acceptable.

2. Penalize duplicate-ambiguous candidate guessing.
   When duplicate-letter uncertainty remains, prefer guesses that test both the
   duplicate and the alternative single-letter options.

3. Separate answer candidates from dictionary-only guesses.
   The current dictionary contains many valid guess words that are unlikely
   answer words. Keeping a local, uncommitted answer list for benchmarking while
   using a public answer-prior file or frequency prior would reduce guesses such
   as obscure dictionary-only words.

4. Track candidate set after each round in the raw trace.
   The current trace records candidate counts, but not the actual candidate set.
   A local-only diagnostic mode can record candidates to analyze individual
   failures without committing answer data.
