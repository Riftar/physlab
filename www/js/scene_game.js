/* physlab scene: THE MACHINE WORKS - one hall drawn in world metres.

   runs[0] = { result: {frames: [{t, x, y, ...}], timelapse: [[t0, t1, speed]]},
   st: page state } where the page state carries the hall layout (from the
   server), every station's public card (facts for THIS player's variant), the
   current knobs, the focused station and the last result. Everything tunable
   is drawn from the CURRENT knobs, so dragging a handle previews instantly;
   the ball, its trail and the moving parts (a ring's temperature, a door, a
   piston, a cable) come from the last run's frames (server physics).

   This file is the engine: camera, trails, the ball, the HUD, time-lapse
   playback, and the drawing kit every hall shares (PL.gameKit). Each hall's
   machine is a painter in PL.gameHalls[<hall id>] (hall_bounce.js,
   hall_foundry.js):
     draw(ctx, cam, S, simT, frames)         the building and the stations
     front(ctx, cam, S, simT, frames, ball)  optional: drawn over the ball
     startPoint(S, station) -> {x, y}        where the ball waits before a run
     tags(S) -> [[station, x, y], ...]       the name tags (world metres)
     hud(S, simT, frames) -> [lines]         optional extra HUD lines
     detail                                  optional: px per metre below which small labels hide
                                             (default 75 - a crowded hall asks for more)

   Camera (page state `camera`): "station" fits the focused station,
   "hall" the whole hall, "follow" keeps the zoom of the focused station and
   glides with the ball while the run plays (it looks a little ahead; while
   paused you can pan freely - the page sets followSnap to re-centre); with
   no run loaded it frames the focused station.

   Time-lapse: slow physics (the Foundry's ring heating for 20 s) comes with
   zones [t0, t1, speed]; playback runs that much faster inside them and the
   HUD says so.                                                               */
(function () {
  "use strict";
  var W = PL.widgets;
  var COL = { bg0: "#0b1128", floor: "#1a2348", mezz: "#26305c", post: "#3a4678", wood: "#c08a4e", steel: "#aab3c5",
              duct: "#9a3b3b", flap: "#ffd84a", water: [61, 143, 224], salt: [160, 214, 232], handle: "#ffd166",
              ball: "#e0455a", trail: "#ff9a5c", ghost: "#5cd6ff", ok: "#7dffa8", bad: "#ff6b6b", text: "#dfe6ff",
              dim: "#8d9acb", wall: "#7a3b58" };

  function mix(a, b, t) {
    return "rgb(" + [0, 1, 2].map(function (i) { return Math.round(a[i] + (b[i] - a[i]) * t); }).join(",") + ")";
  }

  var DETAIL = 75;            // px per metre: below this (the whole-hall view) small labels are left out
  function detail(cam) { return cam.len(1) >= (cam.detailMin || DETAIL); }   // a hall painter may ask for more
  function dlabel(ctx, cam, text, x, y, color, font, align) { if (detail(cam)) W.label(ctx, text, x, y, color, font, align); }

  function rect(ctx, cam, x0, y0, x1, y1, fill, stroke) {
    var X0 = cam.X(x0), X1 = cam.X(x1), Y0 = cam.Y(y0), Y1 = cam.Y(y1);
    ctx.fillStyle = fill;
    ctx.fillRect(Math.min(X0, X1), Math.min(Y0, Y1), Math.abs(X1 - X0), Math.abs(Y1 - Y0));
    if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = 1; ctx.strokeRect(Math.min(X0, X1), Math.min(Y0, Y1), Math.abs(X1 - X0), Math.abs(Y1 - Y0)); }
  }

  function line(ctx, cam, pts, color, width, dash) {
    ctx.strokeStyle = color; ctx.lineWidth = width || 2;
    if (dash) ctx.setLineDash(dash);
    ctx.beginPath();
    pts.forEach(function (p, i) { i ? ctx.lineTo(cam.X(p[0]), cam.Y(p[1])) : ctx.moveTo(cam.X(p[0]), cam.Y(p[1])); });
    ctx.stroke();
    if (dash) ctx.setLineDash([]);
  }

  function knobHandle(ctx, x, y, key, active) {
    ctx.fillStyle = COL.handle; ctx.strokeStyle = "#0b1128"; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(x, y, 8, 0, 7); ctx.fill(); ctx.stroke();
    ctx.strokeStyle = "rgba(255,209,102," + (active ? 0.9 : 0.5) + ")"; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.arc(x, y, 13, 0, 7); ctx.stroke();
  }

  function sprite(ctx, cam, name, x, y, size, rot) {
    var s = cam.len(size);
    if (!PL.drawSprite(ctx, name, cam.X(x), cam.Y(y), s, null, rot)) {     // fallback if a sprite is missing
      ctx.fillStyle = "#3a4678"; ctx.fillRect(cam.X(x) - s / 2, cam.Y(y) - s / 2, s, s);
    }
  }

  function tag(ctx, x, y, n, name, on) {
    ctx.font = "bold 12px system-ui"; var w = ctx.measureText(n + "  " + name).width + 16;
    ctx.fillStyle = on ? "rgba(255,154,92,0.18)" : "rgba(17,26,58,0.85)";
    ctx.strokeStyle = on ? "#ff9a5c" : "#3a4678"; ctx.lineWidth = 1.2;
    ctx.beginPath(); ctx.rect(x - w / 2, y - 11, w, 22); ctx.fill(); ctx.stroke();
    ctx.textAlign = "center"; ctx.fillStyle = "#ff9a5c"; ctx.fillText(n, x - w / 2 + 8 + ctx.measureText(n).width / 2, y + 4);
    ctx.fillStyle = COL.text; ctx.textAlign = "left"; ctx.fillText(name, x - w / 2 + 14 + ctx.measureText(n).width, y + 4);
  }


  function endpoint(ctx, cam, x, y, letter, text, color) {
    var X = cam.X(x), Y = cam.Y(y);
    ctx.fillStyle = color; ctx.strokeStyle = "#ffffff"; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.arc(X, Y, 11, 0, 7); ctx.fill(); ctx.stroke();
    ctx.fillStyle = "#0b1128"; ctx.font = "bold 13px system-ui"; ctx.textAlign = "center"; ctx.fillText(letter, X, Y + 5);
    W.label(ctx, text, X, Y + 24, color, "11px system-ui", "center");
  }

  function trailOf(ctx, cam, frames, simT, color, width, span) {
    if (!frames || frames.length < 2) return;
    ctx.strokeStyle = color; ctx.lineWidth = width; ctx.beginPath();
    var started = false;
    for (var i = 0; i < frames.length; i++) {
      var f = frames[i];
      if (f.t > simT) break;
      if (span && simT - f.t > span) continue;
      if (!started) { ctx.moveTo(cam.X(f.x), cam.Y(f.y)); started = true; } else ctx.lineTo(cam.X(f.x), cam.Y(f.y));
    }
    ctx.stroke();
  }

  var FOLLOW_LEAD = 0.35;    // s: the follow camera aims a little ahead of the ball
  var FOLLOW_RATE = 5.0;     // 1/s: how quickly it catches up (exponential smoothing)

  function painter(S) { return PL.gameHalls[S.hall.id]; }

  function ballAt(S, frames, t) {
    return frames.length ? PL.frameAt(frames, t) : painter(S).startPoint(S, S.focus || S.order[0]);
  }

  function follow(cam, S, frames, simT, clock) {
    var tx, ty;
    if (frames.length) {
      var now = ballAt(S, frames, simT), ahead = ballAt(S, frames, simT + FOLLOW_LEAD);
      tx = 0.6 * now.x + 0.4 * ahead.x; ty = 0.6 * now.y + 0.4 * ahead.y;
    } else {                                                           // nothing running: show the whole station
      var v = S.hall.layout.stations[S.focus || S.order[0]].view;
      tx = (v.x0 + v.x1) / 2; ty = (v.y0 + v.y1) / 2;
    }
    cam.box = S.hall.layout.bounds;                                   // pan limits: the whole hall
    if (S.followSnap) { cam.cx = tx; cam.cy = ty; S.followSnap = false; return; }
    if (!clock.playing || !(clock.real > 0)) return;                   // paused: leave the view to the user
    var k = 1 - Math.exp(-FOLLOW_RATE * clock.real);
    cam.cx += (tx - cam.cx) * k;
    cam.cy += (ty - cam.cy) * k;
  }

  function ball(ctx, cam, L, f) {
    var r = Math.max(cam.len(L.ball.r), 6);
    ctx.fillStyle = L.ball.color; ctx.strokeStyle = "#0b1128"; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(cam.X(f.x), cam.Y(f.y), r, 0, 7); ctx.fill(); ctx.stroke();
    ctx.fillStyle = "rgba(255,255,255,0.4)";
    ctx.beginPath(); ctx.arc(cam.X(f.x) - r * 0.3, cam.Y(f.y) - r * 0.3, r * 0.3, 0, 7); ctx.fill();
  }

  PL.gameHalls = PL.gameHalls || {};
  PL.gameKit = { COL: COL, mix: mix, detail: detail, dlabel: dlabel, rect: rect, line: line, knobHandle: knobHandle,
                 sprite: sprite, tag: tag, endpoint: endpoint, ball: ball };

  var game = {
    continuous: false,
    options: [{ id: "pace", label: "Speed", default: "1",
                choices: [{ id: "0.5", label: "½×" }, { id: "1", label: "1×" }, { id: "2", label: "2×" }] }],
    duration: function (runs) { var f = runs[0].result.frames; return f.length ? f[f.length - 1].t : 0; },
    speed: function (t, runs, view) {
      return parseFloat(view.pace || "1") * PL.game.timelapse(runs[0].result.timelapse, t);
    },
    world: function (runs) {
      var S = runs[0].st, L = S.hall.layout;
      if (S.camera === "hall" || !S.focus) return L.bounds;
      return L.stations[S.focus].view;
    },
    worldPad: 0.02,
    init: function () {},

    render: function (ctx, w, h, simT, clock, runs, view, cam) {
      var S = runs[0].st, L = S.hall.layout, frames = runs[0].result.frames, P = painter(S);
      cam.detailMin = P.detail || DETAIL;
      if (S.camera === "follow") follow(cam, S, frames, simT, clock);
      ctx.clearRect(0, 0, w, h);
      var sky = ctx.createLinearGradient(0, 0, 0, h);
      sky.addColorStop(0, "#101a3e"); sky.addColorStop(1, COL.bg0);
      ctx.fillStyle = sky; ctx.fillRect(0, 0, w, h);

      P.draw(ctx, cam, S, simT, frames);

      // station tags (the focused one highlighted)
      P.tags(S).forEach(function (tg) {
        tag(ctx, cam.X(tg[1]), cam.Y(tg[2]), tg[0], S.stations[tg[0]].title, S.focus === tg[0]);
      });

      // the previous run (faint) and this run's trail, then the ball (and what goes in front of it)
      if (S.ghost) trailOf(ctx, cam, S.ghost, 1e9, "rgba(92,214,255,0.35)", 1.5);
      trailOf(ctx, cam, frames, simT, "rgba(255,154,92,0.85)", 2);
      var f = ballAt(S, frames, simT);
      ball(ctx, cam, L, f);
      if (P.front) P.front(ctx, cam, S, simT, frames, f);

      // HUD + the verdict once the run has played
      var hud = [], here = S.focus;
      if (S.last && S.last.mode === "machine") {          // name the station the ball is in right now
        S.last.stations.forEach(function (r2) { if (simT >= r2.t0 - 1e-9) here = r2.id; });
      }
      if (here) hud.push({ text: (S.last && S.last.mode === "machine" ? "now: " : "") + here + " " + S.stations[here].title +
                                 (S.practice ? "   · practice mode (variant " + S.variant + ")" : "") +
                                 (S.camera === "follow" ? "   · 🎥 following the ball" : ""), color: "#8fd3ff" });
      if (S.last && frames.length) {
        var lapse = PL.game.timelapse(runs[0].result.timelapse, simT);
        hud.push({ text: "t = " + simT.toFixed(2) + " s" + (lapse > 1.01 && !clock.finished
                     ? "   ⏩ time-lapse: " + lapse.toFixed(lapse < 10 ? 1 : 0) + "× faster" : ""),
                   color: lapse > 1.01 ? COL.handle : "#8fd3ff" });
        if (P.hud) P.hud(S, simT, frames).forEach(function (x) { hud.push(x); });
        if (frames.length && (clock.finished || simT >= frames[frames.length - 1].t - 1e-9)) {
          S.last.stations.forEach(function (r2) {
            var sc = r2.ok ? "  🏆 " + r2.score : "";
            var txt = r2.reason.length > 80 ? r2.reason.slice(0, 78) + "…" : r2.reason;
            hud.push({ text: (r2.ok ? "✓ " : "✗ ") + r2.id + sc + "  " + txt, color: r2.ok ? COL.ok : COL.bad });
          });
        }
      } else {
        hud.push({ text: "set the yellow handles (or the settings below), then ▶ Test station", color: COL.dim });
      }
      ctx.fillStyle = "rgba(11,17,40,0.78)";                 // a backdrop, so the hall doesn't show through
      ctx.fillRect(0, 0, w, 8 + 17 * hud.length);
      W.hud(ctx, hud);
      W.legend(ctx, [["yellow = what you can tune · orange = this run · faint blue = the run before", null]], 12, h - 10);
    }
  };

  PL.scenes.game = game;
})();
