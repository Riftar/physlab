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
# cube, 1 kg of copper only 4.8 cm. alpha: linear thermal expansion, 1/K
# (how much longer each metre gets per kelvin; none for the liquid).
MATERIALS = [
    {"id": "water", "label": "Water", "c": 4186.0, "rho": 1000.0, "alpha": None},
    {"id": "aluminum", "label": "Aluminum", "c": 900.0, "rho": 2700.0, "alpha": 23.1e-6},
    {"id": "iron", "label": "Iron", "c": 450.0, "rho": 7874.0, "alpha": 12.0e-6},
    {"id": "copper", "label": "Copper", "c": 385.0, "rho": 8960.0, "alpha": 16.5e-6},
]

# Floating & sinking. rho in kg/m^3 near 20 C; mu = dynamic viscosity, Pa s
# (honey varies a lot, 2-10 Pa s; 6 is a typical runny honey).
SOLIDS = [
    {"id": "cork", "label": "Cork", "rho": 240.0, "color": "#c49a63"},
    {"id": "pine", "label": "Pine wood", "rho": 510.0, "color": "#d8a35a"},
    {"id": "ice", "label": "Ice", "rho": 917.0, "color": "#d9f1ff"},
    {"id": "rubber", "label": "Rubber", "rho": 1100.0, "color": "#4a4a58"},
    {"id": "bouncy", "label": "Bouncy-ball rubber", "rho": 1149.0, "color": "#e0455a"},
    {"id": "woodball", "label": "Toy-ball wood (alder)", "rho": 597.0, "color": "#a8703a"},
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

# Bounces: the balls are the sandbox's bobs (same mass, size, drag); what a
# bounce keeps depends on the PAIR ball x surface (restitution table in
# topics/bounce.py).
BOUNCE_BALLS = [
    {"id": "rubber", "label": "Rubber ball (130 g, 6 cm)", "mass": 0.13, "d": 0.06, "cd": 0.47, "color": "#e0455a"},
    {"id": "tennis", "label": "Tennis ball (58 g, 6.7 cm)", "mass": 0.058, "d": 0.067, "cd": 0.55, "color": "#d8f03c"},
    {"id": "steel", "label": "Steel ball (510 g, 5 cm)", "mass": 0.51, "d": 0.05, "cd": 0.47, "color": "#c0c8d8"},
    {"id": "wood", "label": "Wooden ball (160 g, 8 cm)", "mass": 0.16, "d": 0.08, "cd": 0.47, "color": "#a8703a"},
]
BOUNCE_SURFACES = [
    {"id": "steel_plate", "label": "Steel plate", "color": "#aab3c5"},
    {"id": "hardwood", "label": "Hardwood floor", "color": "#c98b4a"},
    {"id": "foam_mat", "label": "Foam gym mat", "color": "#4f7fd8"},
    {"id": "sand", "label": "Sand", "color": "#e2c27a"},
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
            number("wind", "Wind (+ pushes forward)", -20.0, 20.0, 0.0, "m/s", 0.1),
            number("g", "Gravity", 1.6, 25.0, 9.81, "m/s^2", 0.01),
            number("height", "Launch height", 0.0, 20.0, 0.0, "m", 0.1),
        ],
        "formulas": [
            {"expr": "a = -g - (k/m) * v_air * |v_air|",
             "legend": "gravity pulls down; drag pushes against the ball's motion through the air (v_air = ball velocity - wind)"},
            {"expr": "Range = v0^2 * sin(2*angle) / g", "legend": "no-drag flight distance (the drag slider changes it)"},
            {"expr": "x = v0*cos(a) * (v0*sin(a) + sqrt((v0*sin(a))^2 + 2*g*h)) / g",
             "legend": "no-drag distance when it's launched h metres above the ground"},
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
            {"expr": "dL = alpha * L * dT",
             "legend": "metals grow a tiny bit when they warm up (and shrink when they cool)"},
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
            number("salt", "Salt stirred into fresh water", 0.0, 400.0, 0.0, "g/L", 5.0),
            select("vessel", "Container", [{"id": "tank", "label": "Glass tank (100 × 40 cm)"},
                                           {"id": "well", "label": "Narrow well (10 cm across)"}], "tank"),
            number("depth", "Water depth before", 5.0, 60.0, 40.0, "cm", 0.5),
            number("extra", "Stones already on the bottom", 0.0, 4000.0, 0.0, "cm³", 5.0),
        ],
        "formulas": [
            {"expr": "F_b = rho_fluid * V_sub * g",
             "legend": "Archimedes: the push up equals the weight of the liquid pushed aside"},
            {"expr": "W = rho_obj * V * g", "legend": "the object's weight pulls down"},
            {"expr": "V_sub / V = rho_obj / rho_fluid",
             "legend": "a floater sinks in until F_b = W - the denser it is, the deeper it sits (g cancels out!)"},

            {"expr": "dh = V_pushed / A",
             "legend": "the water rises by the volume pushed aside ÷ the container's area - fast in a narrow well"},
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
            number("screen", "Screen behind the lens (0 = none)", 0.0, 200.0, 0.0, "cm", 0.5),
        ],
        "formulas": [
            {"expr": "1/f = (n - 1) * (1/R1 - 1/R2)",
             "legend": "lensmaker's equation: more curved or denser glass -> shorter focal length"},
            {"expr": "1/f = 1/d_o + 1/d_i", "legend": "the thin-lens equation: where the image appears"},
            {"expr": "m = -d_i / d_o = h_i / h_o", "legend": "magnification: how big, and which way up"},
            {"expr": "n = c / v", "legend": "light slows down in glass - that's why it bends"},
            {"expr": "blur = D * |s - d_i| / d_i",
             "legend": "a screen away from the image gets a blurred patch, not a sharp picture"},
        ],
    },
    {
        "id": "pressure", "title": "Pressure", "status": "ready", "icon": "press",
        "blurb": "Push a small piston, lift a car. The liquid passes the pressure on, so a small force over a small area makes a big force over a big area.",
        "params": [
            number("force", "Your push F1", 1.0, 600.0, 150.0, "N", 1.0),
            number("d1", "Small piston diameter", 1.0, 10.0, 3.0, "cm", 0.5),
            number("d2", "Big piston diameter", 2.0, 60.0, 30.0, "cm", 0.1),
            number("mass", "Load on the big piston", 0.0, 2000.0, 1000.0, "kg", 0.1),
            number("stroke", "Push distance d1", 5.0, 40.0, 25.0, "cm", 1.0),
            select("fluid", "Liquid", HYDRAULIC_FLUIDS, "oil"),
            select("push", "What pushes the small piston",
                   [{"id": "person", "label": "A person (weaker the faster they push)"},
                    {"id": "weight", "label": "A weight resting on it (same push at any speed)"}], "person"),
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
                                      {"id": "hill", "label": "Drop and hill"},
                                      {"id": "camel", "label": "Camel hump (1.5 m machine track)"}], "halfpipe"),
            select("object", "Object", [{"id": "box", "label": "Box (slides)"},
                                        {"id": "solid_ball", "label": "Solid ball (rolls)"},
                                        {"id": "hollow_ball", "label": "Hollow ball (rolls)"}], "box"),
            number("height", "Start height h", 0.5, 8.0, 5.0, "m", 0.1),
            number("mass", "Mass m", 0.5, 100.0, 20.0, "kg", 0.5),
            number("friction", "Friction mu", 0.0, 0.5, 0.0, "", 0.01),
            number("g", "Gravity", 1.6, 25.0, 9.81, "m/s^2", 0.01),
            number("hump", "Hump height (camel track)", 0.2, 1.6, 1.0, "m", 0.01),
        ],
        "formulas": [
            {"expr": "E = 0.5*m*v^2 + m*g*h", "legend": "kinetic + potential: without friction the total never changes"},
            {"expr": "v = sqrt(2*g*h / (1 + k))", "legend": "speed after dropping h: rolling things are slower (k = spin share)"},
            {"expr": "N = m*(g*cos(phi) + v^2/r)", "legend": "how hard the track pushes: more in dips, less over hills"},
            {"expr": "E_heat = mu * N * distance", "legend": "friction turns motion energy into heat"},
        ],
    },
]


TOPICS.append({
    "id": "bounce", "title": "Bounces", "status": "ready", "icon": "bounce", "compare": "ball",
    "blurb": "Drop a ball and watch it bounce back lower every time. How much it keeps depends on the ball AND on "
             "what it lands on.",
    "params": [
        select("ball", "Ball", BOUNCE_BALLS, "rubber"),
        select("surface", "Lands on", BOUNCE_SURFACES, "steel_plate"),
        number("height", "Drop height h0", 0.2, 4.0, 2.0, "m", 0.05),
        number("g", "Gravity", 1.6, 25.0, 9.81, "m/s^2", 0.01),
        boolean("air", "Air drag", True),
    ],
    "formulas": [
        {"expr": "v = sqrt(2*g*h)", "legend": "falling h metres, the ball hits the floor this fast"},
        {"expr": "v_after = e * v_before",
         "legend": "a bounce sends it back up with only a fraction e of that speed - e depends on the ball AND the "
                   "surface"},
        {"expr": "h1 = e^2 * h0", "legend": "height goes with speed squared, so each bounce reaches e^2 of the "
                                            "height before (air takes a little more)"},
    ],
})


TOPICS.append({
    "id": "levers", "title": "Levers & Moments", "status": "ready", "icon": "levers",
    "blurb": "Hang loads on a beam on a pivot. A small weight far out can lift a big one close in - it's the "
             "turning effect that counts, not the weight alone.",
    "params": [
        number("m1", "Left load m1", 0.0, 5.0, 2.0, "kg", 0.05),
        number("d1", "Left load distance d1", 0.05, 1.1, 0.5, "m", 0.05),
        number("m2", "Right load m2", 0.0, 5.0, 1.0, "kg", 0.05),
        number("d2", "Right load distance d2", 0.05, 1.1, 0.8, "m", 0.05),
        number("beam", "Beam mass (2.2 m long)", 0.0, 5.0, 1.0, "kg", 0.1),
        number("friction", "Pivot friction", 0.0, 1.0, 0.03, "N m", 0.01),
        number("start", "Start angle (+ = right end down)", -25.0, 25.0, 0.0, "deg", 1.0),
        number("g", "Gravity", 1.6, 25.0, 9.81, "m/s^2", 0.01),
    ],
    "formulas": [
        {"expr": "m1 * d1 = m2 * d2", "legend": "the principle of moments: the beam balances when mass x distance "
                                                "is the same on both sides"},
        {"expr": "tau = m * g * d", "legend": "turning effect (moment) of a load: its weight x its distance from the "
                                              "pivot"},
        {"expr": "alpha = tau_net / I", "legend": "out of balance it turns - the faster, the bigger the leftover "
                                                  "turning effect and the smaller the moment of inertia I = Σ m r²"},
    ],
})


def spec(topic_id):
    for t in TOPICS:
        if t["id"] == topic_id:
            return t
    return None


# learning content (explanations, annotated figures, real-life uses)
from .learn import attach as _attach_learn  # noqa: E402
_attach_learn(TOPICS)
