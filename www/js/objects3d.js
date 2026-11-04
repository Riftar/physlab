/* physlab software 3D kit - mesh primitives, rotation, perspective
   projection, painter's-algorithm faces with Lambert shading.
   Pure canvas 2D: no WebGL, no libraries. Scene painters feed on this. */
(function () {
  "use strict";
  window.PL = window.PL || {};

  function box(w, h, d) {
    var x = w / 2, y = h / 2, z = d / 2;
    return {
      verts: [[-x, -y, -z], [x, -y, -z], [x, y, -z], [-x, y, -z],
              [-x, -y, z], [x, -y, z], [x, y, z], [-x, y, z]],
      faces: [[0, 1, 2, 3], [5, 4, 7, 6], [4, 0, 3, 7], [1, 5, 6, 2], [4, 5, 1, 0], [3, 2, 6, 7]]
    };
  }

  function cylinder(r, h, seg) {
    seg = seg || 12;
    var verts = [], faces = [], i, a;
    for (i = 0; i < seg; i++) {
      a = (i / seg) * Math.PI * 2;
      verts.push([Math.cos(a) * r, -h / 2, Math.sin(a) * r]);
    }
    for (i = 0; i < seg; i++) {
      a = (i / seg) * Math.PI * 2;
      verts.push([Math.cos(a) * r, h / 2, Math.sin(a) * r]);
    }
    for (i = 0; i < seg; i++) {
      faces.push([i, (i + 1) % seg, seg + (i + 1) % seg, seg + i]);
    }
    var top = [], bot = [];
    for (i = 0; i < seg; i++) { top.push(seg + i); bot.push(seg - 1 - i); }
    faces.push(top, bot);
    return { verts: verts, faces: faces };
  }

  function sphere(r, seg) {
    seg = seg || 10;
    var verts = [], faces = [], la, lo, i, j;
    for (la = 0; la <= seg; la++) {
      var phi = (la / seg) * Math.PI;
      for (lo = 0; lo < seg; lo++) {
        var th = (lo / seg) * Math.PI * 2;
        verts.push([r * Math.sin(phi) * Math.cos(th), r * Math.cos(phi), r * Math.sin(phi) * Math.sin(th)]);
      }
    }
    for (la = 0; la < seg; la++) {
      for (lo = 0; lo < seg; lo++) {
        var a = la * seg + lo, b = la * seg + (lo + 1) % seg;
        var c = (la + 1) * seg + (lo + 1) % seg, d = (la + 1) * seg + lo;
        faces.push([a, b, c, d]);
      }
    }
    return { verts: verts, faces: faces };
  }

  function rot(v, ry, rx) {
    var x = v[0], y = v[1], z = v[2], t;
    if (ry) { var cy = Math.cos(ry), sy = Math.sin(ry); t = x; x = x * cy - z * sy; z = t * sy + z * cy; }
    if (rx) { var cx = Math.cos(rx), sx = Math.sin(rx); t = y; y = y * cx - z * sx; z = t * sx + z * cx; }
    return [x, y, z];
  }

  function shade(hex, k) {
    k = Math.max(0.25, Math.min(1.25, k));
    var n = parseInt(hex.slice(1), 16),
        r = Math.min(255, Math.round(((n >> 16) & 255) * k)),
        g = Math.min(255, Math.round(((n >> 8) & 255) * k)),
        b = Math.min(255, Math.round((n & 255) * k));
    return "rgb(" + r + "," + g + "," + b + ")";
  }

  /* mesh: {verts, faces}; opts: {ry, rx, x, y, scale, cam:{cx,cy,fov,dist}, color, stroke} */
  function draw(ctx, mesh, opts) {
    var cam = opts.cam, s = opts.scale || 1;
    var pts = mesh.verts.map(function (v) {
      var r = rot([v[0] * s, v[1] * s, v[2] * s], opts.ry || 0, opts.rx || 0);
      r[0] += opts.x || 0; r[1] += opts.y || 0;
      var k = cam.fov / (cam.dist + r[2]);
      return [cam.cx + r[0] * k, cam.cy - r[1] * k, r[2]];
    });
    var order = mesh.faces.map(function (f, i) {
      var z = f.reduce(function (a, ix) { return a + pts[ix][2]; }, 0) / f.length;
      return [z, i];
    }).sort(function (a, b) { return b[0] - a[0]; });
    var L = rot([0.4, 0.8, 0.45], opts.ry || 0, opts.rx || 0);
    order.forEach(function (o) {
      var f = mesh.faces[o[1]];
      var A = pts[f[0]], B = pts[f[1]], C = pts[f[2]];
      var u = [B[0] - A[0], B[1] - A[1]], v = [C[0] - A[0], C[1] - A[1]];
      var nz = u[0] * v[1] - u[1] * v[0];
      var zc = o[0];
      var backface = (zc > 0) ? nz < 0 : nz > 0;
      if (backface && f.length <= 4) return;   // cheap cull, caps/faces still fine
      var lum = Math.abs(nz) / (Math.hypot(u[0], u[1]) * Math.hypot(v[0], v[1]) + 1e-9);
      lum = 0.45 + 0.55 * Math.min(1, lum * 1.6 + (L[1] > 0 ? 0.08 : 0));
      ctx.beginPath();
      ctx.moveTo(pts[f[0]][0], pts[f[0]][1]);
      for (var i = 1; i < f.length; i++) ctx.lineTo(pts[f[i]][0], pts[f[i]][1]);
      ctx.closePath();
      ctx.fillStyle = shade(opts.color, lum);
      ctx.fill();
      if (opts.stroke) { ctx.strokeStyle = opts.stroke; ctx.lineWidth = 1; ctx.stroke(); }
    });
  }

  window.PL.obj3d = { box: box, cylinder: cylinder, sphere: sphere, draw: draw, shade: shade };
})();
