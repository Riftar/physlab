# physlab

See the formula happen. Physics experiments for 10-15 year olds: turn
the knobs, run the experiment, and the real formula with live numbers
sits next to the thing it describes. Runs entirely offline with zero
dependencies — Python stdlib server, vanilla JS/canvas client.

## Experiments (v1)

- **Electric Circuits** — battery, switch, 1-3 lamps, series resistor.
  Current from Kirchhoff's loop law `I = V / (R + r)`, lamp glow from
  real power `P = I²R`. More lamps = dimmer. Open the switch and it all
  stops.
- **Projectile Motion** — launch speed, angle, gravity, air drag, wind.
  Integrates `a = -g - (k/m)·v·|v|` per tick; with drag at zero the
  flight matches `Range = v0²·sin(2θ)/g` exactly (the test suite checks).
- **Heat Transfer** — two blocks, four materials, optional heat leak to
  the room. `Q = m·c·ΔT` exchange until both meet at the weighted mean.

More topics (buoyancy, waves, pendulum, lenses, pressure, energy) are
registered as placeholders with their formulas — the topic registry is
data-driven, so a new experiment is a solver module plus a registry
entry, not framework code.

## Quick start

```sh
python3 -m unittest discover -s tests   # 22 tests, offline, loopback only
python3 -m physlab.server 8600          # then open http://127.0.0.1:8600
```

No packages to install. Any modern browser works; nothing ever leaves
your machine.

## Layout

- `physlab/` — registry (`__init__.py`), per-topic solvers
  (`topics/`), validating API + static server (`server.py`)
- `www/` — the whole client: control panel + formula panel kit
  (`js/ui.js`), software 3D renderer (`js/objects3d.js`), particle
  effects (`js/particles.js`), scene painters (`js/scenes.js`)
- `www/icons/` — topic icon set (flat vector-style, kid-friendly),
  AI-generated with Codex's built-in image generation and downscaled
  to 128px; cards fall back to emoji automatically if an icon is
  missing
- `tests/` — physics postconditions, API edges, determinism gates,
  and a fixture generator (`tests/gen_fixtures.py`) whose output must
  regenerate byte-identically

## Design rules

1. The engine lives in Python; the browser is a thin panel + renderer.
2. Same validated params -> byte-identical frames, always.
3. Every input is validated against the topic's spec at the API edge.
4. Stdlib only. No build step, no CDN, no webcam, no accounts.

MIT licensed. See LICENSE.
