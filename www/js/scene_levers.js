/* physlab scene: LEVERS & MOMENTS in world metres (zoomable).
   A 2.2 m beam on a pivot, a load hanging from a hook on each side.
   - the beam turns by the server's frames (theta > 0: right end down),
     rubber stops at +-25 degrees
   - each load shows its turning effect m·g·d as a curved arrow (the
     bigger one wins), and the "mass x distance" balance in the HUD
   - drag a load's hook along the beam to move it (d1 / d2)
   - ticks every 10 cm on the beam, numbers every 50 cm                */
(function () {
  "use strict";
  var W = PL.widgets;
  var PIVOT_Y = 0.95;                       // m above the floor
  var COL = { left: "#5cd6ff", right: "#ff9a5c", beam: "#c08a4e", stop: "#3a4678" };

  function beamPoint(d, th) {              // a point d metres along the beam (negative = left) at tilt th
    return [d * Math.cos(th), PIVOT_Y - d * Math.sin(th)];
  }

  function moArrow(ctx, cam, th, d, side, col, label) {
    // the load's turning effect: an arc round the pivot through the hook's distance, starting above the
    // beam and ending at it, the arrowhead pointing the way that load turns its end (down)
    var px = cam.X(0), py = cam.Y(PIVOT_Y), r = cam.len(d);
    var base = side < 0 ? Math.PI + th : th;                  // screen angle of the hook (canvas: clockwise)
    var a0 = base - side * 0.42, a1 = base - side * 0.06;     // from above the beam down to it
    ctx.strokeStyle = col; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.arc(px, py, r, Math.min(a0, a1), Math.max(a0, a1)); ctx.stroke();
    var ex = px + r * Math.cos(a1), ey = py + r * Math.sin(a1);
    var tx = -Math.sin(a1) * side, ty = Math.cos(a1) * side;   // the direction of travel at the arc's end
    W.arrow(ctx, ex - 10 * tx, ey - 10 * ty, ex + 2 * tx, ey + 2 * ty, col, 3, 10);
    W.label(ctx, label, px + r * Math.cos(a0), py + r * Math.sin(a0) - 8, col, "bold 12px system-ui", "center");
  }

  function load(ctx, cam, x, y, m, col, name) {
    var s = Math.max(0.06, 0.11 * Math.cbrt(Math.max(m, 0.02)));            // drawn size ~ cube root of mass
    var hang = 0.16;
    ctx.strokeStyle = "#cfd6e6"; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.moveTo(cam.X(x), cam.Y(y)); ctx.lineTo(cam.X(x), cam.Y(y - hang)); ctx.stroke();
    if (m > 0) {
      if (!PL.drawSprite(ctx, "crate", cam.X(x), cam.Y(y - hang - s / 2), cam.len(s))) {
        ctx.fillStyle = "#c98b4a"; ctx.fillRect(cam.X(x - s / 2), cam.Y(y - hang), cam.len(s), cam.len(s));
      }
    }
    W.label(ctx, name + " " + m.toFixed(2) + " kg", cam.X(x), cam.Y(y - hang - s) + 16, col, "bold 11px system-ui", "center");
  }

  var levers = {
    continuous: false,
    options: [{ id: "arrows", label: "Turning effects", default: "on",
                choices: [{ id: "on", label: "on" }, { id: "off", label: "off" }] }],
    duration: function (runs) { var f = runs[0].result.frames; return f[f.length - 1].t; },
    world: function () { return { x0: -1.45, x1: 1.45, y0: -0.1, y1: 1.75 }; },
    worldPad: 0.03,
    init: function () {},

    render: function (ctx, w, h, simT, clock, runs, view, cam) {
      var run = runs[0], vz = run.result.viz, f = PL.frameAt(run.result.frames, simT), th = f.theta;
      var half = vz.length / 2, stop = vz.stop * Math.PI / 180;
      ctx.clearRect(0, 0, w, h);
      var theme = vz.theme;
      if (theme && theme.sky) {
        var sky = ctx.createLinearGradient(0, 0, 0, h); sky.addColorStop(0, theme.sky); sky.addColorStop(1, "#0b1128");
        ctx.fillStyle = sky; ctx.fillRect(0, 0, w, h);
      }
      // floor, stand, stops
      ctx.fillStyle = "#1a2348"; ctx.fillRect(0, cam.Y(0), w, h - cam.Y(0));
      ctx.fillStyle = "#3a4678";
      ctx.beginPath(); ctx.moveTo(cam.X(0), cam.Y(PIVOT_Y)); ctx.lineTo(cam.X(-0.22), cam.Y(0));
      ctx.lineTo(cam.X(0.22), cam.Y(0)); ctx.closePath(); ctx.fill();
      [-1, 1].forEach(function (sd) {
        var e = beamPoint(sd * half, sd * stop);
        ctx.fillStyle = COL.stop; ctx.fillRect(cam.X(e[0] - 0.05), cam.Y(e[1] - 0.04), cam.len(0.1), cam.Y(0) - cam.Y(e[1] - 0.04));
        ctx.fillStyle = "#0b1128"; ctx.fillRect(cam.X(e[0] - 0.06), cam.Y(e[1] - 0.02), cam.len(0.12), cam.len(0.04));
      });
      W.label(ctx, "stop ±" + vz.stop + "°", cam.X(half) + 4, cam.Y(0.08), "#8d9acb", "10px system-ui", "right");

      // the beam with its ruler
      var a = beamPoint(-half, th), b = beamPoint(half, th), nx = Math.sin(th), ny = Math.cos(th), tk = 0.03;
      ctx.fillStyle = COL.beam; ctx.strokeStyle = "#0b1128"; ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(cam.X(a[0] + nx * tk), cam.Y(a[1] + ny * tk)); ctx.lineTo(cam.X(b[0] + nx * tk), cam.Y(b[1] + ny * tk));
      ctx.lineTo(cam.X(b[0] - nx * tk), cam.Y(b[1] - ny * tk)); ctx.lineTo(cam.X(a[0] - nx * tk), cam.Y(a[1] - ny * tk));
      ctx.closePath(); ctx.fill(); ctx.stroke();
      ctx.font = "10px ui-monospace, Menlo, monospace"; ctx.textAlign = "center";
      for (var i = -11; i <= 11; i++) {
        var p0 = beamPoint(i / 10, th), big = i % 5 === 0;
        ctx.strokeStyle = "#5a3a1a"; ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(cam.X(p0[0] + nx * tk), cam.Y(p0[1] + ny * tk));
        ctx.lineTo(cam.X(p0[0] + nx * (big ? -tk : 0)), cam.Y(p0[1] + ny * (big ? -tk : 0))); ctx.stroke();
        if (big && i !== 0) { ctx.fillStyle = "#8d9acb"; ctx.fillText(Math.abs(i / 10).toFixed(1) + " m", cam.X(p0[0] + nx * 0.09), cam.Y(p0[1] + ny * 0.09)); }
      }
      ctx.textAlign = "left";
      ctx.fillStyle = "#dfe6ff"; ctx.beginPath(); ctx.arc(cam.X(0), cam.Y(PIVOT_Y), 5, 0, 7); ctx.fill();

      // the loads, hanging from their hooks; drag a hook along the beam
      var h1 = beamPoint(-vz.d1, th), h2 = beamPoint(vz.d2, th);
      load(ctx, cam, h1[0], h1[1], vz.m1, COL.left, vz.names ? vz.names[0] : "m1");
      load(ctx, cam, h2[0], h2[1], vz.m2, COL.right, vz.names ? vz.names[1] : "m2");
      [[h1, "d1", -1], [h2, "d2", 1]].forEach(function (q) {
        var hx = cam.X(q[0][0]), hy = cam.Y(q[0][1]);
        ctx.fillStyle = "#ffd166"; ctx.strokeStyle = "#0b1128"; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(hx, hy, 7, 0, 7); ctx.fill(); ctx.stroke();
        cam.handle({ x: hx, y: hy, r: 12, cursor: "ew-resize", title: "drag the hook along the beam",
                     drag: function (pt) {
                       var d = Math.round(Math.min(1.1, Math.max(0.05, q[2] * pt.x / Math.cos(th))) * 20) / 20, ch = {};
                       ch[q[1]] = d;
                       cam.setParams(ch, false);
                     } });
      });
      // distances along the beam
      W.label(ctx, "d1 = " + vz.d1.toFixed(2) + " m", cam.X(h1[0] / 2), cam.Y(h1[1] / 2 + PIVOT_Y / 2) + 24, COL.left,
              "bold 11px system-ui", "center");
      W.label(ctx, "d2 = " + vz.d2.toFixed(2) + " m", cam.X(h2[0] / 2), cam.Y(h2[1] / 2 + PIVOT_Y / 2) + 24, COL.right,
              "bold 11px system-ui", "center");

      // turning effects (moments)
      var g = vz.g, t1 = vz.m1 * g * vz.d1 * Math.cos(th), t2 = vz.m2 * g * vz.d2 * Math.cos(th);
      if (view.arrows !== "off") {
        if (vz.m1 > 0) moArrow(ctx, cam, th, vz.d1, -1, COL.left, "m1·g·d1 = " + t1.toFixed(2) + " N·m");
        if (vz.m2 > 0) moArrow(ctx, cam, th, vz.d2, 1, COL.right, "m2·g·d2 = " + t2.toFixed(2) + " N·m");
      }

      var verdict = vz.moves ? (vz.hit ? (vz.hit > 0 ? "right" : "left") + " end down" : "turning")
                             : (Math.abs(vz.unbalance) < 1e-9 ? "balanced" : "stays put");
      W.hud(ctx, [
        "t = " + f.t.toFixed(2) + " s   tilt " + (th * 180 / Math.PI).toFixed(1) + "°   " +
          (Math.abs(f.omega) > 1e-4 ? "turning " + Math.abs(f.omega).toFixed(2) + " rad/s" : ""),
        { text: "mass × distance:  left " + (vz.m1 * vz.d1).toFixed(3) + " kg·m   right " + (vz.m2 * vz.d2).toFixed(3) +
                " kg·m   → " + verdict, color: Math.abs(vz.unbalance) < 1e-9 ? "#7dffa8" : "#ffd166" },
        { text: "balance needs " + vz.balance_m2.toFixed(3) + " kg at " + vz.d2.toFixed(2) + " m on the right" +
                (vz.friction > 0 ? " (the pivot's friction holds " + vz.friction.toFixed(2) + " N·m)" : ""), color: "#8d9acb" }
      ]);
      if (vz.hit && simT >= vz.t_hit) {
        W.label(ctx, "hit the stop at " + Math.max(vz.v1, vz.v2).toFixed(2) + " m/s (the far end)", w / 2, h - 30,
                "#ff9a5c", "bold 12px system-ui", "center");
      }
      W.legend(ctx, [["drag the yellow hooks along the beam · arrows: each load's turning effect m·g·d", null]], 12, h - 10);
    }
  };

  PL.scenes.levers = levers;
})();
