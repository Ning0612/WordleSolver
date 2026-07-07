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
.\.venv\bin\python.exe scripts\benchmark_wordle.py --answers data\wordle_answers.txt --strategy adaptive-exploration --output-dir data\benchmark --report docs\benchmark.md
```

## Summary

| Metric | Value |
|---|---:|
| Dataset size | 2309 |
| Strategy | adaptive-exploration |
| Solved | 2183 |
| Failed | 126 |
| Success rate | 94.54% |
| Average attempts (solved) | 4.384333 |
| Median attempts (solved) | 4 |
| Average attempts (all) | 4.527068 |

## Distribution

- `1`: 0
- `2`: 33
- `3`: 342
- `4`: 853
- `5`: 663
- `6`: 292
- `7`: 126

## Failure Cases

| answer | guesses | rounds |
|---|---|---:|
| marry | cares, bardy, marly, pinto, gujar, wharf | 6 |
| paper | cares, taver, lager, waker, jupon, pamhy | 6 |
| booby | cares, bolty, fundi, whomp, gooky, oxboy | 6 |
| stout | cares, soily, shout, spong, umbos, jouks | 6 |
| hatch | cares, macho, latch, gundi, pawky, bafta | 6 |
| jaunt | cares, manly, baton, daunt, hafiz, juang | 6 |
| boozy | cares, bolty, fundi, whomp, gooky, oxboy | 6 |
| fixer | cares, tiver, liner, bider, humpy, forex | 6 |
| badly | cares, manly, gaily, bothy, upwax, baldy | 6 |
| finer | cares, tiver, liner, dhoby, pumex, finew | 6 |
| craze | cares, crane, modif, gulph, bawty, carve | 6 |
| ferry | cares, bergy, polki, thund, jewry, vefry | 6 |
| troll | cares, drony, grout, broth, tromp, kovil | 6 |
| moist | cares, soily, foist, bundh, twigs, josip | 6 |
| fewer | cares, tiver, foder, glyph, burez, weren | 6 |
| heist | cares, stile, deist, gumbo, kevyn, fixes | 6 |
| zesty | cares, stile, guest, festy, whomp, tends | 6 |
| larva | cares, bardy, mario, garth, parka, jalur | 6 |
| homer | cares, tiver, foder, honer, bulky, gomer | 6 |
| glass | cares, plats, flans, bodhi, kumys, swags | 6 |
