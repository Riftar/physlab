/* physlab scene: CIRCUIT LAB (sandbox) - any circuit the student builds
   on a grid of connection dots, solved on the server by nodal analysis
   (physlab/topics/circuitlab.py). World units: one grid step; column c,
   row r sits at (c, rows - 1 - r) so row 0 is the top row.

   Honest encodings
   - charges are spread evenly (same density in every part) and each part's
     charges drift at a speed proportional to ITS current, so Kirchhoff's
     current law is visible: what flows into a dot flows out of it
   - lamp glow = the server's filament temperature (black-body colour) and
     perceived brightness on the SAME scale as the Electric Circuits topic,
     so a 0.5 W indicator really is dimmer than a 5 W car bulb
   - "voltage" view colours every dot and wire by its potential
   Editing: every gap between two neighbouring dots is a clickable handle;
   the page decides what a click does with the current tool (view.tool). */
(function () {
  "use strict";
  var W = PL.widgets;
  var SPEED_PER_AMP = 0.9;          // grid steps per second per ampere (on screen)
  var MAX_SPEED = 4.0;              // cap for big (short-circuit) currents - labelled
  var PER_STEP = 4;                 // charges per grid step, everywhere
  var HOT_AMPS = 5;                 // wires visibly heat up above this

  function node(c, r, rows) { return { x: c, y: rows - 1 - r }; }

  function voltColor(v, vmax) {     // 0 V blue -> highest potential red
    var k = vmax > 1e-9 ? W.clamp(v / vmax, 0, 1) : 0;
    var a = [77, 163, 255], b = [255, 92, 92];
    return "rgb(" + [0, 1, 2].map(function (i) { return Math.round(a[i] + (b[i] - a[i]) * k); }).join(",") + ")";
  }

  var lab = {
    continuous: true,
    options: [
      { id: "carriers", label: "Show", default: "electrons",
        choices: [{ id: "electrons", label: "electrons (−)" }, { id: "conventional", label: "conventional (+)" }] },
      { id: "values", label: "Numbers", default: "current",
        choices: [{ id: "current", label: "current" }, { id: "voltage", label: "voltage" },
                  { id: "none", label: "off" }] }
    ],
    duration: function () { return 4; },
    world: function (runs) {
      var vz = runs[0].result.viz;
      return { x0: -0.7, x1: vz.cols - 1 + 0.7, y0: -1.05, y1: vz.rows - 1 + 0.75 };
    },
    worldPad: 0.01,

    init: function (ctx, w, h, runs) {
      this.phase = {};               // per part: distance its charges have drifted (grid steps)
      this.real = 0;
    },

    render: function (ctx, w, h, simT, clock, runs, view, cam) {
      var run = runs[0], vz = run.result.viz, rows = vz.rows, cols = vz.cols, that = this;
      var X = function (x) { return cam.X(x); }, Y = function (y) { return cam.Y(y); }, s = cam.len(1);
      var specs = vz.specs, res = vz.parts, tool = view.tool || "hand";
      var conventional = view.carriers === "conventional";
      var volts = vz.volts, vmax = 0;
      volts.forEach(function (v) { if (v != null) vmax = Math.max(vmax, v); });
      var P = function (e) { var q = node(e[0], e[1], rows); return [X(q.x), Y(q.y)]; };
      var vAt = function (e) { var v = volts[e[1] * cols + e[0]]; return v == null ? 0 : v; };
      if (clock.playing) this.real += clock.real;
      ctx.clearRect(0, 0, w, h);

      // ---- lamp light on the board (additive, under everything) ----
      ctx.save(); ctx.globalCompositeOperation = "lighter";
      specs.forEach(function (sp, i) {
        var r = res[i];
        if (sp.kind !== "lamp" || !(r.brightness > 0.002)) return;
        var a = P(sp.a), b = P(sp.b), cx = (a[0] + b[0]) / 2, cy = (a[1] + b[1]) / 2;
        var bb = Math.min(1, r.brightness), rad = s * (0.6 + 2.6 * bb);
        var gr = ctx.createRadialGradient(cx, cy, 4, cx, cy, rad);
        gr.addColorStop(0, W.rgba(r.color, 0.35 * Math.min(1, bb * 1.8)));
        gr.addColorStop(1, W.rgba(r.color, 0));
        ctx.fillStyle = gr; ctx.fillRect(cx - rad, cy - rad, 2 * rad, 2 * rad);
      });
      ctx.restore();

      // ---- dots (connection points) ----
      var used = {};
      specs.forEach(function (sp) { used[sp.a.join()] = true; used[sp.b.join()] = true; });
      for (var r0 = 0; r0 < rows; r0++) {
        for (var c0 = 0; c0 < cols; c0++) {
          var q = P([c0, r0]), on = used[c0 + "," + r0];
          ctx.fillStyle = on ? (view.values === "voltage" ? voltColor(vAt([c0, r0]), vmax) : "#c9d3f0") : "#3a4a7a";
          ctx.beginPath(); ctx.arc(q[0], q[1], on ? Math.max(3, s * 0.05) : Math.max(2, s * 0.03), 0, 7); ctx.fill();
        }
      }

      // ---- parts ----
      specs.forEach(function (sp, i) {
        var r = res[i], a = P(sp.a), b = P(sp.b);
        var dx = b[0] - a[0], dy = b[1] - a[1], ang = Math.atan2(dy, dx);
        var cx = (a[0] + b[0]) / 2, cy = (a[1] + b[1]) / 2;
        var wireCol = view.values === "voltage" ? null : "#7b8cc0";
        var lineAB = function (from, to, width) {
          if (wireCol) { ctx.strokeStyle = wireCol; }
          else {
            var g = ctx.createLinearGradient(a[0], a[1], b[0], b[1]);
            g.addColorStop(0, voltColor(r.va, vmax)); g.addColorStop(1, voltColor(r.vb, vmax));
            ctx.strokeStyle = g;
          }
          ctx.lineWidth = width || 4; ctx.lineCap = "round";
          ctx.beginPath();
          ctx.moveTo(a[0] + dx * from, a[1] + dy * from); ctx.lineTo(a[0] + dx * to, a[1] + dy * to);
          ctx.stroke(); ctx.lineCap = "butt";
        };
        // a very hot wire (short circuit) glows
        if ((sp.kind === "wire" || sp.kind === "switch") && Math.abs(r.current) > HOT_AMPS) {
          var heat = W.clamp(Math.log10(Math.abs(r.current) / HOT_AMPS) / 1.5, 0.15, 1);
          ctx.strokeStyle = "rgba(255,120,40," + (0.35 + 0.5 * heat).toFixed(3) + ")";
          ctx.lineWidth = 10 + 8 * heat; ctx.lineCap = "round";
          ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke(); ctx.lineCap = "butt";
        }
        if (sp.kind === "wire") {
          lineAB(0, 1);
        } else if (sp.kind === "switch") {
          lineAB(0, 0.3); lineAB(0.7, 1);
          var p0 = [a[0] + dx * 0.3, a[1] + dy * 0.3], p1 = [a[0] + dx * 0.7, a[1] + dy * 0.7];
          ctx.fillStyle = "#c9d3f0";
          [p0, p1].forEach(function (p) { ctx.beginPath(); ctx.arc(p[0], p[1], Math.max(3, s * 0.045), 0, 7); ctx.fill(); });
          var open = !sp.on, la = ang - (open ? 0.6 : 0), ll = s * 0.4;
          ctx.strokeStyle = open ? "#b0b8d8" : "#ffd166"; ctx.lineWidth = Math.max(3, s * 0.05); ctx.lineCap = "round";
          ctx.beginPath(); ctx.moveTo(p0[0], p0[1]);
          ctx.lineTo(p0[0] + Math.cos(la) * ll, p0[1] + Math.sin(la) * ll); ctx.stroke(); ctx.lineCap = "butt";
          W.label(ctx, open ? "OFF" : "ON", cx + Math.sin(ang) * s * 0.2, cy - Math.cos(ang) * s * 0.2 - 2,
                  open ? "#ff8a8a" : "#7dffa8", "bold " + Math.round(W.clamp(s * 0.12, 9, 13)) + "px system-ui", "center");
        } else if (sp.kind === "resistor") {
          lineAB(0, 0.22); lineAB(0.78, 1);
          if (!PL.drawSprite(ctx, "resistor", cx, cy, s * 0.62, null, ang)) {
            ctx.save(); ctx.translate(cx, cy); ctx.rotate(ang);
            ctx.fillStyle = "#d9b38c"; ctx.fillRect(-s * 0.28, -s * 0.08, s * 0.56, s * 0.16); ctx.restore();
          }
        } else if (sp.kind === "battery") {
          lineAB(0, 0.2); lineAB(0.8, 1);
          // the sprite has + on its right: point that end at the + terminal
          var plusAtB = !sp.flip, rot = plusAtB ? ang : ang + Math.PI;
          if (!PL.drawSprite(ctx, "battery", cx, cy, s * 0.72, null, rot)) {
            ctx.save(); ctx.translate(cx, cy); ctx.rotate(rot);
            ctx.fillStyle = "#3ddc84"; ctx.fillRect(-s * 0.3, -s * 0.12, s * 0.6, s * 0.24); ctx.restore();
          }
          var pp = plusAtB ? b : a, mm = plusAtB ? a : b, fs = Math.round(W.clamp(s * 0.16, 10, 18));
          var nx = -Math.sin(ang) * s * 0.2, ny = Math.cos(ang) * s * 0.2;
          W.label(ctx, "+", cx + (pp[0] - cx) * 0.62 + nx, cy + (pp[1] - cy) * 0.62 + ny + fs / 3, "#ff9a9a", "bold " + fs + "px system-ui", "center");
          W.label(ctx, "−", cx + (mm[0] - cx) * 0.62 + nx, cy + (mm[1] - cy) * 0.62 + ny + fs / 3, "#8fb8ff", "bold " + fs + "px system-ui", "center");
          if (r.short) {
            var blink = 0.5 + 0.5 * Math.sin(that.real * 8);
            W.label(ctx, "⚠ SHORT!", cx, cy - s * 0.3, "rgba(255,120,120," + (0.5 + 0.5 * blink).toFixed(2) + ")",
                    "bold " + Math.round(W.clamp(s * 0.15, 11, 16)) + "px system-ui", "center");
          }
        } else if (sp.kind === "lamp") {
          lineAB(0, 0.3); lineAB(0.7, 1);
          that._lamp(ctx, cx, cy, s, ang, r);
        }
      });

      // ---- moving charges: same density everywhere, speed ∝ each part's current ----
      var capped = false, dir = conventional ? 1 : -1;
      specs.forEach(function (sp, i) {
        var r = res[i], I = r.current || 0;
        if (sp.kind === "switch" && !sp.on) return;
        if ((sp.kind === "lamp" || sp.kind === "resistor") && r.blown) return;
        var v = I * SPEED_PER_AMP;
        if (Math.abs(v) > MAX_SPEED) { v = MAX_SPEED * Math.sign(v); capped = true; }
        if (clock.playing) that.phase[i] = ((that.phase[i] || 0) + v * clock.real) % 1;
        var ph = that.phase[i] || 0, flowing = Math.abs(I) > 1e-6;
        var a = P(sp.a), b = P(sp.b);
        var rad = Math.max(2.2, Math.min(5, s * 0.045)), inner = sp.kind !== "wire" && sp.kind !== "switch";
        ctx.globalAlpha = flowing ? 0.95 : 0.4;
        for (var k = 0; k < PER_STEP; k++) {
          var u = (((k / PER_STEP + dir * ph) % 1) + 1) % 1;
          var x = a[0] + (b[0] - a[0]) * u, y = a[1] + (b[1] - a[1]) * u;
          var rr = inner ? rad * 0.75 : rad;
          ctx.beginPath(); ctx.arc(x, y, rr, 0, 7);
          ctx.fillStyle = conventional ? "#ffcc4d" : "#4da3ff"; ctx.fill();
          ctx.strokeStyle = conventional ? "#6b4a00" : "#ffffff"; ctx.lineWidth = 1.2;
          ctx.beginPath(); ctx.moveTo(x - rr * 0.55, y); ctx.lineTo(x + rr * 0.55, y);
          if (conventional) { ctx.moveTo(x, y - rr * 0.55); ctx.lineTo(x, y + rr * 0.55); }
          ctx.stroke();
        }
        ctx.globalAlpha = 1;
      });

      // ---- lamp halos on top ----
      ctx.save(); ctx.globalCompositeOperation = "lighter";
      specs.forEach(function (sp, i) {
        var r = res[i];
        if (sp.kind !== "lamp" || !(r.brightness > 0.002)) return;
        var a = P(sp.a), b = P(sp.b), cx = (a[0] + b[0]) / 2, cy = (a[1] + b[1]) / 2;
        var bb = Math.min(1, r.brightness), rad = s * (0.2 + 0.9 * bb);
        var gr = ctx.createRadialGradient(cx, cy, 1, cx, cy, rad);
        gr.addColorStop(0, W.rgba(r.color, Math.min(0.95, 1.5 * bb)));
        gr.addColorStop(0.3, W.rgba(r.color, Math.min(0.6, 0.8 * bb)));
        gr.addColorStop(1, W.rgba(r.color, 0));
        ctx.fillStyle = gr; ctx.beginPath(); ctx.arc(cx, cy, rad, 0, 7); ctx.fill();
      });
      ctx.restore();

      // ---- numbers next to the parts ----
      var fsz = Math.round(W.clamp(s * 0.12, 9, 13));
      specs.forEach(function (sp, i) {
        var r = res[i], a = P(sp.a), b = P(sp.b), cx = (a[0] + b[0]) / 2, cy = (a[1] + b[1]) / 2;
        var horiz = Math.abs(b[1] - a[1]) < 1;
        var lx = horiz ? cx : cx + s * 0.2, ly = horiz ? cy + s * 0.3 : cy - s * 0.05;
        var align = horiz ? "center" : "left";
        var lines = [];
        if (sp.short) lines.push([sp.short, "#cfd8f0"]);
        if (view.values === "current" && sp.kind !== "wire" && !(sp.kind === "switch")) {
          if (!r.blown) lines.push([Math.abs(r.current).toFixed(Math.abs(r.current) < 1 ? 3 : 2) + " A", "#ffd166"]);
        } else if (view.values === "voltage" && (sp.kind === "lamp" || sp.kind === "resistor" || sp.kind === "battery")) {
          lines.push([Math.abs(r.va - r.vb).toFixed(2) + " V", "#ff9a9a"]);
        }
        if (sp.kind === "lamp" && r.blown) lines.push(["💥 blown", "#ff8a8a"]);
        else if (sp.kind === "lamp" && r.status === "overvolted") lines.push(["⚠ over-volted", "#ffb347"]);
        lines.forEach(function (ln, j) {
          W.label(ctx, ln[0], lx, ly + j * (fsz + 2), ln[1], (j ? "bold " : "") + fsz + "px system-ui", align);
        });
      });
      if (view.values === "voltage") {
        for (var rr2 = 0; rr2 < rows; rr2++) {
          for (var cc2 = 0; cc2 < cols; cc2++) {
            if (!used[cc2 + "," + rr2]) continue;
            var q2 = P([cc2, rr2]);
            var vv = vAt([cc2, rr2]);
            W.label(ctx, (Math.abs(vv) < 0.05 ? 0 : vv).toFixed(1), q2[0] + 5, q2[1] - 5, voltColor(vv, vmax), "10px system-ui");
          }
        }
      }

      // ---- editing handles: every gap between two neighbouring dots ----
      var hr = Math.max(8, s * 0.22);
      var edge = function (c1, r1, c2, r2) {
        var a = P([c1, r1]), b = P([c2, r2]), key = c1 + "," + r1 + "-" + c2 + "," + r2;
        var mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2;
        if (cam.hoverKey === key && tool !== "hand") that._ghost(ctx, a, b, s, tool);
        cam.handle({ x: mx, y: my, r: hr, key: key, cursor: "pointer",
                     title: tool === "hand" ? "click a switch to flip it, a battery to turn it round"
                       : tool === "eraser" ? "click a part to remove it" : "click to place it here",
                     click: function () { cam.setParams({ edge: [[c1, r1], [c2, r2]] }, true); } });
      };
      for (var r1 = 0; r1 < rows; r1++) {
        for (var c1 = 0; c1 < cols; c1++) {
          if (c1 + 1 < cols) edge(c1, r1, c1 + 1, r1);
          if (r1 + 1 < rows) edge(c1, r1, c1, r1 + 1);
        }
      }

      // ---- HUD + legend ----
      var bats = specs.map(function (sp, i) { return sp.kind === "battery" ? res[i] : null; }).filter(Boolean);
      var lamps = specs.map(function (sp, i) { return sp.kind === "lamp" ? res[i] : null; }).filter(Boolean);
      var pOut = bats.reduce(function (acc, r) { return acc + r.power_out; }, 0);
      var lit = lamps.filter(function (r) { return r.brightness > 0.02; }).length;
      W.hud(ctx, [
        specs.length + " parts · " + bats.length + " batter" + (bats.length === 1 ? "y" : "ies") + " · " +
          lamps.length + " lamp" + (lamps.length === 1 ? "" : "s") + (lamps.length ? " (" + lit + " lit)" : ""),
        bats.length ? "batteries deliver " + pOut.toFixed(pOut < 10 ? 2 : 1) + " W" : "no battery yet"
      ]);
      W.label(ctx, conventional ? "● + charges: conventional current, out of + round to −"
                                : "● electrons drift out of − round to + (current I points the other way)",
              12, h - 28, conventional ? "#ffcc4d" : "#7dbdff", "12px system-ui");
      W.label(ctx, "even spacing everywhere · drift speed ∝ each part's current" +
              (capped ? " (huge ones capped)" : "") + " · real filament colour & brightness",
              12, h - 11, "#9fb3e8", "12px system-ui");
    },

    /* a light bulb centred on its gap, brightness/colour from the server */
    _lamp: function (ctx, cx, cy, s, ang, r) {
      var R = s * 0.22, blown = r.blown, bb = Math.min(1, r.brightness || 0), col = r.color || "#ffd9a0";
      ctx.save(); ctx.translate(cx, cy);
      ctx.beginPath(); ctx.arc(0, 0, R, 0, 7);
      ctx.fillStyle = blown ? "rgba(90,90,100,0.55)" : "rgba(190,205,235,0.16)"; ctx.fill();
      if (bb > 0.001 && !blown) { ctx.fillStyle = W.rgba(col, Math.min(0.92, 2.4 * bb)); ctx.fill(); }
      ctx.strokeStyle = blown ? "#6b7390" : "rgba(210,222,255,0.75)"; ctx.lineWidth = 1.5; ctx.stroke();
      ctx.rotate(ang);
      // filament: glows from ~800 K, its colour is the black-body colour at that temperature
      var vis = W.clamp(((r.filament_k || 293) - 750) / 450, 0, 1);
      var coil = function () {
        ctx.beginPath(); ctx.moveTo(-R * 0.7, 0);
        for (var z = 1; z <= 8; z++) ctx.lineTo(-R * 0.7 + z * R * 0.175, (z % 2 ? -1 : 1) * R * 0.22);
        ctx.stroke();
      };
      ctx.lineWidth = 1.4; ctx.strokeStyle = "#4a4f5e";
      if (blown) {                                   // a broken filament
        ctx.beginPath(); ctx.moveTo(-R * 0.7, 0); ctx.lineTo(-R * 0.1, R * 0.25);
        ctx.moveTo(R * 0.7, 0); ctx.lineTo(R * 0.15, -R * 0.3); ctx.stroke();
      } else {
        coil();
        if (vis > 0) { ctx.strokeStyle = W.rgba(col, vis); ctx.lineWidth = 2; coil(); }
        if (bb > 0.3) { ctx.strokeStyle = "rgba(255,255,255," + Math.min(1, (bb - 0.3) * 1.6).toFixed(3) + ")"; ctx.lineWidth = 1.1; coil(); }
      }
      ctx.restore();
    },

    /* preview of what a click would do */
    _ghost: function (ctx, a, b, s, tool) {
      ctx.save();
      ctx.strokeStyle = tool === "eraser" ? "rgba(255,92,138,0.9)" : "rgba(255,209,102,0.8)";
      ctx.lineWidth = Math.max(6, s * 0.12); ctx.lineCap = "round"; ctx.globalAlpha = 0.45;
      ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
      ctx.restore();
    }
  };

  PL.scenes.circuitlab = lab;
})();
