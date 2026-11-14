# Hall 1: The Bounce Factory. Implementation checklist

This file tracks the progress and to-dos for the first hall of *The Machine Works*, as specified in
[`GDD-machine-works.md`](GDD-machine-works.md) §6.1.

Legend: ✅ done · 🟡 partly done · ⬜ to do · ⏸ deferred to a later stage (by decision)

| | |
|---|---|
| Status | **Hall 1 is playable end to end.** All 4 stations, the whole machine A → B, stars, points, hints and practice mode work. The lab topic and extensions it depends on are shipped. |
| Tests | `python3 -m unittest discover -s tests` runs **338 tests, all green** (there were 263 before the game). 75 are new: `test_bounce`, `test_game`, `test_game_api`, `test_game_browser`, plus one in `test_client`. |
| Try it | `python3 -m physlab.server 8600`, then open <http://127.0.0.1:8600/#/game> or the 🏭 button on the home page. |
| Tester links | [`hall1-solutions.md`](hall1-solutions.md) has the correct settings plus game and lab deep links for every station and variant. |
| Since Hall 2 | Hall 2 is built the same way: [`IMPLEMENTATION-hall2.md`](IMPLEMENTATION-hall2.md). What the halls share moved to `physlab/game/kit.py`, and the Bounce Factory's drawing moved from `scene_game.js` to its own painter, `www/js/hall_bounce.js` (`scene_game.js` is now the engine every hall uses). Hall 1's data and results are unchanged. |

---

## Round 2: playtest feedback

| # | Feedback | Status | What changed |
|---|---|---|---|
| 1 | A follow camera so a running simulation is easier to watch | ✅ | See [R2.1](#r21-follow-camera) |
| 2 | "Copy deep link" and "practice link" don't work, or their purpose isn't clear; fix the navigation | ✅ | See [R2.2](#r22-share-box-and-navigation) |
| 3 | Open the next hall when every station of the previous hall is cleared | ✅ | See [R2.3](#r23-hall-progression) |
| 4 | A score for every station, and highscores to chase | ✅ | See [R2.4](#r24-scores-and-highscores) |
| 5 | Salt Canal: a threshold means it always works above N bags. Add a timer, or make salt/time part of the score | ✅ | See [R2.5](#r25-the-salt-canal-salt-and-time-both-cost) |
| — | Bug found while testing: clicking another station after a run crashed the scene (existed in round 1 too) | ✅ | Fixed, with a browser regression test |

### R2.1 Follow camera

- The camera control is now **📍 station · 🎥 follow ball · 🏭 whole hall**. **Follow is the default.**
- Follow mode keeps the station's zoom (the −/+ buttons still work) and glides with the ball while the run plays.
  It aims 0.35 s ahead and eases with a rate of 5/s, so fast shots stay in frame.
- While paused, you can pan freely; *reset* and a new run re-centre the camera.
- A machine run switches *station* to *follow* automatically. The HUD says which station the ball is in right now ("now: 1.3 Camel Hump").
- The HUD has a backdrop, so the hall no longer shows through the text.
- The choice is remembered for the browser tab.
- Code: `scene_game.js › follow()`, `game.js › setCamera`.

### R2.2 Share box and navigation

- **Share this setup** (replaces the two chips in the test bench):
  - It sits under the debrief and shows the full link in a text field, plus **📋 Copy link**.
  - The link opens this station with these settings **and these station numbers** (the player's variant), in practice mode, so whoever opens it sees exactly the same machine.
  - Copying uses the clipboard where the browser allows it. Otherwise the link is selected and the page says "press Ctrl+C", which covers plain `http://` on a classroom LAN, where browsers block the clipboard API. Before this, the button claimed success when nothing had been copied.
- **🎯 Try ideas in practice mode** (for players) opens the same setup in practice mode and explains why: you can experiment without using up your runs.
  - In practice mode, if a player exists on this computer, the player box shows **← Back to playing as ‹name›** instead of the new-player form.
- **Lab round trip:** "Open in the lab" remembers the station.
  - Experiment and sandbox pages show **🏭 Back to the Machine Works · ‹station›**.
  - Every station's settings, the focused station and the camera are remembered for the tab (`sessionStorage`), so nothing is lost on the way back.
  - Code: `ui.js › setReturn / returnBanner`, `game.js › memory`.
- The practice and back buttons use `goRoute`, so they also work when the URL wouldn't change.

### R2.3 Hall progression

- A hall is **cleared** when every station has ★ It works, and a hall **opens** when the hall before it is cleared.
  *(Since Hall 3 this classroom order is switched on with `PHYSLAB_GAME_LOCKS=on`; by default every hall is open for
  testing - `IMPLEMENTATION-hall3.md` §4.)*
  - The rule is `common.hall_progress()`, enforced by the server for players (`403` on a locked hall). Practice mode can still open any built hall.
- **The map shows each hall's state:**
  - open;
  - 🔒 locked, with the requirement;
  - 🔓 unlocked but still being built (no hall any more: all three are built, see `IMPLEMENTATION-hall3.md`);
  - 🏁 cleared, with the hall score.

  Without a player, it shows a newcomer's progression.
- **On the run that clears a hall,** the debrief celebrates: "🎉 You cleared The Bounce Factory! The Foundry is now unlocked". The hall page then keeps a "🏁 Hall cleared" banner, with a button to the next hall once it's built.
- **Existing players:** progress is worked out from stars. Anyone who already cleared Hall 1 sees the Foundry unlocked straight away.

### R2.4 Scores and highscores

- **Every working run scores 0–1000; a failed run scores 0.**
  - **1000 is the best possible for the player's own variant.** The references (lowest drop, cheapest delivery, fastest safe run) are generated per variant, so scores are fair between classmates.
  - Each station's rule is on its card, and the debrief breaks the score down.

  | Station | Score rule | What it rewards |
  |---|---|---|
  | 1.1 Bounce Flap | 1000 for the lowest drop that can work; −40 for every 10 cm higher | using as little energy as possible (the steel pad and `h₀ = h₁/e²`) |
  | 1.2 Salt Canal | 1000 − (your cost − the cheapest possible), cost = 50 per bag + 300 per second to the outflow | the best **trade-off** between salt and time (R2.5) |
  | 1.3 Camel Hump | 1000 for the fastest safe run; −50 for every 0.1 s slower | running right at the `√(gR)` limit |
  | 1.4 Spring Cannon | up to 800 for coming down dead centre through the mouth (quadratic), +200 for a trick shot off the bumper wall | aiming (the projectile equation), and a bank shot to beat 800 |

- **Highscores:**
  - the best score per station for each player, shown as 🏆 in the station list, on the card and on the map (hall score out of 4000);
  - a **top-5 on this computer** per station, with your rank ("#2 of 7"), and "🎉 new personal best!" in the debrief;
  - scores are derived from `game_runs.score`, never stored separately, like every other number.
- **Migration:**
  - an old database gets the `score` column;
  - working runs from before scores existed are **re-scored exactly**: runs are deterministic, and the variant comes from the player id.
- Star points (★, insight, golden) and station scores (🏆) stay separate: stars track progress, scores are the chase.

### R2.5 The Salt Canal: salt AND time both cost

- **The problem:** above the threshold (the fewest bags that float the ball) every setting works, so there was nothing left to think about.
- **Chosen fix: scoring, not a timer.**
  - Physically, more salt means a bigger net upward push, `(ρ_brine − ρ_ball)·V·g`. The ball pops back up faster after plunging in, so it reaches the outflow sooner.
  - The score charges **50 per bag + 300 per second**, so:
    - the fewest bags float, but slowly (about 550 points);
    - a lot of salt is quick but wasted (about 650);
    - **the best trade-off sits 2–3 bags above the minimum**: 12, 13, 13, 14 or 15 bags depending on the variant. That makes it a real optimisation that differs per student, and can't be copied.
  - A timer was considered but not used. It would only move the threshold (pass/fail from N+1 bags), which is the same problem again, and it would break the concept lesson ("it floats as soon as the water is denser than rubber") and the ★★★ "Just Salty Enough" goal.
- **Mastery vs score are now different goals:** ★★★ = the fewest bags that float (understanding the threshold); 🏆 1000 = the cheapest delivery (engineering the trade-off).


| # | Request | Status | Where |
|---|---|---|---|
| 1 | Check the assets and sprites needed for this level; complete the missing ones in the same design language | ✅ | [§1](#1-assets-and-sprites) |
| 2 | Make every knob (adjusted object) testable, so problems show up in the testing phase | ✅ | [§2](#2-knob-testability) |
| 3 | Save the parameters of the correct value for each station; deep-link each to its related simulation | ✅ | [§3](#3-correct-settings-and-deep-links) |
| 4 | Sound, UI menu and animation outside the simulation: deferred | ⏸ | [§6](#6-deferred-to-a-later-stage) |
| 5 | A checklist document that tracks progress and to-dos | ✅ | this file |

---

## 1. Assets and sprites

**Design language** (from the existing set):

- 128 px items, flat fills, a dark outline `(34, 34, 40)`, a few highlights.
- Drawn 4× and downsampled, on white (the client keys out white at load).
- Topic icons use a thicker navy outline on white.
- Anything whose look *carries physics* is drawn in code, so it can change with the numbers: the ball's colour, the pad material, the water's saltiness, the track's shape, the barrel's angle.

Every new sprite is procedural and reproducible with `python3 tools/make_sprites.py`. Running it re-creates the old sprites byte-identically.

| Asset | Used in | Existed? | Action | File / code |
|---|---|---|---|---|
| Rubber ball | all stations | ✅ colour in catalog (`#e0455a`) | drawn in code (size, highlight) | `scene_game.js` |
| Toy hopper (point **A**) | 1.1 | ⬜ | ✅ **new sprite** | `www/sprites/item_hopper.png` |
| Hatch, rail, feed tube | 1.1 | — | ✅ code (the hatch height is a knob) | `hall_bounce.js › bounceFlap` |
| Bounce pads: steel, hardwood, foam, sand | 1.1 | colours in `BOUNCE_SURFACES` | ✅ code, coloured from the catalog | `physlab/__init__.py`, `hall_bounce.js` |
| One-way flap, shelf, hot duct | 1.1 | — | ✅ code | `hall_bounce.js` |
| Canal tank, water, grate, current arrows | 1.2 | water style from the buoyancy scene | ✅ code; the water tints with the salt | `hall_bounce.js › saltCanal` |
| Salt bag | 1.2 | ⬜ | ✅ **new sprite** (stacked one per bag) | `www/sprites/item_saltbag.png` |
| Camel track and hill | 1.3 | track style from the energy scene | ✅ code; the shape comes from `PL.game.camel`, which mirrors the server | `hall_bounce.js › camelHump`, `core.js` |
| Spring cannon barrel | 1.4 | ⬜ | ✅ **new sprite**, rotated to the launch angle | `www/sprites/item_cannon.png` |
| Cannon stand, funnel, bumper wall | 1.4 | — | ✅ code | `hall_bounce.js › springCannon` |
| Toy box (point **B**) | 1.4 | ⬜ | ✅ **new sprite** | `www/sprites/item_toybox.png` |
| A / B markers, station tags, yellow knob handles | all | handle style from the energy scene | ✅ code | `scene_game.js` |
| Gizmo, the robot foreman | hints / story | ⬜ | ✅ **new sprite** (not shown in the UI yet, see §6) | `www/sprites/item_gizmo.png` |
| Bounces topic icon | home card, lab page | ⬜ | ✅ **new icon** | `www/icons/icon_bounce.png` |
| Bounces learn screenshots (3) | lab learn panel | ⬜ | ✅ captured from the app | `www/learn/bounce_{1,2,3}.png` (`tools/make_figures.py --only bounce`) |
| Hall cards on the game hub | hub | — | ✅ reuse the new sprites (toy box / cannon / hopper) | `game.js › Hub` |

- ✅ New sprite names are registered in `PL.SPRITES` (`widgets.js`). A missing sprite falls back to a plain box, so the scene never breaks.
- ⬜ Art review by a designer: the sprites match the style rules, but a human eye should sign them off.
- ⏸ Sound effects (SPLASH, CLANG, BOING) are deferred.

## 2. Knob testability

Every knob is testable at **four levels**, so a wrong value shows up before students see it.

| Level | What is checked | Where |
|---|---|---|
| **Physics (unit)** | **Validation:** unknown knob / wrong type / NaN / out of range / not a choice are refused with a reason; numbers snap to the slider grid; missing knobs take the default. | `tests/test_game.py › TestKnobValidation` |
| | **Effect:** each knob moves the outcome the right way (see the matrix below). | `TestEachKnobDoesWhatItSays` |
| | **Answers:** the defaults are not already an answer; references pass; wrong answers fail *with the expected reason*; mastery settings earn mastery. | `TestAnswers` |
| | **Determinism:** the same knobs give byte-identical results. | `TestAnswers.test_deterministic` |
| **API** | the same refusals over HTTP, locked stations (403), no answers in public payloads, star and hint rules | `tests/test_game_api.py` |
| **Client (Node)** | the browser snaps and clamps a knob *exactly* like the server (every knob, edge values); the browser's camel track equals the server's to 1e-12; deep links round-trip | `tests/js/test_game.js` via `tests/test_client.py` |
| **Browser (e2e)** | slider, number box (snapped and clamped), choice chips and the URL; dragging the stage handles; every saved solution passes through the UI; a wrong setting fails; the machine runs A → B; every lab link opens | `tests/test_game_browser.py` (Playwright; skipped without it) |

**Knob matrix** (nominal variant; the windows come from [`hall1-solutions.md`](hall1-solutions.md)):

| Station · knob | Kind, range, step | Stage handle | UI selector | Effect checked | Works for (nominal) |
|---|---|---|---|---|---|
| 1.1 `hatch` | number 1.0–4.0 m, 0.05 | drag the hatch up/down | `[data-knob="1.1.hatch"]`, `[data-knob-input="1.1.hatch"]` | higher hatch → higher bounce, ≈ e²·h₀ | steel 2.15–3.20 m; hardwood 2.75–4.00 m |
| 1.1 `pad` | choice: steel_plate / hardwood / foam_mat / sand | — | `[data-knob="1.1.pad"][data-id=…]` | steel > hardwood > foam > sand | foam and sand never work |
| 1.2 `bags` | integer 0–20 | click − / + by the salt pile | `[data-knob="1.2.bags"]` | more bags → denser water, flat after saturation; floats from exactly `min_bags` | 11–20 bags |
| 1.3 `hump` | number 0.20–1.60 m, 0.01 | drag the crest up/down | `[data-knob="1.3.hump"]` | higher hump → slower over the top, always ≤ √(gR) when it stays on | 0.84–1.40 m |
| 1.4 `compression` | number 2.0–20.0 cm, 0.1 | — | `[data-knob="1.4.compression"]` | more compression → faster (≈ x√(k/m)) | 12.7–13.5 cm at 45° (+ bank shots) |
| 1.4 `angle` | number 15–75°, 1 | drag round the barrel's pivot | `[data-knob="1.4.angle"]` | steeper → a little slower (the lift term); changes the landing point | direct shots from about 40° to 75° |

**Tools for manual testing:**

- **🧪 Test bench** under the stage (open it, or add `&debug=1` to the URL). It shows the variant, the facts, the knobs, the last request and the raw result of every station (ok, metric, mastery, reason, stars), plus a *copy deep link* button.
- **`PL.current.game`** in DevTools:
  - `setKnob('1.3','hump',0.9)`, `select('1.2')`
  - `await test()`, `await machine()`, `await hint(1)`
  - `state`, `lastResult`, `hash()`
- **Test ids:** `test-station`, `run-machine`, `hint-1..3`, `predict-value` / `predict-yes` / `predict-no`, `camera-station` / `camera-hall`, `player-name` / `player-start`, `game-cta`. Rows also carry `[data-station]`, `[data-result]`, `[data-lab]` and `[data-fact]`.
- `<html data-sim-ready="1">` means the page is settled (loaded, or a run's answer has arrived), the same contract as the rest of the app.
- **Practice mode** (`?practice=1&v=0..4`) runs any variant without a player and records nothing.

## 3. Correct settings and deep links

- ✅ **Saved:** [`physlab/game/data/bounce_factory.json`](../../physlab/game/data/bounce_factory.json). It is generated by `python3 tools/make_game_solutions.py` from the stations' own physics. For **each station × each of the 5 variants** it stores:
  - a robust correct setting (the middle of the window);
  - the whole window;
  - a mastery setting;
  - the mastery thresholds the runtime reads;
  - the Blueprint explanation;
  - the game and lab deep links.
- ✅ **Readable copy for testers:** [`hall1-solutions.md`](hall1-solutions.md), with clickable links to a local server.
- ✅ **Guarded by tests:**
  - every saved setting passes its variant, and every mastery setting earns mastery;
  - the thresholds mean what they say;
  - every lab link is a valid, unclamped experiment set-up, and **the lab reproduces the station** (same bounce height, same float/sink verdict, same fly-off, same throw);
  - `--check` fails if the files are stale (run inside `test_game`).
- ✅ **In the game:** each station's debrief has **🔬 Open in the lab** with the *student's own* numbers, and the Blueprint hint (tier 3) gives the saved setting for the student's variant.

**Nominal variant** (practice mode, `v=2`); see [`hall1-solutions.md`](hall1-solutions.md) for all five:

| Station | Correct setting | Result | Mastery setting | Game (preloaded) | Related simulation(s) |
|---|---|---|---|---|---|
| 1.1 Bounce Flap | hatch = 2.7 m, pad = steel plate | bounce 1.90 m | hatch = 2.15 m, steel | [play](http://127.0.0.1:8600/#/game/bounce/1.1?practice=1&v=2&k=%7B%22hatch%22%3A2.7%2C%22pad%22%3A%22steel_plate%22%7D) | [Bounces](http://127.0.0.1:8600/#/bounce?ball=rubber&surface=steel_plate&height=2.7) · [Sandbox](http://127.0.0.1:8600/#/sandbox/bounce?w=%7B%22balls%22%3A%5B%22rubber%22%2C%22steel%22%5D%2C%22surface%22%3A%22steel_plate%22%2C%22height%22%3A2.7%7D) |
| 1.2 Salt Canal | 12 bags | water 1172.6 kg/m³ | 11 bags (the minimum) | [play](http://127.0.0.1:8600/#/game/bounce/1.2?practice=1&v=2&k=%7B%22bags%22%3A12%7D) | [Floating & Sinking](http://127.0.0.1:8600/#/buoyancy?shape=sphere&material=bouncy&size=6.0&fluid=water&salt=300.0&start=10.0) |
| 1.3 Camel Hump | hump = 1.12 m | over the top at 1.99 m/s | hump = 0.84 m (speed run) | [play](http://127.0.0.1:8600/#/game/bounce/1.3?practice=1&v=2&k=%7B%22hump%22%3A1.12%7D) | [Energy Ramp (camel track)](http://127.0.0.1:8600/#/energy?track=camel&object=solid_ball&height=1.5&hump=1.12&mass=0.5&friction=0.01) |
| 1.4 Spring Cannon | 13.1 cm at 45° | launch 6.15 m/s | 16.0 cm at 45° (bank shot) | [play](http://127.0.0.1:8600/#/game/bounce/1.4?practice=1&v=2&k=%7B%22angle%22%3A45.0%2C%22compression%22%3A13.1%7D) | [Projectile Motion](http://127.0.0.1:8600/#/motion?v0=6.15&angle=45.0&mass=0.13&drag=0.000814&wind=0.0&g=9.81) |

Whole machine, nominal: run all four settings above with **▶▶ Run machine** (about 22 s of machine time).

---

## 4. What was built

### 4.1 Simulation module: the GDD's "lab teaches first" rule (Phase 1)

| GDD id | Item | Status | Files |
|---|---|---|---|
| N1 | **Bounces** topic: drop a ball on a surface, each bounce e² of the last. Includes the engine, scene, 3 formulas explained, 3 captured figures, 6 presets, 5 real-life cards, **3 quiz questions** (easy/medium/hard), a **sandbox** (balls × surfaces × planets), and a golden fixture | ✅ | `physlab/topics/bounce.py`, `www/js/scene_bounce.js`, `physlab/learn.py`, `physlab/quiz.py`, `physlab/sandbox.py`, `tests/fixtures/bounce.json` |
| N1 | Shared **ball tracer** (motion's Heun + drag + wind, plus obstacles with restitution and goal zones) | ✅ | `physlab/topics/tracer.py` |
| X2 | Energy: **camel track** (a hump with a fixed crest radius), a *hump height* parameter, a draggable crest, the √(gR) limit drawn, an early stop, and `spring_launch_speed()` | ✅ | `physlab/topics/energy.py`, `www/js/scene_energy.js` |
| X3 | Buoyancy: **salt stirred into fresh water** (CRC brine table, saturation at 359 g/L), plus the *bouncy-ball rubber* material (1149 kg/m³) | ✅ | `physlab/topics/buoyancy.py`, `physlab/__init__.py` |
| X1 | Motion: launch height and target zones in the lab UI | ⬜ | the game uses the tracer; the lab's 1.4 link shows the same throw, landing at launch height |
| X2 | A spring launcher in the lab UI (½kx²) | ⬜ | only the function exists; 1.4's lab link goes to Projectile Motion |
| — | Old fixtures unchanged (byte-identical) after the extensions | ✅ | `tests/gen_fixtures.py` |
| — | Fix: dragging a scene handle on a **quiz** page threw a TypeError (pre-existing for energy/optics) | ✅ | `www/js/stage.js` (a no-op `cam.setParams` default) |

### 4.2 The game module

| Item | Status | Files |
|---|---|---|
| Knob specs, validation and snapping; seeded per-student variants (5 steps); public card without answers; star, insight and hint rules | ✅ | `physlab/game/common.py` |
| Hall 1: 4 stations (data + physics adapters), the hall layout, a machine run with continuous connectors, hints with the player's numbers, Blueprints | ✅ | `physlab/game/bounce_factory.py` |
| Service: catalog, hall view, test/machine runs, hints, locking, practice mode, and an LRU cache of deterministic runs | ✅ | `physlab/game/service.py` |
| Storage: `game_runs`, `game_stars`, `game_hints`, `game_golden` (same SQLite file and players as the quiz; scores derived, never stored) | ✅ | `physlab/game/db.py` |
| API: `GET /api/game`, `GET /api/game/hall`, `POST /api/game/run`, `POST /api/game/hint` | ✅ | `physlab/server.py` |
| Client: home button, hub (player + hall cards), hall page (stations, card, knobs, prediction, test/machine, hints, debrief with formulas and lab links, camera/speed, test bench) | ✅ | `www/js/game.js`, `www/style.css`, `www/js/main.js`, `www/index.html` |
| Hall painter: all 4 stations from layout + facts + **current** knobs; handles; trail; the previous run as a ghost | ✅ | `www/js/hall_bounce.js` (the stations), `www/js/scene_game.js` (the engine) |
| Pure client helpers: knob snapping, camel track, game deep links | ✅ | `www/js/core.js › PL.game` |
| Correct-settings generator plus the tester table | ✅ | `tools/make_game_solutions.py`, `physlab/game/data/bounce_factory.json`, `docs/game/hall1-solutions.md` |

### 4.3 Decisions and deviations from the GDD

- **Par** is derived from each station's measured guessability (GDD §7.1): 1.1 = 2, 1.2 = 2, 1.3 = 2, 1.4 = 3.
- **Insight tolerance:** ±10 %, **or ±0.02 in the station's unit**, whichever is larger. The GDD said ±10 % only, which is unfair near zero (e.g. predicting a 4 cm bounce).
- **Stations unlock in order** for players (the next one opens when this one has ★ It works). In practice mode everything is open. A machine run needs no unlocks, because it stops at the first failure anyway.
- **Practice mode never shows a Blueprint.** Otherwise a student could fetch the answer for their own variant without paying stars.
- Efficient-star runs count **every run that tested the station**, including machine runs, so the machine can't be used as free tests.
- The 1.4 lab link goes to *Projectile Motion* with the same launch speed and angle. The lab ball lands at launch height rather than on the toy box's stand (see X1 in §5).

## 5. To do (next steps for Hall 1)

- ⬜ **Classroom playtest** against the GDD §8.9 KPIs. The telemetry is already in `game_runs` / `game_hints`.
- ⬜ **X1 in the lab:** launch height and target zones in Projectile Motion, so the 1.4 lab link shows the toy box.
- ⬜ **Spring launcher in the lab** (energy topic, ½kx²), so 1.4 has a lab page for its first formula.
- ⬜ A **bank-shot view** in the Bounces lab (a tilted wall: angle in = angle out, normal speed × e). This is the physics behind 1.4's Trick Shot.
- ⬜ **Learn content** for the camel track and salt water (a figure each). Presets exist, figures don't.
- 🟡 Salt Canal pacing: at the minimum salt the ball rises slowly. This is now part of the score (R2.5), but 1.2 is still about 10–12 s of a machine run. Consider a faster current.
- ⬜ The whole-hall overview hides small labels (below 75 px/m); station tags can still crowd at some zooms. Do a layout pass with the art review.
- ⬜ Badges and ball skins (GDD §7.5–7.6). The data for them is recorded, but there's no UI.
- ⬜ A teacher switch to hide the on-computer leaderboard (GDD §7.7 prefers no ranking by default; it's shown now at the playtest's request).
- ⬜ Review the score weights after the playtest (1.1: 40 per 10 cm; 1.2: 50 per bag / 300 per second; 1.3: 50 per 0.1 s; 1.4: 800 aim + 200 trick shot).
- ⬜ Station parts unlocking in the Sandbox (GDD §7.6).
- ⬜ A material-ghosts toggle (GDD §4.5). The physics already supports other balls (`fan_jump(ball_id)`-style runs).
- ⬜ **Localisation:** station texts live in `bounce_factory.py`, ready to extract.
- ✅ **Hall 2 prerequisites:** X4 thermal expansion and X6 dead-weight pressure shipped with Hall 2; X5 and X7 turned out not to be needed for play (see `IMPLEMENTATION-hall2.md` §5.1).

## 6. Deferred to a later stage

By decision (request 4), none of this blocks Hall 1:

- ⏸ **Sound:** splash, clang, boing, spring twang, success jingle; captions first, audio off by default.
- ⏸ **UI menus beyond the functional hub:**
  - an animated world map (GDD §3);
  - an animated Workshop hub;
  - a parts shelf and ball rack;
  - a settings menu (reduced motion, sound).
- ⏸ **Animation outside the simulation:**
  - Gizmo's appearances and reactions (the sprite is ready);
  - slow motion at key moments (GDD §4.5). The follow camera is **done** (R2.1);
  - particles (splash droplets, sparks, dust);
  - the Golden Run cinematic and captions;
  - the hub/hall transitions;
  - star-earned effects.
- ⏸ The Class Machine (cooperative meter) and a teacher dashboard (GDD §7.7 / §12.3).

## 7. How to run and verify

```sh
python3 -m unittest discover -s tests           # everything (about 2 min; browser tests skip without Playwright)
python3 -m unittest tests.test_game             # stations, knobs, saved solutions, lab links (~55 s)
python3 -m unittest tests.test_game_api tests.test_game_browser tests.test_bounce
python3 tools/make_game_solutions.py            # after changing a station's physics, layout or facts
python3 tools/make_sprites.py                   # sprites + the Bounces icon (needs Pillow)
python3 tools/make_figures.py --only bounce     # Bounces learn screenshots (needs Playwright + Chromium)
python3 docs/game/level_math.py 1.1 1.2 1.3 1.4 # the GDD's design calculator, Hall 1 only
```

**Checklist before merging a change to a Hall 1 station:**

- ⬜ `make_game_solutions.py` has been re-run, and `hall1-solutions.md` reviewed (windows not too narrow, not too wide).
- ⬜ `test_game` is green, including the lab-reproduces-station checks.
- ⬜ The browser e2e test is green.
- ⬜ If a number on a station card changed, the GDD §6.1 text is updated too.
