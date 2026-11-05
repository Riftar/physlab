/* physlab main client: topic picker -> sim view. The engine is the server;
   this panel only fetches /api/run with the current params and plays frames. */
(function () {
  "use strict";

  var app = document.getElementById("app");
  var state = { topics: null, topic: null, result: null, params: {}, frame: 0,
                fprog: 0, playing: false, lastTs: null, raf: null, debounce: null };

  function stopAnim() { cancelAnimationFrame(state.raf); state.playing = false; }

  // playback speed per topic (heat is time-lapsed, others near real-time)
  var SPEED = { circuits: 1, motion: 1, heat: 120 };

  function fetchJSON(url) { return fetch(url).then(function (r) {
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.json();
  }); }

  function showPicker() {
    stopAnim();
    app.innerHTML = "";
    app.appendChild(PL.ui.topicCards(state.topics, openTopic));
  }

  function openTopic(t) {
    state.topic = t;
    state.params = {};
    t.params.forEach(function (p) { state.params[p.id] = p.default; });
    app.innerHTML = "";
    var sim = document.createElement("div"); sim.className = "sim";
    var left = document.createElement("div"); left.className = "panel";
    var back = document.createElement("button"); back.className = "secondary back";
    back.textContent = "← all experiments";
    back.addEventListener("click", showPicker);
    var h2 = document.createElement("h2"); h2.textContent = t.title;
    var hicon = document.createElement("img");
    hicon.className = "hicon"; hicon.src = "icons/icon_" + t.icon + ".png"; hicon.alt = "";
    h2.insertBefore(hicon, h2.firstChild);
    var blurb = document.createElement("div"); blurb.className = "blurb"; blurb.textContent = t.blurb;
    var fpanel = PL.ui.formulaPanel(t.formulas);
    left.appendChild(back); left.appendChild(h2); left.appendChild(blurb);
    var ctlBox = document.createElement("div");
    left.appendChild(ctlBox);
    var right = document.createElement("div");
    var stage = document.createElement("div"); stage.className = "stage";
    var canvas = document.createElement("canvas");
    canvas.id = "stage"; canvas.width = 880; canvas.height = 500;
    stage.appendChild(canvas);
    var playrow = document.createElement("div"); playrow.className = "playrow";
    var play = document.createElement("button"); play.textContent = "▶ run";
    var reset = document.createElement("button"); reset.className = "secondary"; reset.textContent = "↺ reset";
    playrow.appendChild(play); playrow.appendChild(reset);
    var readBox = document.createElement("div");
    right.appendChild(stage); right.appendChild(playrow); right.appendChild(readBox);
    right.appendChild(fpanel.el);
    sim.appendChild(left); sim.appendChild(right);
    app.appendChild(sim);
    var ctx = canvas.getContext("2d");

    function buildControls() {
      ctlBox.innerHTML = "";
      ctlBox.appendChild(PL.ui.controls(t.params, state.params, function (id, v) {
        state.params[id] = v;
        clearTimeout(state.debounce);
        state.debounce = setTimeout(run, 250);
      }));
    }

    function run() {
      var q = Object.keys(state.params).map(function (k) {
        var v = state.params[k];
        return k + "=" + encodeURIComponent(typeof v === "boolean" ? (v ? "1" : "0") : v);
      }).join("&");
      fetchJSON("/api/run?topic=" + t.id + "&" + q).then(function (res) {
        state.result = res;
        state.frame = 0; state.fprog = 0;
        readBox.innerHTML = "";
        readBox.appendChild(PL.ui.readouts(res.readouts));
        fpanel.update(res.formula);
        PL.scenes[t.id].init(ctx, canvas.width, canvas.height, res, state.params);
        playNow();
      }).catch(function (e) {
        readBox.innerHTML = '<div class="blurb">could not run: ' + e.message + "</div>";
      });
    }

    function drawFrame(dt) {
      if (!state.result) return;
      PL.scenes[t.id].render(ctx, canvas.width, canvas.height,
                             state.frame, dt, state.result, state.params);
    }

    function step(ts) {
      if (!state.playing) return;
      if (state.lastTs == null) state.lastTs = ts;
      var dt = Math.min(0.05, (ts - state.lastTs) / 1000);
      state.lastTs = ts;
      var frames = state.result.frames;
      if (state.frame >= frames.length - 1) { playNow(false); drawFrame(0); state.frame = 0; return; }
      var speed = (SPEED[t.id] || 1);
      state.fprog += speed * dt / 0.05;
      var adv = Math.floor(state.fprog);
      state.fprog -= adv;
      state.frame = Math.min(frames.length - 1, state.frame + adv);
      drawFrame(dt);
      state.raf = requestAnimationFrame(step);
    }

    function playNow(on) {
      if (on === undefined) on = true;
      state.playing = on;
      state.lastTs = null;
      play.textContent = on ? "⏸ pause" : "▶ run";
      if (on) { cancelAnimationFrame(state.raf); state.raf = requestAnimationFrame(step); }
    }

    play.addEventListener("click", function () { playNow(!state.playing); });
    reset.addEventListener("click", function () {
      state.frame = 0; state.fprog = 0;
      if (PL.scenes[t.id].init) PL.scenes[t.id].init(ctx, canvas.width, canvas.height, state.result, state.params);
      playNow();
    });

    buildControls();
    run();
    document.title = "physlab - " + t.title;
  }

  fetchJSON("/api/topics").then(function (data) {
    state.topics = data.topics;
    showPicker();
  }).catch(function (e) {
    app.innerHTML = '<div class="loading">could not load topics: ' + e.message + "</div>";
  });
})();
