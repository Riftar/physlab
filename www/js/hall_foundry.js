/* physlab game hall painter: HALL 2 - THE FOUNDRY (steel ball).
   Registered as PL.gameHalls.foundry and drawn by PL.scenes.game
   (scene_game.js) with the shared drawing kit PL.gameKit. The layout comes
   from the server (physlab/game/foundry.py LAYOUT).

   What moves comes from the run's frames (PL.game.fieldAt): the ring's and
   the ball's temperatures T / Tb (2.1), the trapdoor's opening `door` and
   the latch current I (2.2), the pistons x1 / x2 (2.3) and the cable angle
   th (2.4). What you tune is drawn from the CURRENT knobs - only geometry and
   amounts, never a computed answer (no current or temperature before a run).

   Handles (yellow):
     2.1  water: drag the gauge next to the kettle up/down · target: click the
          "pour on" tag to switch ring → ball → both
     2.2  R: drag round the resistor dial · battery: click the battery to
          swap it (AA → 6 V lantern → 9 V → 12 V car battery)
     2.3  d2: drag the big piston's right edge sideways
     2.4  length: drag the cable's pivot up/down · angle: drag the ball round
          the pivot
   They call cam.setParams({"<station>.<knob>": value}) - the page validates
   and snaps the value exactly like the knob panel.                          */
(function () {
  "use strict";
  var K = PL.gameKit, W = PL.widgets, COL = K.COL;
  var rect = K.rect, line = K.line, dlabel = K.dlabel, knobHandle = K.knobHandle, sprite = K.sprite, mix = K.mix;
  var F = { steel: [170, 179, 197], hot: [255, 128, 48], copper: "#d07a3a", oil: "rgba(224,168,60,0.85)",
            oilDim: "rgba(224,168,60,0.35)", water: "rgba(61,143,224,0.55)", foam: "#d9d2c0", iron: "#5a6480",
            girder: "#46527e", glow: "#ff8a30", wire: "#8fd3ff", wireOn: "#ffe27a" };
  var ROOM = 20, RING_RX = 0.1, RING_RY = 0.028;

  function at(frames, key, t, dflt) { return PL.game.fieldAt(frames, key, t, dflt); }
  function lastOf(S, sid) {
    return S.last ? S.last.stations.filter(function (r) { return r.id === sid; })[0] : null;
  }
  function heatCol(T) { return mix(F.steel, F.hot, Math.max(0, Math.min(1, (T - ROOM) / 75))); }
  function knobSpec(S, sid, kid) { return S.stations[sid].knobs.filter(function (k) { return k.id === kid; })[0]; }
  function choiceOf(S, sid, kid) {
    var spec = knobSpec(S, sid, kid), v = S.knobs[sid][kid];
    return spec.choices.filter(function (c) { return c.id === v; })[0];
  }
  function nextChoice(S, sid, kid) {
    var spec = knobSpec(S, sid, kid), ids = spec.choices.map(function (c) { return c.id; });
    return ids[(ids.indexOf(S.knobs[sid][kid]) + 1) % ids.length];
  }
  function poly(ctx, cam, pts, fill, stroke) {
    ctx.beginPath();
    pts.forEach(function (p, i) { i ? ctx.lineTo(cam.X(p[0]), cam.Y(p[1])) : ctx.moveTo(cam.X(p[0]), cam.Y(p[1])); });
    ctx.closePath();
    if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = 1.2; ctx.stroke(); }
  }
  function ellipse(ctx, cam, x, y, rx, ry, fill, stroke, a0, a1) {
    ctx.beginPath();
    ctx.ellipse(cam.X(x), cam.Y(y), Math.max(cam.len(rx), 0.5), Math.max(cam.len(ry), 0.5), 0, a0 || 0, a1 == null ? 7 : a1);
    if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = 1.5; ctx.stroke(); }
  }
  function startPoint(S, sid) {
    var L = S.hall.layout.stations[sid], r = S.hall.layout.ball.r, k = S.knobs[sid];
    if (sid === "2.1") return { x: L.ring[0], y: L.ring[1] + 0.012 };
    if (sid === "2.2") return { x: L.trap[0], y: L.trap[1] + r };
    if (sid === "2.3") return { x: L.small_x, y: L.top + r };
    var th = k.angle * Math.PI / 180;
    return { x: L.swing[0] - k.length * Math.sin(th), y: L.swing[1] + k.length * (1 - Math.cos(th)) };
  }

  /* ---------------- the building ---------------- */
  function building(ctx, cam, S) {
    var L = S.hall.layout, b = L.bounds;
    rect(ctx, cam, b.x0 - 5, b.y0 - 5, b.x1 + 5, 0, COL.floor);                                  // ground
    L.decks.forEach(function (d) { rect(ctx, cam, d.x0, d.y - 0.12, d.x1, d.y, COL.mezz, "#3a4678"); });
    rect(ctx, cam, b.x0, 0, b.x0 + 0.12, 5.63, COL.post);                                        // wall + columns
    rect(ctx, cam, 3.0, 0, 3.12, L.stations["2.3"].floor - 0.1, COL.post);
    rect(ctx, cam, 4.45, 0, 4.57, 2.33, COL.post);
    [5.6, 6.9].forEach(function (x) { rect(ctx, cam, x - 0.02, L.stations["2.4"].girder_y, x + 0.02, b.y1 + 1, COL.post); });
    // the casting pit under the ladle: a glowing trench
    var s4 = L.stations["2.4"], bx = s4.swing[0] + S.stations["2.4"].fact_values.ladle;
    var g = ctx.createLinearGradient(0, cam.Y(0.35), 0, cam.Y(0));
    g.addColorStop(0, "rgba(255,138,48,0)"); g.addColorStop(1, "rgba(255,138,48,0.55)");
    ctx.fillStyle = g; ctx.fillRect(cam.X(bx - 0.8), cam.Y(0.35), cam.len(1.6), cam.len(0.35));
    rect(ctx, cam, bx - 0.8, -0.12, bx + 0.8, 0.02, "#3a1c14");
    rect(ctx, cam, bx - 0.75, -0.08, bx + 0.75, 0.0, F.glow);
    dlabel(ctx, cam, "casting pit", cam.X(bx + 0.55), cam.Y(0.08) - 4, "#ffb37a", "10px system-ui", "center");
  }

  /* ---------------- 2.1 Hot Ring ---------------- */
  function hotRing(ctx, cam, S, simT, frames) {
    var L = S.hall.layout.stations["2.1"], k = S.knobs["2.1"], fx = S.stations["2.1"].fact_values;
    var rx = L.ring[0], ry = L.ring[1], T = at(frames, "T", simT, ROOM);
    var tgt = k.target, frac = Math.min(1, k.water / L.water_max);
    // the cart (A) and the tube down through the floor
    sprite(ctx, cam, "minecart", S.hall.layout.cart[0], S.hall.layout.cart[1], 0.56);
    line(ctx, cam, [[0.62, 6.25], [rx - 0.04, ry + 0.04]], "#5c6a9c", 3);                          // tipping lip
    rect(ctx, cam, rx - 0.045, L.chute_y, rx + 0.045, L.floor - 0.12, "#26305c", "#5c6a9c");       // drop tube
    // the insulated cup the ring sits in
    var cup = [rx - 0.13, L.floor, rx + 0.13, ry + 0.07];
    poly(ctx, cam, [[cup[0] - 0.03, cup[3]], [cup[2] + 0.03, cup[3]], [cup[2], cup[1]], [cup[0], cup[1]]],
         "rgba(217,210,192,0.22)", F.foam);
    if (k.water > 0 && tgt !== "ball") {                                                         // hot water in the cup
      var top = tgt === "both" ? ry + 0.055 : cup[1] + (ry + 0.015 - cup[1]) * Math.min(1, 0.35 + 1.3 * frac);
      var sl = 0.03 * (top - cup[1]) / (cup[3] - cup[1]);
      poly(ctx, cam, [[cup[0] - sl + 0.01, top], [cup[2] + sl - 0.01, top], [cup[2] - 0.01, cup[1] + 0.01],
                      [cup[0] + 0.01, cup[1] + 0.01]], F.water);
    }
    dlabel(ctx, cam, "foam cup", cam.X(cup[0] - 0.04), cam.Y(cup[1] + 0.03), COL.dim, "10px system-ui", "right");
    // the ring (back half; the front half goes over the ball in front())
    ellipse(ctx, cam, rx, ry, RING_RX, RING_RY, heatCol(T), "#0b1128");
    ellipse(ctx, cam, rx, ry + 0.002, 0.026, 0.008, "#0b1128");
    dlabel(ctx, cam, "hole " + (fx.ball_d - fx.gap_um / 1000).toFixed(2) + " mm · ball " + fx.ball_d.toFixed(2) + " mm",
           cam.X(rx), cam.Y(cup[1]) + 26, COL.dim, "10px system-ui", "center");
    var Tb = at(frames, "Tb", simT, ROOM);
    dlabel(ctx, cam, "🌡 ring " + T.toFixed(0) + " °C · ball " + Tb.toFixed(0) + " °C", cam.X(rx), cam.Y(cup[1]) + 13,
           T > ROOM + 0.5 || Tb > ROOM + 0.5 ? "#ffb37a" : COL.dim, "bold 10px system-ui", "center");
    // the kettle, tilted while it pours, and the stream onto the target
    var kp = L.kettle, pour = k.water > 0;
    sprite(ctx, cam, "kettle", kp[0], kp[1], 0.34, pour ? -0.45 : 0);
    if (pour) {
      var aim = tgt === "ball" ? [rx + 0.01, ry + 0.05] : [rx + 0.14, ry + 0.06];
      ctx.strokeStyle = "rgba(120,190,255,0.8)"; ctx.lineWidth = Math.max(2, cam.len(0.012 + 0.02 * frac));
      ctx.beginPath(); ctx.moveTo(cam.X(kp[0] - 0.17), cam.Y(kp[1] - 0.03));
      ctx.quadraticCurveTo(cam.X(aim[0] + 0.15), cam.Y(kp[1] + 0.02), cam.X(aim[0]), cam.Y(aim[1])); ctx.stroke();
    }
    // water gauge (drag) and the target switch (click)
    var g = L.gauge, gx = g[0], gy = g[1] + (g[2] - g[1]) * frac;
    rect(ctx, cam, gx - 0.025, g[1], gx + 0.025, g[2], "rgba(17,26,58,0.9)", "#5c6a9c");
    rect(ctx, cam, gx - 0.02, g[1], gx + 0.02, gy, "rgba(92,170,255,0.75)");
    dlabel(ctx, cam, k.water.toFixed(2) + " kg of 95 °C water", cam.X(gx) + 14, cam.Y(gy) + 4, COL.handle, "bold 11px system-ui");
    var hx = cam.X(gx), hy = cam.Y(gy);
    knobHandle(ctx, hx, hy, "2.1.water", cam.hoverKey === "2.1.water");
    cam.handle({ x: hx, y: hy, r: 13, key: "2.1.water", cursor: "ns-resize", title: "drag: how much hot water to pour",
                 drag: function (pt) { cam.setParams({ "2.1.water": (pt.y - g[1]) / (g[2] - g[1]) * L.water_max }, false); } });
    var c = choiceOf(S, "2.1", "target"), tx = cam.X(rx - 0.12), ty = cam.Y(ry + 0.3);
    knobHandle(ctx, tx, ty, "2.1.target", cam.hoverKey === "2.1.target");
    ctx.fillStyle = "#0b1128"; ctx.font = "bold 11px system-ui"; ctx.textAlign = "center"; ctx.fillText("⟳", tx, ty + 4);
    ctx.textAlign = "left";
    W.label(ctx, "pour on: " + c.label, tx + 14, ty + 4, COL.handle, "bold 11px system-ui");
    cam.handle({ x: tx, y: ty, r: 13, key: "2.1.target", cursor: "pointer", title: "click: pour on the ring / the ball / both",
                 click: function () { cam.setParams({ "2.1.target": nextChoice(S, "2.1", "target") }, true); } });
  }

  function hotRingFront(ctx, cam, S, simT, frames, f) {
    var L = S.hall.layout.stations["2.1"], rx = L.ring[0], ry = L.ring[1];
    var T = at(frames, "T", simT, ROOM), Tb = at(frames, "Tb", simT, ROOM), r = S.hall.layout.ball.r;
    if (Tb > ROOM + 1 && Math.abs(f.y - ry) < 1.5 && Math.abs(f.x - rx) < 0.5) {                // a hot ball glows
      ctx.globalAlpha = Math.min(0.7, (Tb - ROOM) / 100);
      ellipse(ctx, cam, f.x, f.y, Math.max(r, 6 / cam.len(1)), Math.max(r, 6 / cam.len(1)), "rgb(255,128,48)");
      ctx.globalAlpha = 1;
    }
    if (Math.abs(f.x - rx) < 0.05 && f.y > ry - 0.06 && f.y < ry + 0.05) {                      // the ring's front half
      ellipse(ctx, cam, rx, ry, RING_RX, RING_RY, heatCol(T), "#0b1128", 0, Math.PI);
      ctx.fillStyle = "#0b1128";
      ctx.fillRect(cam.X(rx - 0.026), cam.Y(ry) - 1, cam.len(0.052), 2);
    }
  }

  /* ---------------- 2.2 Trapdoor Latch ---------------- */
  function trapdoor(ctx, cam, S, simT, frames) {
    var L = S.hall.layout.stations["2.2"], k = S.knobs["2.2"], fx = S.stations["2.2"].fact_values;
    var door = at(frames, "door", simT, 0), I = at(frames, "I", simT, 0), res = lastOf(S, "2.2");
    var blown = !!(res && res.viz && res.viz.blown && simT >= res.t0 + 0.05);
    var live = I > 0.001 || (res && simT >= res.t0 && res.ok);
    // the ramp from the ring's tube to the plates
    line(ctx, cam, [[L.ramp[0][0], L.ramp[0][1] - 0.03], [L.ramp[1][0], L.ramp[1][1] - 0.03], [L.plates[0], L.trap[1] + 0.005]],
         COL.steel, 3);
    // the trapdoor: two leaves hinged at the outer edges, meeting under the ball; a copper plate on each
    // (the ball bridges them). Released, both leaves swing down.
    var h0 = L.hinges[0], h1 = L.hinges[1], mid = (h0 + h1) / 2, a = door * Math.PI / 2;
    var ca = Math.cos(a), sa = Math.sin(a), yh = L.door_y - 0.05;
    // point on a leaf: u along it from its hinge (towards the middle), v up from its underside
    function PL_(u, v) { return [h0 + u * ca + v * sa, yh - u * sa + v * ca]; }
    function PR(u, v) { return [h1 - u * ca - v * sa, yh - u * sa + v * ca]; }
    var lw = mid - h0, gap = 0.012;
    poly(ctx, cam, [PL_(0, 0), PL_(lw - 0.003, 0), PL_(lw - 0.003, 0.05), PL_(0, 0.05)], COL.wood, "#0b1128");
    poly(ctx, cam, [PR(0, 0), PR(lw - 0.003, 0), PR(lw - 0.003, 0.05), PR(0, 0.05)], COL.wood, "#0b1128");
    poly(ctx, cam, [PL_(L.plates[0] - h0, 0.05), PL_(lw - gap, 0.05), PL_(lw - gap, 0.08), PL_(L.plates[0] - h0, 0.08)],
         F.copper, "#0b1128");
    poly(ctx, cam, [PR(h1 - L.plates[1], 0.05), PR(lw - gap, 0.05), PR(lw - gap, 0.08), PR(h1 - L.plates[1], 0.08)],
         F.copper, "#0b1128");
    [h0, h1].forEach(function (hx) { ellipse(ctx, cam, hx, yh, 0.016, 0.016, "#aab3c5", "#0b1128"); });
    dlabel(ctx, cam, "copper plates", cam.X(mid), cam.Y(L.door_y + 0.08) - 4, F.copper, "10px system-ui", "center");
    // the latch: the coil pulls its bolt back from under the leaves' meeting point
    var c = L.coil, pull = Math.min(1, door * 6), tip = mid + 0.06 - 0.42 * pull;
    rect(ctx, cam, c[0] + 0.06, yh - 0.03, tip, yh - 0.006, COL.steel, "#0b1128");
    sprite(ctx, cam, "coil", c[0], c[1] - 0.02, 0.16);
    dlabel(ctx, cam, "latch coil " + fx.coil_ohm.toFixed(1) + " Ω", cam.X(c[0] - 0.1), cam.Y(c[1] + 0.1), COL.dim,
           "10px system-ui", "center");
    // the circuit panel: battery -> dial -> fuse -> coil -> left plate | ball | right plate -> back
    var p = L.panel;
    rect(ctx, cam, p[0], p[1], p[2], p[3], "rgba(17,26,58,0.92)", "#2e7fb0");
    var wc = live && !blown ? F.wireOn : F.wire, ww = live && !blown ? 2.5 : 1.5;
    var bat = choiceOf(S, "2.2", "battery"), yb = p[1] + 0.27, yt = p[3] - 0.17;
    var bx = p[0] + 0.42, dial = [p[0] + 0.95, yt], fuse = [p[0] + 1.45, yt], cs = 0.16;
    var tabA = [c[0] - 0.27 * cs, c[1] - 0.02 - 0.42 * cs], tabB = [c[0] + 0.05 * cs, c[1] - 0.02 - 0.42 * cs];
    line(ctx, cam, [[bx + 0.16, yb], [bx + 0.3, yb], [bx + 0.3, yt], [dial[0] - 0.13, yt]], wc, ww);
    line(ctx, cam, [[dial[0] + 0.13, yt], [fuse[0] - 0.08, yt]], wc, ww);
    line(ctx, cam, [[fuse[0] + 0.08, yt], [tabA[0], yt], tabA], wc, ww);                             // to the coil
    line(ctx, cam, [tabB, [tabB[0], yh - 0.12], PL_(L.plates[0] - h0 + 0.03, 0.05)], wc, ww);          // coil -> left plate
    line(ctx, cam, [PR(h1 - L.plates[1] + 0.03, 0.05), [h1 + 0.06, yh - 0.16], [h1 + 0.06, p[3] - 0.06],
                    [p[2] - 0.05, p[3] - 0.06], [p[2] - 0.05, p[1] + 0.06], [bx - 0.25, p[1] + 0.06], [bx - 0.25, yb],
                    [bx - 0.16, yb]], wc, ww);                                                           // right plate -> battery
    sprite(ctx, cam, "battery", bx, yb, 0.34);
    dlabel(ctx, cam, bat.label, cam.X(bx), cam.Y(yb - 0.1) + 4, COL.handle, "bold 11px system-ui", "center");
    dlabel(ctx, cam, "internal r = " + bat.r_int + " Ω", cam.X(bx), cam.Y(yb - 0.1) + 17, COL.dim, "10px system-ui", "center");
    var bhx = cam.X(bx + 0.17), bhy = cam.Y(yb + 0.1);
    knobHandle(ctx, bhx, bhy, "2.2.battery", cam.hoverKey === "2.2.battery");
    ctx.fillStyle = "#0b1128"; ctx.font = "bold 11px system-ui"; ctx.textAlign = "center"; ctx.fillText("⟳", bhx, bhy + 4);
    ctx.textAlign = "left";
    cam.handle({ x: bhx, y: bhy, r: 13, key: "2.2.battery", cursor: "pointer", title: "click: swap the battery",
                 click: function () { cam.setParams({ "2.2.battery": nextChoice(S, "2.2", "battery") }, true); } });
    // the resistor dial: 0 - 50 ohm over 270 degrees
    var spec = knobSpec(S, "2.2", "R"), u = k.R / spec.max, ang = Math.PI * (1.25 - 1.5 * u);
    ellipse(ctx, cam, dial[0], dial[1], 0.12, 0.12, "#1a2348", "#aab3c5");
    sprite(ctx, cam, "resistor", dial[0], dial[1] - 0.005, 0.2);
    var px = dial[0] + 0.1 * Math.cos(ang), py = dial[1] + 0.1 * Math.sin(ang);
    line(ctx, cam, [[dial[0], dial[1]], [px, py]], COL.handle, 2);
    dlabel(ctx, cam, "R = " + k.R.toFixed(1) + " Ω", cam.X(dial[0]), cam.Y(dial[1] - 0.12) + 12, COL.handle, "bold 11px system-ui",
           "center");
    knobHandle(ctx, cam.X(px), cam.Y(py), "2.2.R", cam.hoverKey === "2.2.R");
    cam.handle({ x: cam.X(px), y: cam.Y(py), r: 13, key: "2.2.R", cursor: "grab", title: "turn the dial: 0 - 50 Ω",
                 drag: function (pt) {
                   var a2 = Math.atan2(pt.y - dial[1], pt.x - dial[0]);
                   var v = (1.25 * Math.PI - a2) / (1.5 * Math.PI);
                   if (v < -0.1) v += 4 / 3;                                     // past the top-left end
                   cam.setParams({ "2.2.R": Math.max(0, Math.min(1, v)) * spec.max }, false);
                 } });
    // the fuse: glass tube, broken if it blew
    rect(ctx, cam, fuse[0] - 0.08, fuse[1] - 0.025, fuse[0] + 0.08, fuse[1] + 0.025, "rgba(200,220,255,0.25)", "#aab3c5");
    if (blown) {
      line(ctx, cam, [[fuse[0] - 0.08, fuse[1]], [fuse[0] - 0.02, fuse[1] + 0.01]], "#ff6b6b", 2);
      line(ctx, cam, [[fuse[0] + 0.02, fuse[1] - 0.01], [fuse[0] + 0.08, fuse[1]]], "#ff6b6b", 2);
      W.label(ctx, "💥 fuse blew", cam.X(fuse[0]), cam.Y(fuse[1] + 0.05) - 4, "#ff6b6b", "bold 11px system-ui", "center");
    } else {
      line(ctx, cam, [[fuse[0] - 0.08, fuse[1]], [fuse[0] + 0.08, fuse[1]]], wc, 1.5);
    }
    dlabel(ctx, cam, fx.fuse + " A fuse", cam.X(fuse[0]), cam.Y(fuse[1] - 0.03) + 12, COL.dim, "10px system-ui", "center");
    // the ammeter: reads only what a run measured
    var am = [p[2] - 0.25, p[1] + 0.32];
    ellipse(ctx, cam, am[0], am[1], 0.11, 0.11, "#0f1736", "#aab3c5");
    var needle = Math.PI * (0.9 - 0.8 * Math.min(1.2, I) / 1.2);
    line(ctx, cam, [[am[0], am[1] - 0.04], [am[0] + 0.09 * Math.cos(needle), am[1] - 0.04 + 0.09 * Math.sin(needle)]],
         "#ff6b6b", 1.5);
    W.label(ctx, I > 0.001 ? I.toFixed(2) + " A" : "— A", cam.X(am[0]), cam.Y(am[1] - 0.06), "#dfe6ff", "bold 10px system-ui",
            "center");
    dlabel(ctx, cam, "pulls at " + fx.pull_in.toFixed(2) + " A", cam.X(am[0]), cam.Y(am[1] - 0.11) + 10, COL.dim, "9px system-ui",
           "center");
  }

  /* ---------------- 2.3 Hydraulic Gate ---------------- */
  function hydraulic(ctx, cam, S, simT, frames) {
    var L = S.hall.layout.stations["2.3"], k = S.knobs["2.3"], fx = S.stations["2.3"].fact_values;
    var x1 = at(frames, "x1", simT, 0), x2 = Math.min(at(frames, "x2", simT, 0), 0.14);
    var sx = L.small_x, hw = L.vis * L.d1 / 2, gx = L.gate_x, bw = L.vis * k.d2 / 2, y0 = L.floor;
    var face = L.top - x1;                                                            // the small piston's top
    // tunnel: floor and roof (the roof has a slot for the gate)
    rect(ctx, cam, sx - hw - 0.05, y0 - 0.1, L.tunnel_end, y0, COL.mezz, "#3a4678");
    rect(ctx, cam, sx + hw, L.roof, gx - 0.03, L.roof + 0.03, COL.post);
    rect(ctx, cam, gx + 0.03, L.roof, L.tunnel_end, L.roof + 0.03, COL.post);
    // the oil pipe from the shaft's bottom to the big cylinder (it runs behind the tunnel)
    line(ctx, cam, [[sx, y0 - 0.02], [sx, y0 - 0.07], [3.3, y0 - 0.07]], F.oil, 5);
    line(ctx, cam, [[3.3, y0 - 0.07], [3.3, L.big_y0 + 0.04], [gx - bw, L.big_y0 + 0.04]], F.oilDim, 5, [6, 4]);
    dlabel(ctx, cam, "oil pipe (behind the tunnel)", cam.X(3.3) - 4, cam.Y(y0 + 0.06), "#e0a83c", "9px system-ui", "right");
    // the small cylinder = the ball's shaft: oil below the piston, the piston riding down
    rect(ctx, cam, sx - hw, y0, sx + hw, face - 0.02, F.oil);
    rect(ctx, cam, sx - hw, face - 0.02, sx + hw, face, COL.steel, "#0b1128");
    rect(ctx, cam, sx - hw - 0.02, y0 + (x1 > 0.29 ? 0.07 : 0), sx - hw, L.top + 0.08, COL.post);          // shaft walls
    rect(ctx, cam, sx + hw, y0 + (x1 > 0.29 ? 0.07 : 0), sx + hw + 0.02, L.top + 0.08, COL.post);
    dlabel(ctx, cam, "small piston " + fx.d1 + " cm", cam.X(sx - hw - 0.03), cam.Y(L.top - 0.06), COL.dim, "10px system-ui",
           "right");
    dlabel(ctx, cam, "rides " + fx.stroke + " cm down", cam.X(sx - hw - 0.03), cam.Y(L.top - 0.06) + 13, COL.dim,
           "10px system-ui", "right");
    // the big cylinder on the tunnel roof; its piston's rod lifts the gate
    var by0 = L.big_y0, bface = by0 + 0.1 + x2;
    rect(ctx, cam, gx - bw - 0.015, by0, gx + bw + 0.015, by0 + L.big_h, "#26305c", "#aab3c5");
    rect(ctx, cam, gx - bw, by0, gx + bw, bface, F.oil);
    rect(ctx, cam, gx - bw, bface, gx + bw, bface + 0.04, COL.steel, "#0b1128");
    rect(ctx, cam, gx - 0.006, by0 - 0.03, gx + 0.006, bface, "#cfd6e6");                             // the through-rod
    var gb = y0 + x2;                                                                                  // gate bottom
    rect(ctx, cam, gx - L.gate_half, gb, gx + L.gate_half, gb + L.gate_h, COL.flap, "#0b1128");
    dlabel(ctx, cam, "gate " + fx.gate_kg.toFixed(2) + " kg", cam.X(gx + L.gate_half) + 4, cam.Y(y0 + 0.09), COL.flap,
           "10px system-ui");
    // "must rise 6 cm": a tick at the height the ball needs
    line(ctx, cam, [[gx - 0.06, y0 + L.need], [gx - L.gate_half, y0 + L.need]], "rgba(125,255,168,0.8)", 1.5, [3, 2]);
    dlabel(ctx, cam, "needs " + (100 * L.need).toFixed(0) + " cm", cam.X(gx - 0.07), cam.Y(y0 + L.need) + 4, "#7dffa8",
           "9px system-ui", "right");
    if (x2 > 0.0005) {
      dlabel(ctx, cam, "↑ " + (100 * x2).toFixed(1) + " cm", cam.X(gx + bw) + 8, cam.Y(bface) + 4, "#ffe27a",
             "bold 10px system-ui");
    }
    // the big piston's width is the knob: drag its right edge
    dlabel(ctx, cam, "big piston d2 = " + k.d2.toFixed(1) + " cm (drawn 4× wide)", cam.X(gx), cam.Y(by0 + L.big_h) - 22,
           COL.handle, "bold 11px system-ui", "center");
    var hx = cam.X(gx + bw + 0.015), hy = cam.Y(by0 + L.big_h * 0.6);
    knobHandle(ctx, hx, hy, "2.3.d2", cam.hoverKey === "2.3.d2");
    cam.handle({ x: hx, y: hy, r: 13, key: "2.3.d2", cursor: "ew-resize", title: "drag: the big piston's diameter",
                 drag: function (pt) { cam.setParams({ "2.3.d2": (pt.x - gx) * 2 / L.vis }, false); } });
  }

  /* ---------------- 2.4 Magnet Swing ---------------- */
  function swing(ctx, cam, S, simT, frames) {
    var L = S.hall.layout.stations["2.4"], k = S.knobs["2.4"], fx = S.stations["2.4"].fact_values;
    var sw = L.swing, len = k.length, pv = [sw[0], sw[1] + len], gy = L.girder_y;
    // the chute from the tunnel to the pickup
    line(ctx, cam, L.chute, COL.steel, 3);
    // girder, telescopic arm down to the pivot
    rect(ctx, cam, 5.4, gy, 7.1, gy + 0.12, F.girder, "#0b1128");
    for (var x = 5.5; x < 7.0; x += 0.2) line(ctx, cam, [[x, gy], [x + 0.1, gy + 0.12]], "#2a3358", 1.5);
    rect(ctx, cam, pv[0] - 0.05, Math.max(pv[1], gy - 0.35), pv[0] + 0.05, gy, F.iron, "#0b1128");
    rect(ctx, cam, pv[0] - 0.025, pv[1], pv[0] + 0.025, gy, "#8d98b8", "#0b1128");
    // the swing's arc (dashed) and the trip wire at the bottom
    var th0 = k.angle * Math.PI / 180;
    ctx.strokeStyle = "rgba(255,209,102,0.35)"; ctx.lineWidth = 1; ctx.setLineDash([4, 4]);
    ctx.beginPath(); ctx.arc(cam.X(pv[0]), cam.Y(pv[1]), cam.len(len), Math.PI / 2, Math.PI / 2 + th0); ctx.stroke();
    ctx.setLineDash([]);
    line(ctx, cam, [[sw[0] + 0.02, sw[1] - 0.05], [sw[0] + 0.02, sw[1] + 0.12]], "#ff6b6b", 1.5);
    dlabel(ctx, cam, "trip wire: the magnet lets go here", cam.X(sw[0] + 0.05), cam.Y(sw[1] - 0.08), "#ff8f8f", "10px system-ui");
    // the ladle (B) on its stand, the drop and the distance it sits out
    var bx = sw[0] + fx.ladle, by = sw[1] - fx.drop;
    rect(ctx, cam, bx - 0.03, 0.02, bx + 0.03, by - 0.2, COL.post);
    rect(ctx, cam, bx - 0.2, 0.02, bx + 0.2, 0.08, COL.post);
    line(ctx, cam, [[sw[0], by - 0.3], [bx, by - 0.3]], "rgba(141,154,203,0.6)", 1, [3, 3]);
    dlabel(ctx, cam, "ladle " + fx.ladle.toFixed(2) + " m out, rim " + fx.drop.toFixed(1) + " m down", cam.X((sw[0] + bx) / 2),
           cam.Y(by - 0.3) - 5, COL.dim, "10px system-ui", "center");
    line(ctx, cam, [[bx + 0.25, by], [bx + 0.25, sw[1]]], "rgba(141,154,203,0.6)", 1, [3, 3]);
    // labels for the knobs
    dlabel(ctx, cam, "cable " + len.toFixed(2) + " m · release " + k.angle.toFixed(0) + "°", cam.X(pv[0]) + 14, cam.Y(pv[1]) + 4,
           COL.handle, "bold 11px system-ui");
    dlabel(ctx, cam, "magnet holds " + fx.hold + " N", cam.X(pv[0]) + 14, cam.Y(pv[1]) + 18, COL.dim, "10px system-ui");
    var hx = cam.X(pv[0]), hy = cam.Y(pv[1]);
    knobHandle(ctx, hx, hy, "2.4.length", cam.hoverKey === "2.4.length");
    cam.handle({ x: hx, y: hy, r: 13, key: "2.4.length", cursor: "ns-resize", title: "drag: the cable's length",
                 drag: function (pt) { cam.setParams({ "2.4.length": pt.y - sw[1] }, false); } });
  }

  function swingFront(ctx, cam, S, simT, frames, f) {
    var L = S.hall.layout.stations["2.4"], k = S.knobs["2.4"], fx = S.stations["2.4"].fact_values;
    var sw = L.swing, len = k.length, pv = [sw[0], sw[1] + len], r = S.hall.layout.ball.r;
    var th = at(frames, "th", simT, k.angle * Math.PI / 180);
    var mx = pv[0] - (len - r - 0.05) * Math.sin(th), my = pv[1] - (len - r - 0.05) * Math.cos(th);
    line(ctx, cam, [pv, [mx + 0.04 * Math.sin(th), my + 0.04 * Math.cos(th)]], "#cfd6e6", 1.5);          // the cable
    sprite(ctx, cam, "magnet", mx, my, 0.14, th);
      var a0 = k.angle * Math.PI / 180, ex = pv[0] - (len + 0.09) * Math.sin(a0), ey = pv[1] - (len + 0.09) * Math.cos(a0);
    knobHandle(ctx, cam.X(ex), cam.Y(ey), "2.4.angle", cam.hoverKey === "2.4.angle");
    cam.handle({ x: cam.X(ex), y: cam.Y(ey), r: 13, key: "2.4.angle", cursor: "grab", title: "drag round the pivot: the release angle",
                 drag: function (pt) {
                   cam.setParams({ "2.4.angle": Math.atan2(pv[0] - pt.x, pv[1] - pt.y) * 180 / Math.PI }, false);
                 } });
    // the ladle goes over the ball: it drops INTO it
    var bx = sw[0] + fx.ladle, by = sw[1] - fx.drop;
    sprite(ctx, cam, "ladle", bx, by - 0.072, 0.28);
    K.endpoint(ctx, cam, bx + 0.32, by + 0.2, "B", "the ladle", "#5cc8ff");
  }

  PL.gameHalls.foundry = {
    tags: function () { return [["2.1", 0.75, 6.98], ["2.2", 0.9, 4.75], ["2.3", 3.75, 4.5], ["2.4", 7.55, 4.3]]; },
    startPoint: startPoint,
    draw: function (ctx, cam, S, simT, frames) {
      var L = S.hall.layout;
      building(ctx, cam, S);
      hotRing(ctx, cam, S, simT, frames);
      trapdoor(ctx, cam, S, simT, frames);
      hydraulic(ctx, cam, S, simT, frames);
      swing(ctx, cam, S, simT, frames);
      K.endpoint(ctx, cam, L.A[0], L.A[1], "A", "ore cart", "#5be39b");
    },
    front: function (ctx, cam, S, simT, frames, f) {
      hotRingFront(ctx, cam, S, simT, frames, f);
      swingFront(ctx, cam, S, simT, frames, f);
    }
  };
})();
