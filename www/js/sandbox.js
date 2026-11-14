/* physlab SANDBOX pages: students build a world out of the pieces the
   server offers (GET /api/sandbox) - never free numbers for things that
   have real properties.

     #/sandbox                 pick an experiment
     #/sandbox/<topic>?w=...   one sandbox; w = the world's fields that differ
                               from the defaults, as JSON (PL.sandbox in core.js)

   The page is built from the same components as an experiment page
   (simLayout, Stage, Player, PlayBar, learnPanel) plus one generic
   builder that turns the server's field list into controls:

     object   catalog cards (pick 1, or 1-2 to compare as A / B)
     choice   chips (planet, weather, surface ...); a choice may be
              limited by a picked object (tea can't come from the oven)
     number   a bounded slider
     track    the energy ramp: drag its yellow points on the canvas
     circuit  the circuit board: a tool palette; click between dots

   Every world goes to POST /api/sandbox/run, which validates it strictly.
   If the server refuses, the page says why and returns to the last world
   that worked. Scenes edit the world through cam.setParams(changes, done)
   exactly as on experiment pages. */
(function () {
  "use strict";
  var U = PL.ui, E = U.el;
  var catalog = null;

  function fetchJSON(url, body) {
    var opts = body ? { method: "POST", headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(body) } : undefined;
    return fetch(url, opts).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (b) {
        if (!r.ok) throw new Error(b.error || ("HTTP " + r.status));
        return b;
      });
    });
  }

  function loadCatalog() {
    if (catalog) return Promise.resolve(catalog);
    return fetchJSON("/api/sandbox").then(function (d) { catalog = d.sandbox; return catalog; });
  }

  function setReady(on) { document.documentElement.setAttribute("data-sim-ready", on ? "1" : "0"); }
  function clone(x) { return JSON.parse(JSON.stringify(x)); }

  /* "🔬 Experiment | 🏖️ Sandbox" switch shown on both kinds of page */
  function modeToggle(topicId, mode) {
    var wrap = E("div", "modetoggle");
    [["experiment", "🔬 Experiment", "#/" + topicId], ["sandbox", "🏖️ Sandbox", "#/sandbox/" + topicId]]
      .forEach(function (m) {
        var b = E("button", "mode" + (m[0] === mode ? " on" : ""), m[1]);
        b.type = "button";
        b.setAttribute("data-mode", m[0]);
        b.addEventListener("click", function () { if (m[0] !== mode) location.hash = m[2]; });
        wrap.appendChild(b);
      });
    return wrap;
  }

  /* ---------------- #/sandbox : choose an experiment ---------------- */
  function Picker(app, topics) {
    app.innerHTML = "";
    var head = E("div", "sbhead");
    var back = E("button", "secondary back", "← all experiments");
    back.addEventListener("click", function () { location.hash = "#/"; });
    head.appendChild(back);
    head.appendChild(E("h2", null, "🏖️ Sandbox: build your own world"));
    head.appendChild(E("p", "blurb", "Pick real things from a box - balls, bobs, lamps, liquids - and change the " +
                       "world around them: planet, weather, surface, ramp shape, your own circuit. Every object " +
                       "keeps its real mass, size and material."));
    app.appendChild(head);
    var dead = false;
    loadCatalog().then(function (cat) {
      if (dead) return;
      // each card says what you can play with in that sandbox
      var cards = topics.filter(function (t) { return t.status === "ready" && cat[t.id]; }).map(function (t) {
        var cfg = cat[t.id], seen = {}, things = 0, settings = 0;
        cfg.fields.forEach(function (f) {
          if ((f.kind === "object" || f.kind === "circuit") && !seen[f.catalog]) { seen[f.catalog] = 1; things += f.items.length; }
          if (f.kind === "choice" || f.kind === "track") settings++;
        });
        var what = [things ? "🧺 " + things + (t.id === "circuits" ? " parts" : " things to pick") : "",
                    settings ? "🌍 " + settings + " world setting" + (settings > 1 ? "s" : "") : ""]
          .filter(Boolean).join(" · ");
        return Object.assign({}, t, { blurb: cfg.intro, formulas: [{ expr: what }] });
      });
      app.appendChild(U.topicCards(cards, function (t) { location.hash = "#/sandbox/" + t.id; }));
      setReady(true);
    }).catch(function (e) {
      app.appendChild(E("div", "loading", "could not load the sandbox: " + e.message));
    });
    document.title = "physlab - sandbox";
    return { destroy: function () { dead = true; } };
  }

  /* ---------------- one sandbox ---------------- */
  function Page(app, t, cfg, rawWorld) {
    var scene = PL.scenes[cfg.scene], fields = cfg.fields, byId = {};
    fields.forEach(function (f) { byId[f.id] = f; });
    var world = PL.sandbox.fromRoute(cfg.defaults, rawWorld);
    var good = null, token = 0, debounce = null, pending = false, tool = "hand", alive = true;
    var view = { tool: tool };
    (scene.options || []).forEach(function (o) { view[o.id] = o.default; });

    setReady(false);
    window.scrollTo(0, 0);
    document.title = "physlab - " + t.title + " sandbox";

    var L = U.simLayout(t, function () { location.hash = "#/"; });
    L.root.classList.add("sandbox");
    var blurb = L.left.querySelector(".blurb");
    if (blurb) blurb.textContent = cfg.intro;
    L.left.insertBefore(modeToggle(t.id, "sandbox"), L.left.querySelector("h2"));
    var ret = U.returnBanner();                  // came here from a game station's "Open in the lab"?
    if (ret) L.left.insertBefore(ret, L.left.firstChild);

    var stage = new PL.Stage(880, 500);
    var bar = U.PlayBar(scene.options, view, {
      play: function () { player.toggle(); },
      reset: function () { player.reset(); },
      view: function () { player.redraw(); }
    });
    var player = new PL.Player(stage, scene, bar.setLabel);
    var cast = E("div", "cast"), status = E("span", "sbstatus");
    var errBox = E("div", "sberr"); errBox.hidden = true;
    var notesBox = E("div"), readBox = E("div");
    var learn = t.learn ? U.learnPanel(t) : U.formulaPanel(t.formulas);
    var fieldsBox = E("div", "sbfields");

    // presets
    var pre = E("div", "presets");
    pre.appendChild(E("div", "plabel", "⚡ Ready-made worlds"));
    var chips = E("div", "chips");
    cfg.presets.forEach(function (pr) {
      var b = E("button", "chip", pr.title);
      b.type = "button";
      b.addEventListener("click", function () { world = PL.sandbox.fromRoute(cfg.defaults, JSON.stringify(pr.world)); changed(0); });
      chips.appendChild(b);
    });
    var rs = E("button", "chip reset", "↺ start again");
    rs.type = "button";
    rs.addEventListener("click", function () { world = clone(cfg.defaults); changed(0); });
    chips.appendChild(rs);
    pre.appendChild(chips);
    L.presets.appendChild(pre);
    L.controls.appendChild(fieldsBox);

    var castRow = E("div", "castrow");
    castRow.appendChild(cast); castRow.appendChild(status);
    L.stage.appendChild(castRow);
    L.stage.appendChild(stage.el);
    L.playbar.appendChild(bar.el);
    L.playbar.appendChild(errBox);
    L.notes.appendChild(notesBox);
    L.results.appendChild(readBox);
    L.learn.appendChild(learn.el);
    app.innerHTML = "";
    app.appendChild(L.root);

    stage.onChange = function () { player.redraw(); };
    stage.cam.setParams = setParams;

    /* ---------- the world changed: redraw the controls, run ---------- */
    function changed(ms) {
      hideError();
      renderFields();
      schedule(ms);
    }

    function schedule(ms) {
      clearTimeout(debounce);
      pending = true;                    // a newer world is on its way: answers to older ones must not overwrite it
      debounce = setTimeout(run, ms);
    }

    function syncHash() {
      var h = PL.sandbox.hash(t.id, cfg.defaults, world);
      if (h !== location.hash) history.replaceState(null, "", h);
    }

    function showError(msg) {
      errBox.textContent = "⚠ " + msg;
      errBox.hidden = false;
    }
    function hideError() { errBox.hidden = true; }

    function run() {
      var my = ++token, sent = clone(world);
      pending = false;
      status.textContent = "⏳ simulating…";
      fetchJSON("/api/sandbox/run", { topic: t.id, world: sent }).then(function (out) {
        if (my !== token || !alive) return;
        status.textContent = "";
        good = out.world;
        if (!pending) { world = clone(out.world); syncHash(); }
        show(out);
        setReady(true);
      }).catch(function (e) {
        if (my !== token || !alive) return;
        status.textContent = "";
        if (pending) return;
        if (good) {
          showError(e.message + " - back to your last world that worked.");
          world = clone(good); syncHash(); renderFields();
          setReady(true);
        } else {                           // a broken link: start from the default world instead
          world = clone(cfg.defaults); renderFields(); run();
          showError(e.message + " - starting from the default world instead.");
        }
      });
    }

    function show(out) {
      var multi = out.runs.length > 1;
      var runs = out.runs.map(function (r, i) {
        return { result: r.result, params: r.result.params, color: U.RUN_COLORS[i],
                 label: multi ? U.RUN_LABELS[i] : "", name: r.label };
      });
      // who is who
      cast.innerHTML = "";
      runs.forEach(function (r, i) {
        var tag = E("span", "castitem");
        tag.style.setProperty("--run", r.color);
        tag.textContent = (multi ? r.label + " = " : "") + r.name;
        cast.appendChild(tag);
        if (i < runs.length - 1) cast.appendChild(document.createTextNode(" "));
      });
      // notes + readouts
      var list = (out.notes || []).map(function (n) { return { text: n }; });
      runs.forEach(function (r) {
        (r.result.notes || []).forEach(function (n) {
          list.push({ label: multi ? r.label : "", color: r.color, text: n });
        });
      });
      notesBox.innerHTML = "";
      if (list.length) notesBox.appendChild(U.notes(list));
      readBox.innerHTML = "";
      readBox.appendChild(multi
        ? U.readoutTable(runs.map(function (r) {
            return { label: r.label + " · " + r.name, color: r.color, readouts: r.result.readouts };
          }))
        : U.readouts(runs[0].result.readouts));
      learn.update(multi ? runs.map(function (r) {
        return { label: r.label, color: r.color, formula: r.result.formula };
      }) : runs[0].result.formula);
      view.tool = tool;
      player.load(runs, view, { keepView: true });
    }

    /* ---------- edits coming from the canvas ---------- */
    function setParams(ch, done) {
      if (ch.edge) return editCircuit(ch.edge);
      if (ch.track) {
        if (!done) { player.redraw(); return; }                 // the scene previews the drag itself
        var f = byId.track, bad = PL.spline(f.xs, ch.track).check(f.max_slope);
        if (bad.length) {
          showError(bad[0] === "ground" ? "that shape dips below the ground - lift the low points a little"
                                        : "that ramp is too steep - smooth it out");
          player.redraw();
          return;
        }
        world.track = ch.track.slice();
        return changed(0);
      }
      var any = false;
      Object.keys(ch).forEach(function (k) {
        var f = byId[k];
        if (f && f.kind === "number") {
          world[k] = Math.min(f.max, Math.max(f.min, +ch[k]));
          any = true;
        }
      });
      if (any) { renderFields(); schedule(done ? 0 : 60); }
    }

    /* click between two dots with the current tool */
    function editCircuit(edge) {
      var f = byId.parts, parts = world.parts, key = function (e) { return e[0] + "," + e[1]; };
      var k1 = key(edge[0]) + "|" + key(edge[1]), k2 = key(edge[1]) + "|" + key(edge[0]);
      var at = -1;
      parts.forEach(function (p, i) { var k = key(p.a) + "|" + key(p.b); if (k === k1 || k === k2) at = i; });
      var existing = at >= 0 ? parts[at] : null;
      var spec = function (id) { return f.items.filter(function (it) { return it.id === id; })[0]; };
      hideError();
      if (tool === "hand") {
        if (!existing) return;
        var kind = spec(existing.part).kind;
        if (kind === "switch") existing.on = !existing.on;
        else if (kind === "battery") existing.flip = !existing.flip;
        else { showError("the hand flips switches and turns batteries round - pick a part or the eraser to change this one"); return; }
      } else if (tool === "eraser") {
        if (!existing) return;
        parts.splice(at, 1);
      } else {
        if (existing && existing.part === tool) return;
        var kindNew = spec(tool).kind;
        var count = function (kd) {
          return parts.filter(function (p, i) { return i !== at && spec(p.part).kind === kd; }).length;
        };
        if (!existing && parts.length >= f.max_parts) { showError("the board is full (" + f.max_parts + " parts)"); return; }
        if (kindNew === "battery" && count("battery") >= f.max_batteries) {
          showError("at most " + f.max_batteries + " batteries on the board"); return;
        }
        if (kindNew === "lamp" && count("lamp") >= f.max_lamps) { showError("at most " + f.max_lamps + " lamps"); return; }
        var part = { part: tool, a: edge[0].slice(), b: edge[1].slice(), on: true, flip: false };
        if (existing) parts[at] = part; else parts.push(part);
      }
      renderFields();
      schedule(0);
    }

    /* ---------- the control panel, generated from the field list ---------- */
    function renderFields() {
      fieldsBox.innerHTML = "";
      fields.forEach(function (f) {
        var box = E("div", "sbfield"), head = E("div", "sblabel", f.label);
        box.setAttribute("data-field", f.id);
        box.appendChild(head);
        if (f.kind === "object") objectField(box, f);
        else if (f.kind === "choice") choiceField(box, f);
        else if (f.kind === "number") numberField(box, f);
        else if (f.kind === "track") trackField(box, f);
        else if (f.kind === "circuit") circuitField(box, f);
        fieldsBox.appendChild(box);
      });
    }

    function itemCard(it, on, badge, cls) {
      var b = E("button", "sbitem" + (on ? " on" : "") + (cls ? " " + cls : ""));
      b.type = "button";
      b.setAttribute("data-id", it.id);
      b.title = it.desc;
      b.appendChild(E("span", "ic", it.icon));
      var tx = E("span", "tx");
      tx.appendChild(E("b", null, it.label));
      tx.appendChild(E("small", null, it.desc));
      b.appendChild(tx);
      if (badge) {
        var bd = E("span", "badge2", badge.text);
        bd.style.background = badge.color;
        b.appendChild(bd);
      }
      return b;
    }

    function objectField(box, f) {
      var multi = f.max_count > 1, chosen = multi ? world[f.id] : [world[f.id]];
      if (multi) box.appendChild(E("div", "sbhint", "click to add or remove - pick two to compare them (A and B)"));
      var grid = E("div", "sbgrid");
      f.items.forEach(function (it) {
        var idx = chosen.indexOf(it.id);
        var badge = multi && idx >= 0 && chosen.length > 1 ? { text: U.RUN_LABELS[idx], color: U.RUN_COLORS[idx] } : null;
        var card = itemCard(it, idx >= 0, badge);
        card.addEventListener("click", function () {
          if (!multi) { world[f.id] = it.id; return changed(0); }
          var list = world[f.id].slice(), at = list.indexOf(it.id);
          if (at >= 0) { if (list.length > 1) list.splice(at, 1); else return; }
          else if (list.length < f.max_count) list.push(it.id);
          else list[list.length - 1] = it.id;                 // swap out B
          world[f.id] = list;
          changed(0);
        });
        grid.appendChild(card);
      });
      box.appendChild(grid);
    }

    function choiceField(box, f) {
      var allowed = null, moved = null;
      if (f.limited_by) {
        var byF = byId[f.limited_by], thing = byF.items.filter(function (it) { return it.id === world[f.limited_by]; })[0];
        allowed = thing && thing.sources;
        if (allowed && allowed.indexOf(world[f.id]) < 0) {
          // the picked thing can't come from here: move it to the nearest allowed place
          var cur = f.items.filter(function (it) { return it.id === world[f.id]; })[0];
          var best = f.items.filter(function (it) { return allowed.indexOf(it.id) >= 0; })
            .sort(function (a, b) { return Math.abs(a.temp - cur.temp) - Math.abs(b.temp - cur.temp); })[0];
          if (best) {
            world[f.id] = best.id;
            moved = thing.label + " can't come from the " + cur.label.toLowerCase() + " - moved to the " +
                    best.label.toLowerCase() + ".";
          }
        }
      }
      var row = E("div", "sbchips");
      f.items.forEach(function (it) {
        var ok = !allowed || allowed.indexOf(it.id) >= 0;
        var b = E("button", "sbchip" + (world[f.id] === it.id ? " on" : ""), it.icon + " " + it.label);
        b.type = "button";
        b.setAttribute("data-id", it.id);
        b.title = ok ? it.desc : "not for this object";
        b.disabled = !ok;
        b.addEventListener("click", function () { world[f.id] = it.id; changed(0); });
        row.appendChild(b);
      });
      box.appendChild(row);
      var sel = f.items.filter(function (it) { return it.id === world[f.id]; })[0];
      if (sel) box.appendChild(E("div", "sbdesc", sel.desc));
      if (moved) box.appendChild(E("div", "sbhint warn", moved));
    }

    function numberField(box, f) {
      box.removeChild(box.firstChild);                        // the slider carries its own label
      box.appendChild(U.controls([{ id: f.id, label: f.label, unit: f.unit, min: f.min, max: f.max, step: f.step,
                                    kind: "number" }], world, function (id, v) {
        world[id] = v; hideError(); schedule(150);
      }));
    }

    function trackField(box, f) {
      box.appendChild(E("div", "sbhint", "Drag the yellow dots on the ramp up or down (" + f.y_min + "–" + f.y_max +
                        " m). The object starts at the left end. No dips below the ground, nothing steeper than " +
                        Math.round(Math.atan(f.max_slope) * 180 / Math.PI) + "°."));
      var row = E("div", "sbheights");
      world[f.id].forEach(function (y, i) {
        row.appendChild(E("span", null, f.xs[i] + " m: " + y.toFixed(1)));
      });
      box.appendChild(row);
    }

    function circuitField(box, f) {
      var parts = world[f.id];
      var spec = function (id) { return f.items.filter(function (it) { return it.id === id; })[0]; };
      var n = function (kd) { return parts.filter(function (p) { return spec(p.part).kind === kd; }).length; };
      box.appendChild(E("div", "sbhint", "Pick a tool, then click between two dots on the board."));
      var grid = E("div", "sbgrid tools");
      var tools = [{ id: "hand", icon: "✋", label: "Hand", desc: "flip switches, turn batteries round" },
                   { id: "eraser", icon: "🧽", label: "Eraser", desc: "remove a part" }].concat(f.items);
      tools.forEach(function (it) {
        var card = itemCard(it, tool === it.id, null, "tool");
        card.addEventListener("click", function () {
          tool = it.id; view.tool = tool; renderFields(); player.redraw();
        });
        grid.appendChild(card);
      });
      box.appendChild(grid);
      box.appendChild(E("div", "sbdesc", parts.length + "/" + f.max_parts + " parts · " + n("battery") + "/" +
                        f.max_batteries + " batteries · " + n("lamp") + "/" + f.max_lamps + " lamps"));
      var clr = E("button", "secondary small", "🗑 clear the board");
      clr.type = "button";
      clr.addEventListener("click", function () { world[f.id] = []; changed(0); });
      box.appendChild(clr);
    }

    this.destroy = function () {
      alive = false; token++;
      clearTimeout(debounce);
      player.stop();
    };

    renderFields();
    run();
    PL.current = { topic: t, sandbox: true, get world() { return world; }, stage: stage, player: player,
                   setTool: function (id) { tool = id; view.tool = id; renderFields(); } };
  }

  PL.sandboxUI = {
    modeToggle: modeToggle,
    /* route "sandbox" or "sandbox/<topic>" */
    open: function (app, sub, rt, topics) {
      if (!sub) return Picker(app, topics);
      var t = topics.filter(function (x) { return x.id === sub && x.status === "ready"; })[0];
      if (!t) { location.hash = "#/sandbox"; return { destroy: function () {} }; }
      var page = null, dead = false;
      app.innerHTML = '<div class="loading">loading the sandbox…</div>';
      loadCatalog().then(function (cat) {
        if (dead) return;
        if (!cat[sub]) { app.innerHTML = '<div class="loading">no sandbox for this experiment yet</div>'; return; }
        page = new Page(app, t, cat[sub], rt && rt.a.w);
      }).catch(function (e) {
        app.innerHTML = '<div class="loading">could not load the sandbox: ' + e.message + "</div>";
      });
      return { destroy: function () { dead = true; if (page) page.destroy(); } };
    }
  };
})();
