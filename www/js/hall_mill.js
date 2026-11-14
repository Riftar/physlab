/* physlab game hall painter: HALL 3 - MILLBROOK MILL (wooden ball).
   Registered as PL.gameHalls.mill and drawn by PL.scenes.game
   (scene_game.js) with the shared drawing kit PL.gameKit. The layout comes
   from the server (physlab/game/mill.py LAYOUT).

   What moves comes from the run's frames (PL.game.fieldAt): the well's
   water level lv (3.1, above the well floor), the drawbridge `bridge`
   (3.3) and the hoist's beam angle th (3.4). What you tune is drawn from
   the CURRENT knobs, never a computed answer: before a run the things to
   drop wait in a pile next to the well, and the lamp's light is only
   drawn once a run has measured it.

   Handles (yellow):
     3.1  count: click − / + by the pile · item: click the pile's ⟳ tag
          (stones → bearings → pine blocks)
     3.2  wind: drag the gauge next to the fan up/down
     3.3  d_o: drag the lens up/down the beam
     3.4  hook: drag the bucket's hook along the beam · water: drag the
          measuring jug's level
   They call cam.setParams({"<station>.<knob>": value}) - the page validates
   and snaps the value exactly like the knob panel.                          */
(function () {
  "use strict";
  var K = PL.gameKit, W = PL.widgets, COL = K.COL;
  var rect = K.rect, line = K.line, dlabel = K.dlabel, knobHandle = K.knobHandle, sprite = K.sprite;
  var M = { stone: "#8d8890", stoneDark: "#5a5560", wood: "#c08a4e", pine: "#d8a35a", steel: "#c0c8d8",
            water: "rgba(61,143,224,0.6)", waterTop: "rgba(200,230,255,0.85)", grass: "#2f6b3a", hay: "#f4ce5c",
            beam: "#b07a44", rope: "#cfd6e6", light: "rgba(255,236,150,0.35)" };
  var DEG = Math.PI / 180;

  function at(frames, key, t, dflt) { return PL.game.fieldAt(frames, key, t, dflt); }
  function lastOf(S, sid) {
    return S.last ? S.last.stations.filter(function (r) { return r.id === sid; })[0] : null;
  }
  function knobSpec(S, sid, kid) { return S.stations[sid].knobs.filter(function (k) { return k.id === kid; })[0]; }
  function choiceOf(S, sid, kid) {
    var spec = knobSpec(S, sid, kid), v = S.knobs[sid][kid];
    return spec.choices.filter(function (c) { return c.id === v; })[0];
  }
  function nextChoice(S, sid, kid) {
    var spec = knobSpec(S, sid, kid), ids = spec.choices.map(function (c) { return c.id; });
    return ids[(ids.indexOf(S.knobs[sid][kid]) + 1) % ids.length];
  }
  function poly(ctx, cam, pts, fill, stroke, lw) {
    ctx.beginPath();
    pts.forEach(function (p, i) { i ? ctx.lineTo(cam.X(p[0]), cam.Y(p[1])) : ctx.moveTo(cam.X(p[0]), cam.Y(p[1])); });
    ctx.closePath();
    if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = lw || 1.2; ctx.stroke(); }
  }
  function circle(ctx, cam, x, y, r, fill, stroke) {
    ctx.beginPath(); ctx.arc(cam.X(x), cam.Y(y), Math.max(cam.len(r), 1), 0, 7);
    if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = 1; ctx.stroke(); }
  }
  function gauge(ctx, cam, g, frac, key, title, onDrag) {       // a vertical slider drawn in the hall
    var gx = g[0], gy = g[1] + (g[2] - g[1]) * frac;
    rect(ctx, cam, gx - 0.02, g[1], gx + 0.02, g[2], "rgba(17,26,58,0.9)", "#5c6a9c");
    rect(ctx, cam, gx - 0.016, g[1], gx + 0.016, gy, "rgba(92,170,255,0.75)");
    var hx = cam.X(gx), hy = cam.Y(gy);
    knobHandle(ctx, hx, hy, key, cam.hoverKey === key);
    cam.handle({ x: hx, y: hy, r: 13, key: key, cursor: "ns-resize", title: title,
                 drag: function (pt) { onDrag((pt.y - g[1]) / (g[2] - g[1])); } });
    return [hx, hy];
  }
  function cycleTag(ctx, cam, x, y, key, text, title, onClick) {
    var tx = cam.X(x), ty = cam.Y(y);
    knobHandle(ctx, tx, ty, key, cam.hoverKey === key);
    ctx.fillStyle = "#0b1128"; ctx.font = "bold 11px system-ui"; ctx.textAlign = "center"; ctx.fillText("⟳", tx, ty + 4);
    ctx.textAlign = "left";
    W.label(ctx, text, tx + 14, ty + 4, COL.handle, "bold 11px system-ui");
    cam.handle({ x: tx, y: ty, r: 13, key: key, cursor: "pointer", title: title, click: onClick });
  }

  /* the things to drop, drawn small (size from the item) */
  function item(ctx, cam, id, x, y) {
    if (id === "stone") {
      ctx.fillStyle = M.stone; ctx.strokeStyle = M.stoneDark; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.ellipse(cam.X(x), cam.Y(y), Math.max(cam.len(0.034), 2), Math.max(cam.len(0.026), 2), 0, 0, 7);
      ctx.fill(); ctx.stroke();
    } else if (id === "bearing") {
      circle(ctx, cam, x, y, 0.025, M.steel, "#6b7390");
    } else {
      var h = 0.02;
      rect(ctx, cam, x - h, y - h, x + h, y + h, M.pine, "#8a5a2a");
    }
  }
  var ITEM_STEP = { stone: 0.072, bearing: 0.052, block: 0.044 };

  function startPoint(S, sid) {
    var L = S.hall.layout.stations[sid], r = S.hall.layout.ball.r, k = S.knobs[sid];
    if (sid === "3.1") return { x: L.well[0], y: L.well[1] + L.h - 0.04 };
    if (sid === "3.2") return { x: L.lip[0] - 0.04, y: L.lip[1] + r };
    if (sid === "3.3") return { x: L.x0, y: L.path_y + r };
    var a = S.stations["3.4"].fact_values.arm, th = -L.stop * DEG;
    return { x: L.pivot[0] - a * Math.cos(th), y: L.pivot[1] + a * Math.sin(th) + L.lift };
  }

  /* ---------------- the building ---------------- */
  function building(ctx, cam, S) {
    var L = S.hall.layout, b = L.bounds;
    rect(ctx, cam, b.x0 - 5, b.y0 - 5, b.x1 + 5, 0, "#1b2a1e");                                  // the ground
    rect(ctx, cam, b.x0 - 5, -0.06, b.x1 + 5, 0, M.grass);
    sprite(ctx, cam, "grainsack", L.chute[0][0], L.chute[0][1] + 0.12, 0.42);                   // A
    line(ctx, cam, L.chute, M.wood, 5);
    line(ctx, cam, [[L.chute[0][0] + 0.05, L.chute[0][1] - 0.05], [L.chute[1][0], L.chute[1][1] - 0.05]], "#7a5430", 2);
  }

  /* ---------------- 3.1 Crow's Well ---------------- */
  function crowsWell(ctx, cam, S, simT, frames) {
    var L = S.hall.layout.stations["3.1"], k = S.knobs["3.1"], fx = S.stations["3.1"].fact_values;
    var wx = L.well[0], fy = L.well[1], hw = L.w / 2, top = fy + L.h;
    var res = lastOf(S, "3.1"), dropped = !!(res && frames.length && simT >= res.t0 - 1e-9);
    rect(ctx, cam, wx - 0.16, 0, wx + 0.16, fy - 0.05, "#3b3440", "#5a4f5e");                   // the stone tower
    for (var y = 0.1; y < fy - 0.05; y += 0.16) line(ctx, cam, [[wx - 0.16, y], [wx + 0.16, y]], "#4a4250", 1);
    // water (the level comes from the run; before the ball is in, the first depth)
    var lv = dropped ? at(frames, "lv", simT, fx.depth / 100) : fx.depth / 100;
    rect(ctx, cam, wx - hw, fy, wx + hw, fy + lv, M.water);
    line(ctx, cam, [[wx - hw, fy + lv], [wx + hw, fy + lv]], M.waterTop, 2);
    // what was dropped in: sinkers in a pile on the floor, blocks floating
    var it = k.item, n = k.count;
    if (dropped && n > 0) {
      if (it === "block") {
        for (var i = 0; i < Math.min(n, 12); i++) item(ctx, cam, it, wx - hw + 0.015 + (i % 2) * 0.07, fy + lv - 0.012 - Math.floor(i / 2) * 0.001);
      } else {
        var pile = Math.min(L.h, res.viz.extra_cm3 * 1e-6 / (Math.PI * hw * hw));
        rect(ctx, cam, wx - hw, fy, wx + hw, fy + pile, it === "stone" ? M.stone : "#8d95ab");
        for (var j = 0; j < Math.min(60, n); j++) {
          item(ctx, cam, it, wx - hw + 0.02 + (j % 2) * 0.06, fy + 0.02 + Math.floor(j / 2) * (pile / Math.ceil(Math.max(1, n) / 2)));
        }
      }
    }
    // walls with the paddles' slot on the right
    var slot = L.paddle, wall = "#5a4f5e";
    rect(ctx, cam, wx - hw - 0.05, fy - 0.05, wx - hw, top, wall, "#2c2530");
    rect(ctx, cam, wx + hw, fy - 0.05, wx + hw + 0.05, fy + slot - 0.06, wall, "#2c2530");
    rect(ctx, cam, wx + hw, fy + slot + 0.06, wx + hw + 0.05, top, wall, "#2c2530");
    rect(ctx, cam, wx - hw - 0.05, fy - 0.05, wx + hw + 0.05, fy, wall);
    // the paddles' band and a ruler
    ctx.setLineDash([3, 3]);
    [slot - L.band, slot + L.band].forEach(function (h) {
      line(ctx, cam, [[wx - hw, fy + h], [wx + hw, fy + h]], "rgba(125,255,168,0.8)", 1);
    });
    ctx.setLineDash([]);
    dlabel(ctx, cam, "← paddles sweep " + (100 * slot).toFixed(0) + " ± " + (100 * L.band).toFixed(1) + " cm",
           cam.X(L.wheel[0] + L.wheel_r + 0.04), cam.Y(fy + slot) + 4, "#7dffa8", "10px system-ui");
    for (var c = 0; c <= 70; c += 10) {
      line(ctx, cam, [[wx - hw - 0.09, fy + c / 100], [wx - hw - 0.06, fy + c / 100]], "#8d9acb", 1);
      dlabel(ctx, cam, c + "", cam.X(wx - hw - 0.1), cam.Y(fy + c / 100) + 3, "#8d9acb", "9px system-ui", "right");
    }
    dlabel(ctx, cam, "cm", cam.X(wx - hw - 0.1), cam.Y(top) - 10, "#8d9acb", "9px system-ui", "right");
    dlabel(ctx, cam, "well 10 cm across · " + fx.depth + " cm of water at first", cam.X(wx), cam.Y(fy - 0.08),
           COL.dim, "10px system-ui", "center");
    // the paddle wheel, turning slowly
    var wh = L.wheel, ang = simT * 1.2;
    circle(ctx, cam, wh[0], wh[1], 0.03, "#7a5430", "#0b1128");
    for (var p = 0; p < 6; p++) {
      var a = ang + p * Math.PI / 3, ex = wh[0] + L.wheel_r * Math.cos(a), ey = wh[1] + L.wheel_r * Math.sin(a);
      line(ctx, cam, [[wh[0], wh[1]], [ex, ey]], M.wood, 3);
      line(ctx, cam, [[ex - 0.025 * Math.sin(a), ey + 0.025 * Math.cos(a)], [ex + 0.025 * Math.sin(a), ey - 0.025 * Math.cos(a)]],
           "#7a5430", 5);
    }
    // the pile of things to drop (before they go in) + its handles
    var px = wx - 0.82, py = fy + 0.02, step = ITEM_STEP[it];
    rect(ctx, cam, px - 0.08, fy - 0.06, px + 0.48, fy - 0.02, "#3b3440");
    rect(ctx, cam, px + 0.18, 0, px + 0.22, fy - 0.06, "#3a4678");
    if (!dropped) {
      for (var q = 0; q < n; q++) item(ctx, cam, it, px + (q % 6) * step, py + Math.floor(q / 6) * step * 0.9);
    }
    var ch = choiceOf(S, "3.1", "item");
    dlabel(ctx, cam, n + " × " + ch.label.toLowerCase() + (dropped ? " (in the well)" : " to drop in"),
           cam.X(px + 0.2), cam.Y(fy + 0.56), COL.handle, "bold 11px system-ui", "center");
    [["−", -1, px - 0.02], ["+", 1, px + 0.42]].forEach(function (bt) {
      var bx = cam.X(bt[2]), by = cam.Y(fy + 0.47), key = "3.1.count" + bt[1];
      knobHandle(ctx, bx, by, key, cam.hoverKey === key);
      ctx.fillStyle = "#0b1128"; ctx.font = "bold 14px system-ui"; ctx.textAlign = "center";
      ctx.fillText(bt[0], bx, by + 5); ctx.textAlign = "left";
      cam.handle({ x: bx, y: by, r: 13, key: key, cursor: "pointer", title: (bt[1] > 0 ? "one more" : "one less"),
                   click: function () { cam.setParams({ "3.1.count": Math.max(0, k.count + bt[1]) }, true); } });
    });
    cycleTag(ctx, cam, px - 0.02, fy + 0.66, "3.1.item", "drop: " + ch.label, "click: stones / bearings / pine blocks",
             function () { cam.setParams({ "3.1.item": nextChoice(S, "3.1", "item") }, true); });
  }

  /* ---------------- 3.2 Fan Jump ---------------- */
  function fanJump(ctx, cam, S, simT, frames) {
    var L = S.hall.layout.stations["3.2"], k = S.knobs["3.2"], fx = S.stations["3.2"].fact_values;
    var lip = L.lip, r = S.hall.layout.ball.r;
    // chute from the well's slot down to the ski-jump lip (it turns up 10° at the end)
    var sl = L.slot, mid = [lip[0] - 0.3, lip[1] - 0.02];
    line(ctx, cam, [[sl[0] + 0.05, sl[1] - r], [mid[0], mid[1]], [lip[0], lip[1] - 0.0]], M.wood, 5);
    line(ctx, cam, [[mid[0], mid[1] - 0.05], [lip[0], lip[1] - 0.05]], "#7a5430", 2);
    rect(ctx, cam, lip[0] - 0.05, 0, lip[0] - 0.01, lip[1] - 0.05, "#3a4678");                     // the lip's post
    // the winnowing fan behind the lip, spinning with its wind; streaks show the wind
    var f = L.fan, R = L.fan_r, spin = simT * (1 + k.wind) * 1.5;
    circle(ctx, cam, f[0], f[1], R + 0.03, "#2a3358", "#5c6a9c");
    for (var i = 0; i < 4; i++) {
      var a = spin + i * Math.PI / 2;
      poly(ctx, cam, [[f[0], f[1]], [f[0] + R * Math.cos(a), f[1] + R * Math.sin(a)],
                      [f[0] + R * Math.cos(a + 0.5), f[1] + R * Math.sin(a + 0.5)]], "#aab3c5", "#0b1128");
    }
    circle(ctx, cam, f[0], f[1], 0.04, COL.handle, "#0b1128");
    rect(ctx, cam, f[0] - 0.04, 0, f[0] + 0.04, f[1] - R, "#3a4678");
    if (k.wind > 0) {
      for (var s = 0; s < 3; s++) {
        var y0 = f[1] - 0.15 + s * 0.15, len = 0.15 + 0.05 * k.wind, off = (simT * k.wind * 0.2 + s * 0.3) % 0.6;
        W.arrow(ctx, cam.X(f[0] + R + 0.05 + off), cam.Y(y0), cam.X(f[0] + R + 0.05 + off + len), cam.Y(y0),
                "rgba(92,214,255,0.6)", 1.5, 6);
      }
    }
    var g = gauge(ctx, cam, [f[0], f[1] + R + 0.12, f[1] + R + 0.62], k.wind / 20, "3.2.wind",
                  "drag: the fan's wind", function (u) { cam.setParams({ "3.2.wind": u * 20 }, false); });
    W.label(ctx, "fan " + k.wind.toFixed(1) + " m/s", g[0] + 14, g[1] + 4, COL.handle, "bold 11px system-ui");
    // the mill race, the far bank, the hay cart and the hedge
    var race = L.race;
    rect(ctx, cam, race[0], -0.02, race[1], 0.12, "rgba(61,143,224,0.7)");
    for (var x = race[0] + 0.1; x < race[1] - 0.2; x += 0.35) {
      W.arrow(ctx, cam.X(x), cam.Y(0.06), cam.X(x + 0.2), cam.Y(0.06), "rgba(200,230,255,0.6)", 1.2, 5);
    }
    dlabel(ctx, cam, "mill race", cam.X((race[0] + race[1]) / 2), cam.Y(0.18), "#8fd3ff", "10px system-ui", "center");
    var cx = lip[0] + fx.cart, rim = lip[1] - L.drop - 0.02, cw = 2 * L.cart_half / 0.875;
    rect(ctx, cam, race[1], 0, cx + 0.5, rim - 0.24, "#3b4a2e", "#2a3a22");                        // the bank
    sprite(ctx, cam, "haycart", cx, rim - cw * 0.34 + 0.03, cw);
    for (var h = 0; h < 4; h++) circle(ctx, cam, cx + 0.3 + h * 0.09, rim - 0.1 + (h % 2) * 0.05, 0.09, M.grass, "#1f4a28");
    dlabel(ctx, cam, "hay cart " + fx.cart.toFixed(2) + " m out, 2.5 m down", cam.X(cx), cam.Y(rim) - 30, COL.dim,
           "10px system-ui", "center");
    line(ctx, cam, [[lip[0], rim + 0.02], [cx, rim + 0.02]], "rgba(141,154,203,0.45)", 1, [3, 3]);
  }

  /* ---------------- 3.3 Light Gate ---------------- */
  function lightGate(ctx, cam, S, simT, frames, f) {
    var L = S.hall.layout.stations["3.3"], k = S.knobs["3.3"], fx = S.stations["3.3"].fact_values;
    var py = L.path_y, gx = L.gate_x, lampY = py + fx.bench / 100, lensY = lampY - k.d_o / 100;
    var br = L.bridge, bridge = at(frames, "bridge", simT, 0), res = lastOf(S, "3.3");
    var cartX = S.hall.layout.stations["3.2"].lip[0] + S.stations["3.2"].fact_values.cart;
    // the ramp from the cart, the path, the old contact plates
    line(ctx, cam, [[cartX + 0.14, py + 0.28], [L.x0 - 0.05, py + 0.0]], M.wood, 4);
    rect(ctx, cam, L.x0 - 0.1, py - 0.07, br[0], py, "#6b4a2a", "#3a2a18");
    for (var x = L.x0; x < br[0]; x += 0.5) rect(ctx, cam, x - 0.02, 0, x + 0.02, py - 0.07, "#3a4678");
    rect(ctx, cam, L.plates[0], py, L.plates[1], py + 0.008, "#d07a3a", "#0b1128");
    dlabel(ctx, cam, "old contact plates: wood doesn't conduct", cam.X((L.plates[0] + L.plates[1]) / 2), cam.Y(py) + 26,
           "#ff8f8f", "10px system-ui", "center");
    // the gate: post and arm, the lamp pointing down, the lens, the photocell in the path
    rect(ctx, cam, gx + 0.2, 0, gx + 0.24, lampY + 0.08, "#3a4678");
    line(ctx, cam, [[gx + 0.22, lampY + 0.06], [gx, lampY + 0.06]], "#5c6a9c", 3);
    sprite(ctx, cam, "lamp", gx, lampY + 0.02, 0.1, Math.PI);
    rect(ctx, cam, gx - 0.011, py - 0.004, gx + 0.011, py + 0.004, "#7dffa8", "#0b1128");
    dlabel(ctx, cam, "photocell 1 cm", cam.X(gx), cam.Y(py) + 14, "#7dffa8", "10px system-ui", "center");
    // the light: drawn once a run has measured it (the cone through the lens onto the cell)
    if (res && res.viz) {
      var v = res.viz, lw = 0.05, patch = v.patch / 100, broken = Math.abs(f.x - gx) < S.hall.layout.ball.r && f.y < py + 0.1;
      ctx.save(); ctx.globalCompositeOperation = "lighter";
      poly(ctx, cam, [[gx - 0.005, lampY], [gx + 0.005, lampY], [gx + lw, lensY], [gx - lw, lensY]], M.light);
      var bottom = broken ? f.y + 0.04 : py;
      var wAt = function (y) { var u = (lensY - y) / (lensY - py); return lw + (patch / 2 - lw) * u; };
      poly(ctx, cam, [[gx - lw, lensY], [gx + lw, lensY], [gx + wAt(bottom), bottom], [gx - wAt(bottom), bottom]], M.light);
      ctx.restore();
      W.label(ctx, (100 * v.share).toFixed(0) + "% of the light on the cell" + (v.share >= 0.5 ? " - armed" : " - not armed"),
              cam.X(gx) - 12, cam.Y(py + 0.12), v.share >= 0.5 ? "#7dffa8" : "#ff8a8a", "bold 11px system-ui", "right");
    } else {
      circle(ctx, cam, gx, lampY - 0.01, 0.02, "rgba(255,236,150,0.8)");
    }
    // the lens (drag it along the beam)
    ctx.fillStyle = "rgba(190,230,255,0.5)"; ctx.strokeStyle = "#bfe3ff"; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.ellipse(cam.X(gx), cam.Y(lensY), cam.len(0.05), Math.max(cam.len(0.008), 3), 0, 0, 7);
    ctx.fill(); ctx.stroke();
    line(ctx, cam, [[gx + 0.05, lensY], [gx + 0.2, lensY]], "#5c6a9c", 2);
    var hx = cam.X(gx + 0.2), hy = cam.Y(lensY);
    knobHandle(ctx, hx, hy, "3.3.d_o", cam.hoverKey === "3.3.d_o");
    cam.handle({ x: hx, y: hy, r: 13, key: "3.3.d_o", cursor: "ns-resize", title: "drag the lens up or down the beam",
                 drag: function (pt) { cam.setParams({ "3.3.d_o": (lampY - pt.y) * 100 }, false); } });
    dlabel(ctx, cam, "lens " + k.d_o.toFixed(1) + " cm below the lamp", hx + 14, hy + 4, COL.handle, "bold 11px system-ui");
    dlabel(ctx, cam, "lamp → cell " + fx.bench.toFixed(1) + " cm · f = " + fx.f.toFixed(1) + " cm", cam.X(gx + 0.26),
           cam.Y(lampY) + 4, COL.dim, "10px system-ui");
    // the drawbridge over the leat: up (80°) until the gate sees the ball, then down
    rect(ctx, cam, br[0], -0.02, br[1], 0.12, "rgba(61,143,224,0.7)");
    var a = (1 - bridge) * 80 * DEG, blen = br[1] - br[0];
    poly(ctx, cam, [[br[0], py], [br[0] + blen * Math.cos(a), py + blen * Math.sin(a)],
                    [br[0] + blen * Math.cos(a) + 0.05 * Math.sin(a), py + blen * Math.sin(a) - 0.05 * Math.cos(a)],
                    [br[0] + 0.05 * Math.sin(a), py - 0.05 * Math.cos(a)]], "#8a5a2a", "#3a2a18");
    rect(ctx, cam, br[1], py - 0.06, 8.46, py, "#6b4a2a", "#3a2a18");                               // fixed deck to the hoist
    rect(ctx, cam, br[1] - 0.02, 0, br[1] + 0.02, py - 0.06, "#3a4678");
    dlabel(ctx, cam, bridge > 0.99 ? "drawbridge down" : "drawbridge up", cam.X((br[0] + br[1]) / 2), cam.Y(0.16),
           "#8d9acb", "10px system-ui", "center");
  }

  /* ---------------- 3.4 Mill Hoist ---------------- */
  function beamPt(L, d, th) { return [L.pivot[0] + d * Math.cos(th), L.pivot[1] - d * Math.sin(th)]; }

  function hoist(ctx, cam, S, simT, frames) {
    var L = S.hall.layout.stations["3.4"], k = S.knobs["3.4"], fx = S.stations["3.4"].fact_values;
    var th = at(frames, "th", simT, -L.stop * DEG), half = L.beam / 2, pv = L.pivot;
    // the millstone shelf and the hopper (B)
    var sh = L.shelf, hp = L.hopper, hs = 0.46;
    rect(ctx, cam, 7.62, hp[1] - 0.25, 8.46, hp[1] - 0.21, "#6b4a2a", "#3a2a18");               // the mill floor's beam
    [7.64, 8.43].forEach(function (x) { rect(ctx, cam, x - 0.025, 0, x + 0.025, hp[1] - 0.21, "#3a4678"); });
    rect(ctx, cam, sh[0], sh[2] - 0.04, sh[1], sh[2], M.wood, "#3a2a18");
    sprite(ctx, cam, "millstone", hp[0], hp[1], hs);
    // the A-frame and the stops
    poly(ctx, cam, [[pv[0], pv[1]], [pv[0] - 0.2, 0], [pv[0] + 0.2, 0]], "#3a4678");
    [-1, 1].forEach(function (sd) {
      var e = beamPt(L, sd * half, sd * L.stop * DEG);
      rect(ctx, cam, e[0] - 0.035, 0, e[0] + 0.035, e[1] - 0.035, "#2a3358", "#5c6a9c");
    });
    // the beam
    var a = beamPt(L, -half, th), b = beamPt(L, half, th), nx = Math.sin(th) * 0.025, ny = Math.cos(th) * 0.025;
    poly(ctx, cam, [[a[0] + nx, a[1] + ny], [b[0] + nx, b[1] + ny], [b[0] - nx, b[1] - ny], [a[0] - nx, a[1] - ny]],
         M.beam, "#3a2a18");
    circle(ctx, cam, pv[0], pv[1], 0.025, "#dfe6ff", "#0b1128");
    // the scoop at the arm's end (the ball rides in it)
    var s = beamPt(L, -fx.arm, th);
    ctx.strokeStyle = "#7a5430"; ctx.lineWidth = Math.max(3, cam.len(0.015));
    ctx.beginPath(); ctx.arc(cam.X(s[0]), cam.Y(s[1] + L.lift), cam.len(0.06), 0.1 * Math.PI, 0.9 * Math.PI); ctx.stroke();
    dlabel(ctx, cam, "scoop arm a = " + fx.arm.toFixed(2) + " m", cam.X(pv[0] - 0.5), cam.Y(pv[1] + 0.42), COL.dim,
           "10px system-ui", "center");
    // the bucket on its hook
    var hk = beamPt(L, k.hook, th), rope = 0.05, bs = 0.09 + 0.04 * Math.cbrt(0.2 + k.water);   // (clears the floor)
    line(ctx, cam, [[hk[0], hk[1]], [hk[0], hk[1] - rope]], M.rope, 1.5);
    sprite(ctx, cam, "bucket", hk[0], hk[1] - rope - bs * 0.45, bs);
    dlabel(ctx, cam, "bucket " + (0.2 + k.water).toFixed(2) + " kg (" + k.water.toFixed(2) + " L)", cam.X(hk[0]),
           cam.Y(hk[1] - rope - bs) + 14, COL.handle, "bold 11px system-ui", "center");
    var hx = cam.X(hk[0]), hy = cam.Y(hk[1]);
    knobHandle(ctx, hx, hy, "3.4.hook", cam.hoverKey === "3.4.hook");
    cam.handle({ x: hx, y: hy, r: 12, key: "3.4.hook", cursor: "ew-resize", title: "drag the bucket's hook along the beam",
                 drag: function (pt) { cam.setParams({ "3.4.hook": (pt.x - pv[0]) / Math.cos(th) }, false); } });
    dlabel(ctx, cam, "b = " + k.hook.toFixed(2) + " m", hx, hy - 14, COL.handle, "bold 11px system-ui", "center");
    // the measuring jug: its level is the water (0 - 2 L)
    var jug = [pv[0] + 1.22, 0.1, 0.9];
    var g = gauge(ctx, cam, jug, k.water / 2, "3.4.water", "drag: how much water in the bucket",
                  function (u) { cam.setParams({ "3.4.water": u * 2 }, false); });
    W.label(ctx, "jug: " + k.water.toFixed(2) + " L", g[0] - 12, g[1] + 4, COL.handle, "bold 11px system-ui", "right");
  }

  function hoistFront(ctx, cam, S) {
    var L = S.hall.layout.stations["3.4"];
    K.endpoint(ctx, cam, L.hopper[0] - 0.4, L.hopper[1] + 0.35, "B", "millstone hopper", "#5cc8ff");
  }

  PL.gameHalls.mill = {
    detail: 100,                             // the whole hall is crowded: small labels only when zoomed in
    tags: function () { return [["3.1", 0.55, 4.15], ["3.2", 3.45, 3.55], ["3.3", 5.55, 1.75], ["3.4", 9.85, 1.75]]; },
    startPoint: startPoint,
    draw: function (ctx, cam, S, simT, frames) {
      var L = S.hall.layout, f = frames.length ? PL.frameAt(frames, simT) : startPoint(S, S.focus || "3.1");
      building(ctx, cam, S);
      crowsWell(ctx, cam, S, simT, frames);
      fanJump(ctx, cam, S, simT, frames);
      lightGate(ctx, cam, S, simT, frames, f);
      hoist(ctx, cam, S, simT, frames);
      K.endpoint(ctx, cam, L.A[0], L.A[1], "A", "grain chute", "#5be39b");
    },
    front: function (ctx, cam, S) { hoistFront(ctx, cam, S); }
  };
})();
