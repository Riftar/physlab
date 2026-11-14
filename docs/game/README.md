# docs/game: The Machine Works (Game module, game 1)

| File | What it is |
|---|---|
| [`GDD-machine-works.md`](GDD-machine-works.md) | **The game design document**: world, 3 halls × 4 stations, the challenge and reward system, game-theory balancing, the simulation-module roadmap, technical design |
| [`IMPLEMENTATION-hall1.md`](IMPLEMENTATION-hall1.md) | **Hall 1 implementation checklist**: progress, assets, the knob test plan, correct settings and deep links, to-dos, deferred items |
| [`hall1-solutions.md`](hall1-solutions.md) | Generated table of the correct setting for every Hall 1 station and variant, with game and lab deep links |
| [`IMPLEMENTATION-hall2.md`](IMPLEMENTATION-hall2.md) | **Hall 2 (the Foundry) implementation checklist**: the same structure as Hall 1, plus scores and the lab extensions X4/X6 |
| [`hall2-solutions.md`](hall2-solutions.md) | Generated table of the correct, mastery and top-score settings for every Hall 2 station and variant, with game and lab deep links |
| [`IMPLEMENTATION-hall3.md`](IMPLEMENTATION-hall3.md) | **Hall 3 (Millbrook Mill) implementation checklist**: assets, the knob test plan, deep links, the new Levers & Moments topic and the X1/X3/X8 extensions, **test mode** (every hall open) |
| [`hall3-solutions.md`](hall3-solutions.md) | Generated table of the correct, mastery and top-score settings for every Hall 3 station and variant, with game and lab deep links |
| `GDD-machine-works.pdf` | The same document as a 21-page PDF, for reviewers who don't read Markdown |
| `level_math.py` | The design calculator. It runs every station on the real physlab engines (plus clearly marked prototypes for missing physics) and checks the reference answers, the wrong answers, every variant, the solution density and the mastery windows. These checks become the game's unit tests. |
| `level_math_results.json` | The calculator's last full output (the numbers quoted in the GDD) |
| `make_diagrams.py` | Draws `img/` (world map, the three level maps with simulated ball paths, the difficulty curve). Needs matplotlib (dev-time only, like `tools/make_figures.py`). |
| `img/` | The figures used by the GDD (and `hall2_*.png`, `hall3_*.png`: screenshots of the implemented Foundry and Mill) |

```sh
python3 docs/game/level_math.py                 # all stations, about 4 min (--quick for a fast pass)
python3 docs/game/level_math.py 2.4 3.3         # selected stations
python3 docs/game/level_math.py --json docs/game/level_math_results.json
python3 docs/game/make_diagrams.py
```

Nothing in this folder is imported by the app. It's design material, and the app stays stdlib-only. The
implemented game lives in `physlab/game/` and `www/js/game.js` (+ `scene_game.js`, `hall_*.js`).
