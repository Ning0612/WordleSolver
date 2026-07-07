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
python scripts/benchmark_wordle.py --answers data/wordle_answers.txt --strategy adaptive-exploration --compare-baseline --output-dir data/benchmark --report docs/benchmark.md
```

## Summary

| Metric | Value |
|---|---:|
| Dataset size | 2309 |
| Strategy | adaptive-exploration |
| Solved | 2227 |
| Failed | 82 |
| Success rate | 96.45% |
| Average attempts (solved) | 4.416255 |
| Median attempts (solved) | 4 |
| Average attempts (all) | 4.508012 |

## Distribution

- `1`: 0
- `2`: 33
- `3`: 342
- `4`: 853
- `5`: 663
- `6`: 336
- `7`: 82

## Failure Cases

| answer | guesses | rounds |
|---|---|---:|
| marry | cares, bardy, marly, pinto, gujar, marvy | 6 |
| booby | cares, bolty, fundi, whomp, gooky, boozy | 6 |
| stout | cares, soily, shout, spong, umbos, skout | 6 |
| hatch | cares, macho, latch, gundi, pawky, batch | 6 |
| jaunt | cares, manly, baton, daunt, hafiz, gaunt | 6 |
| craze | cares, crane, modif, gulph, bawty, crake | 6 |
| ferry | cares, bergy, polki, thund, jewry, merry | 6 |
| heist | cares, stile, deist, gumbo, kevyn, feist | 6 |
| zesty | cares, stile, guest, festy, whomp, nesty | 6 |
| glass | cares, plats, flans, bodhi, kumys, slags | 6 |
| sever | cares, soter, sider, glyph, unweb, seker | 6 |
| agape | cares, beany, glave, image, agate, agade | 6 |
| power | cares, tiver, foder, honer, bower, jower | 6 |
| coyly | cares, coiny, bumph, godly, flowk, colly | 6 |
| taunt | cares, manly, baton, daunt, hafiz, gaunt | 6 |
| class | cares, chads, blink, jumpy, flogs, claws | 6 |
| ionic | cares, pinch, monic, tubig, zinky, nonic | 6 |
| carry | cares, carob, midgy, fulth, prank, carvy | 6 |
| crave | cares, crane, modif, gulph, bawty, crake | 6 |
| aging | cares, donia, ligan, aking, upbay, ating | 6 |
