/* physlab scene: ENERGY RAMP in world metres (zoomable), one or two
   objects (compare mode) on the same track.
   - drag the start flag along the track to choose the start height
   - a dashed line at the start height: without extra energy nothing
     climbs above it
   - box slides; balls roll - their drawn spin matches rolling without
     slipping (angle = distance / radius, from the server)
   - arrows: weight, normal force and friction on one newton scale, or
     the velocity
   - stacked energy bars: height (PE), motion (KE), spin, heat
   Sandbox ramps (viz.kind "custom"): the student drags the yellow control
   points up and down; the dragged shape previews instantly (PL.spline is
   the same natural cubic spline the server uses) and turns red when it
   breaks a limit; on release the page re-runs the physics. Objects carry
   their own colour/icon; the surface its colour; the planet the sky.   */
(function () {
  "use strict";
  var W = PL.widgets;
  var COL = { pe: "#5c9dff", ke: "#ff9a5c", spin: "#c792ea", heat: "#8a90a8",
              weight: "#c792ea", normal: "#7dffa8", friction: "#ff5c8a", vel: "#5cd6ff" };
  var BOX = 0.9;                    // m, drawn box size

  var energy = {
    continuous: false,
    options: [{ id: "arrows", label: "Arrows", default: "forces",
                choices: [{ id: "forces", label: "forces" }, { id: "velocity", label: "velocity" },
                          { id: "off", label: "off" }] }],
    duration: function (runs) {
      return Math.max.apply(null, runs.map(function (r) { var f = r.result.frames; return f[f.length - 1].t; }));
    },
    world: function (runs) {
      var vz = runs[0].result.viz, top = 8;
      vz.track.forEach(function (q) { top = Math.max(top, q[1]); });
      // room on the right for the energy bars (two in compare mode)
      return { x0: vz.x0 - 2.2, x1: vz.x1 + (runs.length > 1 ? 7.5 : 4.0), y0: -0.8, y1: top + 1.3 };
    },
    worldPad: 0.02,

    drawGoal: function (ctx, w, h, goal, runs, cam) {
      var X = function (x) { return cam.X(x); }, Y = function (y) { return cam.Y(y); };
      if (goal.metric === "height_if_over_hill") {                 // the crest to get over
        ctx.strokeStyle = "#7dffa8"; ctx.lineWidth = 2; ctx.setLineDash([4, 4]);
        ctx.beginPath(); ctx.moveTo(X(14), Y(3.0)); ctx.lineTo(X(14), Y(6.2)); ctx.stroke(); ctx.setLineDash([]);
        W.label(ctx, "get over this hill!", X(14), Y(6.2) - 6, "#7dffa8", "bold 12px system-ui", "center");
      } else if (goal.metric === "max_speed") {                    // the bottom, where the speed is measured
        var vz = runs[0].result.viz, xb = vz.kind === "halfpipe" ? 8 : 7.9, yb = vz.kind === "halfpipe" ? 0 : 0.5;
        ctx.strokeStyle = "#7dffa8"; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(X(xb), Y(yb), 16, 0, 7); ctx.stroke();
        W.label(ctx, "goal: " + (goal.target || goal.min) + " m/s here", X(xb), Y(yb) + 34, "#7dffa8",
                "bold 12px system-ui", "center");
      }
    },

    init: function (ctx, w, h, runs) { this.trails = runs.map(function () { return []; }); this.dragYs = null; },

    render: function (ctx, w, h, simT, clock, runs, view, cam) {
      var vz0 = runs[0].result.viz, X = function (x) { return cam.X(x); }, Y = function (y) { return cam.Y(y); };
      var multi = runs.length > 1, that = this, custom = vz0.kind === "custom";
      ctx.clearRect(0, 0, w, h);
      if (vz0.theme && vz0.theme.sky) {                       // the planet's sky
        var sky = ctx.createLinearGradient(0, 0, 0, h);
        sky.addColorStop(0, vz0.theme.sky); sky.addColorStop(1, "#0b1128");
        ctx.fillStyle = sky; ctx.fillRect(0, 0, w, h);
      }
      var top = 8;
      vz0.track.forEach(function (q) { top = Math.max(top, Math.ceil(q[1] - 1e-9)); });

      // ---- ground + track ----
      var tr = vz0.track;
      ctx.beginPath(); ctx.moveTo(X(tr[0][0]), Y(-1));
      tr.forEach(function (q) { ctx.lineTo(X(q[0]), Y(q[1])); });
      ctx.lineTo(X(tr[tr.length - 1][0]), Y(-1)); ctx.closePath();
      var gg = ctx.createLinearGradient(0, Y(8), 0, Y(-1));
      gg.addColorStop(0, "#2d3f6e"); gg.addColorStop(1, "#182445");
      ctx.fillStyle = gg; ctx.fill();
      ctx.strokeStyle = (vz0.surface && vz0.surface.color) || "#d9a45b"; ctx.lineWidth = custom ? 5 : 4;
      ctx.lineJoin = "round";
      ctx.beginPath(); tr.forEach(function (q, i) { i ? ctx.lineTo(X(q[0]), Y(q[1])) : ctx.moveTo(X(q[0]), Y(q[1])); });
      ctx.stroke();
      if (custom) {                                 // padded end walls (they bounce back half the speed)
        ctx.fillStyle = "#6b7390";
        [[tr[0], -1], [tr[tr.length - 1], 1]].forEach(function (e) {
          ctx.fillRect(X(e[0][0]) + (e[1] < 0 ? -8 : 0), Y(e[0][1] + 1.2), 8, Y(e[0][1]) - Y(e[0][1] + 1.2));
        });
        if (vz0.surface) W.label(ctx, vz0.surface.icon + " " + vz0.surface.label, X((vz0.x0 + vz0.x1) / 2),
                                  Y(-0.45), "#cfd8f0", "12px system-ui", "center");
      }

      // ---- height ruler ----
      var rx = X(vz0.x0 - 1.2);
      ctx.strokeStyle = "#6f86c4"; ctx.lineWidth = 1; ctx.fillStyle = "#6f86c4"; ctx.font = "10px ui-monospace, Menlo, monospace";
      ctx.beginPath(); ctx.moveTo(rx, Y(0)); ctx.lineTo(rx, Y(top)); ctx.stroke();
      for (var m = 0; m <= top; m++) {
        ctx.beginPath(); ctx.moveTo(rx - 4, Y(m)); ctx.lineTo(rx + 4, Y(m)); ctx.stroke();
        ctx.textAlign = "right"; ctx.fillText(m + " m", rx - 6, Y(m) + 3);
      }
      ctx.textAlign = "left";

      // ---- start height line + draggable start flag ----
      runs.forEach(function (run, ri) {
        var st = run.result.viz.start, col = multi ? run.color : "#ffd166";
        ctx.setLineDash([6, 6]); ctx.strokeStyle = W.rgba(col, 0.6); ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.moveTo(rx, Y(st[1])); ctx.lineTo(w, Y(st[1])); ctx.stroke(); ctx.setLineDash([]);
        W.label(ctx, (multi ? run.label + " " : "") + "start height " + st[1].toFixed(2) + " m", X(vz0.x1) - 4,
                Y(st[1]) - 6 - ri * 14, col, "11px system-ui", "right");
        // flag
        var fx = X(st[0]), fy = Y(st[1]);
        ctx.strokeStyle = "#eef2ff"; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.moveTo(fx, fy); ctx.lineTo(fx, fy - 34); ctx.stroke();
        ctx.fillStyle = col; ctx.beginPath(); ctx.moveTo(fx, fy - 34); ctx.lineTo(fx + 16, fy - 28); ctx.lineTo(fx, fy - 22); ctx.fill();
        if (!custom && ri === (multi ? runs.length - 1 : 0)) {
          cam.handle({ x: fx, y: fy - 28, r: 14, cursor: "grab", title: "drag the start flag along the track",
                       drag: function (pt) { that._dragStart(pt, run.result.viz, cam); } });
        }
      });

      // ---- sandbox: the ramp's control points (drag up / down) ----
      if (custom && vz0.points) this._points(ctx, vz0, cam);

      // ---- the objects ----
      var bars = [], hud = [];
      runs.forEach(function (run, ri) {
        var vz = run.result.viz, f = PL.frameAt(run.result.frames, simT, { hold: ["fly"] });
        var col = multi ? run.color : null, p = run.params;
        var nx = -Math.sin(f.phi), ny = Math.cos(f.phi);          // normal (world, up-ish)
        var size = vz.k === 0 ? BOX : 2 * vz.ball_r;
        var cx = f.x + nx * size / 2, cy = f.y + ny * size / 2;
        if (f.fly) { cx = f.x; cy = f.y + size / 2; }

        // trail
        var trail = that.trails[ri];
        if (clock.real > 0 || !trail.length) trail.push([cx, cy, simT]);
        while (trail.length && (simT - trail[0][2] > 0.5 || trail[0][2] > simT)) trail.shift();
        trail.forEach(function (q, i) {
          ctx.fillStyle = W.rgba(col || "#ffd166", 0.05 + 0.25 * i / trail.length);
          ctx.beginPath(); ctx.arc(X(q[0]), Y(q[1]), cam.len(size) * 0.3, 0, 7); ctx.fill();
        });

        var sx = X(cx), sy = Y(cy), spx = cam.len(size);
        ctx.save(); ctx.translate(sx, sy);
        if (vz.k === 0) {
          ctx.rotate(-f.phi);
          var sprite = vz.id === "crate" ? "crate" : "block", tint = vz.id && vz.id !== "crate" ? vz.color : null;
          if (vz.id === "skateboard") {
            ctx.font = Math.round(spx * 1.1) + "px system-ui"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
            ctx.fillText(vz.icon, 0, 0); ctx.textBaseline = "alphabetic"; ctx.textAlign = "left";
          } else if (!PL.drawSprite(ctx, sprite, 0, 0, spx * 1.25, tint)) {
            ctx.fillStyle = vz.color || "#b0b8c8"; ctx.fillRect(-spx / 2, -spx / 2, spx, spx);
          }
        } else {
          ctx.rotate(f.spin);                                  // rolling: angle = distance / r
          var gr = ctx.createRadialGradient(-spx * 0.15, -spx * 0.15, 1, 0, 0, spx / 2);
          var base = vz.color || (vz.k > 0.5 ? "#5cd6ff" : "#ff9a5c");   // default: hollow blue-ish, solid orange
          gr.addColorStop(0, "#ffffff"); gr.addColorStop(0.3, base); gr.addColorStop(1, W.rgba(base, 0.6));
          ctx.fillStyle = gr; ctx.beginPath(); ctx.arc(0, 0, spx / 2, 0, 7); ctx.fill();
          ctx.strokeStyle = "#0b1128"; ctx.lineWidth = 2;
          ctx.beginPath(); ctx.moveTo(-spx / 2, 0); ctx.lineTo(spx / 2, 0); ctx.moveTo(0, -spx / 2); ctx.lineTo(0, spx / 2);
          ctx.stroke();
          ctx.beginPath(); ctx.arc(0, 0, spx / 2, 0, 7); ctx.stroke();
        }
        ctx.restore();
        if (col) {
          ctx.strokeStyle = col; ctx.lineWidth = 3;
          ctx.beginPath(); ctx.arc(sx, sy, spx * 0.62 + 3, 0, 7); ctx.stroke();
          W.label(ctx, run.label, sx, sy - spx * 0.62 - 8, col, "bold 12px system-ui", "center");
        }
        if (run.name && !col) W.label(ctx, run.name, sx, sy - spx * 0.62 - 8, "#eef2ff", "bold 12px system-ui", "center");
        if (run.name && col) W.label(ctx, run.name, sx, sy + spx * 0.62 + 16, col, "11px system-ui", "center");
        if (f.fly) W.label(ctx, "airborne!", sx, sy - spx - 14, "#ffd166", "bold 12px system-ui", "center");

        // arrows
        var k = 60 / (Math.max.apply(null, runs.map(function (r) { return r.params.mass * r.params.g; })));
        if (view.arrows === "forces") {
          var wgt = p.mass * p.g;
          W.arrow(ctx, sx, sy, sx, sy + wgt * k, COL.weight, 3, 9);
          if (!f.fly && f.N > 0) {
            // in tight dips N is several times the weight: cap the arrow, print the value
            var nl = Math.min(f.N * k, 150);
            W.arrow(ctx, sx, sy, sx + nx * nl, sy - ny * nl, COL.normal, 3, 9);
            W.label(ctx, "N " + f.N.toFixed(0) + " N" + (f.N * k > 150 ? " (arrow cut)" : ""),
                    sx + nx * nl + 6, sy - ny * nl, COL.normal, "11px system-ui");
          }
          if (f.friction > 1e-6) {
            var dir = f.v >= 0 ? -1 : 1, tx = Math.cos(f.phi), ty = Math.sin(f.phi);
            W.arrow(ctx, sx, sy, sx + dir * tx * f.friction * k, sy - dir * ty * f.friction * k, COL.friction, 3, 8);
          }
        } else if (view.arrows === "velocity") {
          var vx = f.fly ? Math.cos(f.phi) : Math.cos(f.phi), vy = Math.sin(f.phi), sp = f.v * 12;
          W.arrow(ctx, sx, sy, sx + vx * sp, sy - vy * sp, COL.vel, 3, 9);
          W.label(ctx, Math.abs(f.v).toFixed(1) + " m/s", sx + vx * sp, sy - vy * sp - 8, COL.vel, "bold 11px system-ui", "center");
        }

        var e0 = vz.e0 || 1e-9;
        bars.push({ title: (multi ? run.label + " " : "") + "energy", color: col || "#cfe0ff", total: e0,
                    text: e0.toFixed(0) + " J",
                    segments: [{ value: f.pe, color: COL.pe }, { value: f.ke, color: COL.ke },
                               { value: f.ker, color: COL.spin }, { value: f.heat, color: COL.heat }] });
        hud.push({ text: (multi ? run.label + "  " : "") + "t = " + f.t.toFixed(2) + " s   speed " +
                         Math.abs(f.v).toFixed(2) + " m/s   height " + f.y.toFixed(2) + " m",
                   color: col || "#8fd3ff" });
      });

      W.hud(ctx, hud);
      W.energyBars(ctx, { x: w - (multi ? 150 : 80), y: h - 70, H: 120, bw: 30, gap: 40, bars: bars,
                          keys: [["height", COL.pe], ["motion", COL.ke], ["spin", COL.spin], ["heat", COL.heat]],
                          keyX: w - 250, keyStep: 58 });
      var how = custom ? "drag the yellow dots to reshape the ramp · objects drawn larger than life"
                       : "drag the flag to change the start height";
      if (view.arrows === "forces") {
        W.legend(ctx, [["weight mg", COL.weight], ["push of the track N", COL.normal], ["friction", COL.friction],
                       ["one N scale · " + how, null]], 12, h - 10);
      } else {
        W.legend(ctx, [[how, null]], 12, h - 10);
      }
    },

    /* the dragged point stops where the shape would break a limit (like a
       physical stop): bisect between the last good height and the wanted
       one, then round to 0.1 m towards the good side */
    _limit: function (pts, last, i, want, lim) {
      var xs = pts.map(function (q) { return q[0]; });
      var test = function (y) { var ys = last.slice(); ys[i] = y; return PL.spline(xs, ys).check(lim.max_slope); };
      var bad = test(want);
      if (!bad.length) { var ok = last.slice(); ok[i] = want; return { ys: ok, blocked: null }; }
      var lo = last[i], hi = want;                     // lo is fine, hi is not
      if (test(lo).length) { return { ys: last, blocked: bad[0] }; }
      for (var k = 0; k < 16; k++) {
        var mid = (lo + hi) / 2;
        if (test(mid).length) hi = mid; else lo = mid;
      }
      var y = want > last[i] ? Math.floor(lo * 10 + 1e-9) / 10 : Math.ceil(lo * 10 - 1e-9) / 10;
      if (test(y).length) y = last[i];
      var ys = last.slice(); ys[i] = y;
      return { ys: ys, blocked: bad[0] };
    },

    /* sandbox ramp editing: a handle per control point (vertical drag only);
       while dragging, the new shape is previewed with the client spline */
    _points: function (ctx, vz, cam) {
      var that = this, X = function (x) { return cam.X(x); }, Y = function (y) { return cam.Y(y); };
      var pts = vz.points, ys = this.dragYs || pts.map(function (q) { return q[1]; });
      var lim = vz.limits || { y_min: 0, y_max: 10, max_slope: 3 };
      if (this.dragYs) {
        var sp = PL.spline(pts.map(function (q) { return q[0]; }), ys), bad = sp.check(lim.max_slope);
        ctx.strokeStyle = bad.length ? "#ff5c5c" : "#ffd166"; ctx.lineWidth = 3; ctx.setLineDash([8, 6]);
        ctx.beginPath();
        sp.polyline(240).forEach(function (q, i) { i ? ctx.lineTo(X(q[0]), Y(q[1])) : ctx.moveTo(X(q[0]), Y(q[1])); });
        ctx.stroke(); ctx.setLineDash([]);
        var why = bad[0] || this.blocked;
        var msg = why === "ground" ? "✋ stop: lower would make the ramp dip below the ground"
          : why === "steep" ? "✋ stop: any further and the ramp gets steeper than the limit"
          : "let go to run the new ramp";
        W.label(ctx, msg, X((pts[0][0] + pts[pts.length - 1][0]) / 2), Y(Math.max.apply(null, ys)) - 16,
                why ? "#ffb36b" : "#ffd166", "bold 13px system-ui", "center");
      }
      pts.forEach(function (q, i) {
        var px = X(q[0]), py = Y(ys[i]);
        ctx.fillStyle = "#ffd166"; ctx.strokeStyle = "#0b1128"; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(px, py, 7, 0, 7); ctx.fill(); ctx.stroke();
        ctx.strokeStyle = "rgba(255,209,102,0.6)"; ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.arc(px, py, 12, 0, 7); ctx.stroke();
        if (that.dragYs && that.dragI === i) {
          W.label(ctx, ys[i].toFixed(1) + " m", px + 14, py - 10, "#ffd166", "bold 12px system-ui");
        }
        cam.handle({ x: px, y: py, r: 12, cursor: "ns-resize",
                     title: "drag up or down (" + lim.y_min + "–" + lim.y_max + " m)",
                     drag: function (pt) {
                       var last = (that.dragYs || pts.map(function (p) { return p[1]; })).slice();
                       var want = Math.min(lim.y_max, Math.max(lim.y_min, Math.round(pt.y * 10) / 10));
                       var r = that._limit(pts, last, i, want, lim);
                       that.dragYs = r.ys; that.dragI = i; that.blocked = r.blocked;
                       cam.setParams({ track: r.ys }, false);
                     },
                     end: function () {
                       var done = that.dragYs;
                       that.dragYs = null; that.blocked = null;
                       if (done) cam.setParams({ track: done }, true);
                     } });
      });
    },

    /* project the pointer onto the start side of the track -> new height */
    _dragStart: function (pt, vz, cam) {
      var best = null;
      vz.track.forEach(function (q) {
        var onStartSide = vz.kind === "halfpipe" ? q[0] <= (vz.x0 + vz.x1) / 2 : q[0] <= 8.0;
        if (!onStartSide) return;
        var d = Math.hypot(q[0] - pt.x, q[1] - pt.y);
        if (!best || d < best.d) best = { d: d, y: q[1] };
      });
      if (best) cam.setParams({ height: Math.min(8, Math.max(0.5, Math.round(best.y * 10) / 10)) }, false);
    }
  };

  PL.scenes.energy = energy;
})();
