/* Unit tests for www/js/core.js (run by tests/test_client.py, or directly:
   node tests/js/test_core.js [routes.json]). No dependencies. */
"use strict";
const assert = require("assert");
const path = require("path");
const fs = require("fs");
require(path.join(__dirname, "..", "..", "www", "js", "core.js"));
const PL = globalThis.PL;
let n = 0;
function test(name, fn) { fn(); n++; }

// ---- frameAt ----
const frames = [
  { t: 0, x: 0, arr: [0, 10], s: "a", c: 0, pos: 3.0 },
  { t: 1, x: 10, arr: [2, 20], s: "b", c: 1, pos: 3.5 },
  { t: 3, x: 30, arr: [4, 40], s: "c", c: 2, pos: 0.2 },
];
test("interpolates numbers linearly", () => {
  assert.strictEqual(PL.frameAt(frames, 0.5).x, 5);
  assert.strictEqual(PL.frameAt(frames, 2).x, 20);
});
test("interpolates arrays element-wise", () => {
  assert.deepStrictEqual(PL.frameAt(frames, 0.5).arr, [1, 15]);
});
test("non-numbers come from the earlier frame", () => {
  assert.strictEqual(PL.frameAt(frames, 0.99).s, "a");
});
test("clamps outside the recorded range", () => {
  assert.strictEqual(PL.frameAt(frames, -1), frames[0]);
  assert.strictEqual(PL.frameAt(frames, 9), frames[2]);
  assert.strictEqual(PL.frameAt([frames[1]], 5), frames[1]);
});
test("t is the requested time", () => { assert.strictEqual(PL.frameAt(frames, 1.7).t, 1.7); });
test("hold keeps counters whole", () => {
  assert.strictEqual(PL.frameAt(frames, 0.5).c, 0.5);
  assert.strictEqual(PL.frameAt(frames, 0.5, { hold: ["c"] }).c, 0);
});
test("forward interpolates only while increasing", () => {
  assert.strictEqual(PL.frameAt(frames, 0.5, { forward: ["pos"] }).pos, 3.25);
  assert.strictEqual(PL.frameAt(frames, 2, { forward: ["pos"] }).pos, 3.5);   // jump back: hold
});
test("binary search finds the right interval in long arrays", () => {
  const fr = []; for (let i = 0; i <= 1000; i++) fr.push({ t: i * 0.01, y: i });
  assert.ok(Math.abs(PL.frameAt(fr, 7.345).y - 734.5) < 1e-9);
});

// ---- routes ----
const topic = { id: "motion", params: [
  { id: "v0", kind: "number", min: 1, max: 50, default: 18 },
  { id: "lamps", kind: "integer", min: 1, max: 3, default: 1 },
  { id: "closed", kind: "boolean", default: true },
  { id: "end", kind: "select", default: "fixed", choices: [{ id: "fixed" }, { id: "open" }] },
] };
const P = (id) => topic.params.find((p) => p.id === id);
test("coerce parses, clamps and validates", () => {
  assert.strictEqual(PL.route.coerce(P("v0"), "12.5"), 12.5);
  assert.strictEqual(PL.route.coerce(P("v0"), "999"), 50);
  assert.strictEqual(PL.route.coerce(P("v0"), "abc"), 18);
  assert.strictEqual(PL.route.coerce(P("lamps"), "2"), 2);
  assert.strictEqual(PL.route.coerce(P("closed"), "0"), false);
  assert.strictEqual(PL.route.coerce(P("end"), "open"), "open");
  assert.strictEqual(PL.route.coerce(P("end"), "sideways"), "fixed");
});
test("parse splits params, compare set, view and seek", () => {
  const r = PL.route.parse("#/motion?v0=20&b.v0=25&view.forces=off&at=1.5");
  assert.strictEqual(r.id, "motion");
  assert.deepStrictEqual(r.a, { v0: "20" });
  assert.deepStrictEqual(r.b, { v0: "25" });
  assert.deepStrictEqual(r.view, { forces: "off" });
  assert.strictEqual(r.at, 1.5);
  assert.deepStrictEqual(PL.route.parse("#/heat?cmp=1").b, {});
  assert.strictEqual(PL.route.parse("#/"), null);
  assert.strictEqual(PL.route.parse(""), null);
});
test("quiz routes parse to quiz/<page>", () => {
  assert.strictEqual(PL.route.parse("#/quiz").id, "quiz");
  assert.strictEqual(PL.route.parse("#/quiz/motion-easy").id, "quiz/motion-easy");
  assert.strictEqual(PL.route.parse("#/quiz/history").id, "quiz/history");
});
test("hash only lists what differs, and round-trips", () => {
  const sets = [{ v0: 20, lamps: 1, closed: true, end: "open" }];
  const h = PL.route.hash(topic, sets, { forces: "on" }, [{ id: "forces", default: "on" }]);
  assert.strictEqual(h, "#/motion?v0=20&end=open");
  const r = PL.route.parse(h);
  assert.strictEqual(PL.route.coerce(P("v0"), r.a.v0), 20);
  const h2 = PL.route.hash(topic, [sets[0], Object.assign({}, sets[0], { v0: 30 })], { forces: "off" },
                           [{ id: "forces", default: "on" }]);
  assert.strictEqual(h2, "#/motion?v0=20&end=open&cmp=1&b.v0=30&view.forces=off");
});

// ---- camera ----
test("fit centres the box and uses the tighter axis", () => {
  const c = new PL.Camera(800, 400).fit({ x0: 0, x1: 100, y0: 0, y1: 20 }, 0);
  assert.strictEqual(c.s, 8);                              // 800 / 100 (width limits)
  assert.strictEqual(c.X(50), 400); assert.strictEqual(c.Y(10), 200);
  assert.strictEqual(c.Y(20), 200 - 80);                   // y up
  const d = new PL.Camera(800, 400).fit({ x0: 0, x1: 10, y0: 0, y1: 10 }, 0.1);
  assert.ok(Math.abs(d.s - 400 / 12) < 1e-12);             // height limits, with padding
});
test("inv is the inverse of X/Y, in both y directions", () => {
  [true, false].forEach((up) => {
    const c = new PL.Camera(880, 500).fit({ x0: -3, x1: 7, y0: -1, y1: 4 }, 0.05, up);
    c.zoomAt(123, 321, 2.5);
    const p = c.inv(c.X(1.234), c.Y(-0.5));
    assert.ok(Math.abs(p.x - 1.234) < 1e-9 && Math.abs(p.y + 0.5) < 1e-9);
  });
});
test("zoomAt keeps the point under the cursor fixed and respects limits", () => {
  const c = new PL.Camera(880, 500).fit({ x0: 0, x1: 10, y0: 0, y1: 5 });
  const before = c.inv(600, 100);
  c.zoomAt(600, 100, 3);
  const after = c.inv(600, 100);
  assert.ok(Math.abs(before.x - after.x) < 1e-9 && Math.abs(before.y - after.y) < 1e-9);
  assert.ok(Math.abs(c.zoom() - 3) < 1e-12);
  c.zoomAt(600, 100, 1e6); assert.strictEqual(c.zoom(), c.maxZ);
  c.zoomAt(600, 100, 1e-9); assert.strictEqual(c.zoom(), c.minZ);
  assert.ok(c.moved);
});
test("pan moves the view; contain keeps pixel scenes on screen", () => {
  const c = new PL.Camera(880, 500).fit({ x0: 0, x1: 880, y0: 0, y1: 500 }, 0, false);
  c.contain = true; c.minZ = 1;
  c.pan(100, 0); assert.strictEqual(c.cx, 440);           // at zoom 1 nothing to pan
  c.zoomAt(440, 250, 2); c.pan(-10000, -10000);
  assert.strictEqual(c.cx, 880 - 220); assert.strictEqual(c.cy, 500 - 125);
  const m = c.matrix();                                    // maps world to the view
  assert.ok(Math.abs(m[0] * 660 + m[4] - 440) < 1e-9);
});

// ---- sandbox deep links ----
test("sandbox routes parse to sandbox/<topic> with the world in w", () => {
  assert.strictEqual(PL.route.parse("#/sandbox").id, "sandbox");
  const w = { balls: ["tennis", "shot_put"], planet: "moon" };
  const h = PL.sandbox.hash("motion", { balls: ["tennis"], planet: "earth", v0: 20 }, Object.assign({ v0: 20 }, w));
  const r = PL.route.parse(h);
  assert.strictEqual(r.id, "sandbox/motion");
  assert.deepStrictEqual(JSON.parse(r.a.w), w);                       // only what differs
});
test("sandbox hash of the default world has no w", () => {
  const d = { track: [8, 3.5, 0.9, 0, 0.9, 3.5, 8], surface: "wood" };
  assert.strictEqual(PL.sandbox.hash("energy", d, JSON.parse(JSON.stringify(d))), "#/sandbox/energy");
});
test("sandbox fromRoute overlays known fields only, and survives junk", () => {
  const d = { balls: ["tennis"], planet: "earth" };
  const w = PL.sandbox.fromRoute(d, JSON.stringify({ planet: "mars", hacker: 1 }));
  assert.deepStrictEqual(w, { balls: ["tennis"], planet: "mars" });
  assert.deepStrictEqual(PL.sandbox.fromRoute(d, "{not json"), d);
  assert.deepStrictEqual(PL.sandbox.fromRoute(d, "[1,2]"), d);
  assert.deepStrictEqual(PL.sandbox.fromRoute(d, null), d);
  w.balls.push("x");
  assert.deepStrictEqual(d.balls, ["tennis"]);                       // defaults are never modified
});

// ---- the client spline is the server's spline (values from Python) ----
if (process.argv[3]) {
  const refs = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
  refs.forEach((ref, i) => {
    test("spline " + i + " " + JSON.stringify(ref.ys), () => {
      const sp = PL.spline(ref.xs, ref.ys);
      ref.samples.forEach((q) => {
        const e = sp.eval(q[0]);
        for (let k = 0; k < 3; k++) assert.ok(Math.abs(e[k] - q[k + 1]) < 1e-9, q[0] + " " + k + ": " + e[k] + " vs " + q[k + 1]);
      });
      assert.deepStrictEqual(sp.check(ref.max_slope), ref.check);
    });
  });
}

// ---- the learning figures' deep links (from Python) parse to their set-ups ----
if (process.argv[2]) {
  const figs = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
  figs.forEach((f) => {
    test("figure route " + f.route, () => {
      const r = PL.route.parse(f.route);
      assert.strictEqual(r.id, f.topic);
      Object.keys(f.params).forEach((k) => {
        const want = f.params[k];
        if (typeof want === "number") assert.strictEqual(parseFloat(r.a[k]), want);
        else assert.strictEqual(r.a[k], String(want));
      });
      assert.deepStrictEqual(Object.keys(r.a).sort(), Object.keys(f.params).sort());
      assert.deepStrictEqual(r.view, f.view);
      assert.strictEqual(r.at, f.at);
      if (f.b) assert.deepStrictEqual(Object.keys(r.b).sort(), Object.keys(f.b).sort());
      else assert.strictEqual(r.b, null);
    });
  });
}
console.log("ok " + n + " client tests");
