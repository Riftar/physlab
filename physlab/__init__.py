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


# c: specific heat, J/(kg K); rho: density, kg/m^3 (room temperature).
# Density sets each block's true size on screen: 1 kg of water is a 10 cm
# cube, 1 kg of copper only 4.8 cm.
MATERIALS = [
    {"id": "water", "label": "Water", "c": 4186.0, "rho": 1000.0},
    {"id": "aluminum", "label": "Aluminum", "c": 900.0, "rho": 2700.0},
    {"id": "iron", "label": "Iron", "c": 450.0, "rho": 7874.0},
    {"id": "copper", "label": "Copper", "c": 385.0, "rho": 8960.0},
]

# Floating & sinking. rho in kg/m^3 near 20 C; mu = dynamic viscosity, Pa s
# (honey varies a lot, 2-10 Pa s; 6 is a typical runny honey).
SOLIDS = [
    {"id": "cork", "label": "Cork", "rho": 240.0, "color": "#c49a63"},
    {"id": "pine", "label": "Pine wood", "rho": 510.0, "color": "#d8a35a"},
    {"id": "ice", "label": "Ice", "rho": 917.0, "color": "#d9f1ff"},
    {"id": "rubber", "label": "Rubber", "rho": 1100.0, "color": "#4a4a58"},
    {"id": "aluminum", "label": "Aluminum", "rho": 2700.0, "color": "#c3c9d2"},
    {"id": "iron", "label": "Iron", "rho": 7874.0, "color": "#6b7079"},
    {"id": "gold", "label": "Gold", "rho": 19300.0, "color": "#f2c230"},
]
FLUIDS = [
    {"id": "water", "label": "Fresh water", "rho": 998.0, "mu": 1.0e-3, "color": "#3d8fe0"},
    {"id": "seawater", "label": "Sea water", "rho": 1025.0, "mu": 1.08e-3, "color": "#2f9fa8"},
    {"id": "oil", "label": "Vegetable oil", "rho": 920.0, "mu": 0.06, "color": "#e3c04a"},
    {"id": "honey", "label": "Honey", "rho": 1420.0, "mu": 6.0, "color": "#d9891c"},
    {"id": "mercury", "label": "Mercury", "rho": 13534.0, "mu": 1.53e-3, "color": "#b5bcc6"},
]

# Lenses: refractive index n at ~589 nm (sodium D line)
GLASSES = [
    {"id": "water", "label": "Water", "n": 1.333},
    {"id": "acrylic", "label": "Acrylic plastic", "n": 1.49},
    {"id": "crown", "label": "Crown glass", "n": 1.52},
    {"id": "flint", "label": "Flint glass", "n": 1.62},
    {"id": "diamond", "label": "Diamond", "n": 2.417},
]
LENS_KINDS = [
    {"id": "converging", "label": "Converging (convex)"},
    {"id": "diverging", "label": "Diverging (concave)"},
]

HYDRAULIC_FLUIDS = [
    {"id": "oil", "label": "Hydraulic oil", "rho": 870.0, "color": "#e3b34a"},
    {"id": "water", "label": "Water", "rho": 998.0, "color": "#3d8fe0"},
]

ENDS = [
    {"id": "fixed", "label": "Tied to a wall (fixed)"},
    {"id": "free", "label": "Ring on a pole (free)"},
    {"id": "open", "label": "Endless rope (no echo)"},
]

TOPICS = [
    {
        "id": "circuits", "title": "Electric Circuits", "status": "ready",
        "icon": "battery",
        "blurb": "Wire a battery to lamps and watch them light. More lamps, more resistance, less current.",
        "params": [
            number("voltage", "Battery voltage", 1.5, 12.0, 6.0, "V", 0.5),
            integer("lamps", "Lamps in series", 1, 3, 1),
            number("lamp_r", "Lamp resistance", 5.0, 50.0, 20.0, "ohm", 1.0),
            number("internal_r", "Battery internal resistance", 0.0, 5.0, 0.5, "ohm"),
            number("resistor", "Extra series resistor", 0.0, 50.0, 0.0, "ohm"),
            boolean("closed", "Switch closed", True),
        ],
        "formulas": [
            {"expr": "I = V / (R + r)", "legend": "current = voltage / total resistance"},
            {"expr": "P = I^2 * R_lamp", "legend": "power that makes the lamp glow"},
            {"expr": "T^4 - T_room^4 ~ P",
             "legend": "more power -> hotter filament -> whiter and MUCH brighter light (a 6 V lamp runs 2700 K at 6 V)"},
        ],
    },
    {
        "id": "motion", "title": "Projectile Motion", "status": "ready",
        "icon": "ball", "compare": "ball",
        "blurb": "Launch a ball. Change speed, angle, gravity, and air drag, then watch the path.",
        "params": [
            number("v0", "Launch speed", 1.0, 50.0, 18.0, "m/s", 0.5),
            number("angle", "Launch angle", 5.0, 85.0, 45.0, "deg", 1.0),
            number("mass", "Mass", 0.1, 5.0, 1.0, "kg", 0.05),
            number("drag", "Air drag k", 0.0, 0.5, 0.0, "kg/m", 0.001),
            number("wind", "Wind (+ pushes forward)", -10.0, 10.0, 0.0, "m/s"),
            number("g", "Gravity", 1.6, 25.0, 9.81, "m/s^2", 0.01),
        ],
        "formulas": [
            {"expr": "a = -g - (k/m) * v_air * |v_air|",
             "legend": "gravity pulls down; drag pushes against the ball's motion through the air (v_air = ball velocity - wind)"},
            {"expr": "Range = v0^2 * sin(2*angle) / g", "legend": "no-drag flight distance (the drag slider changes it)"},
        ],
    },
    {
        "id": "heat", "title": "Heat Transfer", "status": "ready",
        "icon": "flame",
        "blurb": "Touch two blocks together. Heat flows from hot to cold until they agree.",
        "params": [
            select("material_a", "Block A material", MATERIALS, "water"),
            number("mass_a", "Block A mass", 0.1, 10.0, 1.0, "kg", 0.05),
            number("temp_a", "Block A temperature", -20.0, 150.0, 90.0, "C", 1.0),
            select("material_b", "Block B material", MATERIALS, "iron"),
            number("mass_b", "Block B mass", 0.1, 10.0, 1.0, "kg", 0.05),
            number("temp_b", "Block B temperature", -20.0, 150.0, 20.0, "C", 1.0),
            number("ambient", "Room temperature", -10.0, 60.0, 25.0, "C", 1.0),
            number("loss", "Heat leak to room", 0.0, 2.0, 0.0, "W/K"),
        ],
        "formulas": [
            {"expr": "Q = m * c * dT", "legend": "heat moved = mass x specific heat x temperature change"},
            {"expr": "T_eq = (m_a c_a T_a + m_b c_b T_b) / (m_a c_a + m_b c_b)",
             "legend": "where the two temperatures meet (no heat leak)"},
        ],
    },
    {
        "id": "buoyancy", "title": "Floating & Sinking", "status": "ready",
        "icon": "water",
        "blurb": "Drop a block or ball into a tank. The liquid pushes up with the weight of the liquid it pushes aside - density decides who floats.",
        "params": [
            select("shape", "Shape", [{"id": "cube", "label": "Block (cube)"},
                                      {"id": "sphere", "label": "Ball (sphere)"}], "cube"),
            select("material", "Object material", SOLIDS, "pine"),
            number("size", "Size (side or diameter)", 4.0, 30.0, 12.0, "cm", 0.5),
            select("fluid", "Liquid in the tank", FLUIDS, "water"),
            number("g", "Gravity", 1.6, 25.0, 9.81, "m/s^2", 0.01),
            number("start", "Start height (centre above surface)", -30.0, 30.0, 15.0, "cm", 1.0),
        ],
        "formulas": [
            {"expr": "F_b = rho_fluid * V_sub * g",
             "legend": "Archimedes: the push up equals the weight of the liquid pushed aside"},
            {"expr": "W = rho_obj * V * g", "legend": "the object's weight pulls down"},
            {"expr": "V_sub / V = rho_obj / rho_fluid",
             "legend": "a floater sinks in until F_b = W - the denser it is, the deeper it sits (g cancels out!)"},
        ],
    },
    {
        "id": "waves", "title": "Waves", "status": "ready", "icon": "wave",
        "blurb": "Shake one end of a rope and watch the wave travel, bounce back, and - at just the right rhythm - build a standing wave.",
        "params": [
            number("f", "Shake frequency", 0.2, 5.0, 2.5, "Hz", 0.05),
            number("amplitude", "Shake amplitude", 0.5, 10.0, 3.0, "cm", 0.5),
            number("tension", "Rope tension", 1.0, 100.0, 20.0, "N", 0.5),
            number("mu", "Rope mass per metre", 20.0, 1000.0, 200.0, "g/m", 5.0),
            number("length", "Rope length", 1.0, 8.0, 4.0, "m", 0.1),
            select("end", "Far end of the rope", ENDS, "fixed"),
            number("damping", "Damping (friction)", 0.2, 3.0, 1.0, "1/s", 0.05),
        ],
        "formulas": [
            {"expr": "v = sqrt(T / mu)", "legend": "the rope sets the speed: tighter = faster, heavier = slower"},
            {"expr": "v = f * lambda", "legend": "wave speed = frequency x wavelength (shake faster -> shorter waves)"},
            {"expr": "f_n = n * v / (2 * L)",
             "legend": "resonances with a fixed end (free end: f_n = (2n-1) * v / (4L)) - the rope forms a standing wave"},
        ],
    },
    {
        "id": "pendulum", "title": "Pendulum", "status": "ready", "icon": "pendulum",
        "compare": "pendulum",
        "blurb": "Swing a weight on a string. Longer string, slower swing - and the mass doesn't matter.",
        "params": [
            number("length", "String length", 0.1, 3.0, 1.0, "m", 0.01),
            number("amplitude", "Release angle", 2.0, 90.0, 20.0, "deg", 1.0),
            number("mass", "Bob mass", 0.05, 5.0, 1.0, "kg", 0.05),
            number("g", "Gravity", 1.6, 25.0, 9.81, "m/s^2", 0.01),
            number("drag", "Air drag k", 0.0, 0.02, 0.0, "kg/m", 0.0005),
        ],
        "formulas": [
            {"expr": "T = 2*pi * sqrt(L/g)", "legend": "small swings: the period depends on length and gravity, not on mass"},
            {"expr": "T_exact = T / AGM(1, cos(theta0/2))",
             "legend": "exact for any release angle: big swings take a little longer"},
            {"expr": "F_restore = m * g * sin(theta)",
             "legend": "the part of gravity along the swing always pulls the bob back to the middle"},
            {"expr": "E = 0.5*m*v^2 + m*g*h",
             "legend": "height and speed trade energy; without drag the total stays the same"},
        ],
    },
    {
        "id": "optics", "title": "Lenses", "status": "ready", "icon": "eye",
        "blurb": "Put a candle in front of a lens and find its image. The lens's shape and material set the focal length; where you put the candle decides the rest.",
        "params": [
            select("kind", "Lens type", LENS_KINDS, "converging"),
            select("material", "Lens material", GLASSES, "crown"),
            number("radius", "Surface curvature radius R", 6.0, 60.0, 20.0, "cm", 0.5),
            number("d_o", "Candle distance d_o", 2.0, 100.0, 30.0, "cm", 0.5),
            number("h_o", "Candle height h_o", 1.0, 8.0, 4.0, "cm", 0.5),
        ],
        "formulas": [
            {"expr": "1/f = (n - 1) * (1/R1 - 1/R2)",
             "legend": "lensmaker's equation: more curved or denser glass -> shorter focal length"},
            {"expr": "1/f = 1/d_o + 1/d_i", "legend": "the thin-lens equation: where the image appears"},
            {"expr": "m = -d_i / d_o = h_i / h_o", "legend": "magnification: how big, and which way up"},
            {"expr": "n = c / v", "legend": "light slows down in glass - that's why it bends"},
        ],
    },
    {
        "id": "pressure", "title": "Pressure", "status": "ready", "icon": "press",
        "blurb": "Push a small piston, lift a car. The liquid passes the pressure on, so a small force over a small area makes a big force over a big area.",
        "params": [
            number("force", "Your push F1", 10.0, 600.0, 150.0, "N", 5.0),
            number("d1", "Small piston diameter", 1.0, 10.0, 3.0, "cm", 0.5),
            number("d2", "Big piston diameter", 5.0, 60.0, 30.0, "cm", 1.0),
            number("mass", "Load on the big piston", 0.0, 2000.0, 1000.0, "kg", 10.0),
            number("stroke", "Push distance d1", 5.0, 40.0, 25.0, "cm", 1.0),
            select("fluid", "Liquid", HYDRAULIC_FLUIDS, "oil"),
        ],
        "formulas": [
            {"expr": "P = F / A", "legend": "pressure = force / area"},
            {"expr": "F2 = F1 * (A2 / A1)", "legend": "Pascal: the same pressure on a bigger area gives a bigger force"},
            {"expr": "d2 = d1 * (A1 / A2)", "legend": "the liquid doesn't squash: the big piston moves much less"},
            {"expr": "F1 * d1 = F2 * d2", "legend": "work in = work out: you trade distance for force"},
        ],
    },
    {
        "id": "energy", "title": "Energy Ramp", "status": "ready", "icon": "bolt",
        "compare": "object",
        "blurb": "Let go of a box or a ball on a track and watch its energy swap between height, speed, spin and heat.",
        "params": [
            select("track", "Track", [{"id": "halfpipe", "label": "Half-pipe"},
                                      {"id": "hill", "label": "Drop and hill"}], "halfpipe"),
            select("object", "Object", [{"id": "box", "label": "Box (slides)"},
                                        {"id": "solid_ball", "label": "Solid ball (rolls)"},
                                        {"id": "hollow_ball", "label": "Hollow ball (rolls)"}], "box"),
            number("height", "Start height h", 0.5, 8.0, 5.0, "m", 0.1),
            number("mass", "Mass m", 0.5, 100.0, 20.0, "kg", 0.5),
            number("friction", "Friction mu", 0.0, 0.5, 0.0, "", 0.01),
            number("g", "Gravity", 1.6, 25.0, 9.81, "m/s^2", 0.01),
        ],
        "formulas": [
            {"expr": "E = 0.5*m*v^2 + m*g*h", "legend": "kinetic + potential: without friction the total never changes"},
            {"expr": "v = sqrt(2*g*h / (1 + k))", "legend": "speed after dropping h: rolling things are slower (k = spin share)"},
            {"expr": "N = m*(g*cos(phi) + v^2/r)", "legend": "how hard the track pushes: more in dips, less over hills"},
            {"expr": "E_heat = mu * N * distance", "legend": "friction turns motion energy into heat"},
        ],
    },
]


def spec(topic_id):
    for t in TOPICS:
        if t["id"] == topic_id:
            return t
    return None


# learning content (explanations, annotated figures, real-life uses)
from .learn import attach as _attach_learn  # noqa: E402
_attach_learn(TOPICS)
