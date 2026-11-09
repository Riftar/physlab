"""Lenses: a candle, a glass lens and the image it makes.

All lengths are in centimetres; the lens sits at x = 0, light travels
in +x, the candle stands on the axis at x = -d_o. Sign convention
("real is positive"): d_i > 0 is a real image on the far side, d_i < 0 a
virtual image on the candle's side; f > 0 converging, f < 0 diverging.

* lensmaker's equation   1/f = (n - 1) (1/R1 - 1/R2)
  a symmetric lens: converging R1 = +R, R2 = -R -> f = R / (2 (n - 1));
  diverging R1 = -R, R2 = +R -> f = -R / (2 (n - 1))
* thin-lens equation     1/f = 1/d_o + 1/d_i
* magnification          m = h_i / h_o = -d_i / d_o
* speed of light in glass v = c / n; lens power P = 1/f (dioptres, f in m)

Two kinds of rays are returned:
  principal rays  the three textbook rays of the thin-lens model (through
                  the middle; parallel -> through the focus; through the
                  focus -> parallel), bending once at the lens plane
  real rays       a fan from the candle's tip traced through the ACTUAL
                  thick lens - two spherical surfaces - with Snell's law
                  n1 sin(i) = n2 sin(r) at each surface (total internal
                  reflection handled). Where they cross shows how good the
                  thin-lens formula is (and spherical aberration).
"""

import math

C_LIGHT = 299792.458          # km/s
APERTURE = 5.0                # lens half-height, cm
EDGE = 0.3                    # converging lens: thickness at the rim, cm
CENTRE_THIN = 0.4             # diverging lens: thickness in the middle, cm
FAN = 9                       # real rays in the fan
LOOP = 4.0                    # seconds of light animation before it repeats


# ---------------- formulas ----------------

def lensmaker(n, r1, r2):
    """1/f from the lensmaker's equation (thin lens, in air)."""
    return (n - 1.0) * (1.0 / r1 - 1.0 / r2)


def focal_length(n, radius, kind):
    r1, r2 = (radius, -radius) if kind == "converging" else (-radius, radius)
    return 1.0 / lensmaker(n, r1, r2)


def image_distance(f, d_o):
    """Thin-lens equation solved for d_i; None when the image is at
    infinity (object exactly at the focal point)."""
    inv = 1.0 / f - 1.0 / d_o
    if abs(inv) < 1e-12:
        return None
    return 1.0 / inv


def magnification(d_o, d_i):
    return -d_i / d_o


def power_dioptres(f_cm):
    return 100.0 / f_cm


def light_speed(n):
    return C_LIGHT / n


# ---------------- lens geometry ----------------

def geometry(radius, kind):
    """Surfaces of the real (thick) lens: vertices x1 < x2, centres of
    curvature c1, c2 (on the axis) and the outline polygon."""
    a = APERTURE
    sag = radius - math.sqrt(radius * radius - a * a)
    if kind == "converging":
        t = 2.0 * sag + EDGE
        x1, x2 = -t / 2.0, t / 2.0
        c1, c2 = x1 + radius, x2 - radius
        front = lambda y: c1 - math.sqrt(radius * radius - y * y)
        back = lambda y: c2 + math.sqrt(radius * radius - y * y)
        edge = EDGE
    else:
        t = CENTRE_THIN
        x1, x2 = -t / 2.0, t / 2.0
        c1, c2 = x1 - radius, x2 + radius
        front = lambda y: c1 + math.sqrt(radius * radius - y * y)
        back = lambda y: c2 - math.sqrt(radius * radius - y * y)
        edge = CENTRE_THIN + 2.0 * sag
    ys = [a - 2.0 * a * i / 24.0 for i in range(25)]
    outline = [[round(front(y), 4), round(y, 4)] for y in ys] + \
              [[round(back(y), 4), round(y, 4)] for y in reversed(ys)]
    return {"R": radius, "a": a, "sag": sag, "t": t, "edge": edge,
            "x1": x1, "x2": x2, "c1": c1, "c2": c2, "outline": outline}


# ---------------- Snell's law ray tracing ----------------

def refract(d, nrm, n1, n2):
    """Vector Snell's law. d: unit direction; nrm: unit surface normal
    pointing back towards the incoming side. Returns (new_dir, reflected)."""
    cosi = -(d[0] * nrm[0] + d[1] * nrm[1])
    eta = n1 / n2
    k = 1.0 - eta * eta * (1.0 - cosi * cosi)
    if k < 0.0:                                   # total internal reflection
        return (d[0] + 2.0 * cosi * nrm[0], d[1] + 2.0 * cosi * nrm[1]), True
    c = eta * cosi - math.sqrt(k)
    return (eta * d[0] + c * nrm[0], eta * d[1] + c * nrm[1]), False


def _hit(p, d, centre, radius, side):
    """Nearest intersection of the ray with one lens surface: the sphere
    around (centre, 0), restricted to the lens aperture and to the front
    (x < 0) or back (x > 0) half. Returns (s, point) or None."""
    ox, oy = p[0] - centre, p[1]
    b = d[0] * ox + d[1] * oy
    c = ox * ox + oy * oy - radius * radius
    disc = b * b - c
    if disc < 0.0:
        return None
    best = None
    for s in (-b - math.sqrt(disc), -b + math.sqrt(disc)):
        if s <= 1e-9:
            continue
        q = (p[0] + s * d[0], p[1] + s * d[1])
        if abs(q[1]) > APERTURE + 1e-9 or (side == "front" and q[0] > 0) or (side == "back" and q[0] < 0):
            continue
        if best is None or s < best[0]:
            best = (s, q)
    return best


def _normal(q, centre, d):
    nx, ny = q[0] - centre, q[1]
    m = math.hypot(nx, ny)
    nx, ny = nx / m, ny / m
    if nx * d[0] + ny * d[1] > 0.0:               # point it back at the incoming ray
        nx, ny = -nx, -ny
    return (nx, ny)


def trace(start, d, geo, n, x_end):
    """Trace one ray from `start` (direction d) through the thick lens.
    Returns {pts, n (index per segment), exits, tir}."""
    m = math.hypot(*d)
    d = (d[0] / m, d[1] / m)
    pts, idx = [list(start)], []
    hit = _hit(start, d, geo["c1"], geo["R"], "front")
    if hit is None:                               # misses the lens
        s = (x_end - start[0]) / d[0] if d[0] > 0 else 0.0
        pts.append([start[0] + s * d[0], start[1] + s * d[1]])
        return {"pts": pts, "n": [1.0], "exits": False, "tir": False, "missed": True}
    q = hit[1]
    pts.append(list(q)); idx.append(1.0)
    d, tir = refract(d, _normal(q, geo["c1"], d), 1.0, n)
    p, inside, bounces, any_tir = q, True, 0, tir
    while inside and bounces < 6:
        cands = [h + (c, side) for h, c, side in
                 ((_hit(p, d, geo["c2"], geo["R"], "back"), geo["c2"], "back"),
                  (_hit(p, d, geo["c1"], geo["R"], "front"), geo["c1"], "front")) if h]
        if not cands:                              # runs into the rim
            return {"pts": pts, "n": idx, "exits": False, "tir": any_tir, "missed": False}
        s, q, centre, side = min(cands, key=lambda c: c[0])
        pts.append(list(q)); idx.append(n)
        nd, tir = refract(d, _normal(q, centre, d), n, 1.0)
        any_tir = any_tir or tir
        d, p, bounces = nd, q, bounces + 1
        inside = tir
    if inside:
        return {"pts": pts, "n": idx, "exits": False, "tir": True, "missed": False}
    s = (x_end - p[0]) / d[0] if d[0] > 1e-9 else 50.0
    pts.append([p[0] + s * d[0], p[1] + s * d[1]]); idx.append(1.0)
    return {"pts": pts, "n": idx, "exits": True, "tir": any_tir, "missed": False}


def crossing(lines):
    """Least-squares meeting point of lines [(point, direction)], or None."""
    a11 = a12 = a22 = b1 = b2 = 0.0
    for (px, py), (dx, dy) in lines:
        m = math.hypot(dx, dy)
        dx, dy = dx / m, dy / m
        m11, m12, m22 = 1 - dx * dx, -dx * dy, 1 - dy * dy        # projector I - d d^T
        a11 += m11; a12 += m12; a22 += m22
        b1 += m11 * px + m12 * py; b2 += m12 * px + m22 * py
    det = a11 * a22 - a12 * a12
    if abs(det) < 1e-12:
        return None
    return ((a22 * b1 - a12 * b2) / det, (a11 * b2 - a12 * b1) / det)


# ---------------- principal rays ----------------

def principal_rays(f, d_o, h_o, d_i, x_end):
    """The three thin-lens rays from the candle's tip. Each: pts (real
    path), virt (dashed back-extension to a virtual image) or None."""
    tip = (-d_o, h_o)
    rays = []

    def emerge(name, y_lens, slope):
        real = [list(tip), [0.0, y_lens], [x_end, y_lens + slope * x_end]]
        virt = None
        if d_i is not None and d_i < 0:
            virt = [[0.0, y_lens], [d_i, y_lens + slope * d_i]]
        rays.append({"name": name, "pts": [[round(x, 4), round(y, 4)] for x, y in real],
                     "virt": [[round(x, 4), round(y, 4)] for x, y in virt] if virt else None,
                     "outside": abs(y_lens) > APERTURE})

    emerge("parallel", h_o, -h_o / f)            # parallel in -> through the focus
    emerge("centre", 0.0, -h_o / d_o)            # straight through the middle
    if abs(f - d_o) > 1e-9:                      # through the focus -> parallel out
        y3 = h_o * f / (f - d_o)
        if abs(y3) <= 4.0 * APERTURE:
            emerge("focal", y3, 0.0)
    return rays


# ---------------- run ----------------

def run(p):
    from .. import GLASSES
    glass = next(g for g in GLASSES if g["id"] == p["material"])
    n, radius, kind = glass["n"], p["radius"], p["kind"]
    d_o, h_o = p["d_o"], p["h_o"]
    f = focal_length(n, radius, kind)
    d_i = image_distance(f, d_o)
    m = magnification(d_o, d_i) if d_i is not None else None
    h_i = m * h_o if m is not None else None
    geo = geometry(radius, kind)

    # world box (cm): candle, lens, both focal points and the image (capped)
    x_left = -d_o - 8.0
    x_right = max(2.2 * abs(f), 25.0)
    if d_i is not None and 0 < d_i <= 400:
        x_right = max(x_right, d_i + 12.0)
    if d_i is not None and d_i < 0:
        x_left = min(x_left, d_i - 8.0)
        x_right = max(x_right, 30.0)               # room for the eye
    ymax = max(h_o, APERTURE, min(abs(h_i), 40.0) if h_i is not None else 0.0) * 1.3
    x_end = x_right + 200.0                        # rays run off the view

    rays = principal_rays(f, d_o, h_o, d_i, x_end)
    tip = (-d_o, h_o)
    fan, lines_par, lines_all = [], [], []
    for k in range(FAN):
        y_aim = -0.9 * APERTURE + 1.8 * APERTURE * k / (FAN - 1)
        r = trace(tip, (geo["x1"] - tip[0], y_aim - tip[1]), geo, n, x_end)
        fan.append({"pts": [[round(x, 4), round(y, 4)] for x, y in r["pts"]], "n": r["n"],
                    "exits": r["exits"], "tir": r["tir"], "aim": round(y_aim, 3)})
        if r["exits"]:
            a, b = r["pts"][-2], r["pts"][-1]
            line = ((a[0], a[1]), (b[0] - a[0], b[1] - a[1]))
            lines_all.append(line)
            if abs(y_aim) <= 0.35 * APERTURE:
                lines_par.append(line)
    focus = crossing(lines_par) if len(lines_par) >= 2 else None

    if d_i is None:
        kind_txt = "no image: the rays leave parallel"
    else:
        kind_txt = "%s, %s, %.2gx %s" % ("real" if d_i > 0 else "virtual",
                                        "upside down" if m < 0 else "upright",
                                        abs(m), "bigger" if abs(m) > 1 else "smaller")
    notes = []
    if d_i is None:
        notes.append("The candle is exactly at the focal point: the rays come out parallel and never "
                     "meet, so there is no image - that's how a torch or lighthouse makes a beam.")
    elif d_i < 0:
        notes.append("Virtual image: the rays spread out after the lens and never really meet. Your eye "
                     "traces them back (dashed lines) and sees an upright image behind the lens - a "
                     "magnifying glass." if kind == "converging" else
                     "A diverging lens always makes a small, upright, virtual image: the rays spread out "
                     "as if they came from a point in front of the lens.")
    else:
        notes.append("Real image: the rays really meet here. Hold a screen at %.1f cm and an upside-down "
                     "picture of the candle appears - that's how projectors and cameras work." % d_i)
    if d_i is not None and abs(d_i) > 400:
        notes.append("The image is %.1f m away - zoom out, or move the candle away from the focal point."
                     % (abs(d_i) / 100.0))
    if focus is not None and d_i is not None and d_i > 0 and abs(focus[0] - d_i) > 0.03 * d_i:
        notes.append("Real rays (Snell's law through the thick glass) meet at %.1f cm, not %.1f cm: the "
                     "thin-lens formula is a good approximation, not exact." % (focus[0], d_i))
    if any(r["tir"] for r in fan):
        notes.append("Some rays hit the glass so steeply that they reflect inside instead of leaving "
                     "(total internal reflection) - diamond sparkles for the same reason.")

    def r2(x, nd=3):
        return None if x is None else round(x, nd)

    return {
        "frames": [{"t": 0.0}, {"t": LOOP}],
        "notes": notes,
        "viz": {"kind": kind, "n": n, "glass": glass["label"], "f": r2(f, 4), "d_o": d_o, "h_o": h_o,
                "d_i": r2(d_i, 4), "m": r2(m, 5), "h_i": r2(h_i, 4),
                "image": "none" if d_i is None else ("real" if d_i > 0 else "virtual"),
                "lens": {k: (round(v, 5) if isinstance(v, float) else v) for k, v in geo.items()},
                "rays": rays, "fan": fan,
                "focus": [round(focus[0], 4), round(focus[1], 4)] if focus else None,
                "box": {"x0": round(x_left, 3), "x1": round(x_right, 3),
                        "y0": round(-ymax, 3), "y1": round(ymax, 3)},
                "v_light": round(light_speed(n), 1), "loop": LOOP},
        "readouts": [
            {"label": "Focal length f", "value": round(f, 2), "unit": "cm"},
            {"label": "Lens power P = 1/f", "value": round(power_dioptres(f), 2), "unit": "dioptres"},
            {"label": "Image distance d_i", "value": round(d_i, 2) if d_i is not None else "∞",
             "unit": "cm" + (" (virtual: same side as the candle)" if d_i is not None and d_i < 0 else "")},
            {"label": "Magnification m", "value": round(m, 3) if m is not None else "—", "unit": ""},
            {"label": "Image height h_i", "value": round(h_i, 2) if h_i is not None else "—", "unit": "cm"},
            {"label": "The image is", "value": kind_txt, "unit": ""},
            {"label": "Speed of light in the lens", "value": int(round(light_speed(n))),
             "unit": "km/s (%.0f%% of c)" % (100.0 / n)},
        ],
        "formula": [
            {"expr": "1/f = (n - 1) * (1/R1 - 1/R2)",
             "values": {"n": n, "R1": radius if kind == "converging" else -radius,
                        "R2": -radius if kind == "converging" else radius, "f": round(f, 2)}},
            {"expr": "1/f = 1/d_o + 1/d_i",
             "values": {"f": round(f, 2), "d_o": d_o, "d_i": round(d_i, 2) if d_i is not None else None}},
            {"expr": "m = -d_i / d_o = h_i / h_o",
             "values": {"m": round(m, 3) if m is not None else None, "h_o": h_o,
                        "h_i": round(h_i, 2) if h_i is not None else None}},
            {"expr": "n = c / v",
             "values": {"n": n, "c": int(C_LIGHT), "v": int(round(light_speed(n)))}},
        ],
    }
