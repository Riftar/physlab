# physlab

See the formula happen. Physics experiments for 10-15 year olds: turn
the knobs, run the experiment, and the real formula with live numbers
sits next to the thing it describes. Runs entirely offline with zero
dependencies — Python stdlib server, vanilla JS/canvas client.

## Experiments (v1)

- **Electric Circuits** — battery, switch, 1-3 lamps, series resistor.
  Current from Kirchhoff's loop law `I = V / (R + r)`. Charges are drawn
  flowing round the whole loop (through wires, filaments and battery) at
  a speed proportional to the current; toggle between electrons (− → +)
  and conventional current (+ → −). The legend quotes the *real* drift
  speed `v = I / (n e A)` (fractions of a mm/s). Lamps are real 6 V
  incandescent lamps: power sets the filament temperature
  (Stefan-Boltzmann), light output is Planck's spectrum weighted by the
  CIE eye-sensitivity curve, glow colour is the black-body colour, and
  perceived brightness follows Stevens' power law. So two lamps in series
  glow dull orange, three barely glow, and 12 V on one lamp is white-hot
  with a burn-out warning. (Validated in tests against the old candela
  definition and CIE Illuminant A.)
- **Projectile Motion** — launch speed, angle, mass, gravity, air drag,
  wind. `a = -g - (k/m)·v_air·|v_air|` with `v_air = v - wind`, Heun
  (2nd-order) steps; with drag at zero the flight matches
  `Range = v0²·sin(2θ)/g` to <1 mm (the test suite checks). Wind streaks
  move at the true wind speed on the same metre scale as the ball; weight
  and drag arrows share one newton scale; the dashed no-air parabola
  shows what drag costs. **Compare mode** runs two balls (A/B) with
  independent settings on the same axes and flags whether it's a fair
  test (only one setting changed). A **launch height** throws from a tower
  (no-air distance `x = v0·cos a·(v0·sin a + √((v0·sin a)² + 2gh))/g`), and
  the wind goes up to a 20 m/s gale.
- **Heat Transfer** — two touching blocks, each its own material (water
  in a glass tank, aluminum, iron, copper) drawn at its true relative
  size `side = ∛(m/ρ)`, optional heat leak to the room. Atoms jiggle
  harder when hotter; glowing packets (each a fixed, labelled number of
  joules) cross the contact at a rate proportional to the heat flow
  `G·(T_a - T_b)`; live temperature-time graph; "thermal camera" view.
  `Q = m·c·ΔT` exchange until both meet at the weighted mean.

- **Floating & Sinking** — block or ball (cork, pine, ice, rubber,
  aluminum, iron, gold) dropped into a tank of fresh/sea water, oil,
  honey or mercury. `F_b = ρ_liquid·V_sub·g` with the real submerged
  geometry (sphere caps included), the buoyancy acting at the centre of
  buoyancy, added mass, Haider-Levenspiel drag (Stokes → form drag), and
  a tank level that rises by exactly the volume pushed aside. Views: a
  free-body diagram of every force, or water-pressure arrows (`p = ρgh`)
  showing why the bottom pushes harder than the top. A measuring
  cylinder collects the "liquid pushed aside". Floaters settle at
  `V_sub/V = ρ_obj/ρ_liquid` (g cancels - try the Moon). Pick a **narrow
  well** (10 cm across), the starting water depth and the stones already on
  the bottom, and the water rises by `dh = V_pushed/A` - Aesop's crow.
- **Waves** — shake one end of a rope. `v = √(T/μ)`, `v = f·λ`,
  resonances `f_n = n·v/(2L)` (fixed end) or `(2n-1)·v/(4L)` (free end);
  or an endless rope with no echo. Solved with finite differences at
  Courant number 1, which is exact for waves (tests match d'Alembert's
  solution to 1e-16); damped steady state matches the analytic formula.
  A bead shows rope only moves up and down, a marker rides a crest at
  `v`, a λ ruler, the standing-wave envelope with its nodes, and a
  resonance ladder to hunt for `f_n`.
- **Pendulum** — the full nonlinear swing (RK4), exact period for any
  release angle `T = 2π√(L/g) / AGM(1, cos(θ0/2))`, string tension
  `m(g cosθ + Lω²)`, optional air drag. Arrows for weight, tension and
  the restoring part of gravity `mg sinθ`; energy bars trade height for
  speed. **Compare mode** hangs two pendulums side by side (mass doesn't
  change the period; length does).

- **Lenses** — a candle, a lens and its image on a zoomable optical
  bench. The lensmaker's equation `1/f = (n-1)(1/R1 - 1/R2)` turns the
  material (water → diamond) and curvature into a focal length; the
  thin-lens equation `1/f = 1/d_o + 1/d_i` and `m = -d_i/d_o` place the
  image (real on a screen, virtual behind the lens for an eye, or none at
  the focal point). Show the three textbook rays, or real rays traced
  through the thick glass with Snell's law (total internal reflection
  included). Light pulses slow down inside the glass (`n = c/v`).
  **Drag the candle's flame** to move it. Put a **screen** behind the lens:
  away from the image the light spreads into a blur circle
  `D·|s − d_i|/d_i`, and a 1 cm photocell catches only `(cell/patch)²` of it.
- **Pressure** — a hydraulic lift: `p = F/A`, Pascal's `F2 = F1·A2/A1`,
  incompressible `d2 = d1·A1/A2`, and `F1·d1 = F2·d2`. The push is a
  person's (weaker when faster), the liquid's own weight counts, and
  every joule is booked (work in = load + liquid + friction heat).
  Equal pressure arrows on both pistons show why the big one lifts more;
  zoom in to watch it rise a couple of millimetres.
- **Energy Ramp** — a box or a rolling ball on a half-pipe or a
  drop-and-hill track. `E = ½mv² + mgh`, rolling `v = √(2gh/(1+k))`,
  the track's push `N = m(g cosφ + v²/r)` (too fast over the hill and
  the object flies off) and friction heat `μN·distance`. Stacked bars
  show height, motion, spin and heat. **Drag the start flag**; compare a
  box and a ball side by side. A small **camel-hump** track (a hump whose
  crest has a fixed radius R: drag the crest) shows the `v ≤ √(g·R)` limit
  for staying on the track.
- **Bounces** — drop a real ball (rubber, tennis, steel, wood) on a steel
  plate, hardwood, a foam mat or sand. A bounce returns a fraction `e` of
  the speed, and `e` belongs to the ball AND the surface, so each bounce
  reaches `h1 = e²·h0` (`v = √(2gh)` on the way down). The marks show each
  bounce against the faint no-air `e²ⁿ·h0` ticks; air drag can be switched
  off; energy bars book height, motion and the heat + sound of every bounce.
  Runs on the shared ball tracer (`topics/tracer.py`: the projectile
  engine's Heun + drag + wind, plus obstacles with restitution).
- **Levers & Moments** — a 2.2 m beam on a pivot with a load hanging on
  each side (drag the hooks along the beam). The turning effect is
  `τ = m·g·d`; it balances when `m1·d1 = m2·d2` (g cancels); out of balance
  it turns by `α = τ_net/I` with `I = Σ m·r²` against the pivot's friction,
  until it hits a stop - the readouts give the balancing load, the time and
  the speed at the stop, and the energy books balance.

### Challenges (quiz)

`#/quiz` - three challenges per experiment (33 in all): "set the right
value to make the experiment do X", e.g. *what launch speed lands the
ball on the 20 m mark?* Students can only enter the parameters the
question allows. The experiment then **runs with their answer** (with
the target drawn in where it makes sense), and they see whether it
worked, what came out, a hint which way to go, and how to think about
it; the worked answer appears once solved.

- **Easy** - one value, one formula. **Medium** - one value with a twist
  (Moon gravity, a rolling ball, internal resistance, a virtual image).
  **Hard** - two values that depend on each other, or physics no simple
  formula covers (air drag, big swings, friction on a hilly track), so
  the simulation becomes the tool.
- Graded by the simulation itself, not against a stored number: the
  server runs the experiment and measures the outcome, so every valid
  answer counts (30° and 60° both hit the mark).
- Points: easy 10, medium 20, hard 30, earned once; each wrong try first
  costs 25% (never below half). After 2 wrong tries the answer can be
  revealed - for no points.
- Players are just a nickname (no accounts); scores and the full answer
  history live in a SQLite database (`data/physlab.sqlite`, or
  `$PHYSLAB_DB`) with `questions`, `players`, `attempts` and `reveals`
  tables. `#/quiz/history` lists every answer.
- Questions live in `physlab/quiz.py`, each with reference answers and
  common mistakes that the tests grade through the real simulation.

API: `GET /api/quiz`, `GET /api/quiz/question`, `GET /api/quiz/history`,
`GET /api/quiz/players`, `POST /api/quiz/player`, `POST /api/quiz/answer`,
`POST /api/quiz/reveal` (JSON bodies, 16 KB max, all validated).

### Sandbox

`#/sandbox` - build your own world, within strict limits. Students never
type a mass or a drag coefficient: they pick **real things from a box**
(a ping-pong ball, a shot put, a 12 V car bulb, an egg, a copper pot...)
whose properties are fixed, published values, and change **the world
around them**, chosen from catalogs too: planet (Earth, Moon, Mars,
Titan - gravity *and* air density), weather and wind direction, ramp
surface, liquid, where a thing has been (fridge, kettle, oven), what it
is wrapped in... Each experiment page has an **🔬 Experiment | 🏖️
Sandbox** switch.

- **Projectile motion / Pendulum** - pick one or two balls/bobs to
  compare (A/B); the drag constant is computed from the ball and the
  planet's air (`k = ½ρ·Cd·A`). On the Moon every ball flies the same
  parabola. The pendulum gets **weather**: wind pushes on the bob
  (`F = k|u|u` with `u` = wind − bob velocity, both along the swing and
  along the string), so a ping-pong ball in a storm hangs at 73° and
  swings about that lean (`tan θ = kw²/mg`, period from
  `g_eff = √(g² + (kw²/m)²)`), while a brass bob hardly notices.
- **Energy ramp** - **shape the ramp yourself**: drag 7 control points
  (0-10 m high). The track is a natural cubic spline (smooth curvature,
  so the track's push is smooth too); the same spline runs in the browser,
  so a dragged shape previews instantly and the point stops where the
  ramp would dip below the ground or get steeper than 72°. Pick up to
  two objects (crate, ice block, skateboarder, bowling ball, marble...)
  and a surface; friction / rolling resistance come from an object ×
  surface table. Padded walls at both ends bounce back half the speed.
- **Electric circuits** - a **circuit board**: pick a part (wires,
  switch, 4 lamps with real ratings, 3 resistors, 4 batteries with their
  internal resistance) and click between two dots. Any circuit is
  solved by nodal analysis (Kirchhoff's current law at every dot):
  series, parallel, batteries aiding or opposing, short circuits (hot
  wires, the heat inside the battery), over-volted lamps and lamps that
  **blow** (filament past tungsten's melting point → open circuit →
  solved again). Charges move at a speed proportional to each part's
  own current; lamps glow with the same filament model as the
  experiment, so a 0.5 W indicator really is dimmer than a 5 W car
  bulb. A "voltage" view colours every dot by its potential.
- **Floating, heat, waves, lenses, pressure** - everyday objects in six
  liquids (steel floats on mercury, gold doesn't), things from around
  the house that can only come from sensible places (no water in the
  oven), ropes/pulls/rope ends, real lenses and candles, jacks, loads and
  who pushes.

Everything is validated on the server (`physlab/sandbox.py`): unknown
fields, unknown items, numbers out of range, impossible ramps and bad
circuits are refused with a reason, and the page goes back to the last
world that worked. Worlds are deep links too
(`#/sandbox/motion?w={"balls":["ping_pong","shot_put"]}`).

API: `GET /api/sandbox` (catalogs, fields, presets), `POST
/api/sandbox/run {topic, world}`.

### The Machine Works (game)

`#/game` - a Rube Goldberg game built on the lab's engines (design:
`docs/game/GDD-machine-works.md`). The student can't touch the ball: they
tune the machine - a hatch height, bags of salt, a hump, a spring and an
angle - press run, and the real simulations decide what happens. **Hall 1,
the Bounce Factory** (rubber ball) is playable: 1.1 Bounce Flap (bounces,
`h1 = e²h0`), 1.2 Salt Canal (floating in salt water), 1.3 Camel Hump
(energy, don't fly off: `v ≤ √(gR)`), 1.4 Spring Cannon (spring energy into
a projectile, trick shots off the wall), then the whole machine A → B.
**Hall 2, the Foundry** (steel ball) opens once Hall 1 is cleared: 2.1 Hot
Ring (heat balance and thermal expansion: heat the ring, not the ball),
2.2 Trapdoor Latch (the steel ball closes the circuit: `I = V/R_total`
between the latch's pull-in and the fuse), 2.3 Hydraulic Gate (the ball's
weight drives a hydraulic lift: `F2 = F1·A2/A1` against `x2 = x1·A1/A2`),
2.4 Magnet Swing (a crane's pendulum: `T = mg(3 − 2cos θ)` must stay under
the magnet's grip, then a throw into the ladle). Slow physics (the ring
heating for 20 s) plays as a time-lapse. **Hall 3, Millbrook Mill** (wooden
ball): 3.1 Crow's Well (drop stones in a narrow well until the floating ball
reaches the paddles: `dh = V/A`, and a floating block only pushes aside its
own weight of water), 3.2 Fan Jump (a winnowing fan's wind blows the light
ball across the mill race: drag does it, and the simulation is the tool),
3.3 Light Gate (the wooden ball can't close a contact, so a lens must focus
the lamp onto a photocell: of the two sharp positions only the small image
works), 3.4 Mill Hoist (a counterweight beam: balance `m1·d1 = m2·d2`, then
just a little more - too much and it flings the ball).

- Every station is graded by running its engine; each has three stars
  (it works / efficient / mastery), a prediction bonus, three hint tiers
  (the Blueprint only after two failed runs), and **Open in the lab** links
  that reproduce the station in the matching experiment.
- Every student gets a seeded **variant** of the station facts (the same
  method works, copied numbers don't); `?practice=1&v=0..4` plays any
  variant without saving. The same players and SQLite file as the quiz;
  scores are derived from the recorded runs.
- The correct setting for every station and variant, with game and lab
  deep links, is saved by `tools/make_game_solutions.py`
  (`physlab/game/data/<hall>.json`, `docs/game/hall1-solutions.md`,
  `docs/game/hall2-solutions.md`, `docs/game/hall3-solutions.md`).
- Every working run also **scores 0-1000** (1000 = the best possible for
  your variant: the lowest drop, the cheapest salt-and-time delivery, the
  fastest safe run, a dead-centre trick shot); personal bests and a top-5
  per station on this computer make a highscore to chase.
- **Test mode (the default for now):** every hall and every station is
  open, so you can jump straight into any hall. The classroom order - a hall
  opens when every station of the one before it works, a station when the
  one before it works - comes back with `PHYSLAB_GAME_LOCKS=on
  python3 -m physlab.server 8600`. The station's settings and the Test / Run machine buttons sit right
  under the machine. The camera can follow the ball; a share box copies a link to the
  exact setup; lab pages offer a way back to the station.
- Progress and to-dos: `docs/game/IMPLEMENTATION-hall1.md`,
  `docs/game/IMPLEMENTATION-hall2.md`, `docs/game/IMPLEMENTATION-hall3.md`.

API: `GET /api/game`, `GET /api/game/hall`, `POST /api/game/run`,
`POST /api/game/hint`.

### Learn panel

Under every experiment there is a panel that explains it:

- **The big idea** in two or three sentences.
- **Formulas explained** — every formula with your live numbers, a
  plain-words version, a table of its symbols with units, why it works,
  and a "try it" experiment.
- **See it in the simulation** — real screenshots of the simulation at
  a chosen moment, with numbered callouts (hover a note to highlight
  it). **▶ Try this setup** opens exactly that set-up, paused at that
  moment, so you can play on from there.
- **In real life** — where the same physics shows up (guitar strings,
  icebergs, pendulum clocks, fuses, ...), each linked to its formula.

The content lives in `physlab/learn.py`. `tests/test_learn.py` checks
that every formula is explained, every figure set-up is valid, and the
key numbers quoted in the text match what the engine computes. Update the
screenshots with `python3 tools/make_figures.py`.

### Deep links

Any set-up can be shared as a link. The URL updates while you play:
`#/pendulum?length=0.5&cmp=1&b.length=2&view.arrows=velocity&at=1.2`.
`b.*` opens compare mode, `view.*` sets view toggles, and `at` plays up to
that time and pauses there.

Playback runs on simulation time: each scene declares its time-lapse
(shown on screen), and frames are interpolated, so topics can record at
whatever cadence their physics needs.

The topic registry is data-driven: a new experiment is a solver module,
a registry entry, a scene file and its learning content - not framework
code.

### Presets

Every experiment has one-click presets (e.g. "Magnifying glass",
"Box vs ball race", "Car lift"), defined with the learning content.
They are deep links, like the figures' "Try this setup" buttons.

### Zoomable stage

`PL.Stage` is the shared simulation canvas: crisp on high-DPI screens,
zoom with Ctrl/⌘ + scroll, trackpad or touch pinch, double-click, or the
− / + / fit bar (plain scroll zooms once the canvas has been clicked, so
the page still scrolls), drag to pan. Lenses, Pressure and Energy Ramp
draw in world units through its camera (`cam.X(x)`, `cam.Y(y)`,
`cam.len(d)`), so geometry zooms while text and lines stay sharp; the
older scenes are magnified as a whole. Scenes can also register
draggable or clickable handles (`cam.handle({x, y, r, drag, click})`)
that edit parameters - the candle, the start flag, the sandbox ramp's
points and the circuit board's gaps all use this.

## Quick start

```sh
python3 -m unittest discover -s tests   # 459 tests, offline, loopback only
python3 -m physlab.server 8600          # then open http://127.0.0.1:8600
```

No packages to install. Any modern browser works; nothing ever leaves
your machine.

## Layout

- `physlab/` — registry (`__init__.py`), per-topic solvers
  (`topics/`), validating API + static server (`server.py`)
- `www/` — the whole client, built from reusable pieces:
  `js/ui.js` page components (layout, presets, compare, controls, play
  bar, results, learning panel), `js/stage.js` zoomable canvas,
  `js/player.js` simulation-time playback, `js/widgets.js` canvas
  drawing kit (labels, arrows, legends, energy bars, force diagrams,
  graphs, scale bars, sprites), `js/core.js` pure helpers (frame
  interpolation, deep links, camera), and one painter per experiment
  (`js/scenes.js` for the first three, `js/scene_<topic>.js` after that);
  `js/quiz.js` the challenge pages; `js/sandbox.js` the sandbox pages
  (a generic builder turns the server's field list into controls) and
  `js/scene_circuitlab.js` the circuit board; `js/main.js` only routes and wires
  them together; the older software 3D renderer (`js/objects3d.js`)
  and particle kit (`js/particles.js`) remain available to new scenes
- `www/icons/` — topic icon set (flat vector-style, kid-friendly),
  AI-generated with Codex's built-in image generation and downscaled
  to 128px; cards fall back to emoji automatically if an icon is
  missing
- `www/sprites/` — simulation item sprites (lamp, battery, switch,
  resistor, block, ball, ramp, wire), same AI source. The client keys
  out their white background at load (tinting is available and cached).
  The circuit uses the battery and resistor sprites; parts whose look
  must carry physics (lamp glow and filament colour, material blocks,
  balls in compare colours) are drawn in code, with simple fallbacks
  if a sprite is missing
- `physlab/quiz.py` — challenges, outcome metrics and grading;
  `physlab/quizdb.py` — the SQLite store (players, attempts, reveals)
- `physlab/sandbox.py` — sandbox catalogs (every playable item and world
  property, with fixed values), field specs, presets, strict validation
  and the mapping onto the engines; `physlab/topics/circuitlab.py` — the
  nodal-analysis solver behind the circuit board
- `physlab/learn.py` — explanations, figure set-ups + callouts, real-life uses
- `www/learn/` — figure screenshots, captured from the real app by
  `tools/make_figures.py` (dev-time: Playwright + Pillow;
  `--preview DIR` paints the callouts on copies to check their placement)
- `www/js/core.js` — pure helpers (frame interpolation, deep links,
  sandbox links, the ramp spline), unit tested with Node by `tests/test_client.py` (skipped without Node)
- `tools/make_sprites.py` — regenerates the procedural sprites (pendulum
  bob, pivot clamp, wave shaker, hand, candle, eye, car, crate; the game's
  toy hopper, salt bag, spring cannon, toy box, Gizmo, ore cart, kettle,
  latch coil, crane magnet, ladle, grain sack, hay cart, bucket and
  millstone hopper) and the Bounces and Levers & Moments icons in the same
  flat style; a
  dev-time script (needs Pillow), the app itself stays dependency-free
- `physlab/game/` — the game: `common.py` (knob validation, variants,
  star rules), `kit.py` (what every hall shares: the saved table, texts,
  scores, the machine run with connectors and time-lapse zones),
  `bounce_factory.py`, `foundry.py` and `mill.py` (each hall's stations
  and layout),
  `service.py` (the API logic), `db.py` (its SQLite tables), and
  `data/` (the generated correct settings); `www/js/game.js` the game
  pages, `www/js/scene_game.js` the hall engine (camera, ball, HUD,
  time-lapse, a shared drawing kit) and one painter per hall
  (`www/js/hall_bounce.js`, `www/js/hall_foundry.js`, `www/js/hall_mill.js`);
  `tools/make_game_solutions.py` regenerates the correct settings
- `docs/game/` — the game design document, its design calculator
  (`level_math.py`), the checklists of the three halls and their
  correct-settings tables
- `tests/` — physics postconditions, API edges, determinism gates,
  and a fixture generator (`tests/gen_fixtures.py`) whose output must
  regenerate byte-identically; the game's stations and knobs
  (`test_game.py`, `test_foundry.py`, `test_mill.py`; the Hall 3 lab work in
  `test_levers.py`), its API (`test_game_api.py`) and an end-to-end browser
  test (`test_game_browser.py`, Playwright; skipped without it)

## Design rules

1. The engine lives in Python; the browser is a thin panel + renderer.
2. Same validated params -> byte-identical frames, always.
3. Every input is validated against the topic's spec at the API edge.
4. Stdlib only (the quiz uses the stdlib's sqlite3). No build step, no CDN,
   no webcam, no accounts.

MIT licensed. See LICENSE.
