/* physlab ui kit - the DOM components every experiment page is built from:
   simLayout, presetBar, ControlPanel (data-driven sliders), ComparePanel,
   PlayBar, ResultsPanel, learnPanel (formulas / figures / real life) and
   the topic cards. A topic's params spec drives all of it: no per-topic
   UI code. */
(function () {
  "use strict";
  window.PL = window.PL || {};

  // decimals follow the slider step: 1 -> 0, 0.5 -> 1, 0.02 -> 2, 0.005 -> 3
  function decimals(step) {
    if (!step || step >= 1) return 0;
    return Math.min(3, Math.ceil(-Math.log10(step) - 1e-9));
  }
  function fmt(v, step) { return Number(v).toFixed(decimals(step)); }

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function controls(params, values, onChange) {
    var wrap = el("div");
    params.forEach(function (p) {
      var row = el("div", "control");
      var lab = el("label");
      var val = el("span", "val");
      lab.appendChild(document.createTextNode(p.label + (p.unit ? " (" + p.unit + ")" : "")));
      lab.appendChild(val);
      row.appendChild(lab);
      var input;
      if (p.kind === "boolean") {
        var sw = el("div", "switchrow");
        input = document.createElement("input");
        input.type = "checkbox";
        input.checked = !!values[p.id];
        input.addEventListener("change", function () { onChange(p.id, input.checked); });
        sw.appendChild(input);
        var on = el("span");
        sw.appendChild(on);
        var sync = function () { on.textContent = input.checked ? "ON" : "OFF"; val.textContent = ""; };
        input.addEventListener("change", sync); sync();
        row.appendChild(sw);
      } else if (p.kind === "select") {
        input = document.createElement("select");
        p.choices.forEach(function (c) {
          var o = document.createElement("option");
          o.value = c.id; o.textContent = c.label;
          input.appendChild(o);
        });
        input.value = values[p.id];
        val.textContent = "";
        input.addEventListener("change", function () { onChange(p.id, input.value); });
        row.appendChild(input);
      } else {
        input = document.createElement("input");
        input.type = "range";
        input.min = p.min; input.max = p.max;
        input.step = p.kind === "integer" ? 1 : (p.step || (p.max - p.min) / 100);
        input.value = values[p.id];
        val.textContent = fmt(values[p.id], +input.step) + " " + (p.unit || "");
        input.addEventListener("input", function () {
          val.textContent = fmt(+input.value, +input.step) + " " + (p.unit || "");
          onChange(p.id, p.kind === "integer" ? parseInt(input.value, 10) : +input.value);
        });
        row.appendChild(input);
      }
      input.setAttribute("data-param", p.id);
      wrap.appendChild(row);
    });
    return wrap;
  }

  function valuesText(values) {
    return Object.keys(values).map(function (k) {
      var x = values[k];
      return k + " = " + (x === null ? "—" : x);
    }).join("   ");
  }

  /* Formula cards. update() takes either the server's formula list, or a
     list of {label, color, formula} sets (compare mode: one line per set).
     Values are matched to cards by expression, never by position. */
  function formulaPanel(formulas) {
    var wrap = el("div", "formulas");
    var nodes = {};
    formulas.forEach(function (f) {
      var d = el("div", "formula");
      d.appendChild(el("div", "expr", f.expr));
      d.appendChild(el("div", "legend", f.legend || ""));
      var v = el("div", "values");
      d.appendChild(v);
      wrap.appendChild(d);
      nodes[f.expr] = v;
    });
    return {
      el: wrap,
      update: function (data) {
        var sets = (data && data.length && data[0].formula) ? data : [{ formula: data || [] }];
        Object.keys(nodes).forEach(function (k) { nodes[k].innerHTML = ""; });
        sets.forEach(function (set) {
          (set.formula || []).forEach(function (f) {
            var node = nodes[f.expr];
            if (!node || !f.values) return;
            var line = el("div", "vline");
            if (set.label) {
              var tag = el("span", "ntag", set.label);
              tag.style.color = set.color || "";
              line.appendChild(tag);
            }
            line.appendChild(document.createTextNode(valuesText(f.values)));
            node.appendChild(line);
          });
        });
      }
    };
  }

  /* Learning panel: the big idea, then tabs for
       - formulas explained: live values + plain words + symbols + why + try-it
       - see it: simulation screenshots with numbered callouts and a
         "try this setup" deep link that loads exactly that moment's set-up
       - real life: where the same physics shows up in the world
     update() takes the same data as formulaPanel().update(). */
  function learnPanel(topic) {
    var L = topic.learn, wrap = el("section", "learn");
    var idea = el("div", "bigidea");
    idea.appendChild(el("div", "bi-label", "💡 The big idea"));
    idea.appendChild(el("p", null, L.big_idea));
    wrap.appendChild(idea);

    var tabs = el("div", "ltabs"), panes = [];
    [["📐 Formulas explained", "formulas"], ["🔍 See it in the simulation", "figs"],
     ["🌍 In real life", "life"]].forEach(function (tb, i) {
      var b = el("button", "ltab" + (i === 0 ? " on" : ""), tb[0]);
      b.type = "button";
      b.setAttribute("data-tab", tb[1]);
      b.addEventListener("click", function () {
        Array.prototype.forEach.call(tabs.children, function (x) { x.classList.remove("on"); });
        b.classList.add("on");
        panes.forEach(function (pn) { pn.hidden = pn.getAttribute("data-pane") !== tb[1]; });
      });
      tabs.appendChild(b);
    });
    wrap.appendChild(tabs);

    // ---- formulas ----
    var fp = el("div", "lpane"); fp.setAttribute("data-pane", "formulas");
    var nodes = {};
    topic.formulas.forEach(function (f, i) {
      var x = L.formulas[f.expr] || {};
      var card = el("div", "formula");
      var head = el("div", "fhead");
      head.appendChild(el("span", "fnum", String(i + 1)));
      head.appendChild(el("span", "expr", f.expr));
      card.appendChild(head);
      card.appendChild(el("div", "say", x.say || f.legend || ""));
      var v = el("div", "values");
      card.appendChild(el("div", "vlabel", "your numbers right now:"));
      card.appendChild(v);
      nodes[f.expr] = v;
      if (x.symbols && x.symbols.length) {
        var tbl = el("table", "symbols");
        x.symbols.forEach(function (row) {
          var tr = el("tr");
          tr.appendChild(el("td", "sym", row[0]));
          tr.appendChild(el("td", "mean", row[1]));
          tr.appendChild(el("td", "unit", row[2] || ""));
          tbl.appendChild(tr);
        });
        card.appendChild(tbl);
      }
      if (x.explain) card.appendChild(el("p", "explain", x.explain));
      if (x.try_it) {
        var tr2 = el("p", "tryit");
        tr2.appendChild(el("b", null, "🔬 Try it: "));
        tr2.appendChild(document.createTextNode(x.try_it));
        card.appendChild(tr2);
      }
      fp.appendChild(card);
    });
    panes.push(fp); wrap.appendChild(fp);

    // ---- figures ----
    var gp = el("div", "lpane"); gp.setAttribute("data-pane", "figs"); gp.hidden = true;
    (L.figures || []).forEach(function (fig, i) {
      var box = el("figure", "fig");
      box.appendChild(el("div", "figtitle", (i + 1) + " · " + fig.title));
      var shot = el("div", "shot");
      var img = el("img");
      img.src = fig.img; img.alt = fig.title; img.loading = "lazy";
      shot.appendChild(img);
      var badges = [];
      (fig.callouts || []).forEach(function (c, j) {
        var bd = el("span", "badge", String(j + 1));
        bd.style.left = (100 * c.x / 880) + "%";
        bd.style.top = (100 * c.y / 500) + "%";
        shot.appendChild(bd);
        badges.push(bd);
      });
      box.appendChild(shot);
      var ol = el("ol", "callouts");
      (fig.callouts || []).forEach(function (c, j) {
        var li = el("li", null, c.text);
        li.addEventListener("mouseenter", function () { badges[j].classList.add("hot"); });
        li.addEventListener("mouseleave", function () { badges[j].classList.remove("hot"); });
        ol.appendChild(li);
      });
      box.appendChild(ol);
      if (fig.caption) box.appendChild(el("figcaption", null, fig.caption));
      var go = el("button", "secondary small trybtn", "▶ Try this setup");
      go.type = "button";
      go.addEventListener("click", function () { goRoute(fig.route); });
      box.appendChild(go);
      gp.appendChild(box);
    });
    panes.push(gp); wrap.appendChild(gp);

    // ---- real life ----
    var rp = el("div", "lpane"); rp.setAttribute("data-pane", "life"); rp.hidden = true;
    var grid = el("div", "life");
    (L.real_life || []).forEach(function (u) {
      var c = el("div", "usecase");
      var h = el("div", "uhead");
      h.appendChild(el("span", "uicon", u.icon));
      h.appendChild(el("span", "utitle", u.title));
      c.appendChild(h);
      c.appendChild(el("p", null, u.text));
      if (u.formula) c.appendChild(el("div", "ulink", "↳ " + u.formula));
      grid.appendChild(c);
    });
    rp.appendChild(grid);
    panes.push(rp); wrap.appendChild(rp);

    return {
      el: wrap,
      update: function (data) {
        var sets = (data && data.length && data[0].formula) ? data : [{ formula: data || [] }];
        Object.keys(nodes).forEach(function (k) { nodes[k].innerHTML = ""; });
        sets.forEach(function (set) {
          (set.formula || []).forEach(function (f) {
            var node = nodes[f.expr];
            if (!node || !f.values) return;
            var line = el("div", "vline");
            if (set.label) {
              var tag = el("span", "ntag", set.label);
              tag.style.color = set.color || "";
              line.appendChild(tag);
            }
            line.appendChild(document.createTextNode(valuesText(f.values)));
            node.appendChild(line);
          });
        });
      }
    };
  }

  function readouts(items) {
    var grid = el("div", "readouts");
    (items || []).forEach(function (r) {
      var d = el("div", "readout");
      d.appendChild(el("div", "k", r.label));
      d.appendChild(el("div", "v", r.value + (r.unit ? " " + r.unit : "")));
      grid.appendChild(d);
    });
    return grid;
  }

  /* compare mode: one row per readout label, one column per run */
  function readoutTable(sets) {
    var table = el("table", "rtable");
    var head = el("tr");
    head.appendChild(el("th", null, ""));
    sets.forEach(function (s) {
      var th = el("th", null, s.label);
      th.style.color = s.color;
      head.appendChild(th);
    });
    table.appendChild(head);
    (sets[0].readouts || []).forEach(function (r, i) {
      var tr = el("tr");
      tr.appendChild(el("td", "k", r.label));
      sets.forEach(function (s) {
        var x = s.readouts[i];
        tr.appendChild(el("td", "v", x ? x.value + (x.unit ? " " + x.unit : "") : "—"));
      });
      table.appendChild(tr);
    });
    return table;
  }

  function notes(list) {
    var wrap = el("div", "notes");
    (list || []).forEach(function (n) {
      var d = el("div", "note");
      if (n.label) {
        var tag = el("span", "ntag", n.label);
        tag.style.color = n.color || "";
        d.appendChild(tag);
      }
      d.appendChild(document.createTextNode(n.text));
      wrap.appendChild(d);
    });
    return wrap;
  }

  /* small segmented control for client-side view options */
  function segmented(opt, value, onPick) {
    var wrap = el("div", "seg");
    wrap.appendChild(el("span", "seg-label", opt.label));
    opt.choices.forEach(function (c) {
      var b = el("button", "seg-btn" + (c.id === value ? " on" : ""), c.label);
      b.type = "button";
      b.addEventListener("click", function () {
        Array.prototype.forEach.call(wrap.querySelectorAll(".seg-btn"), function (x) {
          x.classList.remove("on");
        });
        b.classList.add("on");
        onPick(c.id);
      });
      wrap.appendChild(b);
    });
    return wrap;
  }

  /* =================== simulation page components ===================
     Each is a small object {el, ...methods}; main.js composes them.    */
  var RUN_COLORS = ["#ff9a5c", "#5cd6ff"], RUN_LABELS = ["A", "B"];

  /* the two-column page skeleton every experiment uses */
  function simLayout(topic, onBack) {
    var L = { root: el("div", "sim"), left: el("div", "panel"), right: el("div") };
    var back = el("button", "secondary back", "← all experiments");
    back.addEventListener("click", onBack);
    var h2 = el("h2", null, topic.title);
    var hicon = el("img", "hicon"); hicon.src = "icons/icon_" + topic.icon + ".png"; hicon.alt = "";
    h2.insertBefore(hicon, h2.firstChild);
    L.left.appendChild(back); L.left.appendChild(h2); L.left.appendChild(el("div", "blurb", topic.blurb));
    ["presets", "compare", "controls"].forEach(function (k) {
      L[k] = el("div", k === "compare" ? "compare" : null); L.left.appendChild(L[k]);
    });
    ["stage", "playbar", "notes", "results", "learn"].forEach(function (k) {
      L[k] = el("div"); L.right.appendChild(L[k]);
    });
    L.root.appendChild(L.left); L.root.appendChild(L.right);
    return L;
  }

  /* one-click set-ups: [{title, route}] -> deep links */
  function presetBar(presets) {
    var wrap = el("div", "presets");
    if (!presets || !presets.length) return wrap;
    wrap.appendChild(el("div", "plabel", "⚡ Presets"));
    var row = el("div", "chips");
    presets.forEach(function (pr) {
      var b = el("button", "chip", pr.title);
      b.type = "button";
      b.title = pr.hint || "";
      b.addEventListener("click", function () { goRoute(pr.route); });
      row.appendChild(b);
    });
    wrap.appendChild(row);
    return wrap;
  }

  /* navigate to a deep link, re-running it even if it is the current one */
  function goRoute(route) {
    if (location.hash === route) window.dispatchEvent(new HashChangeEvent("hashchange"));
    else location.hash = route;
  }

  /* parameter sliders for the active set of a model {sets, active, compare} */
  function ControlPanel(topic, model, onParam) {
    var wrap = el("div");
    return {
      el: wrap,
      render: function () {
        wrap.innerHTML = "";
        var set = model.sets[model.active];
        var box = controls(topic.params, set, function (id, v) { set[id] = v; onParam(id, v); });
        if (model.compare) {
          box.className = "runctl";
          box.style.setProperty("--run", RUN_COLORS[model.active]);
        }
        wrap.appendChild(box);
      }
    };
  }

  /* A/B compare: toggle, tabs, fair-test hint, copy A -> B.
     onChange(kind): "toggle" | "tab" | "copy" */
  function ComparePanel(topic, model, onChange) {
    var wrap = el("div"), noun = typeof topic.compare === "string" ? topic.compare : "set-up";
    var api = {
      el: wrap, noun: noun,
      render: function () {
        wrap.innerHTML = "";
        if (!topic.compare) return;
        var row = el("label", "cmp-toggle");
        var cb = el("input"); cb.type = "checkbox"; cb.checked = model.compare;
        row.appendChild(cb);
        row.appendChild(document.createTextNode(" Compare two " + noun + "s"));
        wrap.appendChild(row);
        cb.addEventListener("change", function () {
          model.compare = cb.checked;
          if (model.compare) {          // B starts as an exact copy: change ONE thing
            model.sets[1] = JSON.parse(JSON.stringify(model.sets[0]));
            model.active = 1;
          } else {
            model.sets.length = 1; model.active = 0;
          }
          api.render(); onChange("toggle");
        });
        if (!model.compare) return;
        var tabs = el("div", "tabs");
        model.sets.forEach(function (_, i) {
          var b = el("button", "tab" + (i === model.active ? " on" : ""),
                     "● " + noun.charAt(0).toUpperCase() + noun.slice(1) + " " + RUN_LABELS[i]);
          b.type = "button";
          b.style.setProperty("--run", RUN_COLORS[i]);
          b.addEventListener("click", function () { model.active = i; api.render(); onChange("tab"); });
          tabs.appendChild(b);
        });
        wrap.appendChild(tabs);
        wrap.appendChild(el("div", "diff"));
        var copy = el("button", "secondary small", "copy A's settings → B");
        copy.type = "button";
        copy.addEventListener("click", function () {
          model.sets[1] = JSON.parse(JSON.stringify(model.sets[0]));
          api.updateDiff(); onChange("copy");
        });
        wrap.appendChild(copy);
        api.updateDiff();
      },
      updateDiff: function () {
        var d = wrap.querySelector(".diff");
        if (!d || !model.compare) return;
        var changed = topic.params.filter(function (p) {
          return model.sets[0][p.id] !== model.sets[1][p.id];
        }).map(function (p) { return p.label.replace(/\s*\(.*\)$/, "").toLowerCase(); });
        d.textContent = changed.length === 0 ? "A and B are identical - change something in B."
          : changed.length === 1 ? "Fair test: only the " + changed[0] + " differs."
          : "Differs in " + changed.length + " things: " + changed.join(", ") +
            ". (Change just one to see what it does.)";
        d.className = "diff" + (changed.length === 1 ? " fair" : "");
      }
    };
    return api;
  }

  /* play / reset + the scene's view toggles */
  function PlayBar(options, view, on) {
    var row = el("div", "playrow");
    var play = el("button", null, "▶ run");
    var reset = el("button", "secondary", "↺ reset");
    play.addEventListener("click", on.play);
    reset.addEventListener("click", on.reset);
    row.appendChild(play); row.appendChild(reset);
    (options || []).forEach(function (o) {
      row.appendChild(segmented(o, view[o.id], function (v) { view[o.id] = v; on.view(o.id, v); }));
    });
    return { el: row, setLabel: function (t) { play.textContent = t; } };
  }

  /* engine notes + readouts (a table in compare mode) */
  function ResultsPanel() {
    var notesBox = el("div"), readBox = el("div");
    return {
      notes: notesBox, readouts: readBox,
      update: function (runs, noun) {
        var multi = runs.length > 1, list = [];
        runs.forEach(function (r) {
          (r.result.notes || []).forEach(function (n) {
            list.push({ label: multi ? noun + " " + r.label : "", color: r.color, text: n });
          });
        });
        notesBox.innerHTML = "";
        if (list.length) notesBox.appendChild(notes(list));
        readBox.innerHTML = "";
        readBox.appendChild(multi
          ? readoutTable(runs.map(function (r) {
              return { label: noun + " " + r.label, color: r.color, readouts: r.result.readouts };
            }))
          : readouts(runs[0].result.readouts));
      },
      error: function (msg) {
        readBox.innerHTML = "";
        readBox.appendChild(el("div", "blurb", "could not run: " + msg));
      }
    };
  }

  var ICONS = { battery: "🔋", ball: "🎯", flame: "🔥", water: "💧", wave: "🌊", pendulum: "⏱️", eye: "👁️", press: "🛠️", bolt: "⚡" };

  function topicIcon(t) {
    var img = document.createElement("img");
    img.className = "ticon";
    img.src = "icons/icon_" + t.icon + ".png";
    img.alt = t.title;
    img.addEventListener("error", function () {
      var s = el("div", "icon", ICONS[t.icon] || "🔬");
      img.replaceWith(s);
    });
    return img;
  }

  function topicCards(topics, onPick) {
    var grid = el("div", "cards");
    topics.forEach(function (t) {
      var c = el("div", "card " + (t.status === "ready" ? "ready" : "placeholder"));
      c.appendChild(topicIcon(t));
      c.appendChild(el("h3", null, t.title));
      c.appendChild(el("p", null, t.blurb));
      c.appendChild(el("div", "status " + (t.status === "ready" ? "ready" : "soon"),
        t.status === "ready" ? "● READY TO PLAY" : "◐ COMING SOON"));
      c.appendChild(el("div", "formula-preview",
        (t.formulas && t.formulas[0] && t.formulas[0].expr) || ""));
      if (t.status === "ready") c.addEventListener("click", function () { onPick(t); });
      grid.appendChild(c);
    });
    return grid;
  }

  window.PL.ui = { simLayout: simLayout, presetBar: presetBar, goRoute: goRoute, ControlPanel: ControlPanel,
                   ComparePanel: ComparePanel, PlayBar: PlayBar, ResultsPanel: ResultsPanel,
                   RUN_COLORS: RUN_COLORS, RUN_LABELS: RUN_LABELS,
                   controls: controls, formulaPanel: formulaPanel, learnPanel: learnPanel, readouts: readouts,
                   readoutTable: readoutTable, notes: notes, segmented: segmented,
                   topicCards: topicCards, fmt: fmt, el: el };
})();
