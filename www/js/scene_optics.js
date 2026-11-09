/* physlab scene: LENSES - an optical bench in world centimetres (zoomable).
   - the candle is the object (drag its flame: distance AND height)
   - principal rays (thin-lens rules) and/or real rays traced through the
     thick glass with Snell's law; light pulses run along them and slow
     down inside the glass (v = c / n)
   - the image: a real one is caught on a screen, a virtual one is a ghost
     that only an eye looking through the lens can see
   - F, F', 2F markers, distance bars for d_o and d_i, a zoom-aware ruler  */
(function () {
  "use strict";
  var W = PL.widgets;
  var RAY_COL = { parallel: "#ffd166", centre: "#7dffa8", focal: "#ff8aa8" };
  var PULSE_SPEED = 30;          // cm per (real) second - light slowed down a LOT to be seen

  function polyLen(pts, ns) {
    var L = 0;
    for (var i = 1; i < pts.length; i++) {
      L += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]) * (ns ? ns[i - 1] : 1);
    }
    return L;
  }

  /* point at "optical distance" s along a polyline whose segments slow
     light by n (so pulses crawl through glass) */
  function pointAt(pts, ns, s) {
    for (var i = 1; i < pts.length; i++) {
      var seg = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]), n = ns ? ns[i - 1] : 1;
      if (s <= seg * n) {
        var k = s / (seg * n);
        return [pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * k, pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * k, n];
      }
      s -= seg * n;
    }
    return null;
  }

  var optics = {
    continuous: true,
    options: [{ id: "rays", label: "Rays", default: "principal",
                choices: [{ id: "principal", label: "3 rules" }, { id: "real", label: "real (Snell)" },
                          { id: "both", label: "both" }] }],
    duration: function (runs) { return runs[0].result.viz.loop; },
    world: function (runs, goal) {
      var b = runs[0].result.viz.box;
      if (goal && goal.metric === "image_distance") {            // keep the target in view
        b = { x0: Math.min(b.x0, goal.min - 8), x1: Math.max(b.x1, goal.max + 10), y0: b.y0, y1: b.y1 };
      }
      return b;
    },
    drawGoal: function (ctx, w, h, goal, runs, cam) {
      if (goal.metric !== "image_distance") return;
      var x0 = cam.X(goal.min), x1 = cam.X(goal.max), y = cam.Y(0);
      ctx.fillStyle = "rgba(125,255,168,0.22)"; ctx.fillRect(x0, y - 60, Math.max(3, x1 - x0), 120);
      ctx.strokeStyle = "#7dffa8"; ctx.setLineDash([4, 4]); ctx.lineWidth = 1.5;
      ctx.strokeRect(x0, y - 60, Math.max(3, x1 - x0), 120); ctx.setLineDash([]);
      W.label(ctx, "image should form here", (x0 + x1) / 2, y - 66, "#7dffa8", "bold 11px system-ui", "center");
    },
    worldPad: 0.04,

    init: function () { this.clock = 0; },

    render: function (ctx, w, h, simT, clock, runs, view, cam) {
      var vz = runs[0].result.viz, X = function (x) { return cam.X(x); }, Y = function (y) { return cam.Y(y); };
      if (clock.playing) this.clock += clock.real;
      ctx.clearRect(0, 0, w, h);
      var lo = cam.inv(0, 0), hi = cam.inv(w, h);

      // ---- axis + ruler (tick spacing follows the zoom) ----
      ctx.strokeStyle = "rgba(160,180,230,0.5)"; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(0, Y(0)); ctx.lineTo(w, Y(0)); ctx.stroke();
      var step = W.niceStep((hi.x - lo.x) / 1.2);
      ctx.font = "10px ui-monospace, Menlo, monospace"; ctx.fillStyle = "#6f86c4"; ctx.textAlign = "center";
      for (var x = Math.ceil(lo.x / step) * step; x <= hi.x; x += step) {
        ctx.fillRect(X(x), Y(0) - 3, 1, 6);
        ctx.fillText((Math.abs(x) < 1e-9 ? 0 : +x.toPrecision(6)) + " cm", X(x), Y(0) + 30);
      }
      ctx.textAlign = "left";

      // ---- focal points ----
      var f = vz.f;
      [[f, "F'"], [-f, "F"], [2 * f, "2F'"], [-2 * f, "2F"]].forEach(function (q) {
        var px = X(q[0]);
        if (px < -20 || px > w + 20) return;
        ctx.fillStyle = q[1].indexOf("2") === 0 ? "#8a9bd0" : "#ffffff";
        ctx.beginPath(); ctx.arc(px, Y(0), q[1].indexOf("2") === 0 ? 3 : 4.5, 0, 7); ctx.fill();
        W.label(ctx, q[1], px, Y(0) + 16, ctx.fillStyle, "bold 11px system-ui", "center");
      });

      // ---- the lens ----
      var L = vz.lens, outside = vz.rays.some(function (r) { return r.outside; });
      if (outside && view.rays !== "real") {        // the ideal thin lens reaches further than the glass
        ctx.setLineDash([4, 5]); ctx.strokeStyle = "rgba(143,211,255,0.45)";
        ctx.beginPath(); ctx.moveTo(X(0), 0); ctx.lineTo(X(0), h); ctx.stroke(); ctx.setLineDash([]);
      }
      ctx.beginPath();
      L.outline.forEach(function (q, i) { i ? ctx.lineTo(X(q[0]), Y(q[1])) : ctx.moveTo(X(q[0]), Y(q[1])); });
      ctx.closePath();
      var gl = ctx.createLinearGradient(X(L.x1 - 1), 0, X(L.x2 + 1), 0);
      gl.addColorStop(0, "rgba(143,211,255,0.18)"); gl.addColorStop(0.5, "rgba(200,235,255,0.42)");
      gl.addColorStop(1, "rgba(143,211,255,0.18)");
      ctx.fillStyle = gl; ctx.fill();
      ctx.strokeStyle = "rgba(210,235,255,0.9)"; ctx.lineWidth = 1.5; ctx.stroke();
      W.label(ctx, vz.glass + ", n = " + vz.n, X(0), Y(L.a) - 10, "#bfe3ff", "11px system-ui", "center");

      // ---- rays ----
      var that = this, pulses = [];
      if (view.rays !== "real") {
        vz.rays.forEach(function (r) {
          var col = RAY_COL[r.name];
          ctx.strokeStyle = W.rgba(col, 0.85); ctx.lineWidth = 1.8;
          ctx.beginPath();
          r.pts.forEach(function (q, i) { i ? ctx.lineTo(X(q[0]), Y(q[1])) : ctx.moveTo(X(q[0]), Y(q[1])); });
          ctx.stroke();
          if (r.virt) {
            ctx.setLineDash([5, 5]); ctx.strokeStyle = W.rgba(col, 0.55);
            ctx.beginPath(); ctx.moveTo(X(r.virt[0][0]), Y(r.virt[0][1])); ctx.lineTo(X(r.virt[1][0]), Y(r.virt[1][1]));
            ctx.stroke(); ctx.setLineDash([]);
          }
          pulses.push({ pts: r.pts, ns: null, col: col });
        });
      }
      if (view.rays !== "principal") {
        vz.fan.forEach(function (r) {
          ctx.strokeStyle = "rgba(255,179,107,0.55)"; ctx.lineWidth = 1.1;
          ctx.beginPath();
          r.pts.forEach(function (q, i) { i ? ctx.lineTo(X(q[0]), Y(q[1])) : ctx.moveTo(X(q[0]), Y(q[1])); });
          ctx.stroke();
          pulses.push({ pts: r.pts, ns: r.n, col: "#ffcf8a", small: true });
        });
      }
      // light pulses: evenly spaced in time, slowed by n inside glass
      ctx.save(); ctx.globalCompositeOperation = "lighter";
      pulses.forEach(function (pl) {
        var len = polyLen(pl.pts, pl.ns), gap = 18;
        for (var s0 = (that.clock * PULSE_SPEED) % gap; s0 < len; s0 += gap) {
          var q = pointAt(pl.pts, pl.ns, s0);
          if (!q) continue;
          var px = X(q[0]), py = Y(q[1]);
          if (px < -10 || px > w + 10 || py < -10 || py > h + 10) continue;
          var r = pl.small ? 2.2 : 3.2;
          var g = ctx.createRadialGradient(px, py, 0, px, py, r * 2.2);
          g.addColorStop(0, "rgba(255,255,255,0.95)"); g.addColorStop(0.4, W.rgba(pl.col, 0.9));
          g.addColorStop(1, W.rgba(pl.col, 0));
          ctx.fillStyle = g; ctx.beginPath(); ctx.arc(px, py, r * 2.2, 0, 7); ctx.fill();
        }
      });
      ctx.restore();

      // ---- the candle (object) ----
      var cx = X(-vz.d_o), hpx = cam.len(vz.h_o);
      this._candle(ctx, cx, Y(0), hpx, 1, false);
      var that2 = this;
      cam.handle({ x: cx, y: Y(vz.h_o), r: Math.max(12, hpx * 0.12), cursor: "grab",
                   title: "drag the candle (distance and height)",
                   drag: function (pt) {
                     cam.setParams({ d_o: Math.min(100, Math.max(2, Math.round(-pt.x * 2) / 2)),
                                     h_o: Math.min(8, Math.max(1, Math.round(pt.y * 2) / 2)) }, false);
                   } });
      ctx.strokeStyle = "rgba(255,209,102,0.9)"; ctx.lineWidth = 1.5; ctx.setLineDash([3, 3]);
      ctx.beginPath(); ctx.arc(cx, Y(vz.h_o), Math.max(12, hpx * 0.12), 0, 7); ctx.stroke(); ctx.setLineDash([]);

      // ---- the image ----
      if (vz.image === "real" && vz.d_i <= 1e5) {
        var ix = X(vz.d_i), ih = cam.len(Math.abs(vz.h_i));
        ctx.fillStyle = "rgba(235,240,250,0.12)";                      // the screen that catches it
        ctx.fillRect(ix - 3, Y(Math.max(vz.lens.a, 1.3 * Math.abs(vz.h_i))), 6,
                     cam.len(2 * Math.max(vz.lens.a, 1.3 * Math.abs(vz.h_i))));
        this._candle(ctx, ix, Y(0), ih, 0.92, true);
        W.label(ctx, "real image (on a screen)", W.clamp(ix, 80, w - 80), Y(0) + 46, "#ffd166", "bold 11px system-ui", "center");
      } else if (vz.image === "virtual") {
        var vx = X(vz.d_i), vh = cam.len(vz.h_i);
        ctx.globalAlpha = 0.38; this._candle(ctx, vx, Y(0), vh, 1, false); ctx.globalAlpha = 1;
        ctx.setLineDash([4, 4]); ctx.strokeStyle = "rgba(255,209,102,0.7)";
        ctx.strokeRect(vx - vh * 0.18, Y(vz.h_i), vh * 0.36, vh); ctx.setLineDash([]);
        W.label(ctx, "virtual image (look through the lens)", W.clamp(vx, 110, w - 110), Y(0) + 46, "#ffd166",
                "bold 11px system-ui", "center");
        var ex = X(Math.max(22, 1.4 * Math.abs(f)));
        PL.drawSprite(ctx, "eye", ex, Y(0), 44);
      } else {
        W.label(ctx, "no image: the rays leave parallel (image at infinity)", X(Math.abs(f)), Y(-vz.lens.a) + 28,
                "#ffd166", "bold 12px system-ui", "center");
      }

      // ---- distance bars ----
      var by = Y(0) + 52;
      this._dim(ctx, X(-vz.d_o), X(0), by, "d_o = " + vz.d_o + " cm", "#cfe0ff");
      if (vz.d_i != null && Math.abs(vz.d_i) <= 1e5) {
        this._dim(ctx, X(0), X(vz.d_i), by + 18, "d_i = " + vz.d_i.toFixed(1) + " cm", "#ffd166");
      }

      W.hud(ctx, [
        "f = " + f.toFixed(1) + " cm   (" + (vz.kind === "converging" ? "converging" : "diverging") + ")",
        "image: " + (vz.image === "none" ? "none (at infinity)" : vz.image + ", m = " + vz.m.toFixed(2)),
        { text: "drag the candle's flame · light slowed down a lot (" + PULSE_SPEED + " cm/s)", color: "#6f86c4" }
      ]);
      if (view.rays !== "real") {
        W.legend(ctx, [["parallel → through F'", RAY_COL.parallel], ["through the centre", RAY_COL.centre],
                       ["through F → parallel", RAY_COL.focal], ["dashed = traced back", null]], 12, h - 10);
      } else {
        W.legend(ctx, [["real rays, bent twice (Snell's law at each surface)", "#ffb36b"]], 12, h - 10);
      }
    },

    /* candle sprite standing on (x, yBase), total height hpx; flip = upside down */
    _candle: function (ctx, x, yBase, hpx, alpha, flip) {
      if (hpx < 2) return;
      var spr = PL.sprites.candle;
      ctx.save(); ctx.globalAlpha *= alpha;
      ctx.translate(x, yBase);
      if (flip) ctx.scale(1, -1);
      if (spr) ctx.drawImage(spr, -hpx / 2, -hpx, hpx, hpx);
      else { ctx.fillStyle = "#f5efe0"; ctx.fillRect(-hpx * 0.12, -hpx * 0.7, hpx * 0.24, hpx * 0.7); }
      ctx.restore();
    },

    _dim: function (ctx, x1, x2, y, text, col) {
      ctx.strokeStyle = col; ctx.fillStyle = col; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(x1, y - 4); ctx.lineTo(x1, y + 4); ctx.moveTo(x2, y - 4); ctx.lineTo(x2, y + 4);
      ctx.moveTo(x1, y); ctx.lineTo(x2, y); ctx.stroke();
      W.label(ctx, text, (x1 + x2) / 2, y - 4, col, "11px system-ui", "center");
    }
  };

  PL.scenes.optics = optics;
})();
