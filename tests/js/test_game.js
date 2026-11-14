/* Unit tests for the game helpers in www/js/core.js (PL.game), run by
   tests/test_client.py with a JSON file of reference values computed by the
   Python side (the server is the source of truth):
     camel     energy.CamelTrack.eval samples -> the browser's copy must agree
     knobs     raw slider values -> what physlab/game/common.validate_knobs keeps
     links     the saved Blueprint deep links -> route() must give back the knobs */
"use strict";
const assert = require("assert");
const path = require("path");
const fs = require("fs");
require(path.join(__dirname, "..", "..", "www", "js", "core.js"));
const PL = globalThis.PL;
const ref = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
let n = 0;
function test(name, fn) { fn(); n++; }

test("camel track matches the server to 1e-12", () => {
  ref.camel.forEach(c => {
    const tr = PL.game.camel(c.top, c.hump);
    c.samples.forEach(s => {
      const e = tr.eval(s[0]);
      for (let i = 0; i < 3; i++) assert.ok(Math.abs(e[i] - s[1 + i]) < 1e-12, JSON.stringify([c, s, e]));
    });
  });
});

test("knob values are snapped and clamped exactly like the server", () => {
  ref.knobs.forEach(k => {
    const got = PL.game.knobValue(k.spec, k.raw);
    assert.strictEqual(got, k.expect, JSON.stringify(k));
  });
});

test("missing or bad knobs fall back to the defaults", () => {
  const knobs = [{ id: "hatch", kind: "number", min: 1, max: 4, step: 0.05, default: 1.5 },
                 { id: "pad", kind: "choice", choices: [{ id: "steel_plate" }, { id: "sand" }], default: "sand" }];
  assert.deepStrictEqual(PL.game.knobsFrom(knobs, null), { hatch: 1.5, pad: "sand" });
  assert.deepStrictEqual(PL.game.knobsFrom(knobs, { hatch: "x", pad: "lava" }), { hatch: 1.5, pad: "sand" });
  assert.deepStrictEqual(PL.game.knobsFrom(knobs, { hatch: 9 }), { hatch: 4, pad: "sand" });
});

test("saved Blueprint links open the station with the solution", () => {
  ref.links.forEach(l => {
    const r = PL.game.route(l.game);
    assert.strictEqual(r.hall, l.hall);
    assert.strictEqual(r.station, l.station);
    assert.strictEqual(r.practice, true);
    assert.strictEqual(r.v, l.step);
    assert.deepStrictEqual(r.knobs, l.solution);
  });
});

test("game hashes round-trip", () => {
  const o = { hall: "bounce", station: "1.4", practice: true, v: 3, knobs: { compression: 13.1, angle: 45 }, debug: true };
  const r = PL.game.route(PL.game.hash(o));
  assert.deepStrictEqual(r, { hall: "bounce", station: "1.4", practice: true, v: 3,
                              knobs: { compression: 13.1, angle: 45 }, debug: true });
  assert.strictEqual(PL.game.hash({ hall: "bounce" }), "#/game/bounce");
  assert.strictEqual(PL.game.route("#/game").hall, null);
  assert.strictEqual(PL.game.route("#/motion?v0=3"), null);
  assert.strictEqual(PL.game.route("#/game/bounce/1.1?k=%7Bbroken").knobs, null);    // a broken link: no knobs
  assert.strictEqual(PL.game.hash({ hall: "bounce", station: "1.1", practice: false, v: 2 }), "#/game/bounce/1.1");
});

test("time-lapse: the zone's speed inside it, 1 outside", () => {
  const z = ref.machine.timelapse;
  assert.ok(z.length === 1 && z[0][2] > 1);
  assert.strictEqual(PL.game.timelapse(z, (z[0][0] + z[0][1]) / 2), z[0][2]);
  assert.strictEqual(PL.game.timelapse(z, z[0][1] + 0.01), 1);
  assert.strictEqual(PL.game.timelapse(z, -1), 1);
  assert.strictEqual(PL.game.timelapse(null, 3), 1);
  assert.strictEqual(PL.game.timelapse([[0, 2, 5], [4, 6, 10]], 5), 10);
});

test("station fields along a run: default before, interpolated within, held after", () => {
  const fr = ref.machine.frames;
  ref.machine.probe.forEach(p => {
    Object.keys(p.fields).forEach(key => {
      const got = PL.game.fieldAt(fr, key, p.t, null), want = p.fields[key];
      if (want === null) assert.strictEqual(got, null, key + "@" + p.t);
      else assert.ok(Math.abs(got - want) < 1e-9, key + "@" + p.t + ": " + got + " vs " + want);
    });
  });
  assert.strictEqual(PL.game.fieldAt([], "T", 1, 20), 20);
  assert.strictEqual(PL.game.fieldAt(null, "T", 1, 20), 20);
  assert.strictEqual(PL.game.fieldAt([{ t: 0, x: 0, y: 0 }], "T", 1, 20), 20);      // no such field: the default
});

console.log("game client tests: " + n + " passed");
