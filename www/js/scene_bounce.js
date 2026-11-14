/* physlab scene: BOUNCES in world metres (zoomable). One ball - or two in
   compare mode, side by side - dropped onto a surface.
   - a height ruler, the drop height as a dashed line with a draggable tab
   - every bounce's top gets a marker as soon as the ball reaches it:
     "1st 1.42 m (71%)"; faint ticks show where e^(2n) h0 would put it
     without air
   - stacked energy bars: height, motion, and what the bounces turned into
     heat and sound                                                      */
(function () {
  "use strict";
  var W = PL.widgets;
  var COL = { pe: "#5c9dff", ke: "#ff9a5c", heat: "#8a90a8", ideal: "#6f86c4" };
  var GAP = 1.15;                    // m between the two balls in compare mode
  var ORD = ["1st", "2nd", "3rd", "4th", "5th", "6th"];

  function ballX(i) { return i * GAP; }

  var bounce = {
    continuous: false,
    options: [{ id: "marks", label: "Marks", default: "on",
                choices: [{ id: "on", label: "bounce heights" }, { id: "off", label: "off" }] }],
    duration: function (runs) {
      return Math.max.apply(null, runs.map(function (r) { var f = r.result.frames; return f[f.length - 1].t; }));
    },
    world: function (runs) {
      var top = 0.5;
      runs.forEach(function (r) { top = Math.max(top, r.result.viz.h0); });
      return { x0: -1.35, x1: ballX(runs.length - 1) + 2.6, y0: -0.4, y1: top + 0.5 };
    },
    worldPad: 0.02,

    init: function () {},

    render: function (ctx, w, h, simT, clock, runs, view, cam) {
      var X = function (x) { return cam.X(x); }, Y = function (y) { return cam.Y(y); };
      var multi = runs.length > 1, top = 0.5;
      runs.forEach(function (r) { top = Math.max(top, r.result.viz.h0); });
      ctx.clearRect(0, 0, w, h);

      // ---- ruler ----
      var rx = X(-0.9), step = top > 2.5 ? 0.5 : 0.25;
      ctx.strokeStyle = "#6f86c4"; ctx.fillStyle = "#6f86c4"; ctx.lineWidth = 1;
      ctx.font = "10px ui-monospace, Menlo, monospace"; ctx.textAlign = "right";
      ctx.beginPath(); ctx.moveTo(rx, Y(0)); ctx.lineTo(rx, Y(top + 0.3)); ctx.stroke();
      for (var m = 0; m <= top + 0.3 + 1e-9; m += step) {
        ctx.beginPath(); ctx.moveTo(rx - 4, Y(m)); ctx.lineTo(rx + 4, Y(m)); ctx.stroke();
        ctx.fillText(m.toFixed(2) + " m", rx - 6, Y(m) + 3);
      }
      ctx.textAlign = "left";

      var bars = [], hud = [];
      runs.forEach(function (run, ri) {
        var vz = run.result.viz, bx = ballX(ri), col = multi ? run.color : "#ffd166";
        var f = PL.frameAt(run.result.frames, simT);

        // ---- the surface under this ball ----
        ctx.fillStyle = vz.surface.color;
        ctx.fillRect(X(bx - 0.38), Y(0), X(bx + 0.38) - X(bx - 0.38), Y(-0.12) - Y(0));
        ctx.fillStyle = "rgba(0,0,0,0.25)";
        ctx.fillRect(X(bx - 0.38), Y(-0.12), X(bx + 0.38) - X(bx - 0.38), Y(-0.18) - Y(-0.12));
        W.label(ctx, vz.surface.label + "  e = " + vz.e.toFixed(2), X(bx), Y(-0.28), "#cfd8f0", "11px system-ui", "center");

        // ---- drop height + its drag tab ----
        ctx.setLineDash([6, 6]); ctx.strokeStyle = W.rgba(col, 0.6); ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.moveTo(ri === 0 ? rx : X(bx - 0.45), Y(vz.h0)); ctx.lineTo(X(bx + 0.45), Y(vz.h0));
        ctx.stroke(); ctx.setLineDash([]);
        var tx = X(bx + 0.5), ty = Y(vz.h0);
        ctx.fillStyle = col; ctx.strokeStyle = "#0b1128"; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.moveTo(tx, ty); ctx.lineTo(tx + 14, ty - 8); ctx.lineTo(tx + 14, ty + 8); ctx.closePath();
        ctx.fill(); ctx.stroke();
        W.label(ctx, (multi ? run.label + "  " : "") + "h0 = " + vz.h0.toFixed(2) + " m", tx + 16, ty - 11, col,
                "bold 11px system-ui", "right");
        if (multi) W.label(ctx, vz.ball.label.split(" (")[0], tx - 4, ty + 16, col, "11px system-ui", "right");
        if (ri === runs.length - 1) {
          cam.handle({ x: tx + 7, y: ty, r: 14, cursor: "ns-resize", title: "drag up or down to change the drop height",
                       drag: function (pt) {
                         cam.setParams({ height: Math.min(4, Math.max(0.2, Math.round(pt.y * 20) / 20)) }, false);
                       } });
        }

        // ---- bounce marks: ideal (faint) and reached ----
        if (view.marks !== "off") {
          vz.ideal.forEach(function (hi, i) {
            if (hi < 0.01) return;
            ctx.strokeStyle = W.rgba(COL.ideal, 0.55); ctx.lineWidth = 1;
            ctx.beginPath(); ctx.moveTo(X(bx - 0.3), Y(hi)); ctx.lineTo(X(bx - 0.18), Y(hi)); ctx.stroke();
          });
          vz.apexes.forEach(function (a, i) {
            if (simT < a.t || a.h < 0.01) return;
            ctx.strokeStyle = col; ctx.lineWidth = 2;
            ctx.beginPath(); ctx.moveTo(X(bx - 0.18), Y(a.h)); ctx.lineTo(X(bx + 0.18), Y(a.h)); ctx.stroke();
            if (i < 4) {
              W.label(ctx, (ORD[i] || i + 1 + "th") + " " + a.h.toFixed(2) + " m (" + Math.round(100 * a.h / vz.h0) + "%)",
                      X(bx + 0.22), Y(a.h) + 4, col, "11px system-ui");
            }
          });
        }

        // ---- the ball ----
        var r = Math.max(cam.len(vz.r), 7), by = Y(f.y + vz.r);
        ctx.fillStyle = vz.ball.color; ctx.strokeStyle = "#0b1128"; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(X(bx), by, r, 0, 7); ctx.fill(); ctx.stroke();
        ctx.fillStyle = "rgba(255,255,255,0.35)";
        ctx.beginPath(); ctx.arc(X(bx) - r * 0.3, by - r * 0.3, r * 0.3, 0, 7); ctx.fill();
        if (multi) W.label(ctx, run.label, X(bx), by - r - 6, col, "bold 12px system-ui", "center");

        var e0 = vz.g * vz.ball.mass * vz.h0 || 1e-9;
        bars.push({ title: (multi ? run.label + " " : "") + "energy", color: multi ? col : "#cfe0ff", total: e0,
                    text: e0.toFixed(2) + " J",
                    segments: [{ value: f.pe, color: COL.pe }, { value: f.ke, color: COL.ke },
                               { value: f.heat, color: COL.heat }] });
        hud.push({ text: (multi ? run.label + "  " : "") + "t = " + f.t.toFixed(2) + " s   height " +
                         Math.max(0, f.y).toFixed(2) + " m   speed " + Math.abs(f.v).toFixed(2) + " m/s",
                   color: multi ? col : "#8fd3ff" });
      });

      W.hud(ctx, hud);
      W.energyBars(ctx, { x: w - (multi ? 150 : 80), y: h - 70, H: 120, bw: 30, gap: 40, bars: bars,
                          keys: [["height", COL.pe], ["motion", COL.ke], ["heat + sound", COL.heat]],
                          keyX: w - 290, keyStep: 70 });
      W.legend(ctx, [["drag the tab to change the drop height · faint ticks: e²ⁿ × h0 without air", null]], 12, h - 10);
    }
  };

  PL.scenes.bounce = bounce;
})();
