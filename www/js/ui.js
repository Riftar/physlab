/* physlab ui kit - data-driven controls, formula panel, topic cards.
   A new topic's params spec drives this whole panel: no per-topic UI code. */
(function () {
  "use strict";
  window.PL = window.PL || {};

  function fmt(v, step) {
    var d = step && step >= 1 ? 0 : step && step >= 0.1 ? 1 : 2;
    return Number(v).toFixed(d);
  }

  function controls(params, values, onChange) {
    var wrap = document.createElement("div");
    params.forEach(function (p) {
      var row = document.createElement("div");
      row.className = "control";
      var lab = document.createElement("label");
      var val = document.createElement("span");
      val.className = "val";
      lab.appendChild(document.createTextNode(p.label + (p.unit ? " (" + p.unit + ")" : "")));
      lab.appendChild(val);
      row.appendChild(lab);
      var input;
      if (p.kind === "boolean") {
        var sw = document.createElement("div");
        sw.className = "switchrow";
        input = document.createElement("input");
        input.type = "checkbox";
        input.checked = !!values[p.id];
        input.addEventListener("change", function () { onChange(p.id, input.checked); });
        sw.appendChild(input);
        var on = document.createElement("span");
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
      wrap.appendChild(row);
    });
    return wrap;
  }

  function formulaPanel(formulas) {
    var wrap = document.createElement("div");
    wrap.className = "formulas";
    var nodes = formulas.map(function (f) {
      var d = document.createElement("div");
      d.className = "formula";
      var e = document.createElement("div"); e.className = "expr"; e.textContent = f.expr;
      var l = document.createElement("div"); l.className = "legend"; l.textContent = f.legend || "";
      var v = document.createElement("div"); v.className = "values"; v.textContent = "";
      d.appendChild(e); d.appendChild(l); d.appendChild(v);
      wrap.appendChild(d);
      return { values: v };
    });
    return {
      el: wrap,
      update: function (formulaData) {
        (formulaData || []).forEach(function (f, i) {
          if (!nodes[i] || !f.values) return;
          var parts = Object.keys(f.values).map(function (k) {
            var x = f.values[k];
            return k + " = " + (x === null ? "—" : x);
          });
          nodes[i].values.textContent = parts.join("   ");
        });
      }
    };
  }

  function readouts(items) {
    var grid = document.createElement("div");
    grid.className = "readouts";
    (items || []).forEach(function (r) {
      var d = document.createElement("div");
      d.className = "readout";
      var k = document.createElement("div"); k.className = "k"; k.textContent = r.label;
      var v = document.createElement("div"); v.className = "v";
      v.textContent = r.value + (r.unit ? " " + r.unit : "");
      d.appendChild(k); d.appendChild(v); grid.appendChild(d);
    });
    return grid;
  }

  var ICONS = { battery: "🔋", ball: "🎯", flame: "🔥", water: "💧", wave: "🌊", pendulum: "⏱️", eye: "👁️", press: "🛠️", bolt: "⚡" };

  function topicIcon(t) {
    var img = document.createElement("img");
    img.className = "ticon";
    img.src = "icons/icon_" + t.icon + ".png";
    img.alt = t.title;
    img.addEventListener("error", function () {
      var s = document.createElement("div");
      s.className = "icon";
      s.textContent = ICONS[t.icon] || "🔬";
      img.replaceWith(s);
    });
    return img;
  }

  function topicCards(topics, onPick) {
    var grid = document.createElement("div");
    grid.className = "cards";
    topics.forEach(function (t) {
      var c = document.createElement("div");
      c.className = "card " + (t.status === "ready" ? "ready" : "placeholder");
      c.appendChild(topicIcon(t));
      var h = document.createElement("h3"); h.textContent = t.title;
      var p = document.createElement("p"); p.textContent = t.blurb;
      var st = document.createElement("div");
      st.className = "status " + (t.status === "ready" ? "ready" : "soon");
      st.textContent = t.status === "ready" ? "● READY TO PLAY" : "◐ COMING SOON";
      var f = document.createElement("div"); f.className = "formula-preview";
      f.textContent = (t.formulas && t.formulas[0] && t.formulas[0].expr) || "";
      c.appendChild(h); c.appendChild(p); c.appendChild(st); c.appendChild(f);
      if (t.status === "ready") c.addEventListener("click", function () { onPick(t); });
      grid.appendChild(c);
    });
    return grid;
  }

  window.PL.ui = { controls: controls, formulaPanel: formulaPanel, readouts: readouts, topicCards: topicCards };
})();
