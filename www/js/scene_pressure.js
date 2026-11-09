/* physlab scene: PRESSURE - a hydraulic lift in world metres (zoomable).
   - the hand pushes the small piston; the load rides the big piston
   - Pascal's principle drawn literally: equal pressure arrows every few
     centimetres on BOTH piston faces - the big face simply has many more
     of them, so the total force is bigger
   - a pressure gauge, liquid flowing through the channel, brackets that
     show how far each piston moved (zoom in to see the big one move!)
   - a force-multiplier panel (the two forces differ by up to 3600x, so
     arrows on one scale would be meaningless) and work-in / work-out bars */
(function () {
  "use strict";
  var W = PL.widgets;
  var ARROW_SPACING = 0.025;       // m between pressure arrows on a piston face

  var pressure = {
    continuous: false,
    duration: function (runs) { var f = runs[0].result.frames; return f[f.length - 1].t; },
    world: function (runs) {
      var g = pressure._geo(runs[0].result.viz);
      return { x0: -0.32, x1: g.xb + g.r2 + 0.22, y0: -0.06, y1: 1.08 };
    },
    worldPad: 0.03,

    drawGoal: function (ctx, w, h, goal, runs, cam) {
      if (goal.metric !== "lift_mm") return;
      var vz = runs[0].result.viz, g = this._geo(vz);
      var y = cam.Y(vz.h0 + (goal.target || goal.min) / 1000);
      ctx.strokeStyle = "#7dffa8"; ctx.lineWidth = 2; ctx.setLineDash([6, 4]);
      ctx.beginPath(); ctx.moveTo(cam.X(g.xb - g.r2 - 0.04), y); ctx.lineTo(cam.X(g.xb + g.r2 + 0.04), y); ctx.stroke();
      ctx.setLineDash([]);
      W.label(ctx, "goal: +" + (goal.target || goal.min) + " mm", cam.X(g.xb - g.r2 - 0.05), y + 4, "#7dffa8",
              "bold 11px system-ui", "right");
    },

    _geo: function (vz) {
      var r1 = vz.d1 / 2, r2 = vz.d2 / 2;
      return { r1: r1, r2: r2, xs: 0.0, xb: r1 + r2 + 0.32, top: 0.8, floor: 0.0, chan: 0.07 };
    },

    init: function () { this.flow = 0; this.rand = W.rng(11); this.dots = null; },

    render: function (ctx, w, h, simT, clock, runs, view, cam) {
      var res = runs[0].result, vz = res.viz, g = this._geo(vz);
      var f = PL.frameAt(res.frames, simT);
      var X = function (x) { return cam.X(x); }, Y = function (y) { return cam.Y(y); };
      ctx.clearRect(0, 0, w, h);
      var liquid = vz.fluid.color;
      var y1 = vz.h0 - f.x1, y2 = vz.h0 + f.x2;                  // piston faces (liquid tops)

      // ---- floor ----
      ctx.fillStyle = "#1c2747"; ctx.fillRect(0, Y(0), w, h - Y(0));

      // ---- liquid: small column, channel, big column ----
      ctx.fillStyle = W.rgba(liquid, 0.75);
      ctx.fillRect(X(g.xs - g.r1), Y(y1), cam.len(2 * g.r1), Y(0) - Y(y1));
      ctx.fillRect(X(g.xb - g.r2), Y(y2), cam.len(2 * g.r2), Y(0) - Y(y2));
      ctx.fillRect(X(g.xs - g.r1), Y(g.chan), X(g.xb + g.r2) - X(g.xs - g.r1), Y(0) - Y(g.chan));

      // liquid flowing from the small side to the big side
      if (!this.dots) {
        this.dots = [];
        for (var i = 0; i < 26; i++) this.dots.push({ u: this.rand(), v: 0.2 + 0.6 * this.rand() });
      }
      var chanLen = g.xb - g.xs;
      this.flow += (f.v1 * vz.a1 / (0.07 * 0.3)) * clock.sim;   // channel speed ~ flow / channel area
      ctx.fillStyle = "rgba(255,255,255,0.55)";
      var that = this;
      this.dots.forEach(function (d) {
        var u = ((d.u + that.flow / chanLen) % 1 + 1) % 1;
        ctx.beginPath(); ctx.arc(X(g.xs + u * chanLen), Y(g.chan * d.v), 1.8, 0, 7); ctx.fill();
      });

      // ---- cylinder walls ----
      ctx.strokeStyle = "#cfd8ee"; ctx.lineWidth = 2.5;
      [[g.xs, g.r1], [g.xb, g.r2]].forEach(function (c) {
        ctx.beginPath();
        ctx.moveTo(X(c[0] - c[1]), Y(g.top)); ctx.lineTo(X(c[0] - c[1]), Y(g.chan));
        ctx.moveTo(X(c[0] + c[1]), Y(g.top)); ctx.lineTo(X(c[0] + c[1]), Y(g.chan));
        ctx.stroke();
      });
      ctx.beginPath();
      ctx.moveTo(X(g.xs - g.r1), Y(g.chan)); ctx.lineTo(X(g.xs - g.r1), Y(0)); ctx.lineTo(X(g.xb + g.r2), Y(0));
      ctx.lineTo(X(g.xb + g.r2), Y(g.chan));
      ctx.moveTo(X(g.xs + g.r1), Y(g.chan)); ctx.lineTo(X(g.xb - g.r2), Y(g.chan));
      ctx.stroke();

      // ---- pistons ----
      var pth = 0.025;
      ctx.fillStyle = "#9aa3b8";
      ctx.fillRect(X(g.xs - g.r1), Y(y1 + pth), cam.len(2 * g.r1), cam.len(pth));
      ctx.fillRect(X(g.xs) - 3, Y(y1 + 0.32), 6, cam.len(0.32 - pth));         // rod
      ctx.fillRect(X(g.xb - g.r2), Y(y2 + pth), cam.len(2 * g.r2), cam.len(pth));

      // Pascal: the same pressure on every patch of both faces
      var arrowPx = 22;
      [[g.xs, g.r1, y1], [g.xb, g.r2, y2]].forEach(function (c) {
        var n = Math.max(1, Math.floor(2 * c[1] / ARROW_SPACING));
        for (var k = 0; k < n; k++) {
          var ax = X(c[0] - c[1] + (k + 0.5) * 2 * c[1] / n);
          W.arrow(ctx, ax, Y(c[2]) + arrowPx + 4, ax, Y(c[2]) + 3, "#ffd166", 1.8, 6);
        }
      });

      // ---- the hand and the load ----
      var hy = Y(y1 + 0.32);
      PL.drawSprite(ctx, "hand", X(g.xs), hy - 26, 54);
      var platW = Math.max(2 * g.r2 + 0.1, 0.34), platY = y2 + pth;
      ctx.fillStyle = "#5d6b94"; ctx.fillRect(X(g.xb - platW / 2), Y(platY + 0.02), cam.len(platW), cam.len(0.02));
      if (vz.mass > 0) {
        var big = vz.mass >= 300, lw = cam.len(platW) * (big ? 1.0 : 0.6);
        PL.drawSprite(ctx, big ? "car" : "crate", X(g.xb), Y(platY + 0.02) - lw / 2 + (big ? lw * 0.1 : 0), lw);
        W.label(ctx, vz.mass.toFixed(0) + " kg" + (big ? " car (not to scale)" : ""), X(g.xb),
                Y(platY + 0.02) - lw * (big ? 0.75 : 1.05), "#eef2ff", "bold 12px system-ui", "center");
      }

      // ---- how far each piston moved ----
      this._bracket(ctx, X(g.xs - g.r1) - 14, Y(vz.h0), Y(y1), "d1 = " + (f.x1 * 100).toFixed(1) + " cm", "#ffb36b", "left");
      this._bracket(ctx, X(g.xb + g.r2) + 14, Y(vz.h0), Y(y2),
                    "d2 = " + (f.x2 * 1000).toFixed(2) + " mm" + (f.x2 > 0 && cam.len(f.x2) < 6 ? "  (zoom in to see it!)" : ""),
                    "#7dffa8", "right");
      ctx.setLineDash([3, 4]); ctx.strokeStyle = "rgba(255,255,255,0.35)"; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(X(g.xs - g.r1 - 0.05), Y(vz.h0)); ctx.lineTo(X(g.xb + g.r2 + 0.05), Y(vz.h0));
      ctx.stroke(); ctx.setLineDash([]);

      // ---- pressure gauge on the channel ----
      this._gauge(ctx, X((g.xs + g.xb) / 2), Y(0.2), Math.max(f.p1, 0), vz);

      // ---- panels (screen space) ----
      this._multiplier(ctx, w, f, vz);
      W.energyBars(ctx, { x: 30, y: h - 62, H: 120, bw: 30, gap: 26,
                          bars: [{ title: "work in", total: Math.max(f.w_in, 1e-9), text: f.w_in.toFixed(2) + " J",
                                   segments: [{ value: f.w_in, color: "#ffb36b" }] },
                                 { title: "goes to", total: Math.max(f.w_in, 1e-9),
                                   text: (f.w_load + f.w_liquid + f.w_loss + f.ke).toFixed(2) + " J",
                                   segments: [{ value: f.w_load, color: "#7dffa8" }, { value: f.w_liquid, color: "#5cd6ff" },
                                              { value: f.w_loss + f.ke, color: "#8a90a8" }] }],
                          keys: [["load", "#7dffa8"], ["liquid", "#5cd6ff"], ["heat", "#8a90a8"]],
                          keyX: 14, keyStep: 60 });
      W.hud(ctx, [
        "t = " + f.t.toFixed(2) + " s   push " + f.f_hand.toFixed(0) + " N",
        "pressure p = " + (f.p1 / 1000).toFixed(1) + " kPa everywhere in the liquid",
        { text: !vz.lifted ? "not enough push - nothing moves" :
                f.v2 > 1e-7 ? "the big piston rises at " + (f.v2 * 1000).toFixed(2) + " mm/s" :
                "the big piston rose " + (f.x2 * 1000).toFixed(2) + " mm", color: vz.lifted ? "#7dffa8" : "#ff8a8a" }
      ]);
      W.legend(ctx, [["each arrow = the same pressure on the same small patch of piston", "#ffd166"]], 12, h - 10);
    },

    _bracket: function (ctx, x, ya, yb, text, col, side) {
      ctx.strokeStyle = col; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(x - 4, ya); ctx.lineTo(x + 4, ya); ctx.moveTo(x, ya); ctx.lineTo(x, yb);
      ctx.moveTo(x - 4, yb); ctx.lineTo(x + 4, yb); ctx.stroke();
      W.label(ctx, text, x + (side === "left" ? -8 : 8), (ya + yb) / 2 + 4, col, "bold 11px system-ui",
              side === "left" ? "right" : "left");
    },

    _gauge: function (ctx, x, y, p, vz) {
      var r = 26, pmax = W.niceUp(Math.max(vz.p_push, vz.weight / vz.a2) * 1.2);
      ctx.fillStyle = "#e8ecf5"; ctx.strokeStyle = "#2a3560"; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.fill(); ctx.stroke();
      ctx.fillRect(x - 3, y + r, 6, 14);
      for (var i = 0; i <= 10; i++) {
        var a = Math.PI * (0.75 + 1.5 * i / 10);
        ctx.beginPath(); ctx.moveTo(x + Math.cos(a) * r * 0.78, y + Math.sin(a) * r * 0.78);
        ctx.lineTo(x + Math.cos(a) * r * 0.92, y + Math.sin(a) * r * 0.92); ctx.stroke();
      }
      var an = Math.PI * (0.75 + 1.5 * Math.min(1, p / pmax));
      ctx.strokeStyle = "#e0455a"; ctx.lineWidth = 2.5;
      ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + Math.cos(an) * r * 0.8, y + Math.sin(an) * r * 0.8); ctx.stroke();
      W.label(ctx, (p / 1000).toFixed(0) + " kPa", x, y + r + 26, "#ffd166", "bold 11px system-ui", "center");
      W.label(ctx, "gauge", x, y - r - 6, "#cfe0ff", "10px system-ui", "center");
    },

    _multiplier: function (ctx, w, f, vz) {
      var x = w - 250, y = 14;
      ctx.fillStyle = "rgba(11,17,40,0.88)"; ctx.fillRect(x, y, 238, 96);
      ctx.strokeStyle = "#2f3f72"; ctx.strokeRect(x, y, 238, 96);
      W.label(ctx, "force multiplier", x + 119, y + 16, "#cfe0ff", "bold 12px system-ui", "center");
      W.label(ctx, "push F1", x + 40, y + 38, "#ffb36b", "11px system-ui", "center");
      W.label(ctx, vz.p_push ? (vz.p_push * vz.a1).toFixed(0) + " N" : "", x + 40, y + 56, "#ffb36b",
              "bold 15px system-ui", "center");
      W.label(ctx, "× " + vz.ratio.toFixed(vz.ratio < 10 ? 2 : 0), x + 119, y + 50, "#ffd166", "bold 14px system-ui", "center");
      W.label(ctx, "(A2 / A1)", x + 119, y + 66, "#9fb3e8", "10px system-ui", "center");
      W.label(ctx, "lift F2", x + 198, y + 38, "#7dffa8", "11px system-ui", "center");
      W.label(ctx, vz.f2.toFixed(0) + " N", x + 198, y + 56, "#7dffa8", "bold 15px system-ui", "center");
      W.label(ctx, "load weighs " + vz.weight.toFixed(0) + " N  →  " + (vz.lifted ? "it rises" : "too heavy"),
              x + 119, y + 86, vz.lifted ? "#7dffa8" : "#ff8a8a", "11px system-ui", "center");
    }
  };

  PL.scenes.pressure = pressure;
})();
