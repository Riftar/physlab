/* physlab Player: plays a scene on a Stage, driven by SIMULATION time.

   Every frame from the server carries its own t; the scene says how many
   simulated seconds pass per real second (speed) and when playback ends
   (duration); values between recorded frames are interpolated by the
   scene (PL.frameAt). Continuous scenes keep animating after the end.

   Scene interface (all optional except render):
     init(ctx, w, h, runs, view, cam)          new result(s) / reset
     render(ctx, w, h, simT, clock, runs, view, cam)
        clock = {real, sim, speed, playing, finished}
     speed(simT, runs, view), duration(runs), continuous, options
     world(runs, goal) -> {x0, x1, y0, y1}  opt in to the world camera (stage.js)
     drawGoal(ctx, w, h, goal, runs, cam, simT)  draw a quiz target (optional)

   Usage: var p = new PL.Player(stage, scene, onState);
          p.load(runs, view, {seek: 1.2, keepView: true});
          p.toggle(); p.reset(); p.redraw();                          */
(function () {
  "use strict";

  function Player(stage, scene, onState) {
    this.stage = stage; this.scene = scene; this.onState = onState || function () {};
    this.runs = null; this.view = {};
    this.simT = 0; this.playing = false; this.finished = false;
    this.lastTs = null; this.raf = null;
    this._step = this._step.bind(this);
  }

  Player.prototype.duration = function () {
    var sc = this.scene, runs = this.runs;
    if (sc.duration) return sc.duration(runs);
    return Math.max.apply(null, runs.map(function (r) { var f = r.result.frames; return f[f.length - 1].t; }));
  };

  Player.prototype.speedAt = function (t) {
    return this.scene.speed ? this.scene.speed(t, this.runs, this.view) : 1;
  };

  Player.prototype.draw = function (dtReal, dtSim) {
    if (!this.runs) return;
    var that = this, clock = { real: dtReal, sim: dtSim, speed: this.speedAt(this.simT),
                               playing: this.playing, finished: this.finished };
    this.stage.draw(function (ctx, w, h, cam) {
      that.scene.render(ctx, w, h, that.simT, clock, that.runs, that.view, cam);
      if (that.goal && that.scene.drawGoal) that.scene.drawGoal(ctx, w, h, that.goal, that.runs, cam, that.simT);
    });
  };

  Player.prototype.redraw = function () { if (!this.playing) this.draw(0, 0); };

  Player.prototype.label = function () {
    return this.playing ? "⏸ pause" : this.finished ? "↻ replay" : "▶ run";
  };

  Player.prototype._emit = function () { this.onState(this.label()); };

  Player.prototype._step = function (ts) {
    if (!this.playing) return;
    if (this.lastTs == null) this.lastTs = ts;
    var dt = Math.min(0.05, (ts - this.lastTs) / 1000);
    this.lastTs = ts;
    var end = this.duration(), dtSim = 0;
    if (this.simT < end) {
      dtSim = Math.min(end - this.simT, this.speedAt(this.simT) * dt);
      this.simT += dtSim;
    }
    var done = this.simT >= end - 1e-9;
    if (done && !this.scene.continuous) {
      this.playing = false; this.finished = true;
      this.draw(dt, dtSim); this._emit();
      return;
    }
    this.finished = done;
    this.draw(dt, dtSim);
    this.raf = requestAnimationFrame(this._step);
  };

  Player.prototype.setPlaying = function (on) {
    this.playing = on;
    this.lastTs = null;
    cancelAnimationFrame(this.raf);
    if (on) this.raf = requestAnimationFrame(this._step);
    else this.draw(0, 0);
    this._emit();
  };

  Player.prototype.restart = function () {
    this.simT = 0; this.finished = false;
    this.draw(0, 0);
    this.setPlaying(true);
  };

  /* play from 0 to `target` in fixed 1/60 s real-time steps (so trails,
     ripples and particles build up exactly as when watching), then pause */
  Player.prototype.fastForward = function (target) {
    this.simT = 0; this.finished = false; this.playing = true;
    target = Math.min(target, this.duration());
    var guard = 0, dtReal = 1 / 60;
    this.draw(0, 0);
    while (this.simT < target - 1e-9 && guard++ < 100000) {
      var sp = this.speedAt(this.simT);
      var dtSim = Math.min(target - this.simT, sp * dtReal);
      this.simT += dtSim;
      this.draw(dtSim / sp, dtSim);
    }
    this.playing = false;
    this.finished = !this.scene.continuous && this.simT >= this.duration() - 1e-9;
    cancelAnimationFrame(this.raf);
    this._emit();
  };

  Player.prototype._init = function () {
    var st = this.stage;
    this.scene.init(st.ctx, st.w, st.h, this.runs, this.view, st.cam, this.goal);
  };

  Player.prototype.load = function (runs, view, opts) {
    opts = opts || {};
    this.runs = runs; this.view = view;
    this.goal = opts.goal || null;               // quiz target the scene may draw (drawGoal)
    this.stage.setScene(this.scene, runs, opts.keepView, this.goal);
    this._init();
    if (opts.seek != null) this.fastForward(opts.seek);
    else if (opts.paused) { this.simT = 0; this.finished = false; this.setPlaying(false); }
    else this.restart();
  };

  Player.prototype.toggle = function () {
    if (!this.runs) return;
    if (this.finished && !this.playing) { this._init(); this.restart(); }
    else this.setPlaying(!this.playing);
  };

  Player.prototype.reset = function () {
    if (!this.runs) return;
    this._init();
    this.restart();
  };

  Player.prototype.stop = function () {
    this.playing = false;
    cancelAnimationFrame(this.raf);
  };

  PL.Player = Player;
})();
