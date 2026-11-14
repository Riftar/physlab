/* physlab GAME pages - The Machine Works (docs/game/GDD-machine-works.md).

     #/game                                   the map: who's playing, the halls
     #/game/<hall>[/<station>]                a hall; the station in focus
         ?practice=1&v=<0-4>                  practice mode: nothing saved, that variant
         &k=<knobs JSON>                      preload the focused station's settings
         &debug=1                             open the test bench

   The server runs and judges everything (POST /api/game/run); this page
   shows the hall (PL.scenes.game on a PL.Stage), the station card, the
   knobs, hints, the debrief and the scores. The knobs are generated from the
   station's knob specs and snapped with PL.game.knobValue - the same rule
   the server applies - so what the slider shows is what runs.

   Layout: the left panel is for reading (stations, the card, hints, scores);
   the settings and the ▶ Test station / ▶▶ Run machine buttons sit in a dock
   right under the stage, next to the machine they change. There is no
   run/reset play bar: a run plays as soon as it arrives (run it again to
   replay); under the stage are only the speed and the camera.

   Camera: 📍 station (fits the station) · 🎥 follow (glides with the ball;
   the default) · 🏭 whole hall. Scores: every working run scores 0-1000;
   the best per station is kept, with a top-5 of the players on this machine.
   Halls open one after another: a hall opens when every station of the one
   before it works.

   Navigation: every station's settings are remembered for this browser tab
   (sessionStorage), so leaving for the lab and coming back keeps them; the
   lab pages show "Back to the Machine Works". The share box makes a link
   that opens the station with the same settings AND the same numbers, in
   practice mode.

   Testability: every knob control has data-knob="<station>.<knob>", buttons
   have data-testid, and PL.current.game exposes the page to scripts:
     setKnob(station, knob, value)  select(station)  test()  machine()
     hint(tier)  camera(mode)  state  lastResult  hash()  shareUrl()
   <html data-sim-ready="1"> is set whenever the page is settled. The player
   is the quiz's (same localStorage key, same players table). */
(function () {
  "use strict";
  var U = PL.ui, E = U.el;
  var KEY = "physlab.player";

  function request(method, url, body) {
    return fetch(url, body ? { method: method, headers: { "Content-Type": "application/json" },
                               body: JSON.stringify(body) } : { method: method })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (j) {
          if (!r.ok) { var e = new Error(j.error || ("HTTP " + r.status)); e.code = r.status; throw e; }
          return j;
        });
      });
  }
  var api = {
    get: function (u) { return request("GET", u); },
    post: function (u, b) { return request("POST", u, b); },
    playerId: function () { try { return localStorage.getItem(KEY) || ""; } catch (e) { return ""; } },
    setPlayer: function (id) { try { if (id) localStorage.setItem(KEY, id); else localStorage.removeItem(KEY); } catch (e) {} }
  };

  /* this tab's memory of every station's settings (per hall, per player or practice variant) */
  var memory = {
    key: function (hall, who) { return "physlab.game." + hall + "." + who; },
    load: function (hall, who) {
      try { return JSON.parse(sessionStorage.getItem(this.key(hall, who)) || "null") || {}; } catch (e) { return {}; }
    },
    save: function (hall, who, data) {
      try { sessionStorage.setItem(this.key(hall, who), JSON.stringify(data)); } catch (e) {}
    }
  };

  /* copy text; falls back to selecting it when the clipboard API is not allowed (plain http on a LAN) */
  function copyText(text, input) {
    function fallback() {
      if (!input) return Promise.resolve(false);
      input.focus(); input.select();
      var ok = false;
      try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
      return Promise.resolve(ok);
    }
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text).then(function () { return true; }, fallback);
    }
    return fallback();
  }

  function setReady(on) { document.documentElement.setAttribute("data-sim-ready", on ? "1" : "0"); }
  function stars(list) {
    var have = list || [];
    return ["works", "efficient", "mastery"].map(function (s) { return have.indexOf(s) >= 0 ? "★" : "☆"; }).join("");
  }
  var STAR_NAME = { works: "★ It works", efficient: "★ Efficient", mastery: "★ Mastery" };
  var SPRITE = { bounce: "toybox", foundry: "ladle", mill: "millstone" };

  /* ---------------- who's playing (same players as the quiz) ---------------- */
  function playerBar(player, score, onChange, practice) {
    var box = E("div", "gplayer");
    if (player) {
      box.appendChild(E("div", "qwho", "Playing as " + player.name + " · " + score + " ★ points"));
      var sw = E("button", "secondary small", "switch player");
      sw.type = "button"; sw.setAttribute("data-testid", "switch-player");
      sw.addEventListener("click", function () { api.setPlayer(""); onChange(); });
      box.appendChild(sw);
      return box;
    }
    if (practice && practice.storedName) {          // a player exists on this computer: practice is a choice
      box.appendChild(E("div", "qwho", "🎯 Practice mode (variant " + practice.variant + ")"));
      box.appendChild(E("div", "sbdesc", "Try anything - nothing is saved, no stars, no scores, your runs aren't counted."));
      var back = E("button", "small", "← Back to playing as " + practice.storedName);
      back.type = "button"; back.setAttribute("data-testid", "leave-practice");
      back.addEventListener("click", practice.leave);
      box.appendChild(back);
      return box;
    }
    box.appendChild(E("div", "qwho", practice ? "🎯 Practice mode (variant " + practice.variant + "): nothing is saved. " +
                      "Pick a player to earn stars and scores:" : "Who's playing? (or just try it: practice mode saves nothing)"));
    var form = E("form", "qname");
    var inp = E("input"); inp.type = "text"; inp.maxLength = 24; inp.placeholder = "your name"; inp.required = true;
    inp.setAttribute("data-testid", "player-name");
    var go = E("button", null, "Start"); go.setAttribute("data-testid", "player-start");
    form.appendChild(inp); form.appendChild(go);
    var err = E("div", "qerr");
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      api.post("/api/quiz/player", { name: inp.value }).then(function (r) { api.setPlayer(r.player.id); onChange(); })
        .catch(function (x) { err.textContent = x.message; });
    });
    box.appendChild(form); box.appendChild(err);
    api.get("/api/quiz/players").then(function (r) {
      if (!r.players.length) return;
      var rec = E("div", "qrecent");
      rec.appendChild(E("span", null, "or continue as: "));
      r.players.slice(0, 6).forEach(function (pl) {
        var b = E("button", "chip", pl.name);
        b.type = "button";
        b.addEventListener("click", function () { api.setPlayer(pl.id); onChange(); });
        rec.appendChild(b);
      });
      box.appendChild(rec);
    }).catch(function () {});
    return box;
  }

  /* ---------------- #/game: the map of halls ---------------- */
  function Hub(app) {
    var alive = true;
    function load() {
      setReady(false);
      api.get("/api/game?player=" + encodeURIComponent(api.playerId())).then(function (data) {
        if (!alive) return;
        if (!data.player && api.playerId()) api.setPlayer("");
        app.innerHTML = "";
        var head = E("div", "sbhead");
        var back = E("button", "secondary back", "← experiments");
        back.addEventListener("click", function () { location.hash = "#/"; });
        head.appendChild(back);
        head.appendChild(E("h2", null, "🏭 The Machine Works"));
        head.appendChild(E("p", "blurb", "The Great Sorter is jammed! Each hall was built for one kind of ball. You " +
          "can't touch the ball - tune the machine (hatches, salt, springs, kettles, batteries, fans, lenses...), press run, and let physics do " +
          "the rest. Every station has three stars and a score out of 1000 to beat. Clear every station of a hall " +
          "to open the next one."));
        head.appendChild(playerBar(data.player, data.score, load, null));
        if (!data.locks) {
          var tm = E("div", "gtestmode", "🧪 Test mode: every hall and every station is open - no need to clear the " +
                     "hall before. (For the classroom order, start the server with PHYSLAB_GAME_LOCKS=on.)");
          tm.setAttribute("data-testid", "test-mode");
          head.appendChild(tm);
        }
        app.appendChild(head);
        var grid = E("div", "cards");
        data.halls.forEach(function (h, i) {
          var ready = h.status === "ready", open = ready && h.unlocked;
          var c = E("div", "card hallcard " + (open ? "ready" : "placeholder") + (h.cleared ? " cleared" : ""));
          c.setAttribute("data-hall", h.id);
          c.setAttribute("data-state", !h.unlocked ? "locked" : ready ? "open" : "unlocked-soon");
          var img = E("img", "ticon"); img.src = "sprites/item_" + (SPRITE[h.id] || "gizmo") + ".png"; img.alt = "";
          c.appendChild(img);
          c.appendChild(E("h3", null, (i + 1) + ". " + h.title + (h.unlocked ? "" : " 🔒")));
          c.appendChild(E("p", null, h.blurb));
          if (!h.unlocked) {
            c.appendChild(E("div", "status soon", "🔒 LOCKED · " + h.requires));
            if (ready && !data.player) {                       // nobody playing: it can still be tried in practice
              c.appendChild(E("div", "formula-preview", "click to try it in practice mode"));
              c.addEventListener("click", function () { location.hash = "#/game/" + h.id + "?practice=1"; });
            }
          } else if (!ready) {
            c.appendChild(E("div", "status soon", "🔓 UNLOCKED! The " + h.ball + " ball's hall is still being built - coming soon."));
          } else {
            var got = 0;
            h.stations.forEach(function (s) { got += s.stars.length; });
            c.appendChild(E("div", "status ready", (h.cleared ? "🏁 CLEARED · " : "● ") + got + " / " + 3 * h.stations.length +
                            " stars" + (h.golden ? " · ★ Golden Run" : "")));
            if (data.player) c.appendChild(E("div", "hallscore", "🏆 hall score " + h.score + " / " + h.max_score));
            c.appendChild(E("div", "formula-preview", h.stations.map(function (s) {
              return s.id + " " + stars(s.stars) + (s.best != null ? " " + s.best : "");
            }).join("  ")));
            c.addEventListener("click", function () { location.hash = "#/game/" + h.id; });
          }
          grid.appendChild(c);
        });
        app.appendChild(grid);
        document.title = "physlab - The Machine Works";
        setReady(true);
      }).catch(function (e) {
        app.innerHTML = '<div class="loading">could not load the game: ' + e.message + "</div>";
      });
    }
    load();
    return { destroy: function () { alive = false; } };
  }

  /* ---------------- #/game/<hall>: a hall ---------------- */
  function HallPage(app, rt) {
    var alive = true, token = 0;
    var stored = api.playerId();
    var pid = rt.practice ? "" : stored;
    var state = { hall: null, stations: {}, order: [], knobs: {}, focus: rt.station, last: null, ghost: null,
                  camera: "follow", followSnap: true, practice: true, variant: rt.v == null ? 2 : rt.v,
                  player: null, score: 0, debug: rt.debug, prediction: null, busy: false, lastRequest: null,
                  cleared: false, nextHall: null, storedName: null };
    var view = { pace: "1" }, stage, player, dom = {};

    setReady(false);
    U.clearReturn();                                    // we're back in the game
    app.innerHTML = '<div class="loading">loading the hall…</div>';
    var q = "/api/game/hall?id=" + encodeURIComponent(rt.hall) +
            (pid ? "&player=" + encodeURIComponent(pid) : (rt.v != null ? "&v=" + rt.v : ""));
    var named = rt.practice && stored ? api.get("/api/game?player=" + encodeURIComponent(stored))
      .then(function (d) { return d.player ? d.player.name : null; }).catch(function () { return null; }) : Promise.resolve(null);
    Promise.all([api.get(q), named]).then(function (both) {
      var data = both[0];
      if (!alive) return;
      state.storedName = both[1];
      state.hall = data.hall; state.practice = data.practice; state.player = data.player; state.score = data.score;
      state.cleared = data.cleared; state.nextHall = data.next_hall;
      if (data.practice && data.variant != null) state.variant = data.variant;
      data.stations.forEach(function (s) { state.stations[s.id] = s; state.order.push(s.id); });
      var mem = memory.load(state.hall.id, who());
      if (!rt.station && mem.focus && state.stations[mem.focus]) state.focus = mem.focus;
      if (!state.stations[state.focus]) state.focus = firstOpen();
      if (mem.camera) state.camera = mem.camera;
      state.order.forEach(function (sid) {
        var s = state.stations[sid], saved = s.progress && s.progress.last_knobs;
        var remembered = (mem.knobs || {})[sid];
        state.knobs[sid] = PL.game.knobsFrom(s.knobs, sid === state.focus && rt.knobs ? rt.knobs : remembered || saved);
      });
      build();
    }).catch(function (e) {
      if (!alive) return;
      if (e.code === 404 && pid && /player/.test(e.message)) { api.setPlayer(""); location.reload(); return; }
      app.innerHTML = "";
      var box = E("div", "sbhead");
      var back = E("button", "secondary back", "← the Machine Works");
      back.addEventListener("click", function () { location.hash = "#/game"; });
      box.appendChild(back);
      box.appendChild(E("h2", null, e.code === 403 ? "🔒 Not open yet" : "Can't open this hall"));
      box.appendChild(E("p", "blurb", e.message));
      app.appendChild(box);
      setReady(true);
    });

    function who() { return state.practice ? "practice-" + state.variant : (state.player ? state.player.id : "anon"); }
    function remember() {
      memory.save(state.hall.id, who(), { knobs: state.knobs, focus: state.focus, camera: state.camera });
    }

    function firstOpen() {
      var open = state.order.filter(function (sid) {
        var s = state.stations[sid];
        return s.unlocked && !(s.progress && s.progress.stars.indexOf("works") >= 0);
      });
      return open[0] || state.order[0];
    }

    function hash() {
      return PL.game.hash({ hall: state.hall.id, station: state.focus, practice: state.practice, v: state.variant,
                            knobs: state.knobs[state.focus], debug: state.debug });
    }
    function syncHash() { var h = hash(); if (h !== location.hash) history.replaceState(null, "", h); }
    /* the shareable link: this station, these settings, THESE numbers (the variant), practice mode */
    function shareHash() {
      return PL.game.hash({ hall: state.hall.id, station: state.focus, practice: true,
                            v: state.stations[state.focus].variant_step, knobs: state.knobs[state.focus] });
    }
    function shareUrl() { return location.href.split("#")[0] + shareHash(); }

    /* ---------- layout ---------- */
    function build() {
      app.innerHTML = "";
      var root = E("div", "sim game");
      var left = E("div", "panel gpanel"), right = E("div");
      var back = E("button", "secondary back", "← Machine Works map");
      back.addEventListener("click", function () { location.hash = "#/game"; });
      left.appendChild(back);
      left.appendChild(E("h2", null, "🏭 " + state.hall.title));
      left.appendChild(E("div", "blurb", state.hall.blurb));
      dom.who = E("div"); left.appendChild(dom.who);
      dom.cleared = E("div"); left.appendChild(dom.cleared);
      dom.list = E("div", "gstations"); left.appendChild(dom.list);
      dom.card = E("div", "gcard"); left.appendChild(dom.card);
      dom.hints = E("div", "ghints"); left.appendChild(dom.hints);
      dom.scores = E("div", "gscores"); left.appendChild(dom.scores);

      // the stage, its view controls (speed, camera) and, right under it, the settings and the run buttons:
      // the knobs sit next to the machine they change
      stage = new PL.Stage(880, 500);
      player = new PL.Player(stage, PL.scenes.game, function () {});
      right.appendChild(stage.el);
      var pb = E("div", "gplaybar");
      PL.scenes.game.options.forEach(function (o) {
        pb.appendChild(U.segmented(o, view[o.id], function (v) { view[o.id] = v; player.redraw(); }));
      });
      dom.camera = E("div", "seg gcam"); pb.appendChild(dom.camera);
      right.appendChild(pb);
      var dock = E("div", "gdock"); dock.setAttribute("data-testid", "game-dock");
      dom.knobs = E("div", "gknobs"); dock.appendChild(dom.knobs);
      var act = E("div", "gactions");
      dom.predict = E("div", "gpredict"); act.appendChild(dom.predict);
      var row = E("div", "gbuttons");
      dom.test = E("button", null, "▶ Test station"); dom.test.type = "button"; dom.test.setAttribute("data-testid", "test-station");
      dom.machine = E("button", "secondary", "▶▶ Run machine"); dom.machine.type = "button";
      dom.machine.setAttribute("data-testid", "run-machine");
      dom.test.addEventListener("click", function () { runTest(); });
      dom.machine.addEventListener("click", function () { runMachine(); });
      row.appendChild(dom.test); row.appendChild(dom.machine);
      act.appendChild(row);
      dock.appendChild(act);
      right.appendChild(dock);
      dom.debrief = E("div", "gdebrief"); right.appendChild(dom.debrief);
      dom.share = E("div", "gshare"); right.appendChild(dom.share);
      dom.bench = E("details", "gbench"); right.appendChild(dom.bench);
      root.appendChild(left); root.appendChild(right);
      app.appendChild(root);

      stage.onChange = function () { player.redraw(); };
      stage.cam.setParams = function (changes) {
        Object.keys(changes).forEach(function (key) {
          var j = key.lastIndexOf(".");
          if (j <= 0 || key.indexOf(".") === j) return;
          setKnob(key.slice(0, j), key.slice(j + 1), changes[key], true);
        });
      };
      renderAll();
      show(null);
      document.title = "physlab - " + state.hall.title;
      setReady(true);
    }

    function renderAll() {
      renderWho(); renderCleared(); renderList(); renderCard(); renderKnobs(); renderPredict(); renderHints();
      renderCamera(); renderShare(); renderBench();
    }

    function renderWho() {
      dom.who.innerHTML = "";
      var practice = state.practice ? {
        variant: state.variant, storedName: state.storedName,
        leave: function () {
          U.goRoute(PL.game.hash({ hall: state.hall.id, station: state.focus, knobs: state.knobs[state.focus] }));
        }
      } : null;
      dom.who.appendChild(playerBar(state.player, state.score, function () {
        U.goRoute(PL.game.hash({ hall: state.hall.id, station: state.focus, knobs: state.knobs[state.focus] }));
      }, practice));
    }

    function renderCleared() {
      dom.cleared.innerHTML = "";
      if (state.cleared && !state.nextHall) {             // the last hall: the whole Machine Works
        var fin = E("div", "gcleared", "🏁 You cleared the last hall - the whole Machine Works runs again! Chase your " +
                    "scores and the Golden Runs.");
        fin.setAttribute("data-testid", "hall-cleared");
        dom.cleared.appendChild(fin);
        return;
      }
      if (!state.cleared || !state.nextHall) return;
      var b = E("div", "gcleared");
      b.setAttribute("data-testid", "hall-cleared");
      b.appendChild(E("b", null, "🏁 Hall cleared! "));
      b.appendChild(document.createTextNode(state.nextHall.status === "ready"
        ? state.nextHall.title + " is open."
        : state.nextHall.title + " is unlocked - it's still being built (coming soon). Chase your scores meanwhile!"));
      if (state.nextHall.status === "ready") {
        var go = E("button", "small", "→ go to " + state.nextHall.title); go.type = "button";
        go.addEventListener("click", function () { location.hash = "#/game/" + state.nextHall.id; });
        b.appendChild(go);
      }
      dom.cleared.appendChild(b);
    }

    function renderList() {
      dom.list.innerHTML = "";
      state.order.forEach(function (sid) {
        var s = state.stations[sid], on = sid === state.focus, locked = !s.unlocked;
        var b = E("button", "gst" + (on ? " on" : "") + (locked ? " locked" : ""));
        b.type = "button"; b.setAttribute("data-station", sid);
        b.appendChild(E("span", "gsn", sid));
        b.appendChild(E("span", "gst-t", s.title));
        var best = s.progress && s.progress.best;
        if (!locked && best != null) b.appendChild(E("span", "gbest", "🏆 " + best));
        b.appendChild(E("span", "gstars", locked ? "🔒" : stars(s.progress && s.progress.stars)));
        b.title = locked ? "get the station before working first" : s.goal;
        b.addEventListener("click", function () { select(sid); });
        dom.list.appendChild(b);
      });
    }

    function leaderboard(s) {
      var box = E("div", "glead");
      box.appendChild(E("div", "gleadh", "Top scores on this computer"));
      if (!s.leaderboard || !s.leaderboard.length) {
        box.appendChild(E("div", "sbdesc", "No scores yet - be the first!"));
        return box;
      }
      var t = E("table", "gfacts");
      s.leaderboard.forEach(function (r, i) {
        var me = state.player && r.player_id === state.player.id;
        var tr = E("tr", me ? "me" : null);
        tr.appendChild(E("td", null, (i + 1) + ". " + r.name + (me ? " (you)" : "")));
        tr.appendChild(E("td", null, String(r.best)));
        t.appendChild(tr);
      });
      box.appendChild(t);
      if (s.rank && s.rank.rank > s.leaderboard.length) {
        box.appendChild(E("div", "sbdesc", "You: #" + s.rank.rank + " of " + s.rank.of + " with " + s.progress.best));
      }
      return box;
    }

    function renderCard() {
      var s = state.stations[state.focus];
      dom.card.innerHTML = "";
      dom.card.appendChild(E("h3", null, s.id + " " + s.title));
      dom.card.appendChild(E("p", null, s.intro));
      var goal = E("p", "ggoal"); goal.appendChild(E("b", null, "Goal: ")); goal.appendChild(document.createTextNode(s.goal));
      dom.card.appendChild(goal);
      dom.card.appendChild(E("p", "ghook", "🧪 " + s.hook));
      var t = E("table", "gfacts");
      s.facts.forEach(function (f) {
        var tr = E("tr"); tr.setAttribute("data-fact", s.id + "." + f.id);
        tr.appendChild(E("td", null, f.label));
        tr.appendChild(E("td", null, (+f.value).toString() + (f.unit ? " " + f.unit : "")));
        t.appendChild(tr);
      });
      dom.card.appendChild(t);
      if (s.table) {
        var det = E("details", "gtablebox");
        det.appendChild(E("summary", null, "📊 " + s.table.title));
        var tb = E("table", "gfacts gtable");
        s.table.rows.forEach(function (r) {
          var un = s.table.units || ["", ""], tr = E("tr");
          tr.appendChild(E("td", null, r[0] + (un[0] ? " " + un[0] : "")));
          tr.appendChild(E("td", null, r[1] + (un[1] ? " " + un[1] : "")));
          tb.appendChild(tr);
        });
        det.appendChild(tb);
        dom.card.appendChild(det);
      }
      dom.card.appendChild(E("p", "gmastery", "★★★ " + s.mastery));
      dom.card.appendChild(E("p", "gpar", "★★ Efficient: make it work within " + s.par + " runs of this station, no formula/blueprint hint."));
      renderScores();
    }

    /* the station's score rule, the player's best and the top-5 on this computer */
    function renderScores() {
      var s = state.stations[state.focus];
      dom.scores.innerHTML = "";
      var head = E("div", "plabel", "🏆 Score" + (s.progress && s.progress.best != null ? " · your best: " + s.progress.best : ""));
      dom.scores.appendChild(head);
      var sc = E("div", "gscorerule"); sc.setAttribute("data-testid", "score-rule");
      sc.textContent = s.score_rule;
      dom.scores.appendChild(sc);
      dom.scores.appendChild(leaderboard(s));
    }

    function renderKnobs() {
      var s = state.stations[state.focus], k = state.knobs[state.focus];
      dom.knobs.innerHTML = "";
      dom.knobs.appendChild(E("div", "plabel", "🎛️ Your settings · " + s.id + " " + s.title));
      s.knobs.forEach(function (spec) {
        var row = E("div", "control gknob");
        row.setAttribute("data-knob-row", s.id + "." + spec.id);
        row.appendChild(E("label", null, spec.label));
        if (spec.kind === "choice") {
          var chips = E("div", "sbchips");
          spec.choices.forEach(function (c) {
            var b = E("button", "sbchip" + (k[spec.id] === c.id ? " on" : ""), (c.icon ? c.icon + " " : "") + c.label);
            b.type = "button"; b.title = c.desc || "";
            b.setAttribute("data-knob", s.id + "." + spec.id); b.setAttribute("data-id", c.id);
            b.addEventListener("click", function () { setKnob(s.id, spec.id, c.id); });
            chips.appendChild(b);
          });
          row.appendChild(chips);
          var sel = spec.choices.filter(function (c) { return c.id === k[spec.id]; })[0];
          if (sel && sel.desc) row.appendChild(E("div", "sbdesc", sel.desc));
        } else {
          var pair = E("div", "gpair");
          var rng = E("input"); rng.type = "range"; rng.min = spec.min; rng.max = spec.max; rng.step = spec.step;
          rng.value = k[spec.id]; rng.setAttribute("data-knob", s.id + "." + spec.id);
          var box = E("input", "gnum"); box.type = "number"; box.min = spec.min; box.max = spec.max; box.step = spec.step;
          box.value = k[spec.id]; box.setAttribute("data-knob-input", s.id + "." + spec.id);
          box.setAttribute("aria-label", spec.label);
          rng.addEventListener("input", function () { setKnob(s.id, spec.id, +rng.value, false, true); box.value = state.knobs[s.id][spec.id]; });
          box.addEventListener("change", function () { setKnob(s.id, spec.id, box.value); });
          pair.appendChild(rng); pair.appendChild(box); pair.appendChild(E("span", "gunit", spec.unit || ""));
          row.appendChild(pair);
          row.appendChild(E("div", "sbdesc", spec.min + " – " + spec.max + " " + (spec.unit || "") +
                            (spec.kind === "number" ? ", steps of " + spec.step : "")));
        }
        dom.knobs.appendChild(row);
      });
    }

    function renderPredict() {
      var s = state.stations[state.focus], pr = s.predict;
      dom.predict.innerHTML = "";
      var first = state.practice || !(s.progress && s.progress.runs);
      if (!first) return;
      dom.predict.appendChild(E("div", "plabel", "🔮 Predict first (optional, +5 points if you're close)"));
      var row = E("div", "gpair");
      row.appendChild(E("span", "gplabel", pr.label));
      if (pr.kind === "boolean") {
        [["yes", true], ["no", false]].forEach(function (c) {
          var b = E("button", "sbchip" + (state.prediction === c[1] ? " on" : ""), c[0]);
          b.type = "button"; b.setAttribute("data-testid", "predict-" + c[0]);
          b.addEventListener("click", function () { state.prediction = state.prediction === c[1] ? null : c[1]; renderPredict(); });
          row.appendChild(b);
        });
      } else {
        var inp = E("input", "gnum"); inp.type = "number"; inp.step = "any"; inp.setAttribute("data-testid", "predict-value");
        inp.value = state.prediction == null ? "" : state.prediction;
        inp.addEventListener("change", function () { var v = parseFloat(inp.value); state.prediction = isFinite(v) ? v : null; });
        row.appendChild(inp); row.appendChild(E("span", "gunit", pr.unit));
      }
      dom.predict.appendChild(row);
      dom.predict.appendChild(E("div", "sbdesc", "Counts only before your first run of this station."));
    }

    function renderHints() {
      var s = state.stations[state.focus];
      dom.hints.innerHTML = "";
      var row = E("div", "chips");
      [[1, "💡 Nudge"], [2, "💡 Formula"], [3, "🗺️ Blueprint"]].forEach(function (h) {
        var b = E("button", "chip", h[1]); b.type = "button"; b.setAttribute("data-testid", "hint-" + h[0]);
        var failed = s.progress ? s.progress.failed : 0;
        if (h[0] === 3 && (state.practice || failed < 2)) { b.disabled = true; b.title = state.practice ? "no Blueprints in practice mode" : "opens after 2 runs that didn't work"; }
        b.addEventListener("click", function () { hint(h[0]); });
        row.appendChild(b);
      });
      dom.hints.appendChild(row);
      dom.hintText = E("div", "ghint"); dom.hints.appendChild(dom.hintText);
    }

    function renderCamera() {
      dom.camera.innerHTML = "";
      dom.camera.appendChild(E("span", "seg-label", "Camera"));
      [["station", "📍 station", "show the whole station"], ["follow", "🎥 follow ball", "the camera travels with the ball"],
       ["hall", "🏭 whole hall", "see the whole machine"]].forEach(function (c) {
        var b = E("button", "seg-btn" + (state.camera === c[0] ? " on" : ""), c[1]);
        b.type = "button"; b.title = c[2]; b.setAttribute("data-testid", "camera-" + c[0]);
        b.addEventListener("click", function () { setCamera(c[0]); });
        dom.camera.appendChild(b);
      });
    }

    /* the share box: a clear, working link to exactly this setup */
    function renderShare() {
      var s = state.stations[state.focus];
      dom.share.innerHTML = "";
      dom.share.appendChild(E("div", "plabel", "🔗 Share this setup"));
      dom.share.appendChild(E("div", "sbdesc", "A link that opens " + s.id + " " + s.title + " with these settings and " +
        "these station numbers, in practice mode (nothing is saved for whoever opens it). Paste it in a message, a " +
        "worksheet or your notes - or send it to your teacher."));
      var row = E("div", "gpair");
      var inp = E("input", "glink"); inp.type = "text"; inp.readOnly = true; inp.value = shareUrl();
      inp.setAttribute("data-testid", "share-url");
      inp.addEventListener("focus", function () { inp.select(); });
      var cp = E("button", "small", "📋 Copy link"); cp.type = "button"; cp.setAttribute("data-testid", "copy-link");
      var msg = E("div", "gcopied"); msg.setAttribute("data-testid", "copy-status");
      cp.addEventListener("click", function () {
        inp.value = shareUrl();
        copyText(inp.value, inp).then(function (ok) {
          msg.textContent = ok ? "✓ Copied! Paste it anywhere with Ctrl+V (⌘V on a Mac)."
                               : "The link is selected - press Ctrl+C (⌘C on a Mac) to copy it.";
          msg.className = "gcopied " + (ok ? "ok" : "warn");
        });
      });
      row.appendChild(inp); row.appendChild(cp);
      dom.share.appendChild(row);
      dom.share.appendChild(msg);
      var acts = E("div", "chips gsharebtns");
      if (!state.practice) {
        var pr = E("button", "chip", "🎯 Try ideas in practice mode"); pr.type = "button";
        pr.setAttribute("data-testid", "open-practice");
        pr.title = "experiment without using up your runs - nothing is saved";
        pr.addEventListener("click", function () { U.goRoute(shareHash()); });
        acts.appendChild(pr);
        acts.appendChild(E("span", "sbdesc", "Practice mode lets you experiment without using up your runs (no stars, no scores)."));
      }
      dom.share.appendChild(acts);
    }

    function renderBench() {
      var s = state.stations[state.focus];
      dom.bench.innerHTML = "";
      dom.bench.open = !!state.debug;
      dom.bench.appendChild(E("summary", null, "🧪 Test bench (for testers)"));
      var pre = E("pre", "gjson");
      var info = { station: s.id, mode: state.practice ? "practice" : "player", variant_step: s.variant_step,
                   facts: s.fact_values, knobs: state.knobs[s.id], camera: state.camera, this_page: hash(),
                   share_link: shareHash() };
      if (state.last) {
        info.last_run = { mode: state.last.mode, ok: state.last.ok,
          stations: state.last.stations.map(function (r) {
            return { id: r.id, ok: r.ok, score: r.score, metric: r.metric, unit: r.unit, mastery: r.mastery, reason: r.reason,
                     knobs: r.knobs, new_stars: r.new_stars, insight: r.insight, t: [r.t0, r.t1] };
          }) };
      }
      if (state.lastRequest) info.last_request = state.lastRequest;
      pre.textContent = JSON.stringify(info, null, 1);
      dom.bench.appendChild(pre);
    }

    /* ---------- state changes ---------- */
    function setKnob(sid, kid, value, fromStage, live) {
      var s = state.stations[sid];
      if (!s) return;
      var spec = s.knobs.filter(function (k) { return k.id === kid; })[0];
      if (!spec) return;
      var v = PL.game.knobValue(spec, value);
      if (state.knobs[sid][kid] === v) return;
      state.knobs[sid][kid] = v;
      if (sid !== state.focus) select(sid);
      if (state.last && state.last.mode === "test" && state.last.stations[0].id === sid) {
        state.ghost = player.runs ? player.runs[0].result.frames : null;     // keep the last path, faint
        state.last = null;
        show(null);
      }
      if (!live || fromStage) renderKnobs();
      else {
        var box = dom.knobs.querySelector('[data-knob-input="' + sid + "." + kid + '"]');
        if (box) box.value = v;
      }
      var link = dom.share.querySelector(".glink");
      if (link) link.value = shareUrl();
      renderBench();
      syncHash(); remember();
      player.redraw();
    }

    function select(sid) {
      if (!state.stations[sid]) return;
      state.focus = sid; state.prediction = null; state.ghost = null;
      state.last = null;                                  // the stage shows the new station from its start
      renderList(); renderCard(); renderKnobs(); renderPredict(); renderHints(); renderShare(); renderBench();
      if (dom.hintText) dom.hintText.textContent = "";
      syncHash(); remember();
      show(null);
    }

    function setCamera(mode) {
      state.camera = mode; state.followSnap = true;
      renderCamera(); remember();
      if (player.runs) { stage.setScene(PL.scenes.game, player.runs, false); player.redraw(); }
    }

    /* load frames into the player (null: just the hall with the ball at the start); slow
       physics comes with time-lapse zones the scene plays faster */
    function show(frames, timelapse) {
      state.followSnap = true;
      player.load([{ result: { frames: frames || [], timelapse: timelapse || [] }, st: state }], view,
                  { keepView: false, paused: !frames });
    }

    function body(mode) {
      var b = { hall: state.hall.id, mode: mode, knobs: {} };
      if (state.player) b.player = state.player.id; else b.v = state.variant;
      if (mode === "test") {
        b.station = state.focus; b.knobs[state.focus] = state.knobs[state.focus];
        var s = state.stations[state.focus];
        if (state.prediction != null && (state.practice || !(s.progress && s.progress.runs))) b.prediction = state.prediction;
      } else {
        state.order.forEach(function (sid) { b.knobs[sid] = state.knobs[sid]; });
      }
      return b;
    }

    function send(mode) {
      if (state.busy) return Promise.resolve(null);
      var my = ++token, b = body(mode);
      state.busy = true; setReady(false);
      state.lastRequest = b;
      dom.test.disabled = dom.machine.disabled = true;
      dom.debrief.innerHTML = ""; dom.debrief.appendChild(E("div", "blurb", "⏳ running the physics…"));
      return api.post("/api/game/run", b).then(function (out) {
        if (my !== token || !alive) return null;
        state.busy = false; dom.test.disabled = dom.machine.disabled = false;
        state.ghost = player.runs && player.runs[0].result.frames.length ? player.runs[0].result.frames : null;
        state.last = out; state.score = out.score;
        out.stations.forEach(function (r) {
          var s = state.stations[r.id];
          if (r.progress) s.progress = r.progress;
          if (r.leaderboard) s.leaderboard = r.leaderboard;
          if (r.rank) s.rank = r.rank;
        });
        state.order.forEach(function (sid, i) {               // the next station opens once this one works
          var prev = state.order[i - 1];
          if (prev && state.stations[prev].progress && state.stations[prev].progress.stars.indexOf("works") >= 0) {
            state.stations[sid].unlocked = true;
          }
        });
        if (out.next_hall) state.nextHall = out.next_hall;
        if (out.hall_cleared_new) state.cleared = true;
        state.prediction = null;
        if (mode === "machine" && state.camera === "station") { state.camera = "follow"; renderCamera(); remember(); }
        show(out.frames, out.timelapse);
        renderWho(); renderCleared(); renderList(); renderCard(); renderPredict(); renderHints(); renderBench();
        debrief(out);
        setReady(true);
        return out;
      }).catch(function (e) {
        if (my !== token || !alive) return null;
        state.busy = false; dom.test.disabled = dom.machine.disabled = false;
        dom.debrief.innerHTML = ""; dom.debrief.appendChild(E("div", "gverdict bad", "⚠ " + e.message));
        setReady(true);
        return null;
      });
    }
    function runTest() { return send("test"); }
    function runMachine() { return send("machine"); }

    function hint(tier) {
      var b = { station: state.focus, tier: tier };
      if (state.player) b.player = state.player.id; else b.v = state.variant;
      return api.post("/api/game/hint", b).then(function (h) {
        dom.hintText.textContent = "";
        dom.hintText.appendChild(E("div", null, h.text));
        dom.hintText.appendChild(E("div", "sbdesc", "(" + h.costs + ")"));
        if (h.progress) { state.stations[state.focus].progress = h.progress; }
        return h;
      }).catch(function (e) { dom.hintText.textContent = "⚠ " + e.message; });
    }

    /* ---------- the debrief ---------- */
    function scoreBox(r) {
      var box = E("div", "gscore");
      box.setAttribute("data-score", r.id);
      var big = E("div", "gscorebig", "🏆 " + r.score);
      box.appendChild(big);
      var side = E("div", "gscoreside");
      var tags = [];
      if (r.new_best) tags.push("🎉 new personal best!");
      else if (r.best != null) tags.push("your best: " + r.best);
      if (r.rank) tags.push("#" + r.rank.rank + " of " + r.rank.of + " on this computer");
      if (state.practice) tags.push("practice - not saved");
      side.appendChild(E("div", "gscoretags", tags.join(" · ")));
      (r.score_parts || []).forEach(function (p) {
        side.appendChild(E("div", "gscorepart", p.label + ": " + p.value + "  (" + p.note + ")"));
      });
      box.appendChild(side);
      return box;
    }

    function debrief(out) {
      dom.debrief.innerHTML = "";
      if (out.hall_cleared_new && !out.next_hall) {
        var fin = E("div", "gverdict ok gcelebrate", "🎉 You cleared " + state.hall.title + " - that was the last hall: " +
                    "the whole Machine Works runs again!");
        fin.setAttribute("data-testid", "hall-cleared-now");
        dom.debrief.appendChild(fin);
      }
      if (out.hall_cleared_new && out.next_hall) {
        var c = E("div", "gverdict ok gcelebrate", "🎉 You cleared " + state.hall.title + "! " + out.next_hall.title +
                  (out.next_hall.status === "ready" ? " is now open." : " is now unlocked (it's still being built - coming soon)."));
        c.setAttribute("data-testid", "hall-cleared-now");
        dom.debrief.appendChild(c);
      }
      if (out.mode === "machine") {
        dom.debrief.appendChild(E("div", "gverdict " + (out.ok ? "ok" : "bad"),
          out.ok ? "🏁 The whole machine ran from A to B!" + (out.golden_new ? "  ★ Golden Run: +30 points" : "")
                 : "The machine stopped at " + out.stations[out.stations.length - 1].id + "."));
      }
      out.stations.forEach(function (r) {
        var s = state.stations[r.id], box = E("div", "gresult");
        box.setAttribute("data-result", r.id);
        box.appendChild(E("div", "gverdict " + (r.ok ? "ok" : "bad"), (r.ok ? "✓ " : "✗ ") + r.id + " " + s.title + ": " + r.reason));
        if (r.ok) box.appendChild(scoreBox(r));
        var meta = [];
        if (r.metric != null && typeof r.metric !== "boolean") meta.push("measured: " + r.metric + " " + r.unit);
        if (r.mastery) meta.push("mastery goal met");
        if (r.new_stars && r.new_stars.length) meta.push("new: " + r.new_stars.map(function (x) { return STAR_NAME[x]; }).join(" "));
        if (r.insight) meta.push("🔮 good prediction (+5)");
        if (meta.length) box.appendChild(E("div", "gmeta", meta.join(" · ")));
        var fl = E("div", "gformulas");
        (r.formula || []).forEach(function (f) {
          var d = E("div", "formula");
          d.appendChild(E("div", "expr", f.expr));
          d.appendChild(E("div", "values", Object.keys(f.values).map(function (kk) { return kk + " = " + f.values[kk]; }).join("  ·  ")));
          fl.appendChild(d);
        });
        box.appendChild(fl);
        var links = E("div", "chips glinks");
        links.appendChild(E("span", "plabel", "🔬 Open in the lab:"));
        (r.lab || []).forEach(function (l) {
          var a = E("a", "chip", l.title); a.href = l.route; a.setAttribute("data-lab", r.id);
          a.addEventListener("click", function () { U.setReturn(hash(), r.id + " " + s.title); });
          links.appendChild(a);
        });
        box.appendChild(links);
        dom.debrief.appendChild(box);
      });
    }

    this.destroy = function () { alive = false; token++; if (player) player.stop(); };
    PL.current = { game: { get state() { return state; }, get lastResult() { return state.last; },
                           setKnob: function (sid, kid, v) { setKnob(sid, kid, v); return state.knobs[sid][kid]; },
                           select: select, test: runTest, machine: runMachine, hint: hint, camera: setCamera,
                           hash: function () { return hash(); }, shareUrl: function () { return shareUrl(); },
                           get stage() { return stage; }, get player() { return player; } } };
    return this;
  }

  PL.gameUI = {
    api: api,
    open: function (app) {
      var rt = PL.game.route(location.hash) || { hall: null };
      if (!rt.hall) return Hub(app);
      return new HallPage(app, rt);
    }
  };
})();
