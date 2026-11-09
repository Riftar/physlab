/* physlab scene: PENDULUM (one, or two side by side in compare mode).
   Every force on the bob is an arrow on one shared newton->pixel scale:
   weight (mg), string tension (towards the pivot), and the restoring part
   of gravity mg sin(theta) - the force that actually drives the swing -
   drawn as the dashed decomposition of the weight. Energy bars show
   kinetic and potential energy trading places (and what drag removes).
   Wind (sandbox weather, from the left): streaks drift at the true wind
   speed on the metre->pixel scale, the air force on the bob is drawn as
   one arrow (it has a part along the swing AND one along the string),
   and a dashed line marks the lean angle the bob swings about. */
(function () {
  "use strict";
  var D = PL.draw;
  var COL = { weight: "#c792ea", tension: "#7dffa8", restore: "#ffb347", drag: "#ff5c8a", vel: "#5cd6ff" };

  function bobRadius(mass) { return 9 + 10 * Math.cbrt(mass); }   // same brass: size ~ cbrt(mass)

  var pendulum = {
    continuous: false,
    options: [{ id: "arrows", label: "Arrows", default: "forces",
                choices: [{ id: "forces", label: "forces" }, { id: "velocity", label: "velocity" },
                          { id: "off", label: "off" }] }],

    duration: function (runs) {
      return Math.max.apply(null, runs.map(function (r) {
        var f = r.result.frames; return f[f.length - 1].t;
      }));
    },

    init: function (ctx, w, h, runs) {
      var multi = runs.length > 1, pivotY = 92;
      var lmax = Math.max.apply(null, runs.map(function (r) { return r.params.length; }));
      var smax = Math.max.apply(null, runs.map(function (r) {     // widest point actually reached
        return Math.max.apply(null, r.result.frames.map(function (f) { return Math.abs(f.x); })
          .concat([r.params.length * Math.sin(r.params.amplitude * Math.PI / 180)]));
      }));
      // one metre->pixel scale for every pendulum, so lengths compare truly
      var scale = Math.min(300 / lmax, (multi ? 250 : 380) / Math.max(smax, 1e-6));
      var pivots = multi ? [w * 0.36, w * 0.66] : [w / 2];
      if (runs.some(function (r) { return r.result.viz.wind; })) {
        // wind blows the bobs to one side: lay the pendulums out by the
        // range each one really covers, left to right, so they never overlap
        var ext = runs.map(function (r) {
          var xs = r.result.frames.map(function (f) { return f.x; });
          return [Math.min(0, Math.min.apply(null, xs)), Math.max(0, Math.max.apply(null, xs))];
        });
        var gap = 70, x0 = 80, x1 = w - 180;
        var total = ext.reduce(function (acc, e) { return acc + (e[1] - e[0]); }, 0);
        scale = Math.min(300 / lmax, (x1 - x0 - gap * (runs.length - 1)) / Math.max(total, 1e-6));
        var used = total * scale + gap * (runs.length - 1), cur = x0 + (x1 - x0 - used) / 2;
        pivots = ext.map(function (e) { var pv = cur - e[0] * scale; cur += (e[1] - e[0]) * scale + gap; return pv; });
      }
      var wmax = Math.max.apply(null, runs.map(function (r) { return r.params.mass * r.params.g; }));
      this.geo = { pivotY: pivotY, scale: scale, pivots: pivots, pxPerN: 56 / wmax };
      this.trails = runs.map(function () { return []; });
      var R = PL.widgets.rng(77);
      this.wind = runs[0].result.viz.wind || 0;
      this.streaks = [];
      for (var i = 0; i < 40; i++) this.streaks.push({ x: R() * w, y: 40 + R() * (h - 90), k: 0.7 + R() * 0.6 });
    },

    render: function (ctx, w, h, simT, clock, runs, view) {
      var g = this.geo, multi = runs.length > 1, that = this;
      ctx.clearRect(0, 0, w, h);
      var theme = runs[0].result.viz.theme;
      if (theme && theme.sky) {                     // sandbox: the planet's sky
        var sky = ctx.createLinearGradient(0, 0, 0, h);
        sky.addColorStop(0, theme.sky); sky.addColorStop(1, "#0b1128");
        ctx.fillStyle = sky; ctx.fillRect(0, 0, w, h);
      }
      if (this.wind) {                              // wind streaks at the true wind speed
        var vpx = this.wind * g.scale, len = Math.min(70, Math.max(18, Math.abs(vpx) * 0.08));
        ctx.lineWidth = 2; ctx.lineCap = "round";
        this.streaks.forEach(function (q) {
          q.x += vpx * q.k * clock.sim;
          if (q.x > w + 80) q.x -= w + 160; else if (q.x < -80) q.x += w + 160;
          var tail = q.x - len * q.k * Math.sign(vpx);
          var gr = ctx.createLinearGradient(q.x, 0, tail, 0);
          gr.addColorStop(0, "rgba(169,187,239,0.55)"); gr.addColorStop(1, "rgba(169,187,239,0)");
          ctx.strokeStyle = gr;
          ctx.beginPath(); ctx.moveTo(q.x, q.y); ctx.lineTo(tail, q.y); ctx.stroke();
        });
        ctx.lineCap = "butt";
      }

      // ceiling beam
      ctx.fillStyle = "#3b4a78"; ctx.fillRect(60, g.pivotY - 34, w - 120, 12);
      ctx.fillStyle = "#2a3560";
      for (var x = 66; x < w - 66; x += 14) ctx.fillRect(x, g.pivotY - 46, 6, 12);

      var hudLines = [], bars = [];
      runs.forEach(function (run, ri) {
        var p = run.params, res = run.result, f = PL.frameAt(res.frames, simT, { hold: ["swings"] });
        var px = g.pivots[ri], py = g.pivotY, L = p.length * g.scale;
        var th0 = p.amplitude * Math.PI / 180;
        var bx = px + f.x * g.scale, by = py - f.y * g.scale;
        var col = multi ? run.color : "#ffd166";

        // swing arc (where the bob can go) + vertical reference
        ctx.setLineDash([4, 6]); ctx.strokeStyle = D.rgba(col, 0.35); ctx.lineWidth = 1.5;
        var thLo = -th0, thHi = th0;
        if (res.viz.wind) {                             // in wind the swing is not symmetric: use what happened
          if (res._thr == null) {
            var ths = res.frames.map(function (q) { return q.theta; });
            res._thr = [Math.min.apply(null, ths), Math.max.apply(null, ths)];
          }
          thLo = res._thr[0]; thHi = res._thr[1];
        }
        ctx.beginPath(); ctx.arc(px, py, L, Math.PI / 2 - thHi, Math.PI / 2 - thLo); ctx.stroke();
        ctx.strokeStyle = "rgba(160,180,230,0.35)";
        ctx.beginPath(); ctx.moveTo(px, py); ctx.lineTo(px, py + L + 24); ctx.stroke();
        ctx.setLineDash([]);

        // wind: the lean angle it swings about
        if (res.viz.wind) {
          var lean = res.viz.lean;
          ctx.setLineDash([3, 5]); ctx.strokeStyle = "rgba(169,187,239,0.8)"; ctx.lineWidth = 1.5;
          ctx.beginPath(); ctx.moveTo(px, py);
          ctx.lineTo(px + Math.sin(lean) * (L + 30), py + Math.cos(lean) * (L + 30)); ctx.stroke(); ctx.setLineDash([]);
          D.label(ctx, "wind lean " + (lean * 180 / Math.PI).toFixed(1) + "°", px + Math.sin(lean) * (L + 34),
                  py + Math.cos(lean) * (L + 34) + 12, "#a9bbef", "11px system-ui", "center");
        }

        // angle arc at the pivot
        var th = f.theta, ar = Math.min(54, L * 0.35);
        ctx.strokeStyle = "#ffd166"; ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(px, py, ar, Math.PI / 2, Math.PI / 2 - th, th > 0);
        ctx.stroke();
        D.label(ctx, "θ = " + (th * 180 / Math.PI).toFixed(1) + "°", px + (th >= 0 ? 8 : -8),
                py + ar + 16, "#ffd166", "bold 12px system-ui", th >= 0 ? "left" : "right");

        // sandbox bobs are drawn at their true size (and colour) on the metre scale
        var spec = res.viz.bob, rb = spec ? Math.max(4, spec.d / 2 * g.scale) : bobRadius(p.mass);
        var off = spec ? 0 : rb * 0.2;                 // the sprite's ball sits a little below its hook

        // motion trail (the last ~0.35 s), conveys speed and direction
        var trail = that.trails[ri];
        if (clock.real > 0 || trail.length === 0) trail.push([bx, by, simT]);
        while (trail.length && trail[trail.length - 1][2] < trail[0][2]) trail.shift();   // after replay
        while (trail.length && simT - trail[0][2] > 0.35) trail.shift();
        trail.forEach(function (q, i) {
          ctx.fillStyle = D.rgba(col, 0.04 + 0.2 * i / trail.length);
          ctx.beginPath(); ctx.arc(q[0], q[1], rb * 0.6, 0, 7); ctx.fill();
        });

        // string + length label
        ctx.strokeStyle = "#e8ecf8"; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.moveTo(px, py); ctx.lineTo(bx, by); ctx.stroke();
        var mx = px + (bx - px) * 0.72, my = py + (by - py) * 0.72;     // clear of the angle label
        var lside = th >= 0 ? -1 : 1;                  // opposite side to the angle label
        D.label(ctx, "L = " + p.length.toFixed(2) + " m", mx + 10 * lside, my, "#cfd8f0",
                "11px system-ui", lside > 0 ? "left" : "right");

        // pivot clamp + bob
        if (!PL.drawSprite(ctx, "clamp", px, py - 24, 64)) {
          ctx.fillStyle = "#e0455a"; ctx.fillRect(px - 12, py - 40, 24, 34);
        }
        ctx.fillStyle = "#dfe5f2"; ctx.beginPath(); ctx.arc(px, py, 4, 0, 7); ctx.fill();
        if (spec) {
          var bg = ctx.createRadialGradient(bx - rb * 0.35, by - rb * 0.35, 1, bx, by, rb);
          bg.addColorStop(0, "#ffffff"); bg.addColorStop(0.35, spec.color); bg.addColorStop(1, D.rgba(spec.color, 0.75));
          ctx.fillStyle = bg; ctx.beginPath(); ctx.arc(bx, by, rb, 0, 7); ctx.fill();
          ctx.strokeStyle = "#0b1128"; ctx.lineWidth = 1; ctx.stroke();
        } else if (!PL.drawSprite(ctx, "bob", bx, by, rb * 2.5)) {
          ctx.fillStyle = "#d6a53e"; ctx.beginPath(); ctx.arc(bx, by, rb, 0, 7); ctx.fill();
        }
        if (multi) {
          ctx.strokeStyle = col; ctx.lineWidth = 3;
          ctx.beginPath(); ctx.arc(bx, by + off, rb * 1.08 + (spec ? 3 : 0), 0, 7); ctx.stroke();
          if (!spec || rb > 9) D.label(ctx, run.label, bx, by + off + 4, "#1b2a55", "bold 12px system-ui", "center");
        }
        if (run.name) D.label(ctx, run.name, bx, by + off + rb * 1.2 + 16, col, "bold 11px system-ui", "center");

        // arrows from the bob centre (screen y points down)
        var cx = bx, cy = by + off;
        var s = Math.sin(th), c = Math.cos(th), k = g.pxPerN;
        if (view.arrows === "forces") {
          var W = p.mass * p.g, wl = W * k;
          // weight and its two components (dashed): along the string and along the swing
          D.arrow(ctx, cx, cy, cx, cy + wl, COL.weight, 3, 9);
          var rl = f.f_restore * k;                     // signed, along +theta tangent
          var tx = c, ty = -s;                          // +theta tangent on screen
          ctx.setLineDash([5, 4]);
          D.arrow(ctx, cx, cy, cx - tx * rl, cy - ty * rl, COL.restore, 3, 9);
          var radial = W * c * k;                       // weight component along the string (outwards)
          D.arrow(ctx, cx, cy, cx + s * radial, cy + c * radial, "rgba(199,146,234,0.55)", 2, 7);
          ctx.setLineDash([]);
          // tension: towards the pivot
          var tl = f.tension * k;
          D.arrow(ctx, cx, cy, cx - s * tl, cy - c * tl, COL.tension, 3, 9);
          if (p.drag > 0 && (Math.abs(f.f_drag) > 1e-4 || f.f_air_r)) {
            // air force: along the swing, plus (in wind) along the string (outwards = (s, c) on screen)
            var dl = f.f_drag * k, dr = (f.f_air_r || 0) * k;
            D.arrow(ctx, cx, cy, cx + tx * dl + s * dr, cy + ty * dl + c * dr, COL.drag, 3, 8);
          }
          var tag = multi ? run.label + " " : "";
          var side = ri === 0 || !multi ? 1 : -1;
          D.label(ctx, tag + "mg " + W.toFixed(1) + " N", cx + 8 * side, cy + wl + 4, COL.weight,
                  "11px system-ui", side > 0 ? "left" : "right");
          D.label(ctx, tag + "tension " + f.tension.toFixed(1) + " N", cx - s * tl + 8 * side, cy - c * tl - 4,
                  COL.tension, "11px system-ui", side > 0 ? "left" : "right");
          if (Math.abs(rl) > 6) {
            // label just beyond the arrow tip, on the side it points to
            var dirx = -tx * Math.sign(rl), ex = cx - tx * rl + dirx * 8;
            D.label(ctx, tag + "restoring " + Math.abs(f.f_restore).toFixed(1) + " N", ex,
                    cy - ty * rl + 16, COL.restore, "bold 11px system-ui", dirx < 0 ? "right" : "left");
          }
        } else if (view.arrows === "velocity") {
          var vl = f.v * 40;                            // 40 px per m/s
          D.arrow(ctx, cx, cy, cx + c * vl, cy - s * vl, COL.vel, 3, 9);
          D.label(ctx, Math.abs(f.v).toFixed(2) + " m/s", cx + c * vl, cy - s * vl - 8, COL.vel,
                  "bold 11px system-ui", "center");
        }

        var sw = Math.floor(f.swings);                 // a counter: never use the interpolated value
        var full = Math.floor(sw / 2), half = sw % 2;
        hudLines.push({ text: (multi ? run.label + "  " : "") + "t = " + f.t.toFixed(2) + " s   swings: " +
                       (full === 0 && half ? "½" : full + (half ? "½" : "")) + "   speed " +
                       Math.abs(f.v).toFixed(2) + " m/s   period " +
                       (res.viz.period_wind || res.viz.period_exact).toFixed(3) + " s" + (res.viz.wind ? " (about the lean)" : ""),
                       color: multi ? col : "#8fd3ff" });
        if (res.viz.wind) {
          // the wind does work on the bob: no fixed total, scale to the most it ever has
          if (res._emax == null) res._emax = Math.max.apply(null, res.frames.map(function (q) { return q.ke + q.pe; }));
          bars.push({ title: (multi ? run.label + " " : "") + "energy", color: multi ? col : "#cfe0ff",
                      total: res._emax || 1e-9, text: (f.ke + f.pe).toFixed(3) + " J",
                      segments: [{ value: f.pe, color: "#5c9dff" }, { value: f.ke, color: "#ff9a5c" }] });
        } else {
          bars.push({ title: (multi ? run.label + " " : "") + "energy", color: multi ? col : "#cfe0ff",
                      total: res.viz.energy0 || 1e-9, text: (f.ke + f.pe).toFixed(2) + " J",
                      segments: [{ value: f.pe, color: "#5c9dff" }, { value: f.ke, color: "#ff9a5c" },
                                 { value: Math.max(0, (res.viz.energy0 || 0) - f.ke - f.pe), color: "#6b7390" }] });
        }
      });

      D.hud(ctx, hudLines);
      // stacked energy bars: height (PE) + speed (KE) + lost to drag = start energy
      D.energyBars(ctx, { x: w - 150 + (runs.length > 1 ? 0 : 35), y: h - 60, H: 150, bw: 34, gap: 36,
                          bars: bars, keys: [["height (PE)", "#5c9dff"], ["speed (KE)", "#ff9a5c"]],
                          keyX: w - 150 });
      if (view.arrows === "forces") {
        var items = [["weight mg", COL.weight], ["string tension", COL.tension],
                     ["restoring part of gravity (mg sin θ)", COL.restore]];
        if (runs.some(function (r) { return r.params.drag > 0; })) {
          items.push([that.wind ? "air force (drag + wind push)" : "air drag", COL.drag]);
        }
        D.legend(ctx, items, 12, h - 10);
        D.label(ctx, "one N scale", w - 12, h - 10, "#9fb3e8", "11px system-ui", "right");
      }
    }
  };

  PL.scenes.pendulum = pendulum;
})();
