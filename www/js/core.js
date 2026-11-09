/* physlab core: pure, DOM-free helpers shared by the client and unit
   tested with Node (tests/js/test_core.js):
     PL.frameAt   interpolate the server's frames at any simulation time
     PL.route     parse / build deep links (#/<topic>?p=v&b.p=v&view.o=v&at=s)
     PL.Camera    world <-> screen mapping, zoom about a point, pan limits
     PL.spline    natural cubic spline (the sandbox ramp; mirrors the server's
                  energy.SplineTrack so a dragged ramp previews instantly)
     PL.sandbox   sandbox deep links: #/sandbox/<topic>?w=<world JSON>, only
                  what differs from the defaults */
(function (root) {
  "use strict";
  var PL = root.PL = root.PL || {};

  /* frame at simulation time t: binary search + linear interpolation of
     every numeric field (non-numeric fields come from the earlier frame).
     opts.hold:    keys that must not be interpolated (counters)
     opts.forward: keys interpolated only while increasing (a tracked
                   position that jumps back when it switches target) */
  PL.frameAt = function (frames, t, opts) {
    var hold = (opts && opts.hold) || [], fwd = (opts && opts.forward) || [];
    var n = frames.length;
    if (n === 1 || t <= frames[0].t) return frames[0];
    if (t >= frames[n - 1].t) return frames[n - 1];
    var lo = 0, hi = n - 1;
    while (hi - lo > 1) {
      var mid = (lo + hi) >> 1;
      if (frames[mid].t <= t) lo = mid; else hi = mid;
    }
    var a = frames[lo], b = frames[hi], k = (t - a.t) / ((b.t - a.t) || 1);
    var out = {};
    for (var key in a) {
      var u = a[key], w = b[key];
      if (hold.indexOf(key) >= 0 || (fwd.indexOf(key) >= 0 && !(w >= u))) {
        out[key] = u;
      } else if (typeof u === "number" && typeof w === "number") {
        out[key] = u + (w - u) * k;
      } else if (Array.isArray(u) && Array.isArray(w) && u.length === w.length) {
        var arr = new Array(u.length);              // e.g. a rope's shape
        for (var j = 0; j < u.length; j++) arr[j] = u[j] + (w[j] - u[j]) * k;
        out[key] = arr;
      } else {
        out[key] = u;
      }
    }
    out.t = t;
    return out;
  };

  /* ---------- deep links ---------- */
  function coerce(p, raw) {
    if (p.kind === "boolean") return raw === "1" || raw === "true";
    if (p.kind === "select") {
      return p.choices.some(function (c) { return c.id === raw; }) ? raw : p.default;
    }
    var v = p.kind === "integer" ? parseInt(raw, 10) : parseFloat(raw);
    if (!isFinite(v)) return p.default;
    return Math.min(p.max, Math.max(p.min, v));
  }

  function parseRoute(hash) {
    var h = (hash || "").replace(/^#\/?/, "");
    if (!h) return null;
    var qi = h.indexOf("?");
    var r = { id: decodeURIComponent(qi < 0 ? h : h.slice(0, qi)), a: {}, b: null, view: {}, at: null };
    (qi < 0 ? "" : h.slice(qi + 1)).split("&").forEach(function (kv) {
      if (!kv) return;
      var i = kv.indexOf("=");
      var k = decodeURIComponent(i < 0 ? kv : kv.slice(0, i));
      var v = i < 0 ? "" : decodeURIComponent(kv.slice(i + 1));
      if (k === "at") r.at = parseFloat(v);
      else if (k === "cmp") r.b = r.b || {};
      else if (k.indexOf("view.") === 0) r.view[k.slice(5)] = v;
      else if (k.indexOf("b.") === 0) (r.b = r.b || {})[k.slice(2)] = v;
      else r.a[k] = v;
    });
    return r;
  }

  function routeHash(t, sets, view, options) {
    var def = {}, parts = [];
    t.params.forEach(function (p) { def[p.id] = p.default; });
    var fmt = function (v) { return typeof v === "boolean" ? (v ? "1" : "0") : String(v); };
    t.params.forEach(function (p) {
      if (sets[0][p.id] !== def[p.id]) parts.push(p.id + "=" + encodeURIComponent(fmt(sets[0][p.id])));
    });
    if (sets.length > 1) {
      parts.push("cmp=1");
      t.params.forEach(function (p) {
        if (sets[1][p.id] !== sets[0][p.id]) parts.push("b." + p.id + "=" + encodeURIComponent(fmt(sets[1][p.id])));
      });
    }
    (options || []).forEach(function (o) {
      if (view[o.id] !== o.default) parts.push("view." + o.id + "=" + encodeURIComponent(view[o.id]));
    });
    return "#/" + t.id + (parts.length ? "?" + parts.join("&") : "");
  }

  PL.route = { parse: parseRoute, hash: routeHash, coerce: coerce };

  /* ---------- camera: world <-> screen for the zoomable stage ----------
     A view of size w x h pixels onto a world measured in any unit.
     s = pixels per world unit, (cx, cy) = world point at the view centre.
     yUp: world y grows upwards (physics); false for pixel "worlds".
     contain: never pan past the fitted box (used for legacy pixel scenes). */
  function Camera(w, h) {
    this.w = w; this.h = h; this.s = 1; this.fitS = 1; this.cx = w / 2; this.cy = h / 2;
    this.yUp = true; this.minZ = 0.25; this.maxZ = 40; this.contain = false;
    this.moved = false; this.box = { x0: 0, x1: w, y0: 0, y1: h };
  }
  Camera.prototype.fit = function (box, pad, yUp) {
    pad = pad == null ? 0.06 : pad;
    this.yUp = yUp !== false;
    var bw = Math.max(box.x1 - box.x0, 1e-9), bh = Math.max(box.y1 - box.y0, 1e-9);
    this.s = this.fitS = Math.min(this.w / (bw * (1 + 2 * pad)), this.h / (bh * (1 + 2 * pad)));
    this.cx = (box.x0 + box.x1) / 2; this.cy = (box.y0 + box.y1) / 2;
    this.box = box; this.moved = false;
    return this;
  };
  Camera.prototype.X = function (x) { return this.w / 2 + (x - this.cx) * this.s; };
  Camera.prototype.Y = function (y) { return this.h / 2 + (this.yUp ? -1 : 1) * (y - this.cy) * this.s; };
  Camera.prototype.len = function (d) { return d * this.s; };
  Camera.prototype.inv = function (px, py) {
    return { x: this.cx + (px - this.w / 2) / this.s,
             y: this.cy + (this.yUp ? -1 : 1) * (py - this.h / 2) / this.s };
  };
  Camera.prototype.zoom = function () { return this.s / this.fitS; };
  Camera.prototype.zoomAt = function (px, py, factor) {
    var p = this.inv(px, py);
    this.s = Math.min(this.fitS * this.maxZ, Math.max(this.fitS * this.minZ, this.s * factor));
    this.cx = p.x - (px - this.w / 2) / this.s;
    this.cy = p.y - (this.yUp ? -1 : 1) * (py - this.h / 2) / this.s;
    this.moved = true;
    this.clampPan();
  };
  Camera.prototype.pan = function (dxPx, dyPx) {
    this.cx -= dxPx / this.s;
    this.cy -= (this.yUp ? -1 : 1) * dyPx / this.s;
    this.moved = true;
    this.clampPan();
  };
  Camera.prototype.clampPan = function () {
    var b = this.box, hw = this.w / (2 * this.s), hh = this.h / (2 * this.s);
    var lim = function (c, lo, hi, half, contain) {
      if (contain) return hi - lo <= 2 * half ? (lo + hi) / 2 : Math.min(hi - half, Math.max(lo + half, c));
      return Math.min(hi + 0.8 * half, Math.max(lo - 0.8 * half, c));   // keep part of the box in view
    };
    this.cx = lim(this.cx, b.x0, b.x1, hw, this.contain);
    this.cy = lim(this.cy, b.y0, b.y1, hh, this.contain);
  };
  /* canvas transform that maps world units to (CSS) pixels */
  Camera.prototype.matrix = function () {
    var sy = this.yUp ? -this.s : this.s;
    return [this.s, 0, 0, sy, this.w / 2 - this.cx * this.s, this.h / 2 - this.cy * sy];
  };
  PL.Camera = Camera;

  /* ---------- natural cubic spline through (xs[i], ys[i]) ----------
     Same maths as physlab/topics/energy.py SplineTrack: moments M_i from
     the tridiagonal system (M_0 = M_n = 0), then y, y', y'' per piece. */
  function Spline(xs, ys) {
    var n = xs.length, m = new Array(n).fill(0);
    if (n >= 3) {
      var a = [], b = [], c = [], d = [];
      for (var i = 0; i < n; i++) { a.push(0); b.push(1); c.push(0); d.push(0); }
      for (i = 1; i < n - 1; i++) {
        var h0 = xs[i] - xs[i - 1], h1 = xs[i + 1] - xs[i];
        a[i] = h0 / 6; b[i] = (h0 + h1) / 3; c[i] = h1 / 6;
        d[i] = (ys[i + 1] - ys[i]) / h1 - (ys[i] - ys[i - 1]) / h0;
      }
      for (i = 1; i < n; i++) { var w = a[i] / b[i - 1]; b[i] -= w * c[i - 1]; d[i] -= w * d[i - 1]; }
      m[n - 1] = d[n - 1] / b[n - 1];
      for (i = n - 2; i >= 0; i--) m[i] = (d[i] - c[i] * m[i + 1]) / b[i];
      m[0] = m[n - 1] = 0;
    }
    this.xs = xs; this.ys = ys; this.m = m; this.x0 = xs[0]; this.x1 = xs[n - 1];
  }
  Spline.prototype.eval = function (x) {
    var xs = this.xs, ys = this.ys, m = this.m, n = xs.length;
    x = Math.min(Math.max(x, this.x0), this.x1);
    var i = 0;
    while (i < n - 2 && xs[i + 1] <= x) i++;
    var h = xs[i + 1] - xs[i], a = (xs[i + 1] - x) / h, b = (x - xs[i]) / h;
    return [a * ys[i] + b * ys[i + 1] + ((a * a * a - a) * m[i] + (b * b * b - b) * m[i + 1]) * h * h / 6,
            (ys[i + 1] - ys[i]) / h - (3 * a * a - 1) * h / 6 * m[i] + (3 * b * b - 1) * h / 6 * m[i + 1],
            a * m[i] + b * m[i + 1]];
  };
  Spline.prototype.polyline = function (n) {
    var out = [];
    for (var i = 0; i <= n; i++) {
      var x = this.x0 + (this.x1 - this.x0) * i / n;
      out.push([x, this.eval(x)[0]]);
    }
    return out;
  };
  /* the same limits the server enforces: ["ground"] dips below 0, ["steep"] */
  Spline.prototype.check = function (maxSlope) {
    var bad = [];
    for (var i = 0; i <= 600; i++) {
      var e = this.eval(this.x0 + (this.x1 - this.x0) * i / 600);
      if (e[0] < -1e-6 && bad.indexOf("ground") < 0) bad.push("ground");
      if (Math.abs(e[1]) > maxSlope && bad.indexOf("steep") < 0) bad.push("steep");
    }
    return bad;
  };
  PL.spline = function (xs, ys) { return new Spline(xs, ys); };

  /* ---------- sandbox worlds in the URL ---------- */
  function same(a, b) { return JSON.stringify(a) === JSON.stringify(b); }
  PL.sandbox = {
    /* only the fields that differ from the defaults */
    diff: function (defaults, world) {
      var out = {};
      Object.keys(world).forEach(function (k) { if (!same(world[k], defaults[k])) out[k] = world[k]; });
      return out;
    },
    hash: function (topic, defaults, world) {
      var d = PL.sandbox.diff(defaults, world);
      return "#/sandbox/" + topic + (Object.keys(d).length ? "?w=" + encodeURIComponent(JSON.stringify(d)) : "");
    },
    /* defaults overlaid with the link's fields (unknown fields dropped; the
       server still validates every value) */
    fromRoute: function (defaults, raw) {
      var w = JSON.parse(JSON.stringify(defaults)), got = null;
      try { got = raw ? JSON.parse(raw) : null; } catch (e) { got = null; }
      if (got && typeof got === "object" && !Array.isArray(got)) {
        Object.keys(got).forEach(function (k) { if (k in defaults) w[k] = got[k]; });
      }
      return w;
    }
  };
})(typeof window !== "undefined" ? window : globalThis);
