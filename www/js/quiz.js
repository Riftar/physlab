/* physlab quiz: "set the right parameter to make the simulation do X".

   Pages (routed by main.js):
     #/quiz            challenge home: player, score, every module's 3 challenges
     #/quiz/<id>       one challenge: prompt, given values, answer inputs,
                       the simulation running YOUR answer, verdict + explanation
     #/quiz/history    every answer you gave

   Grading happens on the server, which runs the experiment with the
   answer and measures the outcome (see physlab/quiz.py). The player is a
   nickname + id kept in localStorage; scores and history live in the
   server's SQLite database (physlab/quizdb.py).

   Built from the same components as the experiment pages: PL.Stage,
   PL.Player, PL.ui.PlayBar, PL.ui.ResultsPanel. */
(function () {
  "use strict";
  var E = PL.ui.el;
  var KEY = "physlab.player";
  var LEVEL = { easy: "Easy", medium: "Medium", hard: "Hard" };

  /* ---------------- api ---------------- */
  function request(method, url, body) {
    return fetch(url, body ? { method: method, headers: { "Content-Type": "application/json" },
                               body: JSON.stringify(body) } : { method: method })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (j) {
          if (!r.ok) throw new Error(j.error || ("HTTP " + r.status));
          return j;
        });
      });
  }
  var api = {
    get: function (url) { return request("GET", url); },
    post: function (url, body) { return request("POST", url, body); },
    playerId: function () { try { return localStorage.getItem(KEY) || ""; } catch (e) { return ""; } },
    setPlayer: function (id) { try { if (id) localStorage.setItem(KEY, id); else localStorage.removeItem(KEY); } catch (e) {} }
  };

  function query(params) {
    return Object.keys(params).map(function (k) {
      var v = params[k];
      return k + "=" + encodeURIComponent(typeof v === "boolean" ? (v ? "1" : "0") : v);
    }).join("&");
  }

  function badge(level) {
    return E("span", "lvl lvl-" + level, LEVEL[level]);
  }

  function status(pg) {
    if (!pg) return ["new", "● new"];
    if (pg.solved) return ["solved", "✓ solved  +" + pg.earned];
    if (pg.revealed) return ["revealed", "👁 answer shown"];
    if (pg.attempts) return ["tried", "✗ " + pg.attempts + (pg.attempts === 1 ? " try" : " tries")];
    return ["new", "● new"];
  }

  /* ---------------- who's playing ---------------- */
  function playerBox(data, onChange) {
    var box = E("div", "qplayer");
    if (data.player) {
      var p = data.player;
      box.appendChild(E("div", "qwho", "Playing as " + p.name));
      var sc = E("div", "qscore");
      sc.appendChild(E("b", null, String(p.score)));
      sc.appendChild(document.createTextNode(" / " + data.max_score + " points · " + p.solved + " / " +
                                             data.count + " solved"));
      box.appendChild(sc);
      var bar = E("div", "qbar"); var fill = E("div", "qfill");
      fill.style.width = (100 * p.score / data.max_score).toFixed(1) + "%";
      bar.appendChild(fill); box.appendChild(bar);
      var row = E("div", "qactions");
      var hist = E("button", "secondary small", "📜 my answers");
      hist.addEventListener("click", function () { location.hash = "#/quiz/history"; });
      var sw = E("button", "secondary small", "switch player");
      sw.addEventListener("click", function () { api.setPlayer(""); onChange(); });
      row.appendChild(hist); row.appendChild(sw); box.appendChild(row);
      return box;
    }
    box.appendChild(E("div", "qwho", "Who's playing?"));
    var form = E("form", "qname");
    var inp = E("input"); inp.type = "text"; inp.maxLength = 24; inp.placeholder = "your name"; inp.required = true;
    var go = E("button", null, "Start");
    form.appendChild(inp); form.appendChild(go);
    var err = E("div", "qerr");
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      api.post("/api/quiz/player", { name: inp.value }).then(function (r) {
        api.setPlayer(r.player.id); onChange();
      }).catch(function (x) { err.textContent = x.message; });
    });
    box.appendChild(form); box.appendChild(err);
    api.get("/api/quiz/players").then(function (r) {
      if (!r.players.length) return;
      var rec = E("div", "qrecent");
      rec.appendChild(E("span", null, "or continue as: "));
      r.players.forEach(function (pl) {
        var b = E("button", "chip", pl.name + " · " + pl.score + " pts");
        b.type = "button";
        b.addEventListener("click", function () { api.setPlayer(pl.id); onChange(); });
        rec.appendChild(b);
      });
      box.appendChild(rec);
    });
    return box;
  }

  /* ---------------- challenge home ---------------- */
  function HomePage(app) {
    var wrap = E("div", "quiz");
    function load() {
      api.get("/api/quiz?player=" + encodeURIComponent(api.playerId())).then(function (data) {
        if (!data.player && api.playerId()) api.setPlayer("");     // stale id
        wrap.innerHTML = "";
        var head = E("div", "qhead");
        var left = E("div");
        var back = E("button", "secondary back", "← experiments");
        back.addEventListener("click", function () { location.hash = "#/"; });
        left.appendChild(back);
        left.appendChild(E("h2", null, "🎯 Physics challenges"));
        left.appendChild(E("p", "blurb", "Each experiment has three challenges. Type in the value you think "
          + "is right - the experiment then runs with YOUR answer and shows whether it works."));
        var key = E("div", "qkey");
        [["easy", "one value, one formula"], ["medium", "one value, with a twist"],
         ["hard", "two values, or physics beyond a simple formula"]].forEach(function (k) {
          var d = E("div"); d.appendChild(badge(k[0])); d.appendChild(document.createTextNode(" " + k[1]));
          key.appendChild(d);
        });
        left.appendChild(key);
        head.appendChild(left);
        head.appendChild(playerBox(data, load));
        wrap.appendChild(head);
        var grid = E("div", "qgrid");
        data.modules.forEach(function (m) {
          var card = E("div", "qmod");
          var h = E("div", "qmodh");
          var ic = E("img", "hicon"); ic.src = "icons/icon_" + m.icon + ".png"; ic.alt = "";
          h.appendChild(ic); h.appendChild(E("span", null, m.title));
          card.appendChild(h);
          m.questions.forEach(function (q) {
            var row = E("button", "qrow");
            row.type = "button";
            row.appendChild(badge(q.difficulty));
            row.appendChild(E("span", "qt", q.title));
            var st = status(q.progress);
            row.appendChild(E("span", "qst " + st[0], data.player ? st[1] : q.points + " pts"));
            row.addEventListener("click", function () { location.hash = "#/quiz/" + q.id; });
            card.appendChild(row);
          });
          grid.appendChild(card);
        });
        wrap.appendChild(grid);
        document.documentElement.setAttribute("data-sim-ready", "1");
      }).catch(function (e) { wrap.textContent = "could not load the quiz: " + e.message; });
    }
    app.innerHTML = ""; app.appendChild(wrap);
    document.title = "physlab - challenges";
    load();
    this.destroy = function () {};
  }

  /* ---------------- one challenge ---------------- */
  function QuestionPage(app, qid) {
    var that = this, pid = api.playerId();
    var player = null, stage = null, seq = 0;
    document.documentElement.setAttribute("data-sim-ready", "0");
    app.innerHTML = "";
    var root = E("div", "sim");
    var left = E("div", "panel qpanel"), right = E("div");
    root.appendChild(left); root.appendChild(right);
    app.appendChild(root);

    api.get("/api/quiz/question?id=" + encodeURIComponent(qid) + "&player=" + encodeURIComponent(pid))
      .then(function (q) { build(q); })
      .catch(function (e) { left.textContent = "could not load this challenge: " + e.message; });

    function topicOf(id) { return (PL.topics || []).filter(function (t) { return t.id === id; })[0]; }

    function build(q) {
      var topic = topicOf(q.topic), scene = PL.scenes[q.topic];
      document.title = "physlab - " + q.title;
      // ---- left: the question ----
      var back = E("button", "secondary back", "← all challenges");
      back.addEventListener("click", function () { location.hash = "#/quiz"; });
      left.appendChild(back);
      var mod = E("div", "qmodline");
      var ic = E("img", "hicon"); ic.src = "icons/icon_" + topic.icon + ".png"; ic.alt = "";
      mod.appendChild(ic); mod.appendChild(E("span", null, topic.title));
      mod.appendChild(badge(q.difficulty)); mod.appendChild(E("span", "qpts", q.points + " pts"));
      left.appendChild(mod);
      left.appendChild(E("h2", null, q.title));
      left.appendChild(E("p", "qprompt", q.prompt));
      var given = E("div", "qgiven");
      given.appendChild(E("div", "plabel", "Given"));
      q.setup.forEach(function (s) {
        var r = E("div", "grow");
        r.appendChild(E("span", null, s.label));
        r.appendChild(E("b", null, s.value + (s.unit ? " " + s.unit : "")));
        given.appendChild(r);
      });
      left.appendChild(given);
      var form = E("form", "qform");
      form.appendChild(E("div", "plabel", "Your answer"));
      var fields = {};
      q.inputs.forEach(function (p) {
        var row = E("label", "qin");
        row.appendChild(E("span", "qinl", p.label + (p.unit ? " (" + p.unit + ")" : "")));
        var inp;
        if (p.kind === "select") {
          inp = E("select");
          p.choices.forEach(function (c) { var o = E("option", null, c.label); o.value = c.id; inp.appendChild(o); });
          inp.value = p.start;
        } else {
          inp = E("input"); inp.type = "number"; inp.min = p.min; inp.max = p.max; inp.step = "any";
          inp.value = p.start; inp.required = true;
          row.appendChild(E("span", "qrange", p.min + " to " + p.max));
        }
        inp.setAttribute("data-param", p.id);
        row.insertBefore(inp, row.children[1] || null);
        fields[p.id] = { el: inp, spec: p };
        form.appendChild(row);
      });
      var submit = E("button", null, "✓ Check my answer");
      form.appendChild(submit);
      var err = E("div", "qerr");
      form.appendChild(err);
      left.appendChild(form);
      var status = E("div", "qstatus");
      left.appendChild(status);
      var reveal = E("button", "secondary small", "👁 Show me the answer (no points)");
      reveal.hidden = true;
      left.appendChild(reveal);
      var next = E("button", "secondary small", "Next challenge →");
      next.hidden = true;
      left.appendChild(next);

      // ---- right: goal, stage, result ----
      var goal = E("div", "qgoal");
      goal.appendChild(E("b", null, "🎯 Goal: "));
      goal.appendChild(document.createTextNode(q.goal.text));
      right.appendChild(goal);
      var view = {};
      (scene.options || []).forEach(function (o) { view[o.id] = o.default; });
      stage = new PL.Stage(880, 500);
      right.appendChild(stage.el);
      var bar = PL.ui.PlayBar(scene.options, view, {
        play: function () { player.toggle(); }, reset: function () { player.reset(); },
        view: function () { player.redraw(); }
      });
      right.appendChild(bar.el);
      player = new PL.Player(stage, scene, bar.setLabel);
      stage.onChange = function () { player.redraw(); };
      var card = E("div", "qresult");
      card.hidden = true;
      right.appendChild(card);
      var results = PL.ui.ResultsPanel();
      right.appendChild(results.notes);
      right.appendChild(results.readouts);

      function values() {
        var out = {};
        Object.keys(fields).forEach(function (k) {
          var f = fields[k];
          out[k] = f.spec.kind === "select" ? f.el.value : parseFloat(f.el.value);
        });
        return out;
      }

      function setStatus(pg) {
        status.innerHTML = "";
        if (!pg) { status.textContent = "Make a player on the challenges page to save your score."; return; }
        var st = statusText(pg);
        status.appendChild(E("span", "qst " + st[0], st[1]));
        reveal.hidden = !pg.can_reveal;
        next.hidden = !(pg.solved || pg.revealed);
      }
      function statusText(pg) {
        return pg.solved ? ["solved", "✓ Solved (+" + pg.earned + " points). You can keep experimenting."]
          : pg.revealed ? ["revealed", "👁 Answer shown - no points for this one."]
          : pg.attempts ? ["tried", pg.attempts + (pg.attempts === 1 ? " try" : " tries") + " so far"]
          : ["new", "No tries yet. Correct on the first try = " + q.points + " points."];
      }
      setStatus(q.progress);

      function showCard(r) {
        card.hidden = false; card.innerHTML = "";
        card.className = "qresult " + (r.correct ? "ok" : "no");
        card.appendChild(E("div", "qverdict", r.correct ? "✅ Correct!" : "❌ Not quite"));
        card.appendChild(E("p", "qmsg", r.message));
        if (r.correct) {
          card.appendChild(E("p", "qpoints", r.points > 0 ? "+" + r.points + " points  (score: " + r.score + ")"
                                                         : "No new points (already solved or answer shown)."));
        }
        if (r.explanation) {
          var ex = E("div", "qexp");
          ex.appendChild(E("b", null, "💡 How to think about it: "));
          ex.appendChild(document.createTextNode(r.explanation));
          card.appendChild(ex);
        }
        if (r.solution) {
          var so = E("div", "qsol");
          so.appendChild(E("b", null, "✏️ Worked answer: "));
          so.appendChild(document.createTextNode(r.solution));
          card.appendChild(so);
        }
        var open = E("a", "qopen", "open this set-up in the experiment →");
        open.href = "#/" + q.topic + "?" + query(r.run.params);
        card.appendChild(open);
      }

      function play(res, paused) {
        var runs = [{ result: res, params: res.params, color: PL.ui.RUN_COLORS[0], label: "" }];
        results.update(runs, "");
        player.load(runs, view, { goal: q.goal, paused: paused });
        document.documentElement.setAttribute("data-sim-ready", "1");
      }

      // preview: the set-up with the starting values, paused at t = 0
      var pre = {};
      topic.params.forEach(function (p) { pre[p.id] = p.default; });
      Object.keys(q.setup_values).forEach(function (k) { pre[k] = q.setup_values[k]; });
      var start = values();
      Object.keys(start).forEach(function (k) { pre[k] = start[k]; });
      api.get("/api/run?topic=" + q.topic + "&" + query(pre)).then(function (res) {
        play(res, true);
        card.hidden = false; card.className = "qresult idle"; card.innerHTML = "";
        card.appendChild(E("p", "qmsg", "This is the set-up with the starting value filled in. Type your "
                           + "answer and press “Check my answer” - the experiment will then run with it."));
      });

      form.addEventListener("submit", function (e) {
        e.preventDefault();
        err.textContent = "";
        if (!api.playerId()) { err.textContent = "Make a player first (on the challenges page)."; return; }
        var my = ++seq;
        submit.disabled = true;
        api.post("/api/quiz/answer", { player: api.playerId(), question: q.id, inputs: values() })
          .then(function (r) {
            if (my !== seq) return;
            showCard(r); setStatus(r.progress); play(r.run, false);
          })
          .catch(function (x) { err.textContent = x.message; })
          .then(function () { submit.disabled = false; });
      });
      reveal.addEventListener("click", function () {
        api.post("/api/quiz/reveal", { player: api.playerId(), question: q.id }).then(function (r) {
          card.hidden = false;
          var so = E("div", "qsol");
          so.appendChild(E("b", null, "✏️ Worked answer: "));
          so.appendChild(document.createTextNode(r.solution));
          card.appendChild(so);
          setStatus(r.progress);
        }).catch(function (x) { err.textContent = x.message; });
      });
      next.addEventListener("click", function () {
        api.get("/api/quiz?player=" + encodeURIComponent(api.playerId())).then(function (data) {
          var all = [];
          data.modules.forEach(function (m) { m.questions.forEach(function (x) { all.push(x); }); });
          var i = all.map(function (x) { return x.id; }).indexOf(q.id);
          var rest = all.slice(i + 1).concat(all.slice(0, i));
          var open = rest.filter(function (x) { return !(x.progress && (x.progress.solved || x.progress.revealed)); })[0];
          location.hash = open ? "#/quiz/" + open.id : "#/quiz";
        });
      });
    }

    this.destroy = function () { seq++; if (player) player.stop(); };
  }

  /* ---------------- history ---------------- */
  function HistoryPage(app) {
    var wrap = E("div", "quiz");
    app.innerHTML = ""; app.appendChild(wrap);
    var back = E("button", "secondary back", "← all challenges");
    back.addEventListener("click", function () { location.hash = "#/quiz"; });
    wrap.appendChild(back);
    api.get("/api/quiz/history?player=" + encodeURIComponent(api.playerId())).then(function (d) {
      wrap.appendChild(E("h2", null, "📜 " + d.player.name + "'s answers"));
      wrap.appendChild(E("p", "blurb", d.player.score + " points · " + d.player.solved + " challenges solved · " +
                         d.history.length + " answers"));
      if (!d.history.length) { wrap.appendChild(E("p", "blurb", "No answers yet.")); return; }
      var t = E("table", "rtable qhist");
      var hr = E("tr");
      ["when", "challenge", "your answer", "result", "", "points"].forEach(function (h) { hr.appendChild(E("th", null, h)); });
      t.appendChild(hr);
      d.history.forEach(function (a) {
        var tr = E("tr");
        tr.appendChild(E("td", "k", new Date(a.created * 1000).toLocaleString()));
        var c = E("td"); c.appendChild(badge(a.difficulty)); c.appendChild(document.createTextNode(" " + a.title));
        c.style.cursor = "pointer";
        c.addEventListener("click", function () { location.hash = "#/quiz/" + a.question_id; });
        tr.appendChild(c);
        tr.appendChild(E("td", "v", Object.keys(a.inputs).map(function (k) { return k + " = " + a.inputs[k]; }).join(", ")));
        tr.appendChild(E("td", "v", a.value == null ? "—" : (+a.value.toPrecision(4)) + (a.unit ? " " + a.unit : "")));
        tr.appendChild(E("td", null, a.correct ? "✅" : "❌"));
        tr.appendChild(E("td", "v", a.points ? "+" + a.points : "0"));
        t.appendChild(tr);
      });
      wrap.appendChild(t);
      document.documentElement.setAttribute("data-sim-ready", "1");
    }).catch(function () {
      wrap.appendChild(E("p", "blurb", "Pick a player on the challenges page first."));
    });
    this.destroy = function () {};
  }

  /* route: "" | "history" | "<question id>" */
  PL.quiz = {
    api: api,
    open: function (app, sub) {
      if (!sub) return new HomePage(app);
      if (sub === "history") return new HistoryPage(app);
      return new QuestionPage(app, sub);
    }
  };
})();
