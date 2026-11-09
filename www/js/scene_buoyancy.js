/* physlab scene: FLOATING & SINKING.
   A side view of a glass tank drawn to scale. Visual cues:
     - forces view: weight (at the centre of mass), buoyancy (at the centre
       of buoyancy - the middle of the submerged part), liquid drag, floor
       support and the net force, all on one newton->pixel scale
     - pressure view: arrows on every face, length ~ rho g depth; the
       bottom push beats the top push, and the difference IS the buoyancy
     - the liquid level rises by exactly the volume pushed aside; a
       measuring cylinder collects that volume ("liquid pushed aside")
     - density bars: object vs liquid decides float or sink
     - splash and ripples scale with the object's real speed
   All numbers come from the server's frames. */
(function () {
  "use strict";
  var D = PL.draw;
  var COL = { weight: "#c792ea", buoy: "#5cd6ff", drag: "#ff5c8a", floor: "#7dffa8", net: "#ffffff" };

  var buoyancy = {
    continuous: false,
    options: [
      { id: "show", label: "Show", default: "forces",
        choices: [{ id: "forces", label: "forces" }, { id: "pressure", label: "water pressure" },
                  { id: "none", label: "nothing" }] },
      { id: "speed", label: "Speed", default: "1",
        choices: [{ id: "1", label: "real time" }, { id: "0.25", label: "×¼" }] }
    ],
    speed: function (t, runs, view) { return view && view.speed ? +view.speed : 1; },
    duration: function (runs) { var f = runs[0].result.frames; return f[f.length - 1].t; },

    init: function (ctx, w, h, runs) {
      var vz = runs[0].result.viz, tank = vz.tank;
      var sc = 560 / tank.w;                           // px per metre (true scale)
      this.geo = { sc: sc, left: w - 20 - tank.w * sc, right: w - 20, floor: h - 18,
                   top: h - 18 - tank.h * sc };
      this.geo.cx = this.geo.left + 0.42 * (this.geo.right - this.geo.left);   // leave room for the force box
      this.ripples = []; this.drops = []; this.prevH = null; this.rand = D.rng(77);
      // pressure arrows: scaled to the most the object itself feels in this run
      var pmax = Math.max.apply(null, runs[0].result.frames.map(function (q) { return q.p_bot; }));
      this.pxPerPa = 44 / Math.max(pmax, 1e-9);
    },

    render: function (ctx, w, h, simT, clock, runs, view) {
      var run = runs[0], res = run.result, vz = res.viz, g = this.geo, sc = g.sc;
      var f = PL.frameAt(res.frames, simT);
      var Y = function (y) { return g.floor - y * sc; };
      var s = vz.size * sc, liq = vz.liquid, sol = vz.solid;
      var oy = Y(f.y), ox = g.cx;                        // object bottom-centre on screen
      var surf = Y(f.level);
      ctx.clearRect(0, 0, w, h);
      this._effects(f, clock, s, ox, surf, vz.size);

      // ---- tank back + liquid body (darker with depth: pressure grows) ----
      ctx.fillStyle = "rgba(255,255,255,0.03)"; ctx.fillRect(g.left, g.top, g.right - g.left, g.floor - g.top);
      var lg = ctx.createLinearGradient(0, surf, 0, g.floor);
      lg.addColorStop(0, D.rgba(liq.color, 0.28)); lg.addColorStop(1, D.rgba(liq.color, 0.55));
      ctx.fillStyle = lg; ctx.fillRect(g.left, surf, g.right - g.left, g.floor - surf);

      // original level vs now
      var y0 = Y(vz.tank.fill);
      ctx.setLineDash([5, 5]); ctx.strokeStyle = "rgba(255,255,255,0.45)"; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(g.left, y0); ctx.lineTo(g.right, y0); ctx.stroke(); ctx.setLineDash([]);
      var rise = (f.level - vz.tank.fill) * 100;
      D.label(ctx, "level before: " + (vz.tank.fill * 100).toFixed(1) + " cm", g.left + 6, y0 + 14,
              "rgba(230,238,255,0.75)", "11px system-ui");
      if (rise > 0.05) {
        D.label(ctx, "now +" + rise.toFixed(2) + " cm (liquid pushed aside)", g.left + 6, surf - 6, "#cfe8ff",
                "bold 11px system-ui");
      }

      // ---- the object ----
      this._object(ctx, vz.shape, ox, oy, s, sol);

      // ---- liquid in front of the submerged part, with the rippled surface ----
      var that = this;
      var surfaceY = function (x) { return surf + that._ripple(x, ox, s); };
      ctx.save();
      ctx.beginPath(); ctx.moveTo(g.left, surfaceY(g.left));
      for (var x = g.left; x <= g.right; x += 4) ctx.lineTo(x, surfaceY(x));
      ctx.lineTo(g.right, g.floor); ctx.lineTo(g.left, g.floor); ctx.closePath();
      ctx.fillStyle = D.rgba(liq.color, 0.30); ctx.fill();
      ctx.restore();
      ctx.strokeStyle = "rgba(230,245,255,0.85)"; ctx.lineWidth = 2; ctx.beginPath();
      for (x = g.left; x <= g.right; x += 4) (x === g.left ? ctx.moveTo : ctx.lineTo).call(ctx, x, surfaceY(x));
      ctx.stroke();

      // glass walls
      ctx.strokeStyle = "rgba(200,225,255,0.8)"; ctx.lineWidth = 3;
      ctx.beginPath(); ctx.moveTo(g.left, g.top); ctx.lineTo(g.left, g.floor); ctx.lineTo(g.right, g.floor);
      ctx.lineTo(g.right, g.top); ctx.stroke();

      // splash drops
      ctx.fillStyle = D.rgba(liq.color, 0.9);
      this.drops.forEach(function (d) { ctx.beginPath(); ctx.arc(d.x, d.y, d.r, 0, 7); ctx.fill(); });

      // the hand lets go at t = 0
      if (simT < 0.45) {
        ctx.globalAlpha = Math.max(0, 1 - simT / 0.45);
        PL.drawSprite(ctx, "hand", ox, oy - s - 26 - simT * 60, 56);
        D.label(ctx, "let go!", ox + 34, oy - s - 30, "#ffd166", "bold 12px system-ui");
        ctx.globalAlpha = 1;
      }

      if (view.show === "forces") this._forces(ctx, f, vz, ox, oy, s);
      else if (view.show === "pressure") this._pressure(ctx, f, vz, ox, oy, s, surf);

      this._panel(ctx, w, h, f, res, clock);
    },

    /* cosmetic water effects driven by the object's real motion */
    _effects: function (f, clock, s, ox, surf, sizeM) {
      var dt = clock.sim, r = this.rand;
      var crossing = f.h > 0 && f.h < sizeM;
      if (dt > 0 && crossing && Math.abs(f.v) > 0.03) {
        this.acc = (this.acc || 0) + dt * 8;
        while (this.acc >= 1) {
          this.acc -= 1;
          this.ripples.push({ age: 0, a: Math.min(9, Math.abs(f.v) * 22) });
        }
      }
      if (this.prevH === 0 && f.h > 0 && f.v < -0.3) {           // entry splash
        var n = Math.min(28, Math.round(Math.abs(f.v) * 9));
        for (var i = 0; i < n; i++) {
          var side = i % 2 ? 1 : -1;
          this.drops.push({ x: ox + side * (s / 2 + r() * 6), y: surf - 2,
                            vx: side * (40 + r() * 120), vy: -(80 + r() * 220) * Math.min(1.6, Math.abs(f.v) / 2),
                            r: 1.5 + r() * 2.5, life: 0.9 });
        }
      }
      if (dt > 0) this.prevH = f.h;
      this.ripples.forEach(function (q) { q.age += dt; });
      this.ripples = this.ripples.filter(function (q) { return q.age < 2.5; });
      this.drops.forEach(function (d) { d.vy += 900 * dt; d.x += d.vx * dt; d.y += d.vy * dt; d.life -= dt; });
      this.drops = this.drops.filter(function (d) { return d.life > 0 && d.y < surf + 4; });
    },
    _ripple: function (x, ox, s) {
      var d = Math.abs(x - ox) - s / 2, y = 0;
      if (d < 0) return 0;
      this.ripples.forEach(function (q) {
        var front = 140 * q.age;                           // ripple speed ~0.25 m/s on screen
        if (d < front) y += q.a * Math.exp(-q.age / 0.9) * Math.exp(-d / 160) * Math.sin((d - front) / 7);
      });
      return y;
    },

    _object: function (ctx, shape, ox, oy, s, sol) {
      var x0 = ox - s / 2, y0 = oy - s, id = sol.id;
      ctx.save();
      ctx.beginPath();
      if (shape === "cube") ctx.rect(x0, y0, s, s); else ctx.arc(ox, oy - s / 2, s / 2, 0, 7);
      var gr = shape === "cube" ? ctx.createLinearGradient(x0, y0, x0 + s, oy)
                                : ctx.createRadialGradient(ox - s * 0.18, oy - s * 0.68, s * 0.05, ox, oy - s / 2, s / 2);
      var base = sol.color, light = id === "rubber" ? "#6a6a7c" : "#ffffff";
      gr.addColorStop(0, shape === "cube" ? base : light);
      gr.addColorStop(shape === "cube" ? 0.6 : 0.25, base);
      gr.addColorStop(1, D.rgba(id === "gold" ? "#a87d10" : "#20242e", 0.9));
      ctx.globalAlpha = id === "ice" ? 0.78 : 1;
      ctx.fillStyle = gr; ctx.fill();
      ctx.clip();
      // textures
      var R = D.rng(5), k;      // fixed seed: texture stays put as it moves
      if (id === "pine") {
        ctx.strokeStyle = "rgba(120,70,20,0.45)"; ctx.lineWidth = 1.2;
        for (k = 0; k < 7; k++) {
          var yy = y0 + (k + 0.5) * s / 7;
          ctx.beginPath(); ctx.moveTo(x0, yy);
          ctx.bezierCurveTo(x0 + s * 0.3, yy - 4, x0 + s * 0.6, yy + 4, x0 + s, yy); ctx.stroke();
        }
      } else if (id === "cork") {
        ctx.fillStyle = "rgba(90,55,20,0.55)";
        for (k = 0; k < s * s / 40; k++) { ctx.beginPath(); ctx.arc(x0 + R() * s, y0 + R() * s, 0.8 + R() * 1.4, 0, 7); ctx.fill(); }
      } else if (id === "ice") {
        ctx.strokeStyle = "rgba(255,255,255,0.8)"; ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.moveTo(x0 + s * 0.2, y0 + s * 0.15); ctx.lineTo(x0 + s * 0.45, y0 + s * 0.4); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(x0 + s * 0.6, y0 + s * 0.55); ctx.lineTo(x0 + s * 0.8, y0 + s * 0.7); ctx.stroke();
      } else if (shape === "cube" && (id === "aluminum" || id === "iron" || id === "gold")) {
        ctx.fillStyle = "rgba(255,255,255,0.25)";
        ctx.fillRect(x0, y0 + s * 0.12, s, s * 0.06);
      }
      ctx.restore();
      ctx.globalAlpha = 1;
      ctx.strokeStyle = "#141824"; ctx.lineWidth = 1.5;
      ctx.beginPath();
      if (shape === "cube") ctx.rect(x0, y0, s, s); else ctx.arc(ox, oy - s / 2, s / 2, 0, 7);
      ctx.stroke();
    },

    /* where the forces act (markers on the object) + a free-body diagram
       with every force on one newton->pixel scale (never clipped) */
    _forces: function (ctx, f, vz, ox, oy, s) {
      var g = this.geo, cmY = oy - s / 2, cbY = g.floor - f.zb * g.sc;
      ctx.fillStyle = COL.weight; ctx.beginPath(); ctx.arc(ox, cmY, 4, 0, 7); ctx.fill();
      if (f.fb > 1e-6) {
        ctx.strokeStyle = COL.buoy; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(ox, cbY, 5, 0, 7); ctx.stroke();
      }

      var W = vz.weight, net = f.fb + f.fd + f.fn - W;
      var k = 64 / Math.max(vz.weight, vz.fb_full);
      D.forceBox(ctx, { x: g.right - 222, y: g.top + 8, w: 214, h: 178 }, [
        { name: "weight", value: -W, color: COL.weight, dx: -14 },
        { name: "buoyancy", value: f.fb, color: COL.buoy, dx: 0 },
        { name: "drag", value: f.fd, color: COL.drag, dx: 14 },
        { name: "floor", value: f.fn, color: COL.floor, dx: 28 },
        { name: "net", value: net, color: COL.net, dx: -34, dashed: true }
      ], k, { balanced: Math.abs(net) * k < 1.5 ? "balanced: no net force" : null });
      D.label(ctx, "● centre of mass (weight acts here)   ○ centre of buoyancy (the push up acts here)",
              g.left, g.top - 8, "#cfe0ff", "11px system-ui");
    },

    _pressure: function (ctx, f, vz, ox, oy, s, surf) {
      var k = this.pxPerPa, sc = this.geo.sc, floorY = this.geo.floor;
      var levelY = floorY - f.level * sc;
      // local gauge pressure is linear in depth: p = p_bot * depth / depth_bot
      var depthBot = (f.level - f.y);
      var pAt = function (py) {
        var depth = (py - levelY) / sc;
        return depthBot > 0 ? Math.max(0, f.p_bot * depth / depthBot) : 0;
      };
      var limit = this.geo.floor + 14;
      var push = function (x, y, nx, ny) {          // arrow pointing INTO the surface (n = outward normal)
        var L = pAt(y) * k;
        if (ny > 0) L = Math.min(L, limit - y - 4);   // under an object on the floor: keep on screen
        if (L < 2) return;
        D.arrow(ctx, x + nx * (L + 4), y + ny * (L + 4), x + nx * 2, y + ny * 2, "#ffd166", 2, 6);
      };
      if (vz.shape === "cube") {
        var x0 = ox - s / 2, top = oy - s, i, n = 4;
        for (i = 0; i < n; i++) {
          var xx = x0 + (i + 0.5) * s / n;
          push(xx, top, 0, -1);                     // top face: pushed down
          push(xx, oy, 0, 1);                       // bottom face: pushed up
        }
        for (i = 0; i < 4; i++) {
          var yy = top + (i + 0.5) * s / 4;
          push(x0, yy, -1, 0); push(x0 + s, yy, 1, 0);
        }
      } else {
        var r = s / 2, cy = oy - r;
        for (var a = 0; a < 20; a++) {
          var ang = a / 20 * Math.PI * 2, nx = Math.cos(ang), ny = Math.sin(ang);
          push(ox + nx * r, cy + ny * r, nx, ny);
        }
      }
      var topL = f.p_top * k;
      D.label(ctx, "top: " + (f.p_top / 1000).toFixed(2) + " kPa" + (f.p_top <= 0 ? " (above the surface)" : ""),
              ox, oy - s - topL - 10, "#ffd166", "bold 11px system-ui", "center");
      D.label(ctx, "p = ρ g depth: deeper pushes harder → bottom push − top push = buoyancy",
              this.geo.left, this.geo.top - 8, "#ffd166", "11px system-ui");
      D.label(ctx, "bottom: " + (f.p_bot / 1000).toFixed(2) + " kPa", ox + s / 2 + 56, oy - 4, "#ffd166",
              "bold 11px system-ui");
    },

    /* left panel: readouts, density bars, measuring cylinder */
    _panel: function (ctx, w, h, f, res, clock) {
      var vz = res.viz, sol = vz.solid, liq = vz.liquid, eq = vz.eq;
      D.hud(ctx, [
        "t = " + f.t.toFixed(2) + " s   (" + D.speedTag(clock.speed) + ")",
        "speed " + Math.abs(f.v).toFixed(3) + " m/s " + (f.v > 0.001 ? "↑" : f.v < -0.001 ? "↓" : ""),
        // the formula is about VOLUME (V_sub / V); for a ball that is not the same as height
        "under the surface: " + (100 * f.vsub / vz.volume).toFixed(0) + "% (volume)"
      ]);
      // density bars
      var x = 14, y = 84, maxR = Math.max(sol.rho, liq.rho), L = 190;
      [[sol, "object"], [liq, "liquid"]].forEach(function (q, i) {
        var len = Math.max(3, L * q[0].rho / maxR), yy = y + i * 30;
        ctx.fillStyle = q[0].color; ctx.fillRect(x, yy, len, 14);
        ctx.strokeStyle = "#141824"; ctx.strokeRect(x, yy, len, 14);
        D.label(ctx, q[1] + ": " + q[0].rho + " kg/m³", x, yy - 3, "#cfe0ff", "11px system-ui");
      });
      var verdict = eq.state === "floats" ? "lighter than the liquid → FLOATS"
                  : eq.state === "sinks" ? "denser than the liquid → SINKS" : "same density → HOVERS";
      D.label(ctx, verdict, x, y + 62, eq.state === "floats" ? "#7dffa8" : eq.state === "sinks" ? "#ff8a8a" : "#ffd166",
              "bold 12px system-ui");

      // measuring cylinder: the liquid pushed aside (V_sub), up to the whole object
      var cx0 = 34, cw = 70, cyTop = 200, cyBot = h - 62, H = cyBot - cyTop;
      var frac = vz.volume > 0 ? f.vsub / vz.volume : 0;
      ctx.fillStyle = D.rgba(liq.color, 0.75);
      ctx.fillRect(cx0, cyBot - frac * H, cw, frac * H);
      ctx.strokeStyle = "rgba(200,225,255,0.9)"; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(cx0, cyTop); ctx.lineTo(cx0, cyBot); ctx.lineTo(cx0 + cw, cyBot); ctx.lineTo(cx0 + cw, cyTop); ctx.stroke();
      ctx.lineWidth = 1; ctx.font = "10px system-ui";
      [0.25, 0.5, 0.75, 1].forEach(function (q) {
        var yy = cyBot - q * H;
        ctx.strokeStyle = "rgba(200,225,255,0.6)"; ctx.beginPath(); ctx.moveTo(cx0 + cw - 14, yy); ctx.lineTo(cx0 + cw, yy); ctx.stroke();
        ctx.fillStyle = "#cfe0ff"; ctx.fillText((q * vz.volume * 1000).toPrecision(2) + " L", cx0 + cw + 4, yy + 3);
      });
      D.label(ctx, "= whole object", cx0 + cw + 4, cyTop + 14, "#9fb3e8", "10px system-ui");
      D.label(ctx, "liquid pushed aside", cx0 - 20, cyTop - 10, "#cfe0ff", "bold 12px system-ui");
      var fb = f.fb;
      D.label(ctx, (f.vsub * 1000).toFixed(3) + " L", cx0 + cw / 2, cyBot + 16, "#ffffff", "bold 12px system-ui", "center");
      D.label(ctx, "weighs " + fb.toFixed(2) + " N", cx0 + cw / 2, cyBot + 31, COL.buoy, "bold 11px system-ui", "center");
      D.label(ctx, "= buoyancy", cx0 + cw / 2, cyBot + 44, COL.buoy, "10px system-ui", "center");
    }
  };

  PL.scenes.buoyancy = buoyancy;
})();
