/* physlab particle kit - cosmetic only. The physics engine is server-side;
   these particles decorate (wind streaks, connect sparks, heat embers). */
(function () {
  "use strict";
  window.PL = window.PL || {};

  function Emitter(cfg) {
    this.cfg = cfg;      // {rate, life, make(p)->{x,y,vx,vy,size,color}, w, h}
    this.ps = [];
    this.acc = 0;
  }

  Emitter.prototype.update = function (dt, active) {
    if (active) {
      this.acc += this.cfg.rate * dt;
      while (this.acc >= 1) {
        this.ps.push(this.cfg.make(this.cfg));
        this.acc -= 1;
      }
    }
    var alive = [];
    this.ps.forEach(function (p) {
      p.age += dt;
      p.x += p.vx * dt; p.y += p.vy * dt;
      if (p.age < p.life && p.x > -40 && p.x < this.cfg.w + 40 && p.y > -40 && p.y < this.cfg.h + 40) alive.push(p);
    }, this);
    this.ps = alive;
  };

  Emitter.prototype.render = function (ctx) {
    this.ps.forEach(function (p) {
      var a = Math.max(0, 1 - p.age / p.life);
      ctx.globalAlpha = a * 0.8;
      if (p.streak) {
        ctx.strokeStyle = p.color;
        ctx.lineWidth = p.size;
        ctx.beginPath();
        ctx.moveTo(p.x, p.y);
        ctx.lineTo(p.x - p.vx * 0.12, p.y - p.vy * 0.12);
        ctx.stroke();
      } else {
        ctx.fillStyle = p.color;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size * a, 0, Math.PI * 2);
        ctx.fill();
      }
    });
    ctx.globalAlpha = 1;
  };

  /* presets: make(w, h) -> Emitter */
  function windStreaks(w, h, speed) {
    return new Emitter({
      rate: 14, life: 1.6, w: w, h: h,
      make: function (c) {
        return { x: speed >= 0 ? -10 : c.w + 10, y: 40 + Math.random() * (c.h - 80),
                 vx: (speed || 1) * (60 + Math.random() * 60), vy: 0,
                 size: 1.5, color: "#9fb3e8", age: 0, life: c.life, streak: true };
      }
    });
  }

  function sparks(w, h, x, y) {
    return new Emitter({
      rate: 24, life: 0.5, w: w, h: h,
      make: function (c) {
        return { x: x + (Math.random() - 0.5) * 8, y: y + (Math.random() - 0.5) * 8,
                 vx: (Math.random() - 0.5) * 90, vy: -30 - Math.random() * 70,
                 size: 2.2, color: "#ffd166", age: 0, life: c.life, streak: false };
      }
    });
  }

  function embers(w, h, x, y) {
    return new Emitter({
      rate: 10, life: 1.4, w: w, h: h,
      make: function (c) {
        return { x: x + (Math.random() - 0.5) * 50, y: y,
                 vx: (Math.random() - 0.5) * 14, vy: -25 - Math.random() * 35,
                 size: 2.6, color: "#ff9e5e", age: 0, life: c.life, streak: false };
      }
    });
  }

  window.PL.particles = { Emitter: Emitter, windStreaks: windStreaks, sparks: sparks, embers: embers };
})();
