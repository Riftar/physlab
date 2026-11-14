/* physlab game hall painter: HALL 1 - THE BOUNCE FACTORY (rubber ball).
   Registered as PL.gameHalls.bounce and drawn by PL.scenes.game (scene_game.js)
   with the shared drawing kit PL.gameKit.

   Handles (yellow): 1.1 hatch height (drag up/down), 1.2 salt bags (+ / −),
   1.3 hump crest (drag up/down), 1.4 barrel angle (drag round the pivot).
   They call cam.setParams({"<station>.<knob>": value}) - the page validates
   and snaps the value exactly like the knob panel.                          */
(function () {
  "use strict";
  var K = PL.gameKit, W = PL.widgets, COL = K.COL;
  var rect = K.rect, line = K.line, dlabel = K.dlabel, knobHandle = K.knobHandle, sprite = K.sprite, mix = K.mix;

  /* ---------------- the stations (drawn from layout + facts + CURRENT knobs) ---------------- */

  function hxLabel(cam, o) { return cam.X(o[0] - 0.24) - 16; }

  function bounceFlap(ctx, cam, L, fx, k, st, S) {
    var o = L.origin, r = S.hall.layout.ball.r, pad = st.knobs[1].choices.filter(function (c) { return c.id === k.pad; })[0];
    var yF = o[1] + fx.flap, yD = yF + fx.duct_gap, yH = o[1] + k.hatch;
    rect(ctx, cam, o[0] + L.pad[0], o[1] - 0.07, o[0] + L.pad[1], o[1], pad.color, "#0b1128");          // the pad
    dlabel(ctx, cam, pad.label, cam.X(o[0] + 0.3), cam.Y(o[1] - 0.07) + 13, COL.dim, "11px system-ui", "center");
    rect(ctx, cam, o[0] - 0.17, o[1], o[0] - 0.09, o[1] + L.rail[1] + 0.35, COL.post);                    // hatch rail
    line(ctx, cam, [[o[0] - 0.02, yH + 2 * r], [o[0] - 0.02, S.hall.layout.hopper[1] - 0.2]], "#5c6a9c", 3);  // feed tube
    rect(ctx, cam, o[0] - 0.13, yH - 0.035, o[0] + 0.05, yH, COL.wood, "#0b1128");                         // hatch ledge
    rect(ctx, cam, o[0] + L.flap_x[1], yF - 0.05, L.shelf_end, yF, COL.wood);                              // shelf
    rect(ctx, cam, o[0] + L.flap_x[0], yF - 0.035, o[0] + L.flap_x[1], yF, COL.flap);                      // one-way flap
    rect(ctx, cam, L.shelf_end - 0.05, o[1], L.shelf_end, yF - 0.05, COL.post);                            // shelf post
    rect(ctx, cam, o[0] + L.duct_x[0], yD, o[0] + L.duct_x[1], yD + 0.14, COL.duct, "#5a1f1f");             // hot duct
    for (var x = o[0] + L.duct_x[0] + 0.08; x < o[0] + L.duct_x[1]; x += 0.16) {
      line(ctx, cam, [[x, yD + 0.02], [x + 0.06, yD + 0.12]], "#d46a4a", 2);
    }
    dlabel(ctx, cam, "hot duct " + fx.duct_gap.toFixed(2) + " m above the flap (" + (fx.flap + fx.duct_gap).toFixed(2) + " m)",
            cam.X(o[0] + L.duct_x[1]) + 6, cam.Y(yD + 0.07) + 4, "#ff8f8f", "11px system-ui");
    dlabel(ctx, cam, "one-way flap " + fx.flap.toFixed(2) + " m", cam.X(o[0] + L.flap_x[1]) + 6, cam.Y(yF) - 6, COL.flap,
            "11px system-ui");
    // hatch height: dashed measure from the pad, value, drag handle
    line(ctx, cam, [[o[0] - 0.3, o[1]], [o[0] - 0.3, yH]], "rgba(255,209,102,0.5)", 1, [4, 4]);
    dlabel(ctx, cam, "hatch h0 = " + k.hatch.toFixed(2) + " m", hxLabel(cam, o), cam.Y(yH) + 4, COL.handle,
            "bold 11px system-ui", "right");
    var hx = cam.X(o[0] - 0.24), hy = cam.Y(yH);
    knobHandle(ctx, hx, hy, "1.1.hatch", cam.hoverKey === "1.1.hatch");
    cam.handle({ x: hx, y: hy, r: 13, key: "1.1.hatch", cursor: "ns-resize", title: "drag the hatch up or down",
                 drag: function (pt) { cam.setParams({ "1.1.hatch": pt.y - o[1] }, false); } });
  }

  function saltCanal(ctx, cam, L, fx, k, st) {
    var t = Math.min(1, k.bags / 15);
    rect(ctx, cam, L.x0, L.floor, L.x1, L.surface, mix(COL.water, COL.salt, t));                           // the water
    ctx.globalAlpha = 0.25; rect(ctx, cam, L.x0, L.floor, L.x1, L.surface, "#0b1128"); ctx.globalAlpha = 1;
    rect(ctx, cam, L.x0 - 0.06, L.floor - 0.06, L.x0, L.rim, COL.post);                                    // walls
    rect(ctx, cam, L.x1, L.floor - 0.06, L.x1 + 0.06, L.surface - 0.02, COL.post);                          // weir side
    rect(ctx, cam, L.x0 - 0.06, L.floor - 0.06, L.x1 + 0.06, L.floor, COL.post);
    line(ctx, cam, [[L.x0 + 0.05, L.floor + 0.03], [L.x1 - 0.05, L.floor + 0.03]], "#6b7390", 2, [3, 4]);   // grate
    for (var ax = L.x0 + 0.4; ax < L.outflow_x - 0.3; ax += 0.8) {                                          // current
      W.arrow(ctx, cam.X(ax), cam.Y(L.surface - 0.12), cam.X(ax + 0.45), cam.Y(L.surface - 0.12), "rgba(92,214,255,0.55)", 1.5, 6);
    }
    dlabel(ctx, cam, "current → outflow", cam.X(L.outflow_x) - 4, cam.Y(L.surface - 0.22), "#8fd3ff", "10px system-ui", "right");
    dlabel(ctx, cam, fx.litres.toFixed(0) + " L of water", cam.X(L.x0 + 0.08), cam.Y(L.floor) - 6, COL.dim, "10px system-ui");
    // the salt bags, stacked on the mezzanine next to the canal
    var px = L.x0 - 0.95, py = 2.0, sz = 0.17;
    for (var i = 0; i < k.bags; i++) {
      sprite(ctx, cam, "saltbag", px + (i % 5) * sz, py + sz / 2 + Math.floor(i / 5) * sz * 0.9, sz);
    }
    dlabel(ctx, cam, k.bags + " bag" + (k.bags === 1 ? "" : "s") + " of salt (" + (k.bags * 1000 / fx.litres).toFixed(0) + " g/L)",
            cam.X(px + 0.35), cam.Y(py + 0.85), COL.handle, "bold 11px system-ui", "center");
    [["−", -1, px - 0.05], ["+", 1, px + 0.75]].forEach(function (b) {
      var bx = cam.X(b[2]), by = cam.Y(py + 0.62), key = "1.2.bags" + b[1];
      knobHandle(ctx, bx, by, key, cam.hoverKey === key);
      ctx.fillStyle = "#0b1128"; ctx.font = "bold 14px system-ui"; ctx.textAlign = "center";
      ctx.fillText(b[0], bx, by + 5); ctx.textAlign = "left";
      cam.handle({ x: bx, y: by, r: 13, key: key, cursor: "pointer", title: (b[1] > 0 ? "add" : "remove") + " a bag of salt",
                   click: function () { cam.setParams({ "1.2.bags": k.bags + b[1] }, true); } });
    });
  }

  function camelHump(ctx, cam, L, fx, k) {
    var o = L.origin, tr = PL.game.camel(fx.h0, k.hump, L.R), pts = tr.polyline(160);
    ctx.beginPath(); ctx.moveTo(cam.X(o[0]), cam.Y(0));                                                     // hill fill
    pts.forEach(function (p) { ctx.lineTo(cam.X(o[0] + p[0]), cam.Y(o[1] + p[1])); });
    ctx.lineTo(cam.X(o[0] + L.x1), cam.Y(0)); ctx.closePath();
    var g = ctx.createLinearGradient(0, cam.Y(2.5), 0, cam.Y(0));
    g.addColorStop(0, "#2d3f6e"); g.addColorStop(1, "#182445"); ctx.fillStyle = g; ctx.fill();
    line(ctx, cam, pts.map(function (p) { return [o[0] + p[0], o[1] + p[1]]; }), COL.wood, 4);
    var cx = o[0] + L.xc, cy = o[1] + k.hump;
    dlabel(ctx, cam, "hump " + k.hump.toFixed(2) + " m · crest radius " + L.R.toFixed(1) + " m", cam.X(cx), cam.Y(cy) + 38,
            COL.handle, "bold 11px system-ui", "center");
    dlabel(ctx, cam, "over the top faster than √(g·R) = " + Math.sqrt(9.81 * L.R).toFixed(2) + " m/s → it flies off",
            cam.X(cx), cam.Y(cy) + 53, COL.dim, "10px system-ui", "center");
    var hx = cam.X(cx), hy = cam.Y(cy) - 14;
    knobHandle(ctx, hx, hy, "1.3.hump", cam.hoverKey === "1.3.hump");
    cam.handle({ x: hx, y: hy, r: 13, key: "1.3.hump", cursor: "ns-resize", title: "drag the hump up or down",
                 drag: function (pt) { cam.setParams({ "1.3.hump": pt.y - o[1] }, false); } });
    dlabel(ctx, cam, "top " + fx.h0.toFixed(2) + " m", cam.X(o[0] + 0.1), cam.Y(o[1] + fx.h0) - 8, COL.dim, "10px system-ui");
  }

  function springCannon(ctx, cam, L, fx, k) {
    var m = L.muzzle, th = k.angle * Math.PI / 180, b = L.barrel;
    var pv = [m[0] - b / 2 * Math.cos(th), m[1] - b / 2 * Math.sin(th)];
    rect(ctx, cam, pv[0] - 0.06, 0, pv[0] + 0.06, pv[1], COL.post);                                        // stand
    rect(ctx, cam, pv[0] - 0.25, 0, pv[0] + 0.25, 0.12, COL.post);
    sprite(ctx, cam, "cannon", pv[0], pv[1], b * 1.08, -th);
    dlabel(ctx, cam, "spring " + k.compression.toFixed(1) + " cm · " + k.angle.toFixed(0) + "°", cam.X(pv[0]), cam.Y(pv[1]) + 34,
            COL.handle, "bold 11px system-ui", "center");
    var hx = cam.X(m[0] + 0.12 * Math.cos(th)), hy = cam.Y(m[1] + 0.12 * Math.sin(th));
    knobHandle(ctx, hx, hy, "1.4.angle", cam.hoverKey === "1.4.angle");
    cam.handle({ x: hx, y: hy, r: 13, key: "1.4.angle", cursor: "grab", title: "drag to aim the barrel",
                 drag: function (pt) {
                   cam.setParams({ "1.4.angle": Math.atan2(pt.y - pv[1], pt.x - pv[0]) * 180 / Math.PI }, false);
                 } });
    // the toy box: a felt funnel on a stand, the rubber bumper wall behind it
    var F = L.funnel, fx0 = m[0] + fx.dx, fy0 = m[1] + fx.dy;
    rect(ctx, cam, fx0 - 0.07, 0, fx0 + 0.07, fy0 - F.depth - 0.5, COL.post);
    sprite(ctx, cam, "toybox", fx0, fy0 - F.depth - 0.22, 0.62);
    line(ctx, cam, [[fx0 - F.mouth, fy0], [fx0 - F.throat, fy0 - F.depth]], COL.wood, 4);
    line(ctx, cam, [[fx0 + F.mouth, fy0], [fx0 + F.throat, fy0 - F.depth]], COL.wood, 4);
    rect(ctx, cam, fx0 + L.bank_wall, fy0 - 0.6, fx0 + L.bank_wall + 0.12, fy0 + 3.0, COL.wall, "#b25a85");
    dlabel(ctx, cam, "rubber bumper wall", cam.X(fx0 + L.bank_wall) - 4, cam.Y(fy0 + 3.0) + 14, "#ff8fb4", "10px system-ui", "right");
    dlabel(ctx, cam, "toy box " + fx.dx.toFixed(2) + " m out, " + fx.dy.toFixed(2) + " m up", cam.X(fx0), cam.Y(fy0) - 10,
            COL.dim, "10px system-ui", "center");
    return [fx0, fy0];
  }

  function startPoint(S, sid) {
    var L = S.hall.layout.stations[sid], fx = S.stations[sid].fact_values, k = S.knobs[sid], r = S.hall.layout.ball.r;
    if (sid === "1.1") return { x: L.origin[0], y: L.origin[1] + k.hatch + r };
    if (sid === "1.2") return { x: L.drop_x, y: L.surface + 0.10 + r };
    if (sid === "1.3") {
      var tr = PL.game.camel(fx.h0, k.hump, L.R);
      return { x: L.origin[0] + L.start_x, y: L.origin[1] + tr.eval(L.start_x)[0] + r };
    }
    return { x: L.muzzle[0], y: L.muzzle[1] };
  }

  PL.gameHalls.bounce = {
    tags: function (S) {                      // where each station's name tag sits (world metres)
      return [["1.1", S.hall.layout.stations["1.1"].origin[0] + 2.0, 5.3], ["1.2", 4.7, 3.2], ["1.3", 9.9, 2.7],
              ["1.4", 15.0, 3.7]];
    },
    startPoint: startPoint,
    draw: function (ctx, cam, S) {
      var L = S.hall.layout;
      rect(ctx, cam, L.bounds.x0 - 5, L.bounds.y0 - 5, L.bounds.x1 + 5, 0, COL.floor);          // building
      rect(ctx, cam, L.mezzanine.x0, L.mezzanine.y - 0.4, L.mezzanine.x1, L.mezzanine.y, COL.mezz);
      rect(ctx, cam, L.mezzanine.x1 - 0.15, 0, L.mezzanine.x1, L.mezzanine.y - 0.4, COL.post);
      var get = function (sid) { return [L.stations[sid], S.stations[sid].fact_values, S.knobs[sid], S.stations[sid]]; };
      var a = get("1.1"); bounceFlap(ctx, cam, a[0], a[1], a[2], a[3], S);
      a = get("1.2"); saltCanal(ctx, cam, a[0], a[1], a[2], a[3]);
      a = get("1.3"); camelHump(ctx, cam, a[0], a[1], a[2]);
      a = get("1.4"); var box = springCannon(ctx, cam, a[0], a[1], a[2]);
      sprite(ctx, cam, "hopper", L.hopper[0], L.hopper[1], 0.55);
      K.endpoint(ctx, cam, L.hopper[0] + 0.5, L.hopper[1] + 0.05, "A", "toy hopper", "#5be39b");
      K.endpoint(ctx, cam, box[0], box[1] + 0.55, "B", "toy box", "#5cc8ff");
    }
  };
})();
