"""physlab - physics formula visualizer for 10-15 year olds.

Every topic is a data-driven registry entry: a parameter spec, a list
of formulas to display, and (when ready) a solver. The server validates
input against the spec, the client builds its control panel from the
same spec. Adding a topic touches no framework code.
"""

__version__ = "0.1.0"


def number(pid, label, lo, hi, default, unit="", step=None):
    return {"id": pid, "kind": "number", "label": label, "min": lo,
            "max": hi, "default": default, "unit": unit, "step": step or (hi - lo) / 100.0}


def integer(pid, label, lo, hi, default, unit=""):
    return {"id": pid, "kind": "integer", "label": label, "min": lo,
            "max": hi, "default": default, "unit": unit}


def boolean(pid, label, default):
    return {"id": pid, "kind": "boolean", "label": label, "default": default}


def select(pid, label, choices, default):
    return {"id": pid, "kind": "select", "label": label, "choices": choices,
            "default": default}


MATERIALS = [
    {"id": "water", "label": "Water", "c": 4186.0},
    {"id": "aluminum", "label": "Aluminum", "c": 900.0},
    {"id": "iron", "label": "Iron", "c": 450.0},
    {"id": "copper", "label": "Copper", "c": 385.0},
]

TOPICS = [
    {
        "id": "circuits", "title": "Electric Circuits", "status": "ready",
        "icon": "battery",
        "blurb": "Wire a battery to lamps and watch them light. More lamps, more resistance, less current.",
        "params": [
            number("voltage", "Battery voltage", 1.5, 12.0, 6.0, "V", 0.5),
            integer("lamps", "Lamps in series", 1, 3, 1),
            number("lamp_r", "Lamp resistance", 5.0, 50.0, 20.0, "ohm"),
            number("internal_r", "Battery internal resistance", 0.0, 5.0, 0.5, "ohm"),
            number("resistor", "Extra series resistor", 0.0, 50.0, 0.0, "ohm"),
            boolean("closed", "Switch closed", True),
        ],
        "formulas": [
            {"expr": "I = V / (R + r)", "legend": "current = voltage / total resistance"},
            {"expr": "P = I^2 * R_lamp", "legend": "power that makes the lamp glow"},
        ],
    },
    {
        "id": "motion", "title": "Projectile Motion", "status": "ready",
        "icon": "ball",
        "blurb": "Launch a ball. Change speed, angle, gravity, and air drag, then watch the path.",
        "params": [
            number("v0", "Launch speed", 1.0, 50.0, 18.0, "m/s"),
            number("angle", "Launch angle", 5.0, 85.0, 45.0, "deg"),
            number("mass", "Mass", 0.1, 5.0, 1.0, "kg"),
            number("drag", "Air drag", 0.0, 0.5, 0.0, ""),
            number("wind", "Wind speed", -10.0, 10.0, 0.0, "m/s"),
            number("g", "Gravity", 1.6, 25.0, 9.81, "m/s^2"),
        ],
        "formulas": [
            {"expr": "a = -g - (k/m) * v * |v|", "legend": "gravity pulls down, drag fights motion"},
            {"expr": "Range = v0^2 * sin(2*angle) / g", "legend": "no-drag flight distance (the drag slider changes it)"},
        ],
    },
    {
        "id": "heat", "title": "Heat Transfer", "status": "ready",
        "icon": "flame",
        "blurb": "Touch two blocks together. Heat flows from hot to cold until they agree.",
        "params": [
            select("material_a", "Block A material", MATERIALS, "water"),
            number("mass_a", "Block A mass", 0.1, 10.0, 1.0, "kg"),
            number("temp_a", "Block A temperature", -20.0, 150.0, 90.0, "C"),
            select("material_b", "Block B material", MATERIALS, "iron"),
            number("mass_b", "Block B mass", 0.1, 10.0, 1.0, "kg"),
            number("temp_b", "Block B temperature", -20.0, 150.0, 20.0, "C"),
            number("ambient", "Room temperature", -10.0, 60.0, 25.0, "C"),
            number("loss", "Heat leak to room", 0.0, 2.0, 0.0, "W/K"),
        ],
        "formulas": [
            {"expr": "Q = m * c * dT", "legend": "heat moved = mass x specific heat x temperature change"},
            {"expr": "T_eq = (m_a c_a T_a + m_b c_b T_b) / (m_a c_a + m_b c_b)",
             "legend": "where the two temperatures meet (no heat leak)"},
        ],
    },
    # --- placeholders: formula shown, solver left for expanding agents ---
    {"id": "buoyancy", "title": "Floating & Sinking", "status": "placeholder", "icon": "wave",
     "blurb": "Drop objects in water. Density decides who floats.",
     "formulas": [{"expr": "F_buoy = rho * V * g", "legend": "Archimedes: the push up equals the weight of water pushed aside"}]},
    {"id": "waves", "title": "Waves", "status": "placeholder", "icon": "wave",
     "blurb": "Wiggle one end of a rope, watch the wave travel.",
     "formulas": [{"expr": "v = f * lambda", "legend": "wave speed = frequency x wavelength"}]},
    {"id": "pendulum", "title": "Pendulum", "status": "placeholder", "icon": "clock",
     "blurb": "Swing a weight on a string. Longer string, slower swing.",
     "formulas": [{"expr": "T = 2*pi * sqrt(L/g)", "legend": "period depends on length, not mass"}]},
    {"id": "optics", "title": "Lenses", "status": "placeholder", "icon": "eye",
     "blurb": "Bend light rays through a lens and project an image.",
     "formulas": [{"expr": "1/f = 1/d0 + 1/di", "legend": "the thin lens equation"}]},
    {"id": "pressure", "title": "Pressure", "status": "placeholder", "icon": "press",
     "blurb": "Push a small piston, move a big one. Hydraulics multiply force.",
     "formulas": [{"expr": "P = F / A", "legend": "pressure = force / area"}]},
    {"id": "energy", "title": "Energy Ramp", "status": "placeholder", "icon": "bolt",
     "blurb": "Roll a ball down a hill and watch energy swap between height and speed.",
     "formulas": [{"expr": "E = 0.5*m*v^2 + m*g*h", "legend": "kinetic + potential: the total never changes"}]},
]


def spec(topic_id):
    for t in TOPICS:
        if t["id"] == topic_id:
            return t
    return None
