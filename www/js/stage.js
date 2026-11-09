/* physlab Stage: the reusable, zoomable simulation canvas.

   - crisp on high-DPI screens (the backing store is devicePixelRatio x
     the 880 x 500 logical size every scene draws in)
   - zoom: Ctrl/⌘ + wheel or trackpad pinch, two-finger pinch on touch,
     plain wheel once the canvas has been clicked (so the page still
     scrolls normally), double-click (Shift = out), or the − / + / fit bar
   - pan: drag
   - handles: scenes can register draggable points while drawing
       cam.handle({x, y, r, cursor, title, drag(worldPoint), end(), click()})
     (x, y in screen px). A press that moves less than 4 px is a click:
     it calls click() (handles without drag() may be clicked, and dragging
     from them pans the view as usual). A handle with a `key` is reported
     as cam.hoverKey while the pointer is over it (scenes may highlight it). The stage does the hit-testing and pointer
     capture; the scene decides what a drag means (e.g. move the candle,
     which changes a parameter). Groundwork for more interaction later.

   Two camera modes:
     world  - scenes that define world(runs) -> {x0, x1, y0, y1} draw with
              cam.X(x) / cam.Y(y) / cam.len(d) (metres or cm, y up), so
              geometry zooms while text and line widths stay crisp
     bitmap - older pixel-space scenes: the whole drawing is magnified
              with a canvas transform (zoom 1 = exactly as before)     */
(function () {
  "use strict";
  var E = PL.ui.el;
  var CLICK_SLOP = 4;              // px a pointer may wander and still count as a click

  function Stage(w, h) {
    this.w = w || 880; this.h = h || 500;
    this.el = E("div", "stage");
    this.canvas = E("canvas"); this.canvas.id = "stage";
    this.dpr = Math.min(3, Math.max(1, window.devicePixelRatio || 1));
    this.canvas.width = Math.round(this.w * this.dpr);
    this.canvas.height = Math.round(this.h * this.dpr);
    this.el.appendChild(this.canvas);
    this.ctx = this.canvas.getContext("2d");
    this.cam = new PL.Camera(this.w, this.h);
    this.mode = "bitmap";
    this.handles = [];
    this.onChange = null;          // camera moved (redraw while paused)
    this.active = false;           // plain wheel zooms once the canvas was clicked
    var that = this;
    this.cam.handle = function (hd) { that.handles.push(hd); };
    this._bar();
    this._bind();
  }

  Stage.prototype._bar = function () {
    var that = this, bar = E("div", "zoombar");
    var mk = function (txt, title, fn) {
      var b = E("button", "zbtn", txt); b.type = "button"; b.title = title;
      b.addEventListener("click", function (e) { e.stopPropagation(); fn(); });
      bar.appendChild(b); return b;
    };
    mk("−", "zoom out", function () { that.zoomBy(1 / 1.5); });
    this.zlabel = E("span", "zlabel", "100%");
    bar.appendChild(this.zlabel);
    mk("+", "zoom in", function () { that.zoomBy(1.5); });
    mk("⤢ fit", "fit the whole experiment", function () { that.fit(); });
    this.hint = E("div", "zhint", "Ctrl + scroll or pinch to zoom · drag to pan");
    this.el.appendChild(bar);
    this.el.appendChild(this.hint);
  };

  /* camera set-up for a scene; keepView keeps a zoom the user chose */
  Stage.prototype.setScene = function (scene, runs, keepView, goal) {
    var c = this.cam;
    this.scene = scene;
    if (scene && scene.world) {
      this.mode = "world";
      this._fitArgs = [scene.world(runs, goal), scene.worldPad == null ? 0.06 : scene.worldPad, true];
      c.minZ = 0.2; c.maxZ = 60; c.contain = false;
    } else {
      this.mode = "bitmap";
      this._fitArgs = [{ x0: 0, x1: this.w, y0: 0, y1: this.h }, 0, false];
      c.minZ = 1; c.maxZ = 6; c.contain = true;
    }
    if (keepView && (c.moved || this.dragging)) {
      c.box = this._fitArgs[0];          // keep the user's view, but pan limits follow the scene
    } else {
      c.fit.apply(c, this._fitArgs);
    }
    this.el.classList.toggle("world", this.mode === "world");
    this._label();
  };

  Stage.prototype.fit = function () {
    if (this._fitArgs) this.cam.fit.apply(this.cam, this._fitArgs);
    this._changed();
  };

  Stage.prototype.zoomBy = function (f, px, py) {
    this.cam.zoomAt(px == null ? this.w / 2 : px, py == null ? this.h / 2 : py, f);
    this._changed();
  };

  Stage.prototype._label = function () {
    this.zlabel.textContent = Math.round(this.cam.zoom() * 100) + "%";
  };

  Stage.prototype._changed = function () {
    this._label();
    if (this.onChange) this.onChange();
  };

  /* draw one frame: fn(ctx, w, h, cam) */
  Stage.prototype.draw = function (fn) {
    var ctx = this.ctx, d = this.dpr;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    this.handles = [];
    if (this.mode === "bitmap") {
      var m = this.cam.matrix();
      ctx.setTransform(d * m[0], 0, 0, d * m[3], d * m[4], d * m[5]);
    } else {
      ctx.setTransform(d, 0, 0, d, 0, 0);
    }
    fn(ctx, this.w, this.h, this.cam);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
  };

  /* ---------- input ---------- */
  Stage.prototype._pt = function (e) {
    var r = this.canvas.getBoundingClientRect();
    return { x: (e.clientX - r.left) * this.w / r.width, y: (e.clientY - r.top) * this.h / r.height };
  };

  Stage.prototype._hit = function (p) {
    for (var i = this.handles.length - 1; i >= 0; i--) {
      var hd = this.handles[i];
      if (Math.hypot(p.x - hd.x, p.y - hd.y) <= (hd.r || 12) + 4) return hd;
    }
    return null;
  };

  Stage.prototype._bind = function () {
    var that = this, cv = this.canvas, pointers = {}, drag = null, pinch = null;

    document.addEventListener("pointerdown", function (e) {
      if (!that.el.contains(e.target)) that._activate(false);
    });
    cv.addEventListener("wheel", function (e) {
      if (!(e.ctrlKey || e.metaKey || that.active)) return;     // let the page scroll
      e.preventDefault();
      var p = that._pt(e);
      // wheel notches send |deltaY| ~ 100, trackpad pinches small steps
      var k = Math.abs(e.deltaY) < 30 ? 0.01 : 0.002;
      that.zoomBy(Math.exp(-e.deltaY * k), p.x, p.y);
    }, { passive: false });
    cv.addEventListener("dblclick", function (e) {
      var p = that._pt(e);
      that.zoomBy(e.shiftKey ? 0.5 : 2, p.x, p.y);
    });
    cv.addEventListener("pointerdown", function (e) {
      that._activate(true);
      var p = that._pt(e);
      pointers[e.pointerId] = p;
      cv.setPointerCapture(e.pointerId);
      var ids = Object.keys(pointers);
      if (ids.length === 2) {                                    // start a pinch
        var a = pointers[ids[0]], b = pointers[ids[1]];
        pinch = { d: Math.hypot(a.x - b.x, a.y - b.y) };
        drag = null;
        return;
      }
      var hd = that.mode === "world" ? that._hit(p) : null;
      if (hd && hd.drag) {
        drag = { handle: hd, start: p };
        cv.style.cursor = "grabbing"; that.dragging = true;
      } else {                 // pan - or, if it ends where it started, a click on a handle
        drag = { pan: true, last: p, start: p, click: hd && hd.click ? hd : null };
      }
    });
    cv.addEventListener("pointermove", function (e) {
      var p = that._pt(e);
      if (pointers[e.pointerId]) pointers[e.pointerId] = p;
      var ids = Object.keys(pointers);
      if (pinch && ids.length === 2) {
        var a = pointers[ids[0]], b = pointers[ids[1]], d = Math.hypot(a.x - b.x, a.y - b.y);
        if (pinch.d > 0) that.zoomBy(d / pinch.d, (a.x + b.x) / 2, (a.y + b.y) / 2);
        pinch.d = d;
        return;
      }
      if (drag && Math.hypot(p.x - drag.start.x, p.y - drag.start.y) > CLICK_SLOP) drag.moved = true;
      if (drag && drag.handle) {
        if (drag.moved) drag.handle.drag(that.cam.inv(p.x, p.y), p);
        return;
      }
      if (drag && drag.pan) {
        if (drag.click && !drag.moved) return;          // maybe a click: don't nudge the view yet
        var canPan = that.mode === "world" || that.cam.zoom() > 1.0001;
        if (canPan && (p.x !== drag.last.x || p.y !== drag.last.y)) {
          that.cam.pan(p.x - drag.last.x, p.y - drag.last.y);
          that._changed();
        }
        drag.last = p;
        return;
      }
      var over = that.mode === "world" ? that._hit(p) : null;     // hover feedback
      that.cam.pointer = p;
      var key = over ? over.key || null : null;
      if (key !== that.cam.hoverKey) { that.cam.hoverKey = key; if (that.onChange) that.onChange(); }
      cv.style.cursor = over ? (over.cursor || "grab") : (that.mode === "world" || that.cam.zoom() > 1.0001 ? "move" : "");
      cv.title = over && over.title ? over.title : "";
    });
    var up = function (e) {
      delete pointers[e.pointerId];
      if (Object.keys(pointers).length < 2) pinch = null;
      if (drag && drag.handle) {
        that.dragging = false;
        if (!drag.moved && drag.handle.click) drag.handle.click();
        else {
          if (drag.handle.end) drag.handle.end();
          if (that.onDragEnd) that.onDragEnd();
        }
      } else if (drag && drag.click && !drag.moved && e.type === "pointerup") {
        drag.click.click();
      }
      drag = null;
      cv.style.cursor = "";
    };
    cv.addEventListener("pointerleave", function () {
      that.cam.pointer = null;
      if (that.cam.hoverKey != null) { that.cam.hoverKey = null; if (that.onChange) that.onChange(); }
    });
    cv.addEventListener("pointerup", up);
    cv.addEventListener("pointercancel", up);
  };

  Stage.prototype._activate = function (on) {
    if (this.active === on) return;
    this.active = on;
    this.el.classList.toggle("active", on);
    this.hint.textContent = on ? "scroll or pinch to zoom · drag to pan · double-click to zoom in"
                               : "Ctrl + scroll or pinch to zoom · drag to pan";
  };

  PL.Stage = Stage;
})();
