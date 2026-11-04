"""Electric circuit solver: single loop, battery + switch + lamps + resistor.

Kirchhoff for one loop: I = V / (r + n*R_lamp + R_extra).
Lamp glow ramps with filament warm-up, tau = 0.15 s, so switching the
circuit on/off is visible. Pure function of validated params.
"""

import math

TAU = 0.15          # filament warm-up time constant, seconds
WARMUP = 1.0        # seconds of transient to record
DT = 0.02
BRIGHT_REF = 5.0    # watts = full glow, so brightness tracks real power


def solve(p):
    """Steady-state solution. Returns dict of readouts + formula values."""
    r_lamps = p["lamps"] * p["lamp_r"]
    r_total = p["internal_r"] + r_lamps + p["resistor"]
    closed = p["closed"] and r_total > 0.0 and p["lamps"] >= 1
    current = p["voltage"] / r_total if closed else 0.0
    lamp_power = current * current * p["lamp_r"]
    # brightness = lamp power against a fixed full-glow reference, so it
    # rises with voltage and falls when lamps share the loop
    brightness = min(1.0, lamp_power / BRIGHT_REF)
    terminal_v = p["voltage"] - current * p["internal_r"]
    return {
        "r_total": r_total,
        "current": current,
        "lamp_power": lamp_power,
        "brightness": brightness,
        "terminal_voltage": terminal_v,
        "total_power": current * p["voltage"],
        "open": not closed,
    }


def run(p):
    s = solve(p)
    frames = []
    steps = int(round(WARMUP / DT))
    for i in range(steps + 1):
        t = i * DT
        ramp = 1.0 - math.exp(-t / TAU)
        frames.append({
            "t": round(t, 4),
            "current": s["current"],
            "brightness": s["brightness"] * ramp,
            "energy": s["total_power"] * t,
        })
    return {
        "frames": frames,
        "readouts": [
            {"label": "Current", "value": round(s["current"], 4), "unit": "A"},
            {"label": "Total resistance", "value": round(s["r_total"], 2), "unit": "ohm"},
            {"label": "Lamp power (each)", "value": round(s["lamp_power"], 3), "unit": "W"},
            {"label": "Battery terminal voltage", "value": round(s["terminal_voltage"], 3), "unit": "V"},
        ],
        "formula": [
            {"expr": "I = V / (R + r)",
             "values": {"V": round(p["voltage"], 2), "R": round(s["r_total"], 2),
                        "r": round(p["internal_r"], 2), "I": round(s["current"], 4)}},
            {"expr": "P = I^2 * R_lamp",
             "values": {"I": round(s["current"], 4), "R_lamp": round(p["lamp_r"], 1),
                        "P": round(s["lamp_power"], 3)}},
        ],
    }
