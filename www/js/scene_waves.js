/* physlab scene: WAVES ON A ROPE.
   The shaker (left) moves the rope end up and down; the rope shape comes
   from the server's finite-difference solution. Visual cues:
     - a red bead: a piece of rope only moves UP and DOWN (its velocity
       arrow), while the wave shape travels sideways
     - a crest marker riding one crest at the wave speed v
     - a lambda ruler (v = f lambda) and a metre scale
     - the steady standing-wave envelope with its nodes, once reflections
       have had time to build it
     - a resonance ladder: the rope's f_n marked on a frequency axis with
       your shaking frequency as a pointer
   The run is periodic once steady, so after the simulated time ends the
   last shake period loops seamlessly. */
(function () {
  "use strict";
  var D = PL.draw;

  function playbackAuto(res) {
    var vz = res.viz;
    var cross = vz.length / vz.v;                  // time to cross the rope
    var f = 1 / vz.period;
    return Math.min(1, cross / 1.5, 1.5 / f);       // front takes >= 1.5 s; <= 1.5 shakes/s
  }

  var waves = {
    continuous: true,
    options: [{ id: "speed", label: "Speed", default: "auto",
                choices: [{ id: "auto", label: "auto" }, { id: "1", label: "real time" },
                          { id: "0.25", label: "×¼" }, { id: "0.1", label: "×1/10" }] }],

    speed: function (t, runs, view) {
      if (view && view.speed && view.speed !== "auto") return +view.speed;
      var res = runs[0].result, s0 = playbackAuto(res);
      var cap = Math.min(1, 1.5 * res.viz.period);
      // slow while the first wave crosses, then up to the cap for the build-up
      return Math.min(Math.max(s0, cap), Math.max(s0, t / 4));
    },

    init: function (ctx, w, h, runs) {
      var res = runs[0].result, vz = res.viz;
      var ymax = 0;
      res.frames.forEach(function (f) {
        for (var i = 0; i < f.y.length; i++) ymax = Math.max(ymax, Math.abs(f.y[i]));
      });
      ymax = Math.max(ymax * vz.unit, vz.amp);
      var x0 = 118, x1 = w - (vz.end === "open" ? 40 : 86);
      this.geo = { x0: x0, x1: x1, base: 222, sx: (x1 - x0) / vz.length, sy: 118 / ymax };
      this.loopT = 0;
    },

    /* time shown: the simulation, then the last period looping */
    _time: function (simT, clock, res) {
      var vz = res.viz;
      if (simT < vz.t_end - 1e-9) { this.loopT = 0; return simT; }
      if (clock.playing) this.loopT = (this.loopT + clock.real * clock.speed) % vz.period;
      return vz.t_end - vz.period + this.loopT;
    },

    render: function (ctx, w, h, simT, clock, runs, view) {
      var res = runs[0].result, p = runs[0].params, vz = res.viz, g = this.geo;
      var tShow = this._time(simT, clock, res);
      var f = PL.frameAt(res.frames, tShow, { forward: ["crest_x"] });
      var X = function (x) { return g.x0 + x * g.sx; };
      var Y = function (y) { return g.base - y * g.sy; };
      ctx.clearRect(0, 0, w, h);

      // metre scale + baseline
      ctx.strokeStyle = "rgba(160,180,230,0.25)"; ctx.setLineDash([3, 6]); ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(g.x0, g.base); ctx.lineTo(g.x1, g.base); ctx.stroke(); ctx.setLineDash([]);
      var step = D.niceStep(vz.length) * 2;
      ctx.font = "10px ui-monospace, Menlo, monospace"; ctx.fillStyle = "#6f86c4"; ctx.textAlign = "center";
      for (var m = 0; m <= vz.length + 1e-9; m += step) {
        ctx.fillRect(X(m), g.base + 150, 1, 6);
        ctx.fillText(m.toFixed(step < 1 ? 1 : 0) + " m", X(m), g.base + 168);
      }
      ctx.textAlign = "left";
      ctx.fillStyle = "rgba(160,180,230,0.4)"; ctx.fillRect(g.x0, g.base + 150, g.x1 - g.x0, 1);

      // steady standing-wave envelope + nodes, once reflections had time to build it
      var built = Math.min(0.5 * vz.t_end, 6 * vz.length / vz.v);
      if (vz.end !== "open" && tShow > built) {
        var a = Math.min(1, (tShow - built) / 1.0);
        ctx.fillStyle = "rgba(143,211,255," + (0.10 * a) + ")";
        ctx.beginPath();
        vz.xs.forEach(function (x, i) { var yy = Y(vz.envelope[i]); i ? ctx.lineTo(X(x), yy) : ctx.moveTo(X(x), yy); });
        for (var i = vz.xs.length - 1; i >= 0; i--) ctx.lineTo(X(vz.xs[i]), Y(-vz.envelope[i]));
        ctx.closePath(); ctx.fill();
        vz.nodes.forEach(function (nx) {
          ctx.fillStyle = "rgba(255,255,255," + (0.9 * a) + ")";
          ctx.beginPath(); ctx.arc(X(nx), g.base, 4, 0, 7); ctx.fill();
          D.label(ctx, "node", X(nx), g.base + 20, "rgba(207,224,255," + a + ")", "10px system-ui", "center");
        });
        if (vz.nodes.length) {
          D.label(ctx, "shaded = steady standing-wave pattern", g.x1, g.base - 128, "rgba(143,211,255," + a + ")",
                  "11px system-ui", "right");
        }
      }

      // far end
      var yEnd = f.y[f.y.length - 1] * vz.unit;
      if (vz.end === "fixed") {
        ctx.fillStyle = "#3b4a78"; ctx.fillRect(g.x1 + 4, g.base - 130, 22, 260);
        ctx.strokeStyle = "#2a3560"; ctx.lineWidth = 2;
        for (var hy = g.base - 126; hy < g.base + 130; hy += 12) {
          ctx.beginPath(); ctx.moveTo(g.x1 + 26, hy); ctx.lineTo(g.x1 + 40, hy + 10); ctx.stroke();
        }
        D.label(ctx, "tied to wall", g.x1 + 16, g.base - 138, "#9fb3e8", "11px system-ui", "center");
      } else if (vz.end === "free") {
        ctx.strokeStyle = "#9aa3b8"; ctx.lineWidth = 5;
        ctx.beginPath(); ctx.moveTo(g.x1 + 8, g.base - 135); ctx.lineTo(g.x1 + 8, g.base + 135); ctx.stroke();
        ctx.strokeStyle = "#ffd166"; ctx.lineWidth = 3;
        ctx.beginPath(); ctx.ellipse(g.x1 + 8, Y(yEnd), 9, 5, 0, 0, 7); ctx.stroke();
        D.label(ctx, "ring slides on pole", g.x1 + 8, g.base - 142, "#9fb3e8", "11px system-ui", "center");
      } else {
        D.label(ctx, "… rope goes on (no echo)", g.x1 - 4, g.base + 40, "#9fb3e8", "11px system-ui", "right");
      }

      // the rope: smooth curve through the solution points
      var pts = vz.xs.map(function (x, i) { return [X(x), Y(f.y[i] * vz.unit)]; });
      var rope = function () {
        ctx.beginPath(); ctx.moveTo(pts[0][0], pts[0][1]);
        for (var i = 1; i < pts.length - 1; i++) {
          var mx = (pts[i][0] + pts[i + 1][0]) / 2, my = (pts[i][1] + pts[i + 1][1]) / 2;
          ctx.quadraticCurveTo(pts[i][0], pts[i][1], mx, my);
        }
        ctx.lineTo(pts[pts.length - 1][0], pts[pts.length - 1][1]);
      };
      ctx.lineCap = "round"; ctx.lineJoin = "round";
      ctx.strokeStyle = "#7a4f1d"; ctx.lineWidth = 8; rope(); ctx.stroke();
      ctx.strokeStyle = "#d9a45b"; ctx.lineWidth = 5; rope(); ctx.stroke();
      if (vz.end === "open") {       // fade the rope off the right edge
        var gr = ctx.createLinearGradient(g.x1, 0, w, 0);
        gr.addColorStop(0, "rgba(217,164,91,1)"); gr.addColorStop(1, "rgba(217,164,91,0)");
        ctx.strokeStyle = gr; ctx.lineWidth = 5;
        var ye = pts[pts.length - 1][1], sl = ye - pts[pts.length - 2][1];   // continue the last slope
        ctx.beginPath(); ctx.moveTo(g.x1, ye);
        ctx.lineTo(w, ye + sl * (w - g.x1) / Math.max(1, g.x1 - pts[pts.length - 2][0])); ctx.stroke();
      }
      ctx.lineCap = "butt";

      // the shaker: box + a rod that moves the rope end
      var yd = Y(f.driver);
      if (!PL.drawSprite(ctx, "oscillator", 60, g.base + 30, 112)) {
        ctx.fillStyle = "#3d84dc"; ctx.fillRect(14, g.base - 10, 80, 76);
      }
      ctx.fillStyle = "#c9ced8"; ctx.fillRect(g.x0 - 6, yd, 12, g.base + 60 - yd);
      ctx.fillStyle = "#ffd166"; ctx.strokeStyle = "#222"; ctx.lineWidth = 1.5;
      ctx.fillRect(g.x0 - 9, yd - 7, 18, 14); ctx.strokeRect(g.x0 - 9, yd - 7, 18, 14);
      var up = Math.cos(2 * Math.PI * tShow / vz.period) >= 0;  // driver velocity sign
      D.arrow(ctx, g.x0 - 28, yd, g.x0 - 28, yd + (up ? -22 : 22), "#ffd166", 2.5, 7);
      D.label(ctx, "shaker: " + (1 / vz.period).toFixed(2) + " Hz, ±" + (vz.amp * 100).toFixed(1) + " cm",
              14, g.base + 104, "#ffd166", "bold 11px system-ui");

      // bead: moves only up and down
      var bx = X(vz.bead_x), byy = Y(f.bead_y);
      ctx.strokeStyle = "rgba(255,110,110,0.35)"; ctx.setLineDash([2, 4]); ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(bx, g.base - 135); ctx.lineTo(bx, g.base + 135); ctx.stroke(); ctx.setLineDash([]);
      var vpx = f.bead_v * g.sy * 0.12;              // velocity arrow: 0.12 s of travel
      if (Math.abs(vpx) > 2) D.arrow(ctx, bx + 14, byy, bx + 14, byy - vpx, "#5cd6ff", 2.5, 7);
      ctx.fillStyle = "#ff5c5c"; ctx.strokeStyle = "#fff"; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.arc(bx, byy, 7, 0, 7); ctx.fill(); ctx.stroke();
      D.label(ctx, "← this bit of rope only moves up & down", bx + 26, byy + 4, "#ff9a9a", "11px system-ui");

      // crest rider: one crest travelling at the wave speed
      if (f.crest_x != null && typeof f.crest_x === "number") {
        var cx = X(f.crest_x);
        ctx.fillStyle = "#ffd166";
        ctx.beginPath(); ctx.moveTo(cx, g.base - 136); ctx.lineTo(cx - 7, g.base - 150); ctx.lineTo(cx + 7, g.base - 150);
        ctx.closePath(); ctx.fill();
        var nearEnd = cx > g.x1 - 170;
        D.label(ctx, "crest → v = " + vz.v.toFixed(2) + " m/s", cx + (nearEnd ? -10 : 10), g.base - 146, "#ffd166",
                "bold 11px system-ui", nearEnd ? "right" : "left");
      }

      // wavelength ruler
      var ly = g.base + 122, lam = vz.lambda * g.sx;
      if (vz.lambda <= vz.length) {
        ctx.strokeStyle = "#ffd166"; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.moveTo(g.x0, ly - 6); ctx.lineTo(g.x0, ly); ctx.lineTo(g.x0 + lam, ly);
        ctx.lineTo(g.x0 + lam, ly - 6); ctx.stroke();
        D.label(ctx, "λ = v / f = " + vz.lambda.toFixed(2) + " m", g.x0 + lam / 2, ly - 8, "#ffd166",
                "bold 12px system-ui", "center");
      } else {
        D.label(ctx, "λ = v / f = " + vz.lambda.toFixed(2) + " m (longer than the rope!)", g.x0, ly - 4,
                "#ffd166", "bold 12px system-ui");
      }

      this._ladder(ctx, w, h, res, p);
      var exag = g.sy / g.sx;
      D.hud(ctx, [
        "t = " + tShow.toFixed(2) + " s   (" + D.speedTag(clock.speed) + ")" +
          (simT >= vz.t_end - 1e-9 ? "   steady: looping one shake" : ""),
        "v = √(T/μ) = " + vz.v.toFixed(2) + " m/s    λ = " + vz.lambda.toFixed(2) + " m",
        { text: "heights drawn ×" + (exag >= 10 ? Math.round(exag) : exag.toFixed(1)) +
                " taller than true scale", color: "#6f86c4" }
      ]);
    },

    /* frequency axis with the rope's resonances and the shaking frequency */
    _ladder: function (ctx, w, h, res, p) {
      var x0 = 118, x1 = w - 40, y = h - 26, fmax = 5.0;
      var X = function (fr) { return x0 + (fr / fmax) * (x1 - x0); };
      ctx.strokeStyle = "#3a4a80"; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(x1, y); ctx.stroke();
      D.label(ctx, "resonances", 14, y + 4, "#9fb3e8", "11px system-ui");
      var vz = res.viz, v = vz.v, L = vz.length;
      var list = [];
      for (var n = 1; n < 60; n++) {
        var fn = vz.end === "fixed" ? n * v / (2 * L) : vz.end === "free" ? (2 * n - 1) * v / (4 * L) : null;
        if (fn == null || fn > fmax) break;
        list.push([n, fn]);
      }
      list.forEach(function (q) {
        ctx.fillStyle = "#7dffa8"; ctx.fillRect(X(q[1]) - 1, y - 8, 2, 16);
        if (list.length <= 14) D.label(ctx, "f" + q[0], X(q[1]), y - 11, "#7dffa8", "10px system-ui", "center");
      });
      if (vz.end === "open") D.label(ctx, "none with an open end", x0 + 8, y - 8, "#7dffa8", "11px system-ui");
      var fx = X(1 / vz.period);
      ctx.fillStyle = "#ffd166";
      ctx.beginPath(); ctx.moveTo(fx, y + 3); ctx.lineTo(fx - 6, y + 14); ctx.lineTo(fx + 6, y + 14); ctx.closePath(); ctx.fill();
      D.label(ctx, "you: " + (1 / vz.period).toFixed(2) + " Hz", fx, y + 24, "#ffd166", "bold 10px system-ui", "center");
    }
  };

  PL.scenes.waves = waves;
})();
