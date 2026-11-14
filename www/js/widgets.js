/* physlab widgets: the shared canvas drawing kit every scene uses.

   Primitives:   label, hud, arrow, rgba, clamp, niceStep/niceUp, speedTag,
                 rng (seeded), tempColor (fixed palette), Path (arc length),
                 sprites (PL.drawSprite; the list is PL.SPRITES)
   Components:   legend      swatch + text row
                 energyBars  stacked "where did the energy go" bars
                 forceBox    free-body diagram: every force, one N scale
                 timeGraph   value-vs-time panel with a reference line
                 scaleBar    "5 cm" style scale bar
   All draw in screen pixels; world-space scenes convert with their camera
   (cam.X / cam.Y, see core.js). Exported as PL.widgets (and PL.draw, the
   older name). */
(function () {
  "use strict";
  window.PL = window.PL || {};

  PL.SPRITES = ["lamp", "battery", "switch", "resistor", "block", "ball", "ramp", "wire",
                "bob", "clamp", "oscillator", "hand", "candle", "eye", "car", "crate",
                "hopper", "saltbag", "cannon", "toybox", "gizmo", "minecart", "kettle", "coil", "magnet", "ladle",
                "grainsack", "haycart", "bucket", "millstone"];

  /* ---- sprite assets: white-keyed at load, tintable ---- */
  PL.sprites = {};
  (function loadSprites() {
    PL.SPRITES.forEach(function (name) {
        var img = new Image();
        img.onload = function () {
          var c = document.createElement("canvas");
          c.width = img.width; c.height = img.height;
          var x = c.getContext("2d");
          x.drawImage(img, 0, 0);
          var d = x.getImageData(0, 0, c.width, c.height);
          for (var i = 0; i < d.data.length; i += 4) {
            if (d.data[i] > 238 && d.data[i + 1] > 238 && d.data[i + 2] > 238) {
              d.data[i + 3] = 0;
            }
          }
          x.putImageData(d, 0, 0);
          PL.sprites[name] = c;
        };
        img.src = "sprites/item_" + name + ".png";
      });
  })();

  /* draw a sprite centered at (cx, cy), size s; optional tint color
     via multiply composite clipped to the sprite's own alpha. Tinted
     copies are cached per (sprite, tint). Optional rotation (radians). */
  var tintCache = {};
  PL.drawSprite = function (ctx, name, cx, cy, s, tint, rot) {
    var spr = PL.sprites[name];
    if (!spr) return false;
    var c = spr;
    if (tint) {
      var key = name + "|" + tint;
      c = tintCache[key];
      if (!c) {
        c = document.createElement("canvas");
        c.width = spr.width; c.height = spr.height;
        var x = c.getContext("2d");
        x.drawImage(spr, 0, 0);
        x.globalCompositeOperation = "multiply";
        x.fillStyle = tint;
        x.fillRect(0, 0, c.width, c.height);
        x.globalCompositeOperation = "destination-in";
        x.drawImage(spr, 0, 0);
        tintCache[key] = c;
      }
    }
    if (rot) {
      ctx.save(); ctx.translate(cx, cy); ctx.rotate(rot);
      ctx.drawImage(c, -s / 2, -s / 2, s, s);
      ctx.restore();
    } else {
      ctx.drawImage(c, cx - s / 2, cy - s / 2, s, s);
    }
    return true;
  };

  /* ---------- shared helpers ---------- */

  /* PL.frameAt lives in core.js */

  function clamp(x, lo, hi) { return Math.max(lo, Math.min(hi, x)); }

  function hexToRgb(hex) {
    var n = parseInt(hex.slice(1), 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }
  function rgba(hex, a) {
    var c = hexToRgb(hex);
    return "rgba(" + c[0] + "," + c[1] + "," + c[2] + "," + clamp(a, 0, 1).toFixed(3) + ")";
  }

  function hud(ctx, lines, x, y) {
    ctx.font = "13px ui-monospace, Menlo, monospace";
    ctx.textAlign = "left";
    lines.forEach(function (l, i) {
      if (!l) return;
      var text = typeof l === "string" ? l : l.text;
      ctx.fillStyle = typeof l === "string" ? "#8fd3ff" : l.color;
      ctx.fillText(text, x == null ? 12 : x, (y == null ? 20 : y) + i * 17);
    });
  }

  function arrow(ctx, x1, y1, x2, y2, color, width, head) {
    var dx = x2 - x1, dy = y2 - y1, len = Math.hypot(dx, dy);
    if (len < 1) return;
    head = Math.min(head || 9, len * 0.6);
    var ux = dx / len, uy = dy / len;
    ctx.strokeStyle = color; ctx.fillStyle = color; ctx.lineWidth = width || 2.5;
    ctx.beginPath(); ctx.moveTo(x1, y1);
    ctx.lineTo(x2 - ux * head * 0.8, y2 - uy * head * 0.8); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x2, y2);
    ctx.lineTo(x2 - ux * head - uy * head * 0.5, y2 - uy * head + ux * head * 0.5);
    ctx.lineTo(x2 - ux * head + uy * head * 0.5, y2 - uy * head - ux * head * 0.5);
    ctx.closePath(); ctx.fill();
  }

  function label(ctx, text, x, y, color, font, align) {
    ctx.font = font || "12px system-ui, sans-serif";
    ctx.textAlign = align || "left";
    ctx.fillStyle = color || "#eef2ff";
    ctx.fillText(text, x, y);
    ctx.textAlign = "left";
  }

  function niceStep(range) {
    var raw = Math.max(range, 1e-6) / 8, mag = Math.pow(10, Math.floor(Math.log10(raw)));
    return [1, 2, 5, 10].map(function (m) { return m * mag; })
      .reduce(function (a, b) { return Math.abs(b - raw) < Math.abs(a - raw) ? b : a; });
  }

  function niceUp(x) {          // smallest 1/2/5 x 10^n that is >= x
    if (x <= 0) return 1;
    var mag = Math.pow(10, Math.floor(Math.log10(x)));
    var m = [1, 2, 5, 10].filter(function (k) { return k * mag >= x - 1e-12; })[0];
    return m * mag;
  }

  function speedTag(s) {
    if (Math.abs(s - 1) < 0.01) return "real time";
    if (s < 1) return "slow motion ×" + s.toPrecision(2);
    return "time-lapse ×" + (s >= 100 ? Math.round(s) : s.toPrecision(2));
  }

  /* deterministic PRNG so a given set-up always looks the same */
  function rng(seed) {
    var a = seed >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) >>> 0;
      var t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  /* fixed temperature palette, -20..150 C (the slider range), so the
     same temperature is always the same colour in every experiment */
  var T_STOPS = [[-20, [48, 80, 255]], [10, [79, 184, 255]], [30, [226, 232, 205]],
                 [60, [255, 179, 71]], [100, [255, 90, 54]], [150, [255, 31, 90]]];
  function tempRgb(t) {
    if (t <= T_STOPS[0][0]) return T_STOPS[0][1];
    for (var i = 1; i < T_STOPS.length; i++) {
      if (t <= T_STOPS[i][0]) {
        var a = T_STOPS[i - 1], b = T_STOPS[i], k = (t - a[0]) / (b[0] - a[0]);
        return [0, 1, 2].map(function (j) { return Math.round(a[1][j] + (b[1][j] - a[1][j]) * k); });
      }
    }
    return T_STOPS[T_STOPS.length - 1][1];
  }
  function tempColor(t, a) {
    var c = tempRgb(t);
    return a == null ? "rgb(" + c.join(",") + ")" : "rgba(" + c.join(",") + "," + a + ")";
  }

  /* polyline with arc-length lookup (for charges flowing round a loop) */
  function Path(pts) {
    this.pts = pts; this.cum = [0];
    for (var i = 1; i < pts.length; i++) {
      this.cum.push(this.cum[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
    }
    this.len = this.cum[this.cum.length - 1];
  }
  Path.prototype.at = function (s) {
    s = ((s % this.len) + this.len) % this.len;
    var lo = 0, hi = this.cum.length - 1;
    while (hi - lo > 1) { var m = (lo + hi) >> 1; if (this.cum[m] <= s) lo = m; else hi = m; }
    var seg = (this.cum[hi] - this.cum[lo]) || 1, k = (s - this.cum[lo]) / seg;
    var a = this.pts[lo], b = this.pts[hi];
    return [a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k];
  };


  /* ---------------- components ---------------- */

  /* a row of [text, colour] items; colour null = plain text. Returns end x. */
  function legend(ctx, items, x, y, font, gap) {
    gap = gap == null ? 14 : gap;
    ctx.font = font || "11px system-ui, sans-serif";
    ctx.textAlign = "left";
    items.forEach(function (it) {
      if (it[1]) { ctx.fillStyle = it[1]; ctx.fillRect(x, y - 8, 9, 9); x += 13; }
      ctx.fillStyle = "#cfe0ff"; ctx.fillText(it[0], x, y);
      x += ctx.measureText(it[0]).width + gap;
    });
    return x;
  }

  /* stacked bars, each normalised to its own total:
     opts = {x, y (bottom), H, bw, gap, keys: [[name, colour]],
             bars: [{title, color, total, text, segments: [{value, color}]}]} */
  function energyBars(ctx, o) {
    var H = o.H || 150, bw = o.bw || 34, gap = o.gap || 36, n = o.bars.length;
    o.bars.forEach(function (b, i) {
      var x = o.x + i * (bw + gap), y0 = o.y, y = y0, tot = b.total || 1e-12;
      ctx.fillStyle = "rgba(20,30,62,0.85)"; ctx.fillRect(x - 8, y0 - H - 38, bw + 16, H + 62);
      b.segments.forEach(function (sg) {
        var hh = Math.max(0, sg.value / tot) * H;
        ctx.fillStyle = sg.color; ctx.fillRect(x, y - hh, bw, hh); y -= hh;
      });
      ctx.strokeStyle = "#cfe0ff"; ctx.lineWidth = 1; ctx.strokeRect(x, y0 - H, bw, H);
      label(ctx, b.title, x + bw / 2, y0 - H - 22, b.color || "#cfe0ff", "bold 11px system-ui", "center");
      if (b.text) label(ctx, b.text, x + bw / 2, y0 - H - 8, "#cfe0ff", "10px system-ui", "center");
    });
    if (o.keys) {
      var kx = o.keyX != null ? o.keyX : o.x - 8;
      o.keys.forEach(function (k, i) {
        label(ctx, "■ " + k[0], kx + (o.keyStep || 70) * i, o.y + 14, k[1], "10px system-ui");
      });
    }
    return n;
  }

  /* free-body diagram. forces: [{name, value (+ = up), color, dx, dashed}]
     scale: pixels per newton. Values too small to see are skipped. */
  function forceBox(ctx, r, forces, scale, opts) {
    opts = opts || {};
    ctx.fillStyle = "rgba(11,17,40,0.88)"; ctx.fillRect(r.x, r.y, r.w, r.h);
    ctx.strokeStyle = "#2f3f72"; ctx.lineWidth = 1; ctx.strokeRect(r.x, r.y, r.w, r.h);
    label(ctx, opts.title || "forces on the object", r.x + r.w / 2, r.y + 16, "#cfe0ff",
          "bold 12px system-ui", "center");
    var cx = r.x + (opts.cx || 50), cy = r.y + r.h / 2 + 8, rows = [];
    forces.forEach(function (f) {
      if (Math.abs(f.value) * scale < 1.5) return;
      if (f.dashed) ctx.setLineDash([4, 3]);
      arrow(ctx, cx + (f.dx || 0), cy, cx + (f.dx || 0), cy - f.value * scale, f.color, 3, 8);
      ctx.setLineDash([]);
      var v = Math.abs(f.value);
      rows.push([f.name + " " + v.toFixed(v >= 100 ? 1 : 2) + " N " + (f.value > 0 ? "↑" : "↓"), f.color]);
    });
    ctx.fillStyle = "#e8ecf8"; ctx.beginPath(); ctx.arc(cx, cy, 3.5, 0, 7); ctx.fill();
    rows.forEach(function (row, i) {
      label(ctx, row[0], r.x + (opts.textX || 92), r.y + 44 + i * 18, row[1], "bold 11px system-ui");
    });
    if (opts.balanced) {
      label(ctx, opts.balanced, r.x + r.w / 2, r.y + r.h - 8, "#7dffa8", "bold 11px system-ui", "center");
    }
  }

  /* value-vs-time panel. o = {x, y, w, h, tEnd, lo, hi,
       series: [{points: [[t, v], ...], color}], ref: {v, text, color},
       unit, legend: [[name, colour]]} */
  function timeGraph(ctx, o) {
    var x0 = o.x, y0 = o.y, gw = o.w, gh = o.h, lo = o.lo, hi = o.hi;
    if (hi - lo < 1e-9) { lo -= 1; hi += 1; }
    var X = function (t) { return x0 + (t / (o.tEnd || 1)) * gw; };
    var Y = function (v) { return y0 + gh - (v - lo) / (hi - lo) * gh; };
    ctx.fillStyle = "rgba(20,30,62,0.85)"; ctx.fillRect(x0 - 40, y0 - 8, gw + 48, gh + 30);
    ctx.strokeStyle = "#2f3f72"; ctx.lineWidth = 1; ctx.strokeRect(x0, y0, gw, gh);
    if (o.ref) {
      ctx.setLineDash([4, 4]); ctx.strokeStyle = o.ref.color || "#7dffa8";
      ctx.beginPath(); ctx.moveTo(x0, Y(o.ref.v)); ctx.lineTo(x0 + gw, Y(o.ref.v)); ctx.stroke();
      ctx.setLineDash([]);
      label(ctx, o.ref.text, x0 + gw - 2, Y(o.ref.v) - 3, o.ref.color || "#7dffa8", "10px system-ui", "right");
    }
    o.series.forEach(function (s) {
      if (!s.points.length) return;
      ctx.strokeStyle = s.color; ctx.lineWidth = 2; ctx.beginPath();
      s.points.forEach(function (p, i) { i ? ctx.lineTo(X(p[0]), Y(p[1])) : ctx.moveTo(X(p[0]), Y(p[1])); });
      ctx.stroke();
    });
    var u = o.unit || "";
    label(ctx, hi.toFixed(0) + u, x0 - 4, y0 + 8, "#9fb3e8", "10px system-ui", "right");
    label(ctx, lo.toFixed(0) + u, x0 - 4, y0 + gh, "#9fb3e8", "10px system-ui", "right");
    label(ctx, "0", x0, y0 + gh + 13, "#9fb3e8", "10px system-ui");
    label(ctx, "time →  " + (o.tEnd || 0).toFixed(0) + " s", x0 + gw, y0 + gh + 13, "#9fb3e8", "10px system-ui", "right");
    (o.legend || []).forEach(function (l, i) {
      label(ctx, "━ " + l[0], x0 + 40 + 32 * i, y0 + gh + 13, l[1], "bold 10px system-ui");
    });
  }

  /* a nice-length scale bar: pxPerUnit pixels per unit, labelled in unit */
  function scaleBar(ctx, x, y, pxPerUnit, unit, maxPx) {
    maxPx = maxPx || 120;
    var len = niceStep(maxPx / pxPerUnit * 8), px = len * pxPerUnit;
    while (px > maxPx) { len /= 2; px = len * pxPerUnit; }
    ctx.strokeStyle = "#cfe0ff"; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(x, y - 4); ctx.lineTo(x, y); ctx.lineTo(x + px, y); ctx.lineTo(x + px, y - 4); ctx.stroke();
    label(ctx, +len.toPrecision(3) + " " + unit, x + px + 6, y + 3, "#cfe0ff", "11px system-ui");
  }

  PL.widgets = PL.draw = {
    clamp: clamp, rgba: rgba, hexToRgb: hexToRgb, hud: hud, arrow: arrow, label: label,
    niceStep: niceStep, niceUp: niceUp, speedTag: speedTag, rng: rng, tempColor: tempColor,
    T_STOPS: T_STOPS, Path: Path,
    legend: legend, energyBars: energyBars, forceBox: forceBox, timeGraph: timeGraph, scaleBar: scaleBar
  };
})();
