/* physlab scene painters. One draw function per ready topic; each consumes
   the obj3d + particles kits and the frame array from /api/run. */
(function () {
  "use strict";
  window.PL = window.PL || {};

  /* ---- sprite assets: white-keyed at load, tintable ---- */
  PL.sprites = {};
  (function loadSprites() {
    ["lamp", "battery", "switch", "resistor", "block", "ball", "ramp", "wire"]
      .forEach(function (name) {
        var img = new Image();
        img.onload = function () {
          var c = document.createElement("canvas");
          c.width = img.width; c.height = img.height;
          var x = c.getContext("2d");
          x.drawImage(img, 0, 0);
          var d = x.getImageData(0, 0, c.width, c.height);
          for (var i = 0; i < d.data.length; i += 4) {
            if (d.data[i] > 238 && d.data[i + 1] > 238 && d.data[i + 2] > 238) {
              d.data[i + 3] = 0;
            }
          }
          x.putImageData(d, 0, 0);
          PL.sprites[name] = c;
        };
        img.src = "sprites/item_" + name + ".png";
      });
  })();

  /* draw a sprite centered at (cx, cy), size s; optional tint color
     via multiply composite clipped to the sprite's own alpha */
  PL.drawSprite = function (ctx, name, cx, cy, s, tint) {
    var spr = PL.sprites[name];
    if (!spr) return false;
    var c = spr;
    if (tint) {
      c = document.createElement("canvas");
      c.width = spr.width; c.height = spr.height;
      var x = c.getContext("2d");
      x.drawImage(spr, 0, 0);
      x.globalCompositeOperation = "multiply";
      x.fillStyle = tint;
      x.fillRect(0, 0, c.width, c.height);
      x.globalCompositeOperation = "destination-in";
      x.drawImage(spr, 0, 0);
    }
    ctx.drawImage(c, cx - s / 2, cy - s / 2, s, s);
    return true;
  };

  function cam(w, h) { return { cx: w / 2, cy: h / 2, fov: 500, dist: 700 }; }
  function hud(ctx, lines) {
    ctx.font = "13px ui-monospace, Menlo, monospace";
    ctx.fillStyle = "#8fd3ff";
    lines.forEach(function (l, i) { ctx.fillText(l, 12, 20 + i * 17); });
  }
  function tempColor(t, lo, hi) {
    var k = Math.max(0, Math.min(1, (t - lo) / (hi - lo || 1)));
    var r = Math.round(30 + k * 225), g = Math.round(90 + k * 40), b = Math.round(220 - k * 190);
    return "rgb(" + r + "," + g + "," + b + ")";
  }

  /* ---------- circuits ---------- */
  var circuits = {
    init: function (ctx, w, h, result, params) {
      this.wind = null;
      this.spark = PL.particles.sparks(w, h, 0, 0);
    },
    render: function (ctx, w, h, i, dt, result, params) {
      var f = result.frames[Math.min(i, result.frames.length - 1)];
      ctx.clearRect(0, 0, w, h);
      var c = cam(w, h);
      // wire loop: rounded rectangle path
      var lx = w * 0.22, rx = w * 0.78, ty = h * 0.3, by = h * 0.72;
      ctx.strokeStyle = "#5a6ea0"; ctx.lineWidth = 4;
      ctx.beginPath(); ctx.moveTo(lx + 30, ty); ctx.lineTo(rx - 30, ty);
      ctx.lineTo(rx, ty + 30); ctx.lineTo(rx, by - 30);
      ctx.lineTo(rx - 30, by); ctx.lineTo(lx + 30, by);
      ctx.lineTo(lx, by - 30); ctx.lineTo(lx, ty + 30);
      ctx.lineTo(lx + 30, ty); ctx.stroke();
      // battery: sprite (3D cylinder fallback)
      if (!PL.drawSprite(ctx, "battery", w / 2, by - 20, 84)) {
        PL.obj3d.draw(ctx, PL.obj3d.cylinder(26, 54, 14),
          { x: 0, y: 10, ry: 0.7, rx: 0.12, scale: 1, cam: c, color: "#3ddc84", stroke: "#1c7a4a" });
      }
      ctx.fillStyle = "#eef2ff"; ctx.font = "bold 13px system-ui";
      ctx.fillText(params.voltage.toFixed(1) + " V", w / 2 - 20, by - 24);
      // switch on the right side
      var sx = rx, sy = (ty + by) / 2;
      ctx.strokeStyle = params.closed ? "#ffd166" : "#8899cc"; ctx.lineWidth = 4;
      ctx.beginPath(); ctx.moveTo(sx, sy - 26); ctx.lineTo(sx, sy - 6); ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(sx, sy - 26);
      ctx.lineTo(sx + (params.closed ? 4 : 26), sy + 2);
      ctx.stroke();
      ctx.fillStyle = params.closed ? "#7dffa8" : "#ff8a8a"; ctx.font = "bold 12px system-ui";
      ctx.fillText(params.closed ? "ON" : "OFF", sx + 10, sy + 26);
      // lamps along the top
      var n = params.lamps, that = this;
      var lx0 = lx + 60, span = (rx - lx - 120) / Math.max(1, n - 1 || 1);
      for (var k = 0; k < n; k++) {
        var px = n === 1 ? (lx + rx) / 2 : lx0 + span * k;
        var py = ty - 36;
        // lamp sprite + code-drawn glow (brightness stays physics-driven)
        if (f.brightness > 0.01) {
          var g = ctx.createRadialGradient(px, py, 4, px, py, 30 + 60 * f.brightness);
          g.addColorStop(0, "rgba(255,230,140," + (0.9 * f.brightness) + ")");
          g.addColorStop(1, "rgba(255,230,140,0)");
          ctx.fillStyle = g;
          ctx.beginPath(); ctx.arc(px, py, 30 + 60 * f.brightness, 0, Math.PI * 2); ctx.fill();
        }
        if (!PL.drawSprite(ctx, "lamp", px, py, 64)) {
          PL.obj3d.draw(ctx, PL.obj3d.sphere(16, 10),
            { x: 0, y: 0, ry: 0.4 + k, rx: 0.3, scale: 1, cam: { cx: px, cy: py, fov: 500, dist: 640 },
              color: f.brightness > 0.01 ? "#ffe08a" : "#55628f", stroke: "#2c365e" });
        }
        // sparks when current flows
        that.spark.cfg.make = function (cc) {
          return { x: px + (Math.random() - 0.5) * 10, y: py + 12,
                   vx: (Math.random() - 0.5) * 80, vy: -20 - Math.random() * 60,
                   size: 2, color: "#ffd166", age: 0, life: cc.life, streak: false };
        };
      }
      this.spark.update(dt, f.brightness > 0.05);
      this.spark.render(ctx);
      hud(ctx, ["I = " + f.current.toFixed(3) + " A",
                "glow = " + Math.round(f.brightness * 100) + "%",
                "E used = " + f.energy.toFixed(1) + " J"]);
    }
  };

  /* ---------- motion ---------- */
  var motion = {
    init: function (ctx, w, h, result, params) {
      this.wind = PL.particles.windStreaks(w, h, params.wind * 14);
      this.trail = [];
    },
    render: function (ctx, w, h, i, dt, result, params) {
      var f = result.frames[Math.min(i, result.frames.length - 1)];
      ctx.clearRect(0, 0, w, h);
      var xs = result.frames.map(function (d) { return d.x; });
      var ys = result.frames.map(function (d) { return d.y; });
      var xmax = Math.max.apply(null, xs) * 1.12 + 0.01;
      var ymax = Math.max.apply(null, ys) * 1.25 + 0.01;
      var gx = (w - 80) / xmax, gy = (h - 90) / Math.max(ymax, xmax * 0.5);
      var sx = function (x) { return 50 + x * gx; };
      var sy = function (y) { return h - 46 - y * gy; };
      // ground + distance grid
      ctx.strokeStyle = "#2c3a66"; ctx.lineWidth = 1;
      var step = niceStep(xmax);
      for (var d = 0; d <= xmax; d += step) {
        ctx.beginPath(); ctx.moveTo(sx(d), h - 46); ctx.lineTo(sx(d), 30); ctx.stroke();
      }
      ctx.strokeStyle = "#5a6ea0"; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(30, h - 46); ctx.lineTo(w - 20, h - 46); ctx.stroke();
      ctx.fillStyle = "#8fd3ff"; ctx.font = "11px ui-monospace, Menlo, monospace";
      for (d = 0; d <= xmax; d += step) { ctx.fillText(d.toFixed(0) + "m", sx(d) - 8, h - 28); }
      // launcher
      var rad = params.angle * Math.PI / 180;
      ctx.strokeStyle = "#ffd166"; ctx.lineWidth = 5;
      ctx.beginPath(); ctx.moveTo(sx(0), sy(0));
      ctx.lineTo(sx(0) + Math.cos(rad) * 46, sy(0) - Math.sin(rad) * 46); ctx.stroke();
      // trail
      this.trail.push([sx(f.x), sy(f.y)]);
      if (this.trail.length > 400) this.trail.shift();
      ctx.strokeStyle = "rgba(143,211,255,.7)"; ctx.lineWidth = 2;
      ctx.beginPath();
      this.trail.forEach(function (p, ix) { ix ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]); });
      ctx.stroke();
      // ball sprite (3D sphere fallback)
      if (!PL.drawSprite(ctx, "ball", sx(f.x), sy(f.y), 34)) {
        PL.obj3d.draw(ctx, PL.obj3d.sphere(13, 10),
          { x: 0, y: 0, ry: i * 0.05, rx: 0.3, scale: 1, cam: { cx: sx(f.x), cy: sy(f.y), fov: 500, dist: 640 },
            color: "#ff8a5c", stroke: "#a34a28" });
      }
      this.wind.cfg.w = w; this.wind.cfg.h = h;
      this.wind.update(dt, Math.abs(params.wind) > 0.05 && params.drag > 0);
      this.wind.render(ctx);
      hud(ctx, ["t = " + f.t.toFixed(2) + " s", "x = " + f.x.toFixed(2) + " m",
                "y = " + f.y.toFixed(2) + " m", "speed = " + Math.hypot(f.vx, f.vy).toFixed(2) + " m/s"]);
    }
  };

  function niceStep(range) {
    var raw = range / 8, mag = Math.pow(10, Math.floor(Math.log10(raw)));
    return [1, 2, 5, 10].map(function (m) { return m * mag; })
      .reduce(function (a, b) { return Math.abs(b - raw) < Math.abs(a - raw) ? b : a; });
  }

  /* ---------- heat ---------- */
  var heat = {
    init: function (ctx, w, h, result, params) { this.emb = null; },
    render: function (ctx, w, h, i, dt, result, params) {
      var f = result.frames[Math.min(i, result.frames.length - 1)];
      ctx.clearRect(0, 0, w, h);
      var c = cam(w, h);
      var lo = Math.min(params.temp_a, params.temp_b) - 5;
      var hi = Math.max(params.temp_a, params.temp_b) + 5;
      var blocks = [
        { x: -110, t: f.temp_a, label: params.material_a + "  " + params.mass_a + " kg" },
        { x: 110, t: f.temp_b, label: params.material_b + "  " + params.mass_b + " kg" }
      ];
      var that = this;
      blocks.forEach(function (b, ix) {
        // tinted block sprite keeps the temperature→color mapping physics-true
        if (!PL.drawSprite(ctx, "block", (w / 2) + b.x, h / 2 - 20, 150, tempColor(b.t, lo, hi))) {
          PL.obj3d.draw(ctx, PL.obj3d.box(120, 120, 120),
            { x: b.x, y: -20, ry: 0.5 + ix * 0.1, rx: 0.18, scale: 1, cam: c,
              color: tempColor(b.t, lo, hi), stroke: "#0b1128" });
        }
        ctx.fillStyle = "#eef2ff"; ctx.font = "13px system-ui";
        ctx.fillText(b.label, (w / 2) + b.x * 0.62 - 60, h - 54);
        ctx.fillStyle = tempColor(b.t, lo, hi);
        ctx.font = "bold 20px ui-monospace, Menlo, monospace";
        ctx.fillText(b.t.toFixed(1) + " °C", (w / 2) + b.x * 0.62 - 34, h - 76);
      });
      // heat flow arrows between blocks while transferring
      var gap = f.temp_a - f.temp_b;
      if (Math.abs(gap) > 0.5) {
        var dir = gap > 0 ? 1 : -1;
        ctx.strokeStyle = "rgba(255,158,94," + Math.min(1, Math.abs(gap) / 30) + ")";
        ctx.lineWidth = 3;
        for (var a = 0; a < 3; a++) {
          var yy = h / 2 - 30 + a * 30;
          ctx.beginPath();
          ctx.moveTo(w / 2 - dir * 36, yy); ctx.lineTo(w / 2 + dir * 36, yy);
          ctx.lineTo(w / 2 + dir * 36 - dir * 8, yy - 5);
          ctx.stroke();
        }
        if (!this.emb) this.emb = PL.particles.embers(w, h, w / 2, h / 2 - 60);
        this.emb.update(dt, Math.abs(gap) > 5);
        this.emb.render(ctx);
      }
      hud(ctx, ["t = " + f.t.toFixed(0) + " s",
                "A: " + f.temp_a.toFixed(1) + " °C   B: " + f.temp_b.toFixed(1) + " °C"]);
    }
  };

  window.PL.scenes = { circuits: circuits, motion: motion, heat: heat };
})();
