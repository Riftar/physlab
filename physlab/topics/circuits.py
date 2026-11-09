"""Electric circuit solver: one series loop - battery (EMF V, internal
resistance r), switch, n identical lamps, optional series resistor.

Electrical model (Kirchhoff's loop law, ohmic parts):

    I = V / (r + n * R_lamp + R_extra)

The same current flows through every part of a series loop, so every
lamp gets V_lamp = I * R_lamp and P = I^2 * R_lamp.

Lamp model - a real incandescent filament, not a linear "glow = power":

* Every lamp is a 6 V lamp (like a classroom bulb marked "6 V"): with
  6 V across it, it takes its rated power P_rated = 6^2 / R_lamp and the
  tungsten filament runs at 2700 K. R_lamp is the hot (operating)
  resistance and is held constant (the ohmic teaching model).
* Steady state: electrical power in = radiated power out, and radiation
  goes as T^4 - T_room^4 (Stefan-Boltzmann), so
      T = (T_room^4 + (T_rated^4 - T_room^4) * P / P_rated) ** 0.25
* Light: luminous flux Phi = P * LER(T), where LER is the luminous
  efficacy of the filament's spectrum - Planck's law weighted by the CIE
  photopic eye-sensitivity curve (grey-body filament: emissivity cancels
  in the ratio). This is strongly non-linear: a lamp on a quarter of its
  power runs ~1900 K and gives only ~3% of its rated light, dull orange.
* Colour: black-body chromaticity at T (CIE 1931 XYZ -> sRGB).
* Perceived brightness: Stevens' power law B ~ Phi^(1/3), normalised to
  the brightest lamp this kit can build, so 0..1 and never clipped.

Warm-up: filament temperature approaches steady state with tau = 0.15 s.
Pure function of validated params.
"""

import math

TAU = 0.15          # filament warm-up time constant, seconds
WARMUP = 1.0        # seconds of transient to record
DT = 0.02

# ---- lamp + physical constants ----
LAMP_V_RATED = 6.0      # V, every lamp is a "6 V" lamp
T_RATED = 2700.0        # K, filament temperature at rated power
T_ROOM = 293.15         # K
T_MELT_W = 3695.0       # K, tungsten melts - a real filament fails here
OVERVOLT_WARN = 1.1     # x rated voltage: lamp life collapses (~V^-12)
STEVENS = 1.0 / 3.0     # brightness exponent for an extended light source

# SI constants (exact 2019 values) and the luminous efficacy maximum
H = 6.62607015e-34
C = 2.99792458e8
KB = 1.380649e-23
SIGMA = 5.670374419e-8
KM = 683.0              # lm/W at 555 nm (540 THz), fixed by the SI candela

# copper hook-up wire, for the real electron drift speed v = I / (n e A)
N_CU = 8.49e28          # free electrons per m^3
E_CHARGE = 1.602176634e-19
WIRE_AREA = 0.5e-6      # m^2 (0.5 mm^2, ~20 AWG)

LAMBDA_NM = [360.0 + 5.0 * i for i in range(95)]   # 360..830 nm, 5 nm steps


def _lobe(lam, mu, s1, s2):
    s = s1 if lam < mu else s2
    return math.exp(-0.5 * ((lam - mu) / s) ** 2)


def _cmf(lam):
    """CIE 1931 2-degree colour matching functions, multi-lobe analytic fit
    (Wyman, Sloan & Shirley, JCGT 2013). ybar is the photopic V(lambda)."""
    x = (1.056 * _lobe(lam, 599.8, 37.9, 31.0) + 0.362 * _lobe(lam, 442.0, 16.0, 26.7)
         - 0.065 * _lobe(lam, 501.1, 20.4, 26.2))
    y = 0.821 * _lobe(lam, 568.8, 46.9, 40.5) + 0.286 * _lobe(lam, 530.9, 16.3, 31.1)
    z = 1.217 * _lobe(lam, 437.0, 11.8, 36.0) + 0.681 * _lobe(lam, 459.0, 26.0, 13.8)
    return x, y, z


CMF = [_cmf(lam) for lam in LAMBDA_NM]


def blackbody_xyz(temp_k):
    """Tristimulus integrals of Planck spectral radiance (W sr^-1 m^-2
    weighted by the CMFs), 360-830 nm."""
    X = Y = Z = 0.0
    w = 5.0e-9
    for lam_nm, (xb, yb, zb) in zip(LAMBDA_NM, CMF):
        lam = lam_nm * 1e-9
        arg = H * C / (lam * KB * temp_k)
        if arg > 700.0:          # exp overflow: radiance is ~0 anyway
            continue
        b = 2.0 * H * C * C / lam ** 5 / math.expm1(arg)
        X += b * xb * w
        Y += b * yb * w
        Z += b * zb * w
    return X, Y, Z


def luminance(temp_k):
    """Black-body luminance in cd/m^2."""
    return KM * blackbody_xyz(temp_k)[1]


def efficacy(temp_k):
    """Luminous efficacy of (grey-)black-body radiation, lm per radiated W."""
    return luminance(temp_k) / (SIGMA * temp_k ** 4 / math.pi)


def chromaticity(temp_k):
    X, Y, Z = blackbody_xyz(temp_k)
    s = X + Y + Z
    return (X / s, Y / s) if s > 0 else (0.0, 0.0)


def glow_color(temp_k):
    """sRGB hex of the black-body colour at temp_k, at full intensity
    (brightness is carried separately)."""
    X, Y, Z = blackbody_xyz(max(temp_k, 500.0))
    r = 3.2406 * X - 1.5372 * Y - 0.4986 * Z
    g = -0.9689 * X + 1.8758 * Y + 0.0415 * Z
    b = 0.0557 * X - 0.2040 * Y + 1.0570 * Z
    r, g, b = max(r, 0.0), max(g, 0.0), max(b, 0.0)   # gamut clip (deep reds)
    m = max(r, g, b) or 1.0

    def enc(u):
        u /= m
        u = 12.92 * u if u <= 0.0031308 else 1.055 * u ** (1 / 2.4) - 0.055
        return int(round(max(0.0, min(1.0, u)) * 255))
    return "#%02x%02x%02x" % (enc(r), enc(g), enc(b))


def filament_temp(power, p_rated):
    """Steady filament temperature from the radiation balance."""
    if power <= 0.0:
        return T_ROOM
    k = power / p_rated
    return (T_ROOM ** 4 + (T_RATED ** 4 - T_ROOM ** 4) * k) ** 0.25


def lumens(power_radiated, temp_k):
    return power_radiated * efficacy(temp_k) if power_radiated > 0.0 else 0.0


_MAX_LM = []


def max_lumens():
    """Light from the brightest lamp the kit can make: top battery voltage
    straight across the lowest-resistance lamp. Normalises brightness."""
    if not _MAX_LM:
        from .. import spec
        prm = {p["id"]: p for p in spec("circuits")["params"]}
        v, r = prm["voltage"]["max"], prm["lamp_r"]["min"]
        pw, pr = v * v / r, LAMP_V_RATED ** 2 / r
        _MAX_LM.append(lumens(pw, filament_temp(pw, pr)))
    return _MAX_LM[0]


def perceived(lm):
    return (lm / max_lumens()) ** STEVENS if lm > 0.0 else 0.0


def solve(p):
    """Steady-state solution. Returns dict of readouts + formula values."""
    r_lamps = p["lamps"] * p["lamp_r"]
    r_total = p["internal_r"] + r_lamps + p["resistor"]
    closed = p["closed"] and r_total > 0.0 and p["lamps"] >= 1
    current = p["voltage"] / r_total if closed else 0.0
    lamp_v = current * p["lamp_r"]
    lamp_power = current * current * p["lamp_r"]
    p_rated = LAMP_V_RATED ** 2 / p["lamp_r"]
    temp = filament_temp(lamp_power, p_rated)
    lm = lumens(lamp_power, temp)
    terminal_v = p["voltage"] - current * p["internal_r"]
    return {
        "r_total": r_total,
        "current": current,
        "lamp_voltage": lamp_v,
        "lamp_power": lamp_power,
        "rated_power": p_rated,
        "filament_k": temp,
        "lumens": lm,
        # perceived brightness 0..1 (Stevens), rises steeply with voltage
        # and collapses when lamps share the loop
        "brightness": perceived(lm),
        "color": glow_color(temp),
        "terminal_voltage": terminal_v,
        "total_power": current * p["voltage"],
        "drift_mm_s": current / (N_CU * E_CHARGE * WIRE_AREA) * 1000.0,
        "open": not closed,
    }


def notes(s):
    out = []
    if s["open"]:
        out.append("Switch open: no complete loop, so no current - the electrons "
                   "are still in the wire, they just stop drifting.")
        return out
    ratio = s["lamp_voltage"] / LAMP_V_RATED
    if s["filament_k"] >= T_MELT_W:
        out.append("Warning: the filament would be %.0f K - hotter than tungsten's "
                   "melting point (%.0f K). A real %.0f V lamp would blow instantly."
                   % (s["filament_k"], T_MELT_W, LAMP_V_RATED))
    elif ratio > OVERVOLT_WARN:
        out.append("Over-volted: %.1f V across a %.0f V lamp. It shines extra bright "
                   "and white, but a real filament would burn out quickly "
                   "(life falls roughly as V^-12: about %s of normal here)."
                   % (s["lamp_voltage"], LAMP_V_RATED, _pct(ratio ** -12)))
    elif s["filament_k"] < 1000.0:
        out.append("Too little power: the filament only reaches %.0f K. Below about "
                   "800-1000 K a filament gives almost no visible light, so the "
                   "lamp looks dark even though current flows." % s["filament_k"])
    return out


def _pct(x):
    return "%.2g%%" % (100.0 * x)


def run(p):
    s = solve(p)
    frames = []
    steps = int(round(WARMUP / DT))
    t_ss = s["filament_k"]
    e_ss = t_ss ** 4 - T_ROOM ** 4
    for i in range(steps + 1):
        t = i * DT
        # first-order warm-up of the filament temperature; it radiates
        # (and so shines) according to its *current* temperature
        # the last frame is the steady state the circuit then holds
        ramp = 1.0 if i == steps else 1.0 - math.exp(-t / TAU)
        temp = T_ROOM + (t_ss - T_ROOM) * ramp
        p_rad = s["lamp_power"] * (temp ** 4 - T_ROOM ** 4) / e_ss if e_ss > 0 else 0.0
        lm = lumens(p_rad, temp)
        frames.append({
            "t": round(t, 4),
            "current": s["current"],
            "brightness": round(perceived(lm), 6),
            "filament_k": round(temp, 1),
            "lumens": round(lm, 4),
            "color": glow_color(temp),
            "energy": s["total_power"] * t,
        })
    return {
        "frames": frames,
        "notes": notes(s),
        # display hints for the renderer (no physics is re-derived client-side)
        "viz": {"lamp_v_rated": LAMP_V_RATED, "drift_mm_s": s["drift_mm_s"]},
        "readouts": [
            {"label": "Current (same everywhere in the loop)", "value": round(s["current"], 4), "unit": "A"},
            {"label": "Total resistance", "value": round(s["r_total"], 2), "unit": "ohm"},
            {"label": "Voltage across each lamp", "value": round(s["lamp_voltage"], 3),
             "unit": "V (rated %.0f V)" % LAMP_V_RATED},
            {"label": "Lamp power (each)", "value": round(s["lamp_power"], 3),
             "unit": "W (rated %.2f W)" % s["rated_power"]},
            {"label": "Filament temperature", "value": int(round(s["filament_k"])), "unit": "K"},
            {"label": "Light from each lamp", "value": round(s["lumens"], 2), "unit": "lm"},
            {"label": "Battery terminal voltage", "value": round(s["terminal_voltage"], 3), "unit": "V"},
            {"label": "Real electron drift speed", "value": round(s["drift_mm_s"], 4),
             "unit": "mm/s (0.5 mm\u00b2 copper wire)"},
        ],
        "formula": [
            {"expr": "I = V / (R + r)",
             "values": {"V": round(p["voltage"], 2), "R": round(s["r_total"] - p["internal_r"], 2),
                        "r": round(p["internal_r"], 2), "I": round(s["current"], 4)}},
            {"expr": "P = I^2 * R_lamp",
             "values": {"I": round(s["current"], 4), "R_lamp": round(p["lamp_r"], 1),
                        "P": round(s["lamp_power"], 3)}},
            {"expr": "T^4 - T_room^4 ~ P",
             "values": {"P/P_rated": round(s["lamp_power"] / s["rated_power"], 3),
                        "T": int(round(s["filament_k"])), "lm": round(s["lumens"], 2)}},
        ],
    }
