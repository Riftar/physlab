/* physlab scene painters. One painter per ready topic; each consumes the
   frame array(s) from /api/run and never re-derives the physics.

   Scene interface (used by main.js):
     init(ctx, w, h, runs, view)            new result(s) arrived / reset
     render(ctx, w, h, simT, clock, runs, view)
         simT  - simulation time in seconds (frames are interpolated)
         clock - {real, sim, speed, playing, finished}: real / simulated
                 seconds since the last draw and the current time-lapse
         runs  - [{result, params, color, label}] (2 in compare mode)
     speed(simT, runs)   simulated seconds per real second (optional, 1)
     duration(runs)      end of playback (optional, last frame time)
     continuous          keep animating after the end (steady states)
     options             client-only view toggles [{id,label,choices,default}]

   Visual encodings are kept honest and labelled: speeds, sizes, arrow
   lengths and packet counts are proportional to the physical quantity
   they show, and anything exaggerated says so on screen. */
(function () {
  "use strict";
  window.PL = window.PL || {};

  /* shared drawing kit (widgets.js) */
  var W = PL.widgets;
  var clamp = W.clamp, rgba = W.rgba, hud = W.hud, arrow = W.arrow, label = W.label,
      niceStep = W.niceStep, niceUp = W.niceUp, speedTag = W.speedTag, rng = W.rng,
      tempColor = W.tempColor, T_STOPS = W.T_STOPS, Path = W.Path;

  /* =====================================================================
     ELECTRIC CIRCUIT
     Charges are spread evenly along the whole loop - through wires,
     lamps and battery - and all drift at the same speed, because the
     current is the same everywhere in a series loop. Drift speed on
     screen is proportional to the current (the real one is ~0.01-0.4
     mm/s; shown in the legend). Lamp glow uses the server's filament
     temperature, black-body colour and perceived brightness.
     ===================================================================== */
  var ELECTRON_PX_PER_AMP = 110;   // on-screen drift speed per ampere
  var CARRIER_SPACING = 21;        // px between charges (uniform density)

  var circuits = {
    continuous: true,
    options: [{ id: "carriers", label: "Show", default: "electrons",
                choices: [{ id: "electrons", label: "electrons (−)" },
                          { id: "conventional", label: "conventional current (+)" }] }],

    init: function (ctx, w, h, runs) {
      var p = runs[0].params;
      this.phase = 0;
      this.elapsed = 0;
      var L = 175, R = 705, T = 200, B = 395, C = 22;
      var bx = (L + R) / 2, half = 44;
      var lamps = [];
      for (var k = 0; k < p.lamps; k++) lamps.push(L + (R - L) * (k + 1) / (p.lamps + 1));
      // path in CONVENTIONAL current direction: out of battery +, up the
      // right side (switch), right-to-left through the lamps, down the
      // left side (resistor), back into battery -, through the battery
      var pts = [[bx + half, B], [R - C, B], [R, B - C], [R, T + C], [R - C, T]];
      lamps.slice().reverse().forEach(function (cx) {
        pts.push([cx + 20, T], [cx + 7, T - 24], [cx + 9, T - 52], [cx - 9, T - 52],
                 [cx - 7, T - 24], [cx - 20, T]);
      });
      pts.push([L + C, T], [L, T + C], [L, B - C], [L + C, B], [bx - half, B], [bx + half, B]);
      this.geo = { L: L, R: R, T: T, B: B, C: C, bx: bx, half: half, lamps: lamps,
                   path: new Path(pts) };
    },

    render: function (ctx, w, h, simT, clock, runs, view) {
      var run = runs[0], p = run.params, res = run.result, g = this.geo;
      var f = PL.frameAt(res.frames, simT);
      var viz = res.viz || {};
      var I = f.current, flowing = p.closed && I > 0;
      var b = f.brightness, col = f.color, TK = f.filament_k;
      var conventional = view.carriers === "conventional";
      if (clock.playing) this.elapsed += clock.real;
      if (flowing) this.phase += I * ELECTRON_PX_PER_AMP * clock.real;

      ctx.clearRect(0, 0, w, h);
      // the lamps light up the room (additive, scaled by perceived brightness)
      if (b > 0.002) {
        ctx.save(); ctx.globalCompositeOperation = "lighter";
        g.lamps.forEach(function (cx) {
          var r = 90 + 420 * b, gr = ctx.createRadialGradient(cx, g.T - 52, 10, cx, g.T - 52, r);
          gr.addColorStop(0, rgba(col, 0.30 * Math.min(1, b * 1.8)));
          gr.addColorStop(1, rgba(col, 0));
          ctx.fillStyle = gr; ctx.fillRect(cx - r, g.T - 52 - r, 2 * r, 2 * r);
        });
        ctx.restore();
      }

      // ---- wires (chamfered loop); gaps where parts sit ----
      var my = (g.T + g.B) / 2;
      ctx.strokeStyle = "#7b8cc0"; ctx.lineWidth = 4; ctx.lineJoin = "round";
      ctx.beginPath();
      ctx.moveTo(g.bx + g.half, g.B); ctx.lineTo(g.R - g.C, g.B); ctx.lineTo(g.R, g.B - g.C);
      ctx.lineTo(g.R, my + 22);
      ctx.moveTo(g.R, my - 22); ctx.lineTo(g.R, g.T + g.C); ctx.lineTo(g.R - g.C, g.T);
      ctx.lineTo(g.L + g.C, g.T); ctx.lineTo(g.L, g.T + g.C);
      if (p.resistor > 0) { ctx.lineTo(g.L, my - 38); ctx.moveTo(g.L, my + 38); }
      ctx.lineTo(g.L, g.B - g.C); ctx.lineTo(g.L + g.C, g.B); ctx.lineTo(g.bx - g.half, g.B);
      ctx.stroke();

      // ---- battery (+ on the right, as on the sprite) ----
      if (!PL.drawSprite(ctx, "battery", g.bx, g.B, 104)) {
        ctx.fillStyle = "#3ddc84"; ctx.fillRect(g.bx - g.half, g.B - 18, 2 * g.half, 36);
      }
      label(ctx, "−", g.bx - g.half - 16, g.B - 12, "#8fb8ff", "bold 20px system-ui");
      label(ctx, "+", g.bx + g.half + 6, g.B - 12, "#ff9a9a", "bold 20px system-ui");
      label(ctx, p.voltage.toFixed(1) + " V battery  (inside: r = " + p.internal_r.toFixed(1) + " Ω)",
            g.bx, g.B + 40, "#eef2ff", "bold 13px system-ui", "center");

      // ---- resistor on the left side ----
      if (p.resistor > 0) {
        if (!PL.drawSprite(ctx, "resistor", g.L, my, 92, null, Math.PI / 2)) {
          ctx.fillStyle = "#d9b38c"; ctx.fillRect(g.L - 9, my - 30, 18, 60);
        }
        label(ctx, p.resistor.toFixed(0) + " Ω", g.L - 16, my + 4, "#ffd166", "bold 13px system-ui", "right");
        label(ctx, "resistor", g.L - 16, my + 20, "#9fb3e8", "11px system-ui", "right");
      }

      // ---- knife switch on the right side ----
      var sy0 = my + 22, sy1 = my - 22;
      ctx.fillStyle = "#c9d3f0";
      [sy0, sy1].forEach(function (y) { ctx.beginPath(); ctx.arc(g.R, y, 4.5, 0, 7); ctx.fill(); });
      var ang = p.closed ? 0 : -0.75;                          // lever pivots at the bottom contact
      var lx = g.R + Math.sin(-ang) * 44, ly = sy0 - Math.cos(ang) * 44;
      ctx.strokeStyle = p.closed ? "#ffd166" : "#b0b8d8"; ctx.lineWidth = 5; ctx.lineCap = "round";
      ctx.beginPath(); ctx.moveTo(g.R, sy0); ctx.lineTo(lx, ly); ctx.stroke();
      ctx.fillStyle = "#e0455a"; ctx.beginPath(); ctx.arc(lx + (p.closed ? 0 : 3), ly, 5, 0, 7); ctx.fill();
      ctx.lineCap = "butt";
      label(ctx, p.closed ? "switch ON" : "switch OFF", g.R + (p.closed ? 16 : 42), my + 5,
            p.closed ? "#7dffa8" : "#ff8a8a", "bold 12px system-ui");

      // ---- lamps: socket, glass, support wires, filament ----
      var ratedV = viz.lamp_v_rated || 6;
      var filVis = clamp((TK - 750) / 450, 0, 1);     // visible incandescence starts ~800 K
      g.lamps.forEach(function (cx) {
        var gy = g.T - 52;
        // glass bulb
        ctx.beginPath(); ctx.arc(cx, gy, 25, Math.PI * 0.78, Math.PI * 2.22);
        ctx.lineTo(cx + 11, g.T - 24); ctx.lineTo(cx - 11, g.T - 24); ctx.closePath();
        ctx.fillStyle = "rgba(190,205,235,0.14)"; ctx.fill();
        if (b > 0.001) { ctx.fillStyle = rgba(col, Math.min(0.92, 2.4 * b)); ctx.fill(); }
        ctx.strokeStyle = "rgba(210,222,255,0.65)"; ctx.lineWidth = 1.5; ctx.stroke();
        // screw base + socket
        ctx.fillStyle = "#c9a94a"; ctx.fillRect(cx - 11, g.T - 24, 22, 14);
        ctx.strokeStyle = "#8a7230"; ctx.lineWidth = 1;
        for (var s = 0; s < 3; s++) {
          ctx.beginPath(); ctx.moveTo(cx - 11, g.T - 21 + s * 4); ctx.lineTo(cx + 11, g.T - 19 + s * 4); ctx.stroke();
        }
        ctx.fillStyle = "#3a4466"; ctx.fillRect(cx - 20, g.T - 10, 40, 14);
        // support wires + coiled filament
        ctx.strokeStyle = "#9aa3b8"; ctx.lineWidth = 1.2;
        ctx.beginPath(); ctx.moveTo(cx - 7, g.T - 24); ctx.lineTo(cx - 9, gy); ctx.moveTo(cx + 7, g.T - 24);
        ctx.lineTo(cx + 9, gy); ctx.stroke();
        var coil = function () {
          ctx.beginPath(); ctx.moveTo(cx - 9, gy);
          for (var z = 1; z <= 8; z++) ctx.lineTo(cx - 9 + z * 2.25, gy + (z % 2 ? -3 : 3));
          ctx.stroke();
        };
        ctx.lineWidth = 1.6; ctx.strokeStyle = "#4a4f5e"; coil();
        if (filVis > 0) { ctx.strokeStyle = rgba(col, filVis); ctx.lineWidth = 2.2; coil(); }
        if (b > 0.3) { ctx.strokeStyle = "rgba(255,255,255," + Math.min(1, (b - 0.3) * 1.6) + ")"; ctx.lineWidth = 1.2; coil(); }
        label(ctx, ratedV.toFixed(0) + " V lamp", cx, g.T + 22, "#9fb3e8", "11px system-ui", "center");
        label(ctx, p.lamp_r.toFixed(0) + " Ω", cx, g.T + 36, "#ffd166", "bold 12px system-ui", "center");
        if (flowing && I * p.lamp_r > ratedV * 1.1) {
          label(ctx, TK >= 3695 ? "⚠ would melt!" : "⚠ over-volted", cx, g.T - 86, "#ff8a8a", "bold 11px system-ui", "center");
        }
      });

      // ---- charges flowing round the loop ----
      var path = g.path, n = Math.floor(path.len / CARRIER_SPACING), sp = path.len / n;
      var dir = conventional ? 1 : -1;
      for (var i = 0; i < n; i++) {
        var pt = path.at(i * sp + dir * this.phase);
        var inLamp = pt[1] < g.T - 12;           // smaller inside the bulb: keep the filament visible
        var rr = inLamp ? 3.2 : 4.6, sg = inLamp ? 1.6 : 2.4;
        ctx.globalAlpha = (flowing ? 0.95 : 0.45) * (inLamp ? 0.8 : 1);
        ctx.beginPath(); ctx.arc(pt[0], pt[1], rr, 0, 7);
        ctx.fillStyle = conventional ? "#ffcc4d" : "#4da3ff"; ctx.fill();
        ctx.strokeStyle = conventional ? "#fff1c2" : "#cfe6ff"; ctx.lineWidth = 1; ctx.stroke();
        ctx.strokeStyle = conventional ? "#6b4a00" : "#ffffff"; ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.moveTo(pt[0] - sg, pt[1]); ctx.lineTo(pt[0] + sg, pt[1]);
        if (conventional) { ctx.moveTo(pt[0], pt[1] - sg); ctx.lineTo(pt[0], pt[1] + sg); }
        ctx.stroke();
      }
      ctx.globalAlpha = 1;

      // ---- glow halos on top (additive) ----
      if (b > 0.002) {
        ctx.save(); ctx.globalCompositeOperation = "lighter";
        g.lamps.forEach(function (cx) {
          var gy = g.T - 52, r = 26 + 120 * b;
          var gr = ctx.createRadialGradient(cx, gy, 2, cx, gy, r);
          gr.addColorStop(0, rgba(col, Math.min(0.95, 1.5 * b)));
          gr.addColorStop(0.25, rgba(col, Math.min(0.6, 0.8 * b)));
          gr.addColorStop(1, rgba(col, 0));
          ctx.fillStyle = gr; ctx.beginPath(); ctx.arc(cx, gy, r, 0, 7); ctx.fill();
        });
        ctx.restore();
      }

      // ---- readouts + legend ----
      var lampV = I * p.lamp_r;
      hud(ctx, [
        "I = " + I.toFixed(3) + " A  (same in every part of the loop)",
        "each lamp: " + lampV.toFixed(2) + " V, " + (I * I * p.lamp_r).toFixed(2) + " W",
        "filament: " + Math.round(TK) + " K" + (TK < 800 ? "  (too cool to glow)" : ""),
        "light: " + f.lumens.toFixed(f.lumens < 1 ? 3 : 1) + " lm per lamp,  looks " + Math.round(b * 100) + "% bright",
        "energy from battery: " + (p.voltage * I * this.elapsed).toFixed(1) + " J"
      ]);
      var who = conventional
        ? "● + charges show CONVENTIONAL current: out of + , round the loop, into −"
        : "● electrons drift out of − , round the loop, into +  (conventional current I points the other way)";
      label(ctx, who, 14, h - 30, conventional ? "#ffcc4d" : "#7dbdff", "12px system-ui");
      label(ctx, flowing
        ? "Drift speed on screen ∝ current. Real electrons crawl at only " +
          (viz.drift_mm_s != null ? viz.drift_mm_s.toPrecision(2) : "?") +
          " mm/s - but they all start moving at once, so lamps light instantly."
        : "No complete loop → no current: the electrons stay put (they don't get used up).",
        14, h - 12, "#9fb3e8", "12px system-ui");
    }
  };

  /* =====================================================================
     PROJECTILE MOTION
     One common metre->pixel scale for x and y (angles look true), wind
     streaks move at the real wind speed on that same scale, force arrows
     share one newton->pixel scale, and the dashed no-air parabola shows
     what drag costs. Up to two balls (compare mode) share the axes.
     ===================================================================== */
  function beaufort(v) {
    var a = Math.abs(v);
    return a < 0.3 ? "calm" : a < 1.6 ? "light air" : a < 3.4 ? "light breeze"
      : a < 5.5 ? "gentle breeze" : a < 8.0 ? "moderate breeze" : a < 10.8 ? "fresh breeze"
      : a < 13.9 ? "strong breeze" : a < 17.2 ? "near gale" : "gale";
  }

  var motion = {
    continuous: false,
    options: [{ id: "forces", label: "Force arrows", default: "on",
                choices: [{ id: "on", label: "on" }, { id: "off", label: "off" }] }],

    duration: function (runs) {
      return Math.max.apply(null, runs.map(function (r) {
        var f = r.result.frames; return f[f.length - 1].t;
      }));
    },
    speed: function (t, runs) {
      var d = this.duration(runs);
      // blink-short hops in slow motion, very long lobs time-lapsed
      return d < 0.5 ? 0.25 : d < 1 ? 0.5 : d > 10 ? d / 10 : 1;
    },

    init: function (ctx, w, h, runs, view, cam, goal) {
      var xs = [0], ys = [0];
      if (goal && goal.metric === "landing_x") xs.push(goal.min, goal.max * 1.05);   // keep the target in view
      runs.forEach(function (r) {
        r.result.frames.forEach(function (f) { xs.push(f.x); ys.push(f.y); });
      });
      var xmin = Math.min.apply(null, xs), xmax = Math.max.apply(null, xs);
      var ymax = Math.max.apply(null, ys);
      var span0 = Math.max(xmax - xmin, 1e-3);
      // include the no-air path unless it would squash the real flight
      runs.forEach(function (r) {
        if (r.params.drag <= 0) return;
        var vac = r.result.vacuum, vx = vac[vac.length - 1][0];
        var vy = Math.max.apply(null, vac.map(function (q) { return q[1]; }));
        if (vx <= xmin + 2.5 * span0 && vy <= 2.5 * Math.max(ymax, 1e-3)) {
          xmax = Math.max(xmax, vx); ymax = Math.max(ymax, vy);
        }
      });
      var span = Math.max(xmax - xmin, 1e-3);
      var padL = 56, padR = 64, top = 70, ground = h - 46;
      var sc = Math.min((w - padL - padR) / span, (ground - top) / Math.max(ymax, 1e-3));
      var ox = padL + (w - padL - padR - span * sc) / 2 - xmin * sc;
      var maxW = Math.max.apply(null, runs.map(function (r) { return r.params.mass * r.params.g; }));
      this.geo = { sc: sc, ox: ox, ground: ground, top: top, xmin: xmin, xmax: xmax, ymax: ymax,
                   pxPerN: 42 / maxW };
      // wind fields: one shared if the winds match, else one per ball
      var winds = runs.map(function (r) { return r.params.wind; });
      var same = winds.every(function (v) { return v === winds[0]; });
      var R = rng(1234);
      this.fields = (same ? [{ wind: winds[0], color: "#a9bbef", label: "" }]
        : runs.map(function (r) { return { wind: r.params.wind, color: r.color, label: r.label }; }))
        .map(function (fl) {
          fl.parts = [];
          var count = same ? 34 : 24;
          for (var i = 0; i < count; i++) {   // evenly spread sky particles
            fl.parts.push({ x: R() * w, y: top - 30 + R() * (ground - top + 16), k: 0.7 + R() * 0.6 });
          }
          return fl;
        });
    },

    render: function (ctx, w, h, simT, clock, runs, view) {
      var g = this.geo, sc = g.sc;
      var sx = function (x) { return g.ox + x * sc; };
      var sy = function (y) { return g.ground - y * sc; };
      ctx.clearRect(0, 0, w, h);
      var theme = runs[0].result.viz && runs[0].result.viz.theme;     // sandbox: the planet's sky and ground
      if (theme && theme.sky) {
        var skyG = ctx.createLinearGradient(0, 0, 0, g.ground);
        skyG.addColorStop(0, theme.sky); skyG.addColorStop(1, "#0b1128");
        ctx.fillStyle = skyG; ctx.fillRect(0, 0, w, g.ground);
      }

      // ---- grid + ground ----
      var step = niceStep(Math.max(g.xmax - g.xmin, g.ymax));
      var dec = step >= 1 ? 0 : step >= 0.1 ? 1 : 2;
      ctx.fillStyle = (theme && theme.ground) || "#15301f"; ctx.fillRect(0, g.ground, w, h - g.ground);
      ctx.lineWidth = 1; ctx.strokeStyle = "#1f2c54";
      ctx.font = "11px ui-monospace, Menlo, monospace"; ctx.fillStyle = "#6f86c4";
      for (var d = Math.ceil(g.xmin / step) * step; sx(d) <= w - 10; d += step) {
        ctx.beginPath(); ctx.moveTo(sx(d), g.ground); ctx.lineTo(sx(d), 26); ctx.stroke();
        ctx.fillStyle = "#8fb8a0"; ctx.textAlign = "center"; ctx.fillText(d.toFixed(dec) + " m", sx(d), g.ground + 16);
      }
      for (d = step; sy(d) >= 26; d += step) {
        ctx.beginPath(); ctx.moveTo(20, sy(d)); ctx.lineTo(w - 10, sy(d)); ctx.stroke();
        if (sy(d) < 12 + 17 * (runs.length + 1)) continue;      // keep clear of the HUD lines
        ctx.fillStyle = "#6f86c4"; ctx.textAlign = "right"; ctx.fillText(d.toFixed(dec) + " m", sx(g.xmin) - 6 > 40 ? sx(g.xmin) - 6 : 46, sy(d) + 4);
      }
      ctx.textAlign = "left";
      ctx.strokeStyle = "#5fae6e"; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(0, g.ground); ctx.lineTo(w, g.ground); ctx.stroke();

      // ---- wind: streaks move at the true wind speed (same m->px scale) ----
      this.fields.forEach(function (fl) {
        if (Math.abs(fl.wind) < 0.05) return;
        // tail = distance the air moves in ~0.1 s (a motion blur)
        var vpx = fl.wind * sc, len = clamp(Math.abs(vpx) * 0.1, 18, 60) * Math.sign(fl.wind);
        var alpha = 0.3 + 0.45 * Math.abs(fl.wind) / 10;
        ctx.lineWidth = 2; ctx.lineCap = "round";
        fl.parts.forEach(function (q) {
          q.x += vpx * q.k * clock.sim;
          if (q.x > w + 70) q.x -= w + 140; else if (q.x < -70) q.x += w + 140;
          var wob = Math.sin(q.x * 0.02 + q.y) * 2, tail = q.x - len * q.k;
          var gr = ctx.createLinearGradient(q.x, 0, tail, 0);
          gr.addColorStop(0, rgba(fl.color, alpha)); gr.addColorStop(1, rgba(fl.color, 0));
          ctx.strokeStyle = gr;
          ctx.beginPath(); ctx.moveTo(q.x, q.y + wob); ctx.lineTo(tail, q.y + wob); ctx.stroke();
        });
        ctx.lineCap = "butt";
      });

      var multi = runs.length > 1, showForces = view.forces !== "off";
      var info = [];
      runs.forEach(function (run, ri) {
        var p = run.params, res = run.result, frames = res.frames, col = run.color;
        var last = frames[frames.length - 1];
        var f = PL.frameAt(frames, simT);
        var landed = simT >= last.t && res.landed;

        // launcher (on a tower when it's launched from a height)
        var rad = p.angle * Math.PI / 180, h0 = p.height || 0;
        if (h0 > 0 && ri === 0) {
          ctx.fillStyle = "#3a4678"; ctx.fillRect(sx(0) - 26, sy(h0), 26, g.ground - sy(h0));
          ctx.strokeStyle = "#5c6a9c"; ctx.lineWidth = 1; ctx.strokeRect(sx(0) - 26, sy(h0), 26, g.ground - sy(h0));
          label(ctx, "launched " + h0.toFixed(h0 < 10 ? 1 : 0) + " m up", sx(0) - 30, sy(h0) + 14, "#a9bbef",
                "11px system-ui", "right");
        }
        ctx.strokeStyle = rgba(col, 0.9); ctx.lineWidth = 5; ctx.lineCap = "round";
        ctx.beginPath(); ctx.moveTo(sx(0), sy(h0));
        ctx.lineTo(sx(0) + Math.cos(rad) * 40, sy(h0) - Math.sin(rad) * 40); ctx.stroke();
        ctx.lineCap = "butt";

        // no-air parabola (dashed) - what the drag costs
        if (p.drag > 0) {
          var vac = res.vacuum, vend = vac[vac.length - 1];
          ctx.setLineDash([6, 6]); ctx.strokeStyle = rgba(col, 0.45); ctx.lineWidth = 1.6;
          ctx.beginPath();
          vac.forEach(function (q, i) { i ? ctx.lineTo(sx(q[0]), sy(q[1])) : ctx.moveTo(sx(q[0]), sy(q[1])); });
          ctx.stroke(); ctx.setLineDash([]);
          var lx = sx(vend[0]);
          if (lx < w - 20) {
            label(ctx, (multi ? run.label + " " : "") + "no air: " + vend[0].toFixed(1) + " m",
                  lx, g.ground - 8 - ri * 14, rgba(col, 0.8), "11px system-ui", "center");
          } else {
            label(ctx, (multi ? run.label + " " : "") + "no air → " + vend[0].toFixed(0) + " m",
                  w - 12, g.top - 20 + ri * 14, rgba(col, 0.85), "11px system-ui", "right");
          }
        }

        // travelled path
        ctx.strokeStyle = col; ctx.lineWidth = 2.5;
        ctx.beginPath(); ctx.moveTo(sx(0), sy(h0));
        for (var i = 1; i < frames.length && frames[i].t <= simT; i++) ctx.lineTo(sx(frames[i].x), sy(frames[i].y));
        ctx.lineTo(sx(f.x), sy(f.y)); ctx.stroke();

        var bx = sx(f.x), by = sy(f.y) - (f.y <= 0 ? 0 : 0);
        var vax = f.vx - p.wind, vay = f.vy, vair = Math.hypot(vax, vay);
        var fd = Math.hypot(f.fdx, f.fdy), weight = p.mass * p.g;

        // air rushing past the ball (drag only): lines along -v_air
        if (p.drag > 0 && vair > 0.2 && !landed) {
          var ux = vax / vair, uy = vay / vair, ln = clamp(vair * sc * 0.12, 10, 46);
          ctx.strokeStyle = "rgba(200,220,255," + clamp(0.2 + 0.35 * fd / weight, 0.2, 0.85) + ")";
          ctx.lineWidth = 1.3;
          [-7, 0, 7].forEach(function (off) {
            var px = -uy * off, py = ux * off;    // perpendicular offset (world -> screen y flips)
            var x0 = bx - ux * 12 + px, y0 = by + uy * 12 + py;
            ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x0 - ux * ln, y0 + uy * ln); ctx.stroke();
          });
        }

        // ball (sandbox balls wear their own colour, ringed in the run colour)
        var bcol = (res.viz && res.viz.ball_color) || col;
        var gr = ctx.createRadialGradient(bx - 4, by - 16, 2, bx, by - 11, 12);
        gr.addColorStop(0, "#ffffff"); gr.addColorStop(0.25, bcol); gr.addColorStop(1, rgba(bcol, 0.55));
        ctx.fillStyle = gr; ctx.beginPath(); ctx.arc(bx, by - 11, 11, 0, 7); ctx.fill();
        ctx.strokeStyle = bcol !== col ? col : "#0b1128"; ctx.lineWidth = bcol !== col ? 2.5 : 1.5; ctx.stroke();
        if (run.name) label(ctx, run.name, bx + 14, by - 24 - ri * 13, col, "bold 11px system-ui", "left");
        if (multi) label(ctx, run.label, bx, by - 7, "#0b1128", "bold 11px system-ui", "center");

        // free-body arrows: weight and drag on ONE newton->pixel scale
        if (showForces && !landed) {
          var cy = by - 11, maxL = 130;
          var wl = weight * g.pxPerN, tag = multi ? run.label + " " : "";
          // in compare mode, ball A labels sit right of the arrows, B's left
          var lside = ri === 0 ? 1 : -1;
          arrow(ctx, bx, cy, bx, cy + wl, "#c792ea", 3, 9);
          label(ctx, tag + "weight " + weight.toFixed(1) + " N", bx + 8 * lside, cy + wl + 2,
                "#c792ea", "11px system-ui", lside > 0 ? "left" : "right");
          if (p.drag > 0 && fd > 1e-3) {
            var dl = fd * g.pxPerN, clipped = dl > maxL;
            dl = Math.min(dl, maxL);
            var ex = bx + (f.fdx / fd) * dl, ey = cy - (f.fdy / fd) * dl;
            arrow(ctx, bx, cy, ex, ey, "#ff5c8a", 3, 9);
            var dside = multi ? lside : (f.fdx < 0 ? -1 : 1);
            label(ctx, tag + "drag " + fd.toFixed(fd < 10 ? 2 : 0) + " N" + (clipped ? " (arrow cut)" : ""),
                  ex + 6 * dside, ey - 6 - (multi ? ri * 12 : 0), "#ff8aa8", "11px system-ui", dside < 0 ? "right" : "left");
          }
        }

        // landing flag
        if (landed) {
          ctx.strokeStyle = col; ctx.lineWidth = 2;
          ctx.beginPath(); ctx.moveTo(bx, g.ground); ctx.lineTo(bx, g.ground - 30); ctx.stroke();
          ctx.fillStyle = col; ctx.beginPath(); ctx.moveTo(bx, g.ground - 30);
          ctx.lineTo(bx + 14, g.ground - 25); ctx.lineTo(bx, g.ground - 20); ctx.fill();
          var right = bx > w - 90;
          label(ctx, (multi ? run.label + ": " : "") + last.x.toFixed(2) + " m", right ? bx - 6 : bx + 4,
                g.ground - 34 - ri * 16, col, "bold 12px system-ui", right ? "right" : "left");
        }

        info.push({ text: (multi ? run.label + "  " : "") + "t = " + f.t.toFixed(2) + " s   x = " +
                    f.x.toFixed(2) + " m   y = " + f.y.toFixed(2) + " m   speed = " +
                    Math.hypot(f.vx, f.vy).toFixed(1) + " m/s" +
                    (p.drag > 0 ? "   drag = " + fd.toFixed(2) + " N" : ""), color: multi ? col : "#8fd3ff" });
        if (Math.abs(p.wind) >= 0.05 && p.drag === 0) {
          info.push({ text: (multi ? run.label + "  " : "") +
                      "air drag is 0, so the wind cannot push this ball at all", color: "#ffd166" });
        }
      });

      // wind gauge (top right)
      this.fields.forEach(function (fl, i) {
        var y = 22 + i * 20, x = w - 14;
        var txt = (fl.label ? fl.label + " " : "") + "wind " + Math.abs(fl.wind).toFixed(1) + " m/s " +
                  (Math.abs(fl.wind) < 0.05 ? "(calm)" : (fl.wind > 0 ? "→" : "←") + " " + beaufort(fl.wind));
        label(ctx, txt, x, y, fl.label ? fl.color : "#cfe0ff", "bold 12px system-ui", "right");
      });
      info.push({ text: "⏱ " + speedTag(clock.speed), color: "#6f86c4" });
      hud(ctx, info);
      if (showForces) {
        W.legend(ctx, [["arrows (one N scale):", null], ["weight mg", "#c792ea"],
                       ["air drag - always against the ball's motion through the air", "#ff5c8a"]], 12, h - 10, null, 12);
      }
    }
  };

  /* quiz target: a landing zone on the ground */
  motion.drawGoal = function (ctx, w, h, goal) {
    if (goal.metric !== "landing_x") return;
    var g = this.geo, x0 = g.ox + goal.min * g.sc, x1 = g.ox + goal.max * g.sc;
    var xt = g.ox + (goal.target != null ? goal.target : goal.min) * g.sc;
    ctx.fillStyle = "rgba(125,255,168,0.28)"; ctx.fillRect(x0, g.ground - 6, Math.max(3, x1 - x0), 12);
    ctx.strokeStyle = "#7dffa8"; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(xt, g.ground); ctx.lineTo(xt, g.ground - 44); ctx.stroke();
    ctx.fillStyle = "#7dffa8"; ctx.beginPath(); ctx.moveTo(xt, g.ground - 44); ctx.lineTo(xt + 16, g.ground - 38);
    ctx.lineTo(xt, g.ground - 32); ctx.fill();
    label(ctx, "target " + (goal.target != null ? goal.target : goal.min) + " m", xt + 4, g.ground - 50, "#7dffa8",
          "bold 12px system-ui", "center");
  };

  /* =====================================================================
     HEAT TRANSFER
     Two blocks touching, each drawn as ITS material (copper, aluminum,
     iron, or water in a glass tank) at its TRUE size: side = cbrt(m/rho).
     Atoms inside jiggle harder when hotter (exaggerated). Glowing packets
     carry heat across the contact face at a rate proportional to the heat
     flow (each packet is a fixed, labelled number of joules); with a heat
     leak, packets also escape to (or arrive from) the room.
     ===================================================================== */
  var BIG_BLOCK_PX = 190;          // the larger block is drawn this tall
  var LOOK = {
    copper:   { face: ["#e2a06a", "#b87333", "#8a4f22"], edge: "#5e3313", name: "Copper" },
    aluminum: { face: ["#eef1f5", "#c3c9d2", "#98a0ad"], edge: "#6b7380", name: "Aluminum" },
    iron:     { face: ["#8a9099", "#5f6670", "#454b54"], edge: "#2a2e35", name: "Iron" },
    water:    { face: ["#7cc4ff", "#3d8fe0", "#2a6bb8"], edge: "#bfe3ff", name: "Water" }
  };
  var LABEL_COLORS = { a: "#ffd166", b: "#b79cff" };

  function fmtJoules(j) {
    return j >= 1000 ? +(j / 1000).toPrecision(3) + " kJ" : +j.toPrecision(3) + " J";
  }

  function heatSpeed0(res) { return Math.max(1, (res.tau || 1) / 3); }

  var heat = {
    continuous: true,
    options: [{ id: "look", label: "View", default: "real",
                choices: [{ id: "real", label: "real look + atoms" }, { id: "thermal", label: "thermal camera" }] }],

    duration: function (runs) {
      var f = runs[0].result.frames; return f[f.length - 1].t;
    },
    // slow enough at first to watch the fast exchange, then speeds up as
    // the system slows down (the HUD always shows the current factor)
    speed: function (t, runs) { return Math.max(heatSpeed0(runs[0].result), t / 3); },

    init: function (ctx, w, h, runs) {
      var res = runs[0].result, p = runs[0].params, mats = res.materials;
      var contact = w / 2 - 30, table = 392;
      // true relative sizes: side = cbrt(m / rho); one scale for both blocks
      var cm = function (m, rho) { return Math.cbrt(m / rho) * 100; };
      var ca = cm(p.mass_a, mats.a.rho), cb = cm(p.mass_b, mats.b.rho);
      var pxPerCm = clamp(BIG_BLOCK_PX / Math.max(ca, cb), 6, 40);
      var sa = ca * pxPerCm, sb = cb * pxPerCm;
      var R = rng(97 + Math.round(sa * 7 + sb * 13));
      function atoms(x0, s, liquid) {
        var list = [], sp = 13, n = Math.max(1, Math.floor(s / sp)), step = s / n;
        if (liquid) {
          var count = Math.max(2, Math.round(n * n * 0.75));
          for (var i = 0; i < count; i++) {   // evenly spread sky particles
            var a = R() * Math.PI * 2;
            list.push({ x: x0 + 4 + R() * (s - 8), y: table - s + 6 + R() * (s - 10),
                        vx: Math.cos(a), vy: Math.sin(a), ph: R() * 6.3 });
          }
        } else {
          for (var ix = 0; ix < n; ix++) for (var iy = 0; iy < n; iy++) {
            list.push({ x: x0 + (ix + 0.5) * step, y: table - s + (iy + 0.5) * step,
                        ph: R() * 6.3, ph2: R() * 6.3, fq: 0.8 + R() * 0.4 });
          }
        }
        return list;
      }
      this.geo = {
        contact: contact, table: table, pxPerCm: pxPerCm,
        A: { x0: contact - sa, x1: contact, s: sa, mat: mats.a, key: "a",
             atoms: atoms(contact - sa, sa, mats.a.id === "water") },
        B: { x0: contact, x1: contact + sb, s: sb, mat: mats.b, key: "b",
             atoms: atoms(contact, sb, mats.b.id === "water") }
      };
      // one packet = a fixed, "nice" amount of heat chosen so the first
      // second shows ~25 packets; later the rate follows the real flow
      var f0 = res.frames[0];
      var p0 = Math.max(Math.abs(f0.flow), Math.abs(f0.leak_a) + Math.abs(f0.leak_b), 1e-6);
      this.joules = niceUp(p0 * heatSpeed0(res) / 25);
      this.packets = []; this.acc = { flow: 0, a: 0, b: 0 };
      this.clock = 0; this.rand = rng(4242);
    },

    _spawnFlow: function (hot, cold) {
      var g = this.geo, r = this.rand, hmin = Math.min(g.A.s, g.B.s);
      var y = g.table - hmin * (0.1 + 0.8 * r());
      var dh = Math.min(hot.s * 0.7, 70), dc = Math.min(cold.s * 0.7, 70);
      var sgn = hot === g.A ? 1 : -1;
      this.packets.push({ x0: g.contact - sgn * dh * (0.2 + 0.8 * r()), y0: y,
                          x1: g.contact + sgn * dc * (0.2 + 0.8 * r()), y1: y + (r() - 0.5) * 18,
                          age: 0, life: 1.1 + r() * 0.3, wob: r() * 6 });
    },
    _spawnLeak: function (blk, out) {
      var r = this.rand, g = this.geo;
      var x = blk.x0 + blk.s * (0.15 + 0.7 * r()), top = g.table - blk.s;
      var pk = { x0: x, y0: top + 6, x1: x + (r() - 0.5) * 30, y1: top - 60 - r() * 30,
                 age: 0, life: 1.4 + r() * 0.4, wob: r() * 6, leak: true };
      if (!out) { var t0 = pk.x0, t1 = pk.y0; pk.x0 = pk.x1; pk.y0 = pk.y1; pk.x1 = t0; pk.y1 = t1; }
      this.packets.push(pk);
    },

    render: function (ctx, w, h, simT, clock, runs, view) {
      var run = runs[0], p = run.params, res = run.result, g = this.geo;
      var f = PL.frameAt(res.frames, simT);
      var thermal = view.look === "thermal";
      if (clock.playing) this.clock += clock.real;
      var T = { a: f.temp_a, b: f.temp_b };
      ctx.clearRect(0, 0, w, h);

      // ---- heat packets: emission rate = real power x time-lapse / J ----
      var that = this;
      var spawn = function (key, watts, fn) {
        that.acc[key] += Math.abs(watts) * clock.sim / that.joules;
        var k = 0;
        while (that.acc[key] >= 1 && k++ < 12) { that.acc[key] -= 1; fn(); }
        if (that.acc[key] > 1) that.acc[key] = 1;
      };
      if (clock.sim > 0) {
        spawn("flow", f.flow, function () { f.flow > 0 ? that._spawnFlow(g.A, g.B) : that._spawnFlow(g.B, g.A); });
        if (p.loss > 0) {
          spawn("a", f.leak_a, function () { that._spawnLeak(g.A, f.leak_a > 0); });
          spawn("b", f.leak_b, function () { that._spawnLeak(g.B, f.leak_b > 0); });
        }
      }

      // ---- table ----
      ctx.fillStyle = "#3b2f4a"; ctx.fillRect(120, g.table, w - 240, 12);
      ctx.fillStyle = "#2a2236"; ctx.fillRect(120, g.table + 12, w - 240, 6);

      // ---- blocks (A first; B overlaps A's hidden side) ----
      [g.A, g.B].forEach(function (blk) {
        var t = T[blk.key], look = LOOK[blk.mat.id] || LOOK.iron, s = blk.s;
        var dx = 0.22 * s, dy = -0.17 * s, top = g.table - s;
        var water = blk.mat.id === "water";
        var faceFill, topFill, sideFill;
        if (thermal) {
          faceFill = tempColor(t); topFill = tempColor(t + 8); sideFill = tempColor(t - 8);
        } else {
          var lg = ctx.createLinearGradient(blk.x0, top, blk.x1, g.table);
          lg.addColorStop(0, look.face[0]); lg.addColorStop(0.55, look.face[1]); lg.addColorStop(1, look.face[2]);
          faceFill = water ? "rgba(61,143,224,0.55)" : lg;
          topFill = water ? "rgba(124,196,255,0.45)" : look.face[0];
          sideFill = water ? "rgba(42,107,184,0.6)" : look.face[2];
        }
        // side + top faces (oblique)
        ctx.fillStyle = sideFill;
        ctx.beginPath(); ctx.moveTo(blk.x1, top); ctx.lineTo(blk.x1 + dx, top + dy);
        ctx.lineTo(blk.x1 + dx, g.table + dy); ctx.lineTo(blk.x1, g.table); ctx.closePath(); ctx.fill();
        ctx.fillStyle = topFill;
        ctx.beginPath(); ctx.moveTo(blk.x0, top); ctx.lineTo(blk.x0 + dx, top + dy);
        ctx.lineTo(blk.x1 + dx, top + dy); ctx.lineTo(blk.x1, top); ctx.closePath(); ctx.fill();
        // front face
        ctx.fillStyle = faceFill; ctx.fillRect(blk.x0, top, s, s);
        if (water && !thermal) {          // ripples on the surface
          ctx.strokeStyle = "rgba(220,240,255,0.7)"; ctx.lineWidth = 1.5; ctx.beginPath();
          for (var xx = 0; xx <= s; xx += 3) {
            var yy = top + 2 + Math.sin(xx * 0.18 + that.clock * 3) * 1.3;
            xx ? ctx.lineTo(blk.x0 + xx, yy) : ctx.moveTo(blk.x0, yy);
          }
          ctx.stroke();
        }
        ctx.strokeStyle = water ? "rgba(210,235,255,0.9)" : look.edge; ctx.lineWidth = water ? 2 : 1.2;
        ctx.strokeRect(blk.x0, top, s, s);
        // temperature rim (thin, true colour), so real look still shows T
        if (!thermal) { ctx.strokeStyle = tempColor(t, 0.9); ctx.lineWidth = 2; ctx.strokeRect(blk.x0 - 2, top - 2, s + 4, s + 4); }

        // atoms: vibration amplitude + frequency rise with temperature
        if (!thermal) {
          var k = clamp((t + 20) / 170, 0, 1);
          var amp = 0.5 + 3.2 * k, om = 5 + 14 * k, spd = 8 + 46 * k;
          var rad = Math.min(3.3, Math.max(1.6, s / 14));
          ctx.fillStyle = tempColor(t); ctx.strokeStyle = "rgba(11,17,40,0.55)"; ctx.lineWidth = 0.8;
          blk.atoms.forEach(function (a) {
            var x, y;
            if (water) {
              if (clock.playing) {
                a.ph += clock.real * 3;
                a.vx += Math.sin(a.ph * 1.7) * 0.15; a.vy += Math.cos(a.ph * 1.3) * 0.15;
                var m = Math.hypot(a.vx, a.vy) || 1; a.vx /= m; a.vy /= m;
                a.x += a.vx * spd * clock.real; a.y += a.vy * spd * clock.real;
                if (a.x < blk.x0 + 4) { a.x = blk.x0 + 4; a.vx = Math.abs(a.vx); }
                if (a.x > blk.x1 - 4) { a.x = blk.x1 - 4; a.vx = -Math.abs(a.vx); }
                if (a.y < top + 6) { a.y = top + 6; a.vy = Math.abs(a.vy); }
                if (a.y > g.table - 4) { a.y = g.table - 4; a.vy = -Math.abs(a.vy); }
              }
              x = a.x; y = a.y;
            } else {
              x = a.x + amp * Math.sin(om * a.fq * that.clock + a.ph);
              y = a.y + amp * Math.cos(om * a.fq * 1.13 * that.clock + a.ph2);
            }
            ctx.beginPath(); ctx.arc(x, y, rad, 0, 7); ctx.fill(); ctx.stroke();
          });
        }

        // identity + live temperature under each block (A left, B right)
        var lc = LABEL_COLORS[blk.key];
        var side = blk === g.A ? "right" : "left", ax = blk === g.A ? g.contact - 12 : g.contact + 12;
        label(ctx, blk.key.toUpperCase() + " · " + look.name + " · " + p["mass_" + blk.key].toFixed(2) + " kg",
              ax, g.table + 34, lc, "bold 13px system-ui", side);
        label(ctx, t.toFixed(1) + " °C", ax, g.table + 58, tempColor(t), "bold 21px ui-monospace, Menlo, monospace", side);
        label(ctx, "c = " + blk.mat.c + " J/(kg·K) · ρ = " + blk.mat.rho + " kg/m³ · " +
              (s / g.pxPerCm).toFixed(1) + " cm cube", ax, g.table + 76, "#9fb3e8", "11px system-ui", side);
      });

      // contact line
      var hmin = Math.min(g.A.s, g.B.s);
      ctx.strokeStyle = "rgba(255,230,180,0.5)"; ctx.setLineDash([3, 3]); ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(g.contact, g.table); ctx.lineTo(g.contact, g.table - hmin); ctx.stroke();
      ctx.setLineDash([]);

      // ---- packets (additive glow) ----
      ctx.save(); ctx.globalCompositeOperation = "lighter";
      var alive = [];
      this.packets.forEach(function (pk) {
        pk.age += clock.real;
        if (pk.age >= pk.life) return;
        alive.push(pk);
        var u = pk.age / pk.life, e = u * u * (3 - 2 * u);
        var x = pk.x0 + (pk.x1 - pk.x0) * e, y = pk.y0 + (pk.y1 - pk.y0) * e + Math.sin(u * 9 + pk.wob) * (pk.leak ? 4 : 2);
        var a = Math.min(1, u * 5) * (1 - Math.max(0, (u - 0.75) / 0.25));
        var gr = ctx.createRadialGradient(x, y, 0, x, y, 8);
        gr.addColorStop(0, "rgba(255,236,170," + (0.95 * a) + ")");
        gr.addColorStop(0.4, "rgba(255,150,60," + (0.7 * a) + ")");
        gr.addColorStop(1, "rgba(255,120,40,0)");
        ctx.fillStyle = gr; ctx.beginPath(); ctx.arc(x, y, 8, 0, 7); ctx.fill();
      });
      this.packets = alive;
      ctx.restore();

      // ---- temperature-time graph (top right) ----
      this._graph(ctx, w, res, p, simT);
      this._colorbar(ctx, 14, 128, 200);
      this._scalebar(ctx, 14, 176, g.pxPerCm);

      // ---- HUD ----
      var dir = f.flow >= 0 ? "A → B" : "B → A";
      var lines = [
        "t = " + f.t.toFixed(f.t < 10 ? 1 : 0) + " s of lab time   (" + speedTag(clock.speed) + ")",
        { text: "heat flow " + dir + ": " + Math.abs(f.flow).toFixed(Math.abs(f.flow) < 10 ? 2 : 0) + " W", color: "#ffb36b" },
        "heat moved so far: " + (f.q / 1000).toFixed(2) + " kJ",
        p.loss > 0 ? "leak to room: A " + f.leak_a.toFixed(1) + " W, B " + f.leak_b.toFixed(1) + " W" : null,
        { text: "● = " + fmtJoules(this.joules) + " of heat", color: "#ffcf8a" }
      ].filter(Boolean);
      if (Math.abs(f.temp_a - f.temp_b) < 0.05 && simT > 0) {
        lines.push({ text: "✔ same temperature: no more net heat flow", color: "#7dffa8" });
      }
      hud(ctx, lines);
      label(ctx, thermal ? "thermal camera: colour = temperature (scale above)"
                         : "atoms jiggle faster when hotter (motion exaggerated) · true relative sizes: side = ∛(m/ρ)",
            14, h - 8, "#9fb3e8", "11px system-ui");
    },

    _graph: function (ctx, w, res, p, simT) {
      var fr = res.frames;
      // the time axis zooms out as the run goes on, so the fast early
      // exchange is readable even when a heat leak stretches the run
      var tLast = fr[fr.length - 1].t || 1;
      var tEnd = Math.min(tLast, Math.max(simT * 1.35, 6 * (res.tau || 1)));
      var lo = Infinity, hi = -Infinity;
      fr.forEach(function (q) { lo = Math.min(lo, q.temp_a, q.temp_b); hi = Math.max(hi, q.temp_a, q.temp_b); });
      if (p.loss > 0) { lo = Math.min(lo, p.ambient); hi = Math.max(hi, p.ambient); }
      if (hi - lo < 2) { lo -= 1; hi += 1; }
      var cur = PL.frameAt(fr, simT);
      var series = [["temp_a", LABEL_COLORS.a], ["temp_b", LABEL_COLORS.b]].map(function (s) {
        var pts = [];
        for (var i = 0; i < fr.length && fr[i].t <= simT; i++) pts.push([fr[i].t, fr[i][s[0]]]);
        pts.push([Math.min(simT, tEnd), cur[s[0]]]);
        return { points: pts, color: s[1] };
      });
      W.timeGraph(ctx, { x: w - 250, y: 16, w: 234, h: 110, tEnd: tEnd, lo: lo, hi: hi, unit: "°C",
                         series: series, legend: [["A", LABEL_COLORS.a], ["B", LABEL_COLORS.b]],
                         ref: p.loss > 0 ? { v: p.ambient, text: "room " + p.ambient.toFixed(0) + "°" }
                                         : { v: res.readouts[2].value,
                                             text: "meet " + res.readouts[2].value.toFixed(1) + "°" } });
    },

    _scalebar: function (ctx, x, y, pxPerCm) { W.scaleBar(ctx, x, y, pxPerCm, "cm", 120); },

    _colorbar: function (ctx, x, y, wdt) {
      var gr = ctx.createLinearGradient(x, 0, x + wdt, 0);
      T_STOPS.forEach(function (s) { gr.addColorStop((s[0] + 20) / 170, "rgb(" + s[1].join(",") + ")"); });
      ctx.fillStyle = gr; ctx.fillRect(x, y, wdt, 7);
      label(ctx, "-20 °C", x, y + 19, "#9fb3e8", "10px system-ui");
      label(ctx, "temperature colour", x + wdt / 2, y + 19, "#9fb3e8", "10px system-ui", "center");
      label(ctx, "150 °C", x + wdt, y + 19, "#9fb3e8", "10px system-ui", "right");
    }
  };

  window.PL.scenes = PL.scenes || {};
  PL.scenes.circuits = circuits; PL.scenes.motion = motion; PL.scenes.heat = heat;


})();
