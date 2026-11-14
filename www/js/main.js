/* physlab main client: topic picker -> experiment page. The engine is the
   server; the page fetches /api/run with the current params and plays
   the frames. Everything an experiment page is made of is a reusable
   component:

     PL.ui.simLayout     page skeleton           (ui.js)
     PL.ui.presetBar     one-click set-ups        (ui.js)
     PL.ui.ComparePanel  A/B compare mode         (ui.js)
     PL.ui.ControlPanel  parameter sliders        (ui.js)
     PL.ui.PlayBar       run / reset / view       (ui.js)
     PL.ui.ResultsPanel  notes + readouts         (ui.js)
     PL.ui.learnPanel    formulas, figures, life  (ui.js)
     PL.Stage            zoomable canvas          (stage.js)
     PL.Player           simulation-time playback (player.js)

   so this file is only routing + gluing them to one parameter model.

   Deep links: #/<topic>?<param>=<v>&b.<param>=<v>&view.<opt>=<v>&at=<s>
     b.*    opens compare mode, B = a copy of A with these overrides
     view.* client-side view options (arrows on/off, ...)
     at     fast-forwards the simulation to that time and pauses there
   The hash follows your changes, so any set-up can be shared; presets
   and "Try this setup" are such links. #/quiz..., #/sandbox... and #/game...
   routes belong to quiz.js, sandbox.js and game.js. When a route has finished
   loading (and seeking), <html data-sim-ready="1">. */
(function () {
  "use strict";

  var app = document.getElementById("app");
  var U = PL.ui;
  var state = { topics: null, page: null };

  function fetchJSON(url) {
    return fetch(url).then(function (r) {
      if (!r.ok) return r.json().catch(function () { return {}; }).then(function (b) {
        throw new Error(b.error || ("HTTP " + r.status));
      });
      return r.json();
    });
  }

  function setReady(on) { document.documentElement.setAttribute("data-sim-ready", on ? "1" : "0"); }

  function closePage() {
    if (state.page) state.page.destroy();
    state.page = null;
  }

  function showPicker() {
    closePage();
    U.clearReturn();
    app.innerHTML = "";
    var cta = U.el("button", "quizcta");
    cta.type = "button";
    cta.appendChild(U.el("span", "qi", "🎯"));
    var txt = U.el("span");
    txt.appendChild(U.el("b", null, "Physics challenges"));
    txt.appendChild(U.el("span", null, " - set the right value and watch the experiment prove it. "
                         + "3 per experiment: easy, medium, hard."));
    cta.appendChild(txt);
    cta.addEventListener("click", function () { location.hash = "#/quiz"; });
    var sb = U.el("button", "quizcta sbcta");
    sb.type = "button";
    sb.appendChild(U.el("span", "qi", "🏖️"));
    var stx = U.el("span");
    stx.appendChild(U.el("b", null, "Sandbox"));
    stx.appendChild(U.el("span", null, " - build your own world from real things: balls, planets, weather, " +
                         "ramps you shape, circuits you wire."));
    sb.appendChild(stx);
    sb.addEventListener("click", function () { location.hash = "#/sandbox"; });
    var gm = U.el("button", "quizcta gamecta");
    gm.type = "button";
    gm.setAttribute("data-testid", "game-cta");
    gm.appendChild(U.el("span", "qi", "🏭"));
    var gtx = U.el("span");
    gtx.appendChild(U.el("b", null, "The Machine Works (game)"));
    gtx.appendChild(U.el("span", null, " - tune a Rube Goldberg machine so the ball gets from A to B. Three halls: " +
                         "rubber, steel and wood."));
    gm.appendChild(gtx);
    gm.addEventListener("click", function () { location.hash = "#/game"; });
    var ctas = U.el("div", "ctas");
    ctas.appendChild(cta); ctas.appendChild(sb); ctas.appendChild(gm);
    app.appendChild(ctas);
    app.appendChild(U.topicCards(state.topics, function (t) { location.hash = "#/" + t.id; }));
    document.title = "physlab - see the formula happen";
    setReady(true);
  }

  function route() {
    var r = PL.route.parse(location.hash);
    if (r && (r.id === "quiz" || r.id.indexOf("quiz/") === 0)) {
      closePage();
      state.page = PL.quiz.open(app, r.id.slice(5));
      return;
    }
    if (r && (r.id === "game" || r.id.indexOf("game/") === 0)) {
      closePage();
      state.page = PL.gameUI.open(app);
      return;
    }
    if (r && (r.id === "sandbox" || r.id.indexOf("sandbox/") === 0)) {
      closePage();
      state.page = PL.sandboxUI.open(app, r.id.slice(8), r, state.topics);
      return;
    }
    var t = r && state.topics.filter(function (x) { return x.id === r.id && x.status === "ready"; })[0];
    if (t) { closePage(); state.page = new SimPage(t, r); } else showPicker();
  }

  function defaults(t) {
    var p = {};
    t.params.forEach(function (x) { p[x.id] = x.default; });
    return p;
  }

  function query(params) {
    return Object.keys(params).map(function (k) {
      var v = params[k];
      return k + "=" + encodeURIComponent(typeof v === "boolean" ? (v ? "1" : "0") : v);
    }).join("&");
  }

  /* ---------------- one experiment page ---------------- */
  function SimPage(t, rt) {
    var that = this, scene = PL.scenes[t.id];
    var model = { sets: [defaults(t)], active: 0, compare: false };
    var view = {}, token = 0, debounce = null;
    var seekTo = rt && isFinite(rt.at) ? rt.at : null;

    // deep-link overrides
    (scene.options || []).forEach(function (o) {
      var want = rt && rt.view[o.id];
      view[o.id] = want != null && o.choices.some(function (c) { return c.id === want; }) ? want : o.default;
    });
    if (rt) {
      t.params.forEach(function (p) { if (rt.a[p.id] != null) model.sets[0][p.id] = PL.route.coerce(p, rt.a[p.id]); });
      if (rt.b && t.compare) {
        model.compare = true; model.active = 1;
        model.sets[1] = JSON.parse(JSON.stringify(model.sets[0]));
        t.params.forEach(function (p) { if (rt.b[p.id] != null) model.sets[1][p.id] = PL.route.coerce(p, rt.b[p.id]); });
      }
    }

    setReady(false);
    window.scrollTo(0, 0);
    document.title = "physlab - " + t.title;

    // components
    var L = U.simLayout(t, function () { location.hash = "#/"; });
    L.left.insertBefore(PL.sandboxUI.modeToggle(t.id, "experiment"), L.left.querySelector("h2"));
    var ret = U.returnBanner();                  // came here from a game station's "Open in the lab"?
    if (ret) L.left.insertBefore(ret, L.left.firstChild);
    var stage = new PL.Stage(880, 500);
    var bar = U.PlayBar(scene.options, view, {
      play: function () { player.toggle(); },
      reset: function () { player.reset(); },
      view: function () { syncHash(); player.redraw(); }
    });
    var player = new PL.Player(stage, scene, bar.setLabel);
    var cmp = U.ComparePanel(t, model, function (kind) {
      ctl.render();
      if (kind !== "tab") run();
    });
    var ctl = U.ControlPanel(t, model, function () { cmp.updateDiff(); schedule(250); });
    var results = U.ResultsPanel();
    var learn = t.learn ? U.learnPanel(t) : U.formulaPanel(t.formulas);

    L.presets.appendChild(U.presetBar(t.learn && t.learn.presets));
    var qlink = U.el("button", "secondary small quizlink", "🎯 Take the " + t.title + " challenges");
    qlink.addEventListener("click", function () { location.hash = "#/quiz"; });
    L.presets.appendChild(qlink);
    L.compare.appendChild(cmp.el);
    L.controls.appendChild(ctl.el);
    L.stage.appendChild(stage.el);
    L.playbar.appendChild(bar.el);
    L.notes.appendChild(results.notes);
    L.results.appendChild(results.readouts);
    L.learn.appendChild(learn.el);
    app.innerHTML = "";
    app.appendChild(L.root);

    // camera moves redraw a paused scene; dragging a scene handle edits params
    stage.onChange = function () { player.redraw(); };
    stage.cam.setParams = function (changes, done) {
      var set = model.sets[model.active];
      Object.keys(changes).forEach(function (k) {
        var p = t.params.filter(function (x) { return x.id === k; })[0];
        if (p) set[k] = PL.route.coerce(p, String(changes[k]));
      });
      ctl.render(); cmp.updateDiff();
      schedule(done ? 0 : 60);
    };

    stage.onDragEnd = function () { schedule(0); };   // re-fit the view once the drag is over

    function syncHash() {
      var h = PL.route.hash(t, model.sets, view, scene.options);
      if (h !== location.hash) history.replaceState(null, "", h);
    }

    function schedule(ms) {
      clearTimeout(debounce);
      debounce = setTimeout(run, ms);
    }

    function run() {
      var my = ++token, sets = model.sets.slice();
      syncHash();
      Promise.all(sets.map(function (p) {
        return fetchJSON("/api/run?topic=" + t.id + "&" + query(p));
      })).then(function (out) {
        if (my !== token) return;                 // a newer request superseded this one
        var runs = out.map(function (res, i) {
          return { result: res, params: res.params, color: U.RUN_COLORS[i],
                   label: sets.length > 1 ? U.RUN_LABELS[i] : "" };
        });
        results.update(runs, cmp.noun);
        learn.update(runs.length > 1 ? runs.map(function (r) {
          return { label: r.label, color: r.color, formula: r.result.formula };
        }) : runs[0].result.formula);
        var seek = seekTo;
        seekTo = null;                            // only the first run of a deep link seeks
        player.load(runs, view, { seek: seek, keepView: true });
        setReady(true);
      }).catch(function (e) {
        if (my !== token) return;
        results.error(e.message);
      });
    }

    this.destroy = function () {
      token++;
      clearTimeout(debounce);
      player.stop();
    };

    cmp.render();
    ctl.render();
    run();
    that.model = model;
    PL.current = { topic: t, model: model, stage: stage, player: player };   // for devtools and tests
  }

  fetchJSON("/api/topics").then(function (data) {
    state.topics = data.topics;
    PL.topics = data.topics;
    window.addEventListener("hashchange", route);
    route();
  }).catch(function (e) {
    app.innerHTML = '<div class="loading">could not load topics: ' + e.message + "</div>";
  });
})();
