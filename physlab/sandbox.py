"""Sandbox mode: students build their own world - but only out of pieces
we define.

Every experiment gets
  catalogs   ENUMs of playable things (a tennis ball, a 12 V car bulb, an
             egg, a bowling ball ...). Each item carries FIXED, realistic
             physical properties; students choose items, never edit them.
  fields     what the world is made of: objects (1 or 2 to compare),
             world properties chosen from catalogs (planet, weather,
             surface, liquid, insulation ...), a few bounded numbers, and
             for two experiments a shapeable world: the energy ramp's
             track (control points) and the circuit board (parts on a grid)
  presets    ready-made worlds to start from

A world is a small JSON object. validate() accepts only known fields,
catalog ids and numbers inside their limits (everything else is
rejected with a reason); run() maps the world onto the physics engines
and returns ordinary runs that the normal scenes draw.

Numbers are typical published values (sources: manufacturers' specs and
standard tables for masses, sizes, drag coefficients, densities, friction
and rolling-resistance coefficients); friction in particular varies a
lot in reality - these are sensible middles.
"""

import math

from .topics import motion, pendulum, energy, buoyancy, heat, waves, optics, pressure, circuitlab


def item(id_, label, icon, desc, **props):
    d = {"id": id_, "label": label, "icon": icon, "desc": desc}
    d.update(props)
    return d


# ---------------------------------------------------------------- catalogs

PLANETS = [
    item("earth", "Earth", "🌍", "g = 9.81 m/s², air 1.225 kg/m³", g=9.81, rho_air=1.225,
         sky="#0b1128", ground="#15301f"),
    item("moon", "Moon", "🌕", "g = 1.62 m/s², no air at all", g=1.62, rho_air=0.0,
         sky="#05070f", ground="#3b3b44"),
    item("mars", "Mars", "🔴", "g = 3.71 m/s², very thin air (0.020 kg/m³)", g=3.71, rho_air=0.020,
         sky="#2a1410", ground="#5c2a1a"),
    item("titan", "Titan (Saturn's moon)", "🟠", "g = 1.35 m/s², thick air (5.3 kg/m³)", g=1.35,
         rho_air=5.3, sky="#2b2108", ground="#4a3a12"),
]

WEATHER = [
    item("calm", "Calm", "☀️", "no wind", wind=0.0),
    item("breeze", "Light breeze", "🍃", "3 m/s", wind=3.0),
    item("windy", "Windy", "🌬️", "8 m/s", wind=8.0),
    item("storm", "Storm", "🌪️", "15 m/s", wind=15.0),
]

WIND_DIR = [
    item("behind", "From behind", "➡️", "pushes the ball forward", sign=1.0),
    item("ahead", "In your face", "⬅️", "blows against the throw", sign=-1.0),
]

BALLS = [
    item("ping_pong", "Ping-pong ball", "🏓", "2.7 g, 4 cm", mass=0.0027, d=0.040, cd=0.50, color="#f5f5f0"),
    item("tennis", "Tennis ball", "🎾", "58 g, 6.7 cm", mass=0.058, d=0.067, cd=0.55, color="#d8f03c"),
    item("baseball", "Baseball", "⚾", "145 g, 7.4 cm", mass=0.145, d=0.074, cd=0.35, color="#f2efe6"),
    item("soccer", "Football", "⚽", "430 g, 22 cm", mass=0.43, d=0.22, cd=0.25, color="#ffffff"),
    item("basketball", "Basketball", "🏀", "620 g, 24 cm", mass=0.62, d=0.24, cd=0.47, color="#e8762d"),
    item("shot_put", "Shot put", "⚫", "7.26 kg iron, 12 cm", mass=7.26, d=0.12, cd=0.47, color="#6b7079"),
    item("beach_ball", "Beach ball", "🏖️", "100 g, 40 cm", mass=0.10, d=0.40, cd=0.47, color="#ff5c8a"),
]

BOBS = [
    item("brass", "Brass bob", "🟡", "0.96 kg, 6 cm", mass=0.96, d=0.06, cd=0.47, color="#d6a53e"),
    item("steel", "Steel ball", "⚪", "0.51 kg, 5 cm", mass=0.51, d=0.05, cd=0.47, color="#c0c8d8"),
    item("wood", "Wooden ball", "🟤", "0.16 kg, 8 cm", mass=0.16, d=0.08, cd=0.47, color="#a8703a"),
    item("rubber", "Rubber ball", "🔴", "0.13 kg, 6 cm", mass=0.13, d=0.06, cd=0.47, color="#e0455a"),
    item("tennis", "Tennis ball", "🎾", "58 g, 6.7 cm", mass=0.058, d=0.067, cd=0.55, color="#d8f03c"),
    item("ping_pong", "Ping-pong ball", "🏓", "2.7 g, 4 cm", mass=0.0027, d=0.04, cd=0.50, color="#f5f5f0"),
]

# energy ramp: kind decides sliding (box) or rolling (balls, spin share k);
# "contact" picks the friction row below
RAMP_OBJECTS = [
    item("crate", "Wooden crate", "📦", "10 kg, slides", kind="box", mass=10.0, contact="wood",
         color="#c98b4a"),
    item("ice_block", "Ice block", "🧊", "5 kg, slides", kind="box", mass=5.0, contact="ice",
         color="#cdeeff"),
    item("steel_block", "Steel block", "🔩", "20 kg, slides", kind="box", mass=20.0, contact="steel",
         color="#9aa3b0"),
    item("skateboard", "Skateboarder", "🛹", "45 kg on wheels (rolls, wheels barely spin)", kind="box",
         mass=45.0, contact="wheels", color="#ffb347"),
    item("bowling", "Bowling ball", "🎳", "7 kg solid ball", kind="solid_ball", mass=7.0, contact="hard",
         color="#4a54c8"),
    item("marble", "Marble", "🔮", "5 g solid glass ball", kind="solid_ball", mass=0.005,
         contact="hard", color="#7fd0ff"),
    item("basketball", "Basketball", "🏀", "0.62 kg hollow ball", kind="hollow_ball", mass=0.62,
         contact="rubber", color="#e8762d"),
    item("tennis", "Tennis ball", "🎾", "58 g hollow ball", kind="hollow_ball", mass=0.058,
         contact="felt", color="#d8f03c"),
]

SURFACES = [
    item("ice", "Ice rink", "⛸️", "very slippery", color="#bfe6ff"),
    item("wood", "Polished wood", "🪵", "a gym floor", color="#d9a45b"),
    item("concrete", "Concrete", "🧱", "a skate park", color="#9aa0aa"),
    item("carpet", "Carpet", "🟥", "soft and grippy", color="#b5485a"),
]

# sliding friction (kinetic; static taken the same) and rolling resistance,
# by object contact x surface
FRICTION = {
    "wood":   {"ice": 0.05, "wood": 0.30, "concrete": 0.50, "carpet": 0.35},
    "ice":    {"ice": 0.02, "wood": 0.05, "concrete": 0.10, "carpet": 0.15},
    "steel":  {"ice": 0.03, "wood": 0.35, "concrete": 0.45, "carpet": 0.40},
    "wheels": {"ice": 0.002, "wood": 0.004, "concrete": 0.01, "carpet": 0.05},
    "hard":   {"ice": 0.001, "wood": 0.002, "concrete": 0.004, "carpet": 0.03},
    "rubber": {"ice": 0.005, "wood": 0.01, "concrete": 0.012, "carpet": 0.05},
    "felt":   {"ice": 0.01, "wood": 0.02, "concrete": 0.025, "carpet": 0.08},
}

FLOATERS = [
    item("wood_block", "Wooden block", "🪵", "pine, 15 cm cube, 510 kg/m³", shape="cube", size=15.0, rho=510.0,
         color="#d8a35a"),
    item("duck", "Rubber duck", "🦆", "hollow toy, 10 cm, 250 kg/m³", shape="sphere", size=10.0, rho=250.0,
         color="#ffd166"),
    item("apple", "Apple", "🍎", "8 cm, 840 kg/m³", shape="sphere", size=8.0, rho=840.0, color="#e0455a"),
    item("egg", "Egg", "🥚", "5 cm, 1031 kg/m³", shape="sphere", size=5.0, rho=1031.0, color="#f3e5c8"),
    item("potato", "Potato", "🥔", "8 cm, 1090 kg/m³", shape="sphere", size=8.0, rho=1090.0, color="#c9a063"),
    item("ice_cube", "Ice cube", "🧊", "5 cm, 917 kg/m³", shape="cube", size=5.0, rho=917.0, color="#d9f1ff"),
    item("steel_ball", "Steel ball", "⚪", "4 cm, 7850 kg/m³", shape="sphere", size=4.0, rho=7850.0,
         color="#b0b8c8"),
    item("gold_bar", "Gold bar", "🥇", "5 cm cube, 19 300 kg/m³", shape="cube", size=5.0, rho=19300.0,
         color="#f2c230"),
]

LIQUIDS = [
    item("water", "Fresh water", "💧", "998 kg/m³", rho=998.0, mu=1.0e-3, color="#3d8fe0"),
    item("seawater", "Sea water", "🌊", "1025 kg/m³", rho=1025.0, mu=1.08e-3, color="#2f9fa8"),
    item("dead_sea", "Dead Sea water", "🧂", "super salty, 1240 kg/m³", rho=1240.0, mu=1.9e-3, color="#4fb3a8"),
    item("oil", "Vegetable oil", "🫒", "920 kg/m³", rho=920.0, mu=0.06, color="#e3c04a"),
    item("honey", "Honey", "🍯", "1420 kg/m³, very thick", rho=1420.0, mu=6.0, color="#d9891c"),
    item("mercury", "Mercury", "🪩", "13 534 kg/m³", rho=13534.0, mu=1.53e-3, color="#b5bcc6"),
]

THINGS = [   # heat: material + mass, and where it is allowed to come from
    item("tea", "Mug of tea", "☕", "0.3 kg of water", material="water", mass=0.3,
         sources=["fridge", "room", "sunny_car", "hot_tap", "kettle"]),
    item("bucket", "Bucket of water", "🪣", "5 kg of water", material="water", mass=5.0,
         sources=["fridge", "room", "sunny_car", "hot_tap", "kettle"]),
    item("pan", "Cast-iron pan", "🍳", "1.5 kg of iron", material="iron", mass=1.5,
         sources=["freezer", "fridge", "room", "sunny_car", "oven"]),
    item("pot", "Copper pot", "🥘", "1 kg of copper", material="copper", mass=1.0,
         sources=["freezer", "fridge", "room", "sunny_car", "oven"]),
    item("tray", "Aluminium tray", "🧇", "0.4 kg of aluminium", material="aluminum", mass=0.4,
         sources=["freezer", "fridge", "room", "sunny_car", "oven"]),
    item("bolt", "Big iron bolt", "🔩", "100 g of iron", material="iron", mass=0.1,
         sources=["freezer", "fridge", "room", "sunny_car", "oven"]),
]

SOURCES = [
    item("freezer", "Freezer", "🧊", "-18 °C", temp=-18.0),
    item("fridge", "Fridge", "🥶", "4 °C", temp=4.0),
    item("room", "Room", "🏠", "22 °C", temp=22.0),
    item("sunny_car", "Sunny car", "🚗", "55 °C", temp=55.0),
    item("hot_tap", "Hot tap", "🚿", "60 °C", temp=60.0),
    item("kettle", "Kettle", "🫖", "95 °C", temp=95.0),
    item("oven", "Oven", "🔥", "150 °C", temp=150.0),
]

ROOMS = [
    item("winter", "Winter garden", "❄️", "-5 °C", temp=-5.0),
    item("indoors", "Indoors", "🏠", "22 °C", temp=22.0),
    item("summer", "Summer day", "☀️", "35 °C", temp=35.0),
]

INSULATION = [
    item("none", "Nothing", "🌬️", "heat leaks 2 W/K", loss=2.0),
    item("towel", "Wrapped in a towel", "🧣", "0.5 W/K", loss=0.5),
    item("thermos", "Thermos flask", "🧪", "0.05 W/K", loss=0.05),
    item("perfect", "Perfect insulation", "🛡️", "no leak (a thought experiment)", loss=0.0),
]

ROPES = [
    item("cord", "Thin cord", "🧵", "20 g/m", mu=20.0),
    item("skipping", "Skipping rope", "🪢", "150 g/m", mu=150.0),
    item("thick", "Thick rope", "🪢", "500 g/m", mu=500.0),
    item("chain", "Heavy chain", "⛓️", "1 kg/m", mu=1000.0),
]

PULLS = [
    item("gentle", "Gentle pull", "🤏", "5 N", tension=5.0),
    item("firm", "Firm pull", "✊", "20 N", tension=20.0),
    item("strong", "Strong pull", "💪", "60 N", tension=60.0),
    item("tug", "Tug of war", "🏋️", "100 N", tension=100.0),
]

ROPE_ENDS = [
    item("wall", "Tied to a wall", "🧱", "fixed end", end="fixed"),
    item("ring", "Ring on a pole", "💍", "free end", end="free"),
    item("endless", "Endless rope", "➰", "no echo", end="open"),
]

MEDIUMS = [
    item("air", "In the air", "🌤️", "little friction", damping=0.5),
    item("pool", "Under water", "🏊", "water slows the rope", damping=2.5),
]

SHAKES = [
    item("small", "Small shake", "〰️", "±1 cm", amplitude=1.0),
    item("medium", "Medium shake", "〰️", "±3 cm", amplitude=3.0),
    item("big", "Big shake", "🌊", "±8 cm", amplitude=8.0),
]

LENSES = [
    item("magnifier", "Magnifying glass", "🔎", "acrylic, R = 30 cm", kind="converging", material="acrylic",
         radius=30.0),
    item("reading", "Reading glasses", "👓", "crown glass, R = 40 cm", kind="converging", material="crown",
         radius=40.0),
    item("camera", "Camera lens", "📷", "flint glass, R = 12 cm", kind="converging", material="flint", radius=12.0),
    item("drop", "Water drop", "💧", "water, R = 6 cm", kind="converging", material="water", radius=6.0),
    item("gem", "Diamond gem", "💎", "diamond, R = 10 cm", kind="converging", material="diamond", radius=10.0),
    item("myopia", "Glasses for short sight", "🤓", "diverging, crown glass, R = 40 cm", kind="diverging",
         material="crown", radius=40.0),
]

CANDLES = [
    item("birthday", "Birthday candle", "🎂", "2 cm tall", h=2.0),
    item("candle", "Candle", "🕯️", "4 cm tall", h=4.0),
    item("tall", "Tall candle", "🕯️", "8 cm tall", h=8.0),
]

JACKS = [
    item("syringes", "Two syringes", "💉", "1.5 cm -> 4 cm", d1=1.5, d2=4.0),
    item("bottle_jack", "Bottle jack", "🧴", "2 cm -> 8 cm", d1=2.0, d2=8.0),
    item("garage", "Garage lift", "🏗️", "3 cm -> 30 cm", d1=3.0, d2=30.0),
    item("press", "Giant press", "🏭", "2 cm -> 60 cm", d1=2.0, d2=60.0),
]

LOADS = [
    item("bike", "Bicycle", "🚲", "15 kg", mass=15.0),
    item("person", "A person", "🧍", "60 kg", mass=60.0),
    item("motorbike", "Motorbike", "🏍️", "200 kg", mass=200.0),
    item("car", "Car", "🚗", "1000 kg", mass=1000.0),
    item("van", "Van", "🚐", "2000 kg", mass=2000.0),
]

PUSHERS = [
    item("child", "A child", "🧒", "pushes 80 N", force=80.0),
    item("adult", "An adult", "🧑", "pushes 200 N", force=200.0),
    item("strong", "A weightlifter", "🏋️", "pushes 400 N", force=400.0),
]

HYDRAULIC = [
    item("oil", "Hydraulic oil", "🛢️", "870 kg/m³", fluid="oil"),
    item("water", "Water", "💧", "998 kg/m³", fluid="water"),
]

# circuit lab parts (placed on a grid edge)
PARTS = [
    item("wire", "Wire", "➖", "connects two dots", kind="wire", short=""),
    item("switch", "Switch", "🔘", "click it with the hand to open / close", kind="switch", short=""),
    item("lamp_torch", "Torch bulb 2.5 V", "💡", "2.5 V, 0.3 A (8.3 Ω)", kind="lamp", v_rated=2.5, R=2.5 / 0.3,
         short="2.5 V 0.75 W"),
    item("lamp_6v", "Lamp 6 V 3 W", "💡", "12 Ω", kind="lamp", v_rated=6.0, R=12.0, short="6 V 3 W"),
    item("lamp_car", "Car bulb 12 V 5 W", "💡", "28.8 Ω", kind="lamp", v_rated=12.0, R=28.8, short="12 V 5 W"),
    item("lamp_tiny", "Indicator 6 V 0.5 W", "🔆", "72 Ω", kind="lamp", v_rated=6.0, R=72.0, short="6 V 0.5 W"),
    item("res_10", "Resistor 10 Ω", "🟫", "10 Ω", kind="resistor", R=10.0, short="10 Ω"),
    item("res_47", "Resistor 47 Ω", "🟫", "47 Ω", kind="resistor", R=47.0, short="47 Ω"),
    item("res_100", "Resistor 100 Ω", "🟫", "100 Ω", kind="resistor", R=100.0, short="100 Ω"),
    item("aa", "AA battery 1.5 V", "🔋", "internal 0.15 Ω", kind="battery", emf=1.5, r_int=0.15, short="1.5 V"),
    item("lantern", "Lantern battery 6 V", "🔋", "internal 0.3 Ω", kind="battery", emf=6.0, r_int=0.3, short="6 V"),
    item("nine_v", "9 V battery", "🔋", "internal 1.5 Ω", kind="battery", emf=9.0, r_int=1.5, short="9 V"),
    item("car_battery", "Car battery 12 V", "🔋", "internal 0.02 Ω", kind="battery", emf=12.0, r_int=0.02, short="12 V"),
]

CATALOGS = {
    "planets": PLANETS, "weather": WEATHER, "wind_dir": WIND_DIR, "balls": BALLS, "bobs": BOBS,
    "ramp_objects": RAMP_OBJECTS, "surfaces": SURFACES, "floaters": FLOATERS, "liquids": LIQUIDS,
    "things": THINGS, "sources": SOURCES, "rooms": ROOMS, "insulation": INSULATION, "ropes": ROPES,
    "pulls": PULLS, "rope_ends": ROPE_ENDS, "mediums": MEDIUMS, "shakes": SHAKES, "lenses": LENSES,
    "candles": CANDLES, "jacks": JACKS, "loads": LOADS, "pushers": PUSHERS, "hydraulic": HYDRAULIC,
    "parts": PARTS,
}
BY_ID = {name: {it["id"]: it for it in items} for name, items in CATALOGS.items()}


# ---------------------------------------------------------------- fields

def obj(id_, label, catalog, default, max_count=1):
    return {"id": id_, "kind": "object", "label": label, "catalog": catalog, "default": default,
            "max_count": max_count}


def choice(id_, label, catalog, default, limited_by=None):
    """limited_by: id of an object field whose chosen item lists the
    allowed ids of this choice in its "sources" (tea can't come from the oven)."""
    f = {"id": id_, "kind": "choice", "label": label, "catalog": catalog, "default": default}
    if limited_by:
        f["limited_by"] = limited_by
    return f


def num(id_, label, lo, hi, default, unit="", step=None):
    return {"id": id_, "kind": "number", "label": label, "min": lo, "max": hi, "default": default,
            "unit": unit, "step": step or (hi - lo) / 100.0}


TRACK_X = [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0]
TRACK_LIMITS = {"y_min": 0.0, "y_max": 10.0, "max_slope": 3.0}
CIRCUIT_LIMITS = {"cols": 7, "rows": 5, "max_parts": 40, "max_batteries": 3, "max_lamps": 8}


def _loop(battery="lantern", lamp="lamp_6v", switch=True):
    parts = [{"part": battery, "a": [1, 4], "b": [2, 4]}, {"part": "wire", "a": [2, 4], "b": [3, 4]},
             {"part": "wire", "a": [3, 4], "b": [4, 4]}, {"part": "wire", "a": [4, 4], "b": [5, 4]},
             {"part": "switch" if switch else "wire", "a": [5, 4], "b": [5, 3], "on": True},
             {"part": "wire", "a": [5, 3], "b": [5, 2]},
             {"part": "wire", "a": [5, 2], "b": [5, 1]}, {"part": lamp, "a": [4, 1], "b": [5, 1]},
             {"part": "wire", "a": [3, 1], "b": [4, 1]}, {"part": "wire", "a": [2, 1], "b": [3, 1]},
             {"part": "wire", "a": [1, 1], "b": [2, 1]}, {"part": "wire", "a": [1, 1], "b": [1, 2]},
             {"part": "wire", "a": [1, 2], "b": [1, 3]}, {"part": "wire", "a": [1, 3], "b": [1, 4]}]
    return [dict(p, on=p.get("on", True), flip=False) for p in parts]


def _series():
    parts = _loop()
    parts[9] = {"part": "lamp_6v", "a": [2, 1], "b": [3, 1], "on": True, "flip": False}
    return parts


def _parallel():
    parts = _loop()
    parts += [{"part": "wire", "a": [3, 1], "b": [3, 0], "on": True, "flip": False},
              {"part": "lamp_6v", "a": [3, 0], "b": [4, 0], "on": True, "flip": False},
              {"part": "wire", "a": [4, 0], "b": [5, 0], "on": True, "flip": False},
              {"part": "wire", "a": [5, 0], "b": [5, 1], "on": True, "flip": False}]
    return parts


SANDBOX = {
    "motion": {
        "intro": "Pick up to two balls, choose the planet and the weather, then throw. Every ball keeps "
                 "its real mass, size and shape - only the world around it changes.",
        "fields": [obj("balls", "Balls (pick 1 or 2)", "balls", ["tennis"], 2),
                   choice("planet", "Planet", "planets", "earth"),
                   choice("weather", "Weather", "weather", "calm"),
                   choice("wind_dir", "Wind direction", "wind_dir", "ahead"),
                   num("v0", "Launch speed", 1.0, 50.0, 20.0, "m/s", 0.5),
                   num("angle", "Launch angle", 5.0, 85.0, 45.0, "deg", 1.0)],
        "presets": [{"title": "Ping-pong vs shot put", "world": {"balls": ["ping_pong", "shot_put"]}},
                    {"title": "Storm in your face", "world": {"balls": ["soccer"], "weather": "storm"}},
                    {"title": "Baseball on the Moon", "world": {"balls": ["baseball"], "planet": "moon"}},
                    {"title": "Beach ball on Titan", "world": {"balls": ["beach_ball", "basketball"],
                                                               "planet": "titan"}}],
    },
    "pendulum": {
        "intro": "Hang up to two bobs and change the planet and the weather. Wind pushes on the bob - "
                 "light, big bobs get blown sideways, heavy small ones hardly notice.",
        "fields": [obj("bobs", "Bobs (pick 1 or 2)", "bobs", ["brass"], 2),
                   choice("planet", "Planet", "planets", "earth"),
                   choice("weather", "Weather (wind from the left)", "weather", "calm"),
                   num("length", "String length", 0.2, 2.5, 1.0, "m", 0.05),
                   num("amplitude", "Release angle", 2.0, 80.0, 20.0, "deg", 1.0)],
        "presets": [{"title": "Ping-pong in a storm", "world": {"bobs": ["ping_pong", "brass"], "weather": "storm"}},
                    {"title": "Clock on Mars", "world": {"bobs": ["brass"], "planet": "mars"}},
                    {"title": "Thick air on Titan", "world": {"bobs": ["wood", "steel"], "planet": "titan",
                                                              "amplitude": 60.0}}],
    },
    "energy": {
        "intro": "Shape your own ramp by dragging the yellow dots (within limits), pick the surface and "
                 "up to two objects, and let go from the left end.",
        "fields": [obj("objects", "Objects (pick 1 or 2)", "ramp_objects", ["crate"], 2),
                   choice("surface", "Ramp surface", "surfaces", "wood"),
                   choice("planet", "Planet", "planets", "earth"),
                   {"id": "track", "kind": "track", "label": "Ramp shape", "xs": TRACK_X,
                    "default": [8.0, 3.5, 0.9, 0.0, 0.9, 3.5, 8.0], **TRACK_LIMITS}],
        "presets": [{"title": "Half-pipe", "world": {"track": [8.0, 3.5, 0.9, 0.0, 0.9, 3.5, 8.0]}},
                    {"title": "Straight ramp", "world": {"track": [8.0, 5.5, 3.2, 1.4, 0.6, 0.3, 0.3]}},
                    {"title": "Two hills", "world": {"track": [8.0, 1.0, 4.0, 0.5, 3.0, 0.5, 6.0]}},
                    {"title": "Ski jump", "world": {"track": [9.0, 4.5, 1.5, 2.5, 1.0, 0.6, 0.6],
                                                    "objects": ["skateboard"]}},
                    {"title": "Ice block vs bowling ball", "world": {"objects": ["ice_block", "bowling"],
                                                                     "surface": "ice"}},
                    {"title": "Carpet slows everything", "world": {"objects": ["marble", "tennis"],
                                                                   "surface": "carpet"}}],
    },
    "buoyancy": {
        "intro": "Drop an everyday object into the tank and choose the liquid. Each object has its real "
                 "size and density.",
        "fields": [obj("object", "Object", "floaters", "egg"),
                   choice("liquid", "Liquid", "liquids", "water"),
                   choice("planet", "Planet", "planets", "earth"),
                   num("start", "Drop from (centre above surface)", -30.0, 30.0, 15.0, "cm", 1.0)],
        "presets": [{"title": "Egg in the Dead Sea", "world": {"object": "egg", "liquid": "dead_sea"}},
                    {"title": "Apple vs potato", "world": {"object": "potato"}},
                    {"title": "Steel ball on mercury", "world": {"object": "steel_ball", "liquid": "mercury"}},
                    {"title": "Gold on mercury", "world": {"object": "gold_bar", "liquid": "mercury"}},
                    {"title": "Duck in honey", "world": {"object": "duck", "liquid": "honey", "start": -20.0}}],
    },
    "heat": {
        "intro": "Take two things from around the house, say where each one has been, and put them "
                 "together. Some things can't go everywhere (no water in the oven!).",
        "fields": [obj("thing_a", "Thing A", "things", "tea"), choice("source_a", "A comes from", "sources", "kettle", "thing_a"),
                   obj("thing_b", "Thing B", "things", "pot"), choice("source_b", "B comes from", "sources", "fridge", "thing_b"),
                   choice("room", "Where they sit", "rooms", "indoors"),
                   choice("insulation", "Wrapped in", "insulation", "perfect")],
        "presets": [{"title": "Hot pan, cold water", "world": {"thing_a": "pan", "source_a": "oven",
                                                               "thing_b": "bucket", "source_b": "fridge"}},
                    {"title": "Tea left outside in winter", "world": {"thing_a": "tea", "source_a": "kettle",
                                                                      "thing_b": "bolt", "source_b": "room",
                                                                      "room": "winter", "insulation": "none"}},
                    {"title": "Tea in a thermos", "world": {"insulation": "thermos", "room": "winter"}}],
    },
    "waves": {
        "intro": "Choose a rope, how hard you pull it, what its end is tied to and where you are. Then "
                 "shake it.",
        "fields": [choice("rope", "Rope", "ropes", "skipping"), choice("pull", "Pull", "pulls", "firm"),
                   choice("end", "Far end", "rope_ends", "wall"), choice("medium", "Where", "mediums", "air"),
                   choice("shake", "Shake size", "shakes", "medium"),
                   num("f", "Shake frequency", 0.2, 5.0, 1.5, "Hz", 0.05),
                   num("length", "Rope length", 1.0, 8.0, 4.0, "m", 0.1)],
        "presets": [{"title": "Chain under water", "world": {"rope": "chain", "medium": "pool"}},
                    {"title": "Thin cord, strong pull", "world": {"rope": "cord", "pull": "tug", "f": 5.0}},
                    {"title": "Endless rope", "world": {"end": "endless"}}],
    },
    "optics": {
        "intro": "Pick a lens and a candle. Move the candle (drag its flame) to find every kind of image.",
        "fields": [choice("lens", "Lens", "lenses", "magnifier"), obj("candle", "Candle", "candles", "candle"),
                   num("d_o", "Candle distance", 2.0, 100.0, 40.0, "cm", 0.5)],
        "presets": [{"title": "Water-drop magnifier", "world": {"lens": "drop", "d_o": 3.0}},
                    {"title": "Reading glasses", "world": {"lens": "reading", "d_o": 25.0}},
                    {"title": "Short-sight glasses", "world": {"lens": "myopia"}},
                    {"title": "Diamond", "world": {"lens": "gem", "d_o": 15.0}}],
    },
    "pressure": {
        "intro": "Choose the machine, what to lift, who pushes and the liquid inside.",
        "fields": [choice("jack", "Machine", "jacks", "garage"), obj("load", "Load", "loads", "car"),
                   choice("pusher", "Who pushes", "pushers", "adult"), choice("fluid", "Liquid", "hydraulic", "oil"),
                   num("stroke", "Push distance", 5.0, 40.0, 25.0, "cm", 1.0)],
        "presets": [{"title": "Child lifts a car", "world": {"pusher": "child", "load": "car"}},
                    {"title": "Syringes lift a person?", "world": {"jack": "syringes", "load": "person"}},
                    {"title": "Giant press, van", "world": {"jack": "press", "load": "van", "pusher": "child"}}],
    },
    "circuits": {
        "scene": "circuitlab",
        "intro": "Build your own circuit: pick a part, then click between two dots to place it. Click a "
                 "switch to flip it; the eraser removes parts. Up to 40 parts, 3 batteries and 8 lamps.",
        "fields": [{"id": "parts", "kind": "circuit", "label": "Circuit board", "catalog": "parts",
                    "default": _loop(), **CIRCUIT_LIMITS}],
        "presets": [{"title": "Simple loop", "world": {"parts": _loop()}},
                    {"title": "Two lamps in series", "world": {"parts": _series()}},
                    {"title": "Two lamps in parallel", "world": {"parts": _parallel()}},
                    {"title": "Torch bulb on a car battery", "world": {"parts": _loop("car_battery", "lamp_torch")}},
                    {"title": "Empty board", "world": {"parts": []}}],
    },
}


# ---------------------------------------------------------------- validation

def _is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def defaults(topic):
    out = {}
    for f in SANDBOX[topic]["fields"]:
        d = f["default"]
        out[f["id"]] = list(d) if isinstance(d, list) else d
    return out


def validate(topic, world):
    """Return (clean_world, error). Missing fields take their default;
    anything unknown, out of range or not in a catalog is rejected."""
    if topic not in SANDBOX:
        return None, "no sandbox for '%s'" % str(topic)[:32]
    if not isinstance(world, dict):
        return None, "the world must be an object"
    fields = {f["id"]: f for f in SANDBOX[topic]["fields"]}
    for k in world:
        if k not in fields:
            return None, "'%s' is not part of this world" % str(k)[:40]
    clean = defaults(topic)
    for fid, f in fields.items():
        if fid not in world:
            continue
        v, kind = world[fid], f["kind"]
        if kind == "choice":
            if not isinstance(v, str) or v not in BY_ID[f["catalog"]]:
                return None, "'%s' is not a choice for %s" % (str(v)[:40], f["label"].lower())
        elif kind == "object":
            vals = v if isinstance(v, list) else [v]
            if f["max_count"] == 1 and isinstance(v, list):
                return None, "pick one %s" % f["label"].lower()
            if f["max_count"] > 1 and not isinstance(v, list):
                return None, "%s must be a list of 1 to %d" % (f["label"].lower(), f["max_count"])
            if not 1 <= len(vals) <= f["max_count"]:
                return None, "pick 1 to %d for %s" % (f["max_count"], f["label"].lower())
            for x in vals:
                if not isinstance(x, str) or x not in BY_ID[f["catalog"]]:
                    return None, "'%s' is not in the %s box" % (str(x)[:40], f["label"].lower())
            v = list(vals) if f["max_count"] > 1 else vals[0]
        elif kind == "number":
            if not _is_num(v) or not f["min"] <= v <= f["max"]:
                return None, "%s must be between %g and %g" % (f["label"].lower(), f["min"], f["max"])
            v = float(v)
        elif kind == "track":
            err = _check_track(f, v)
            if err:
                return None, err
            v = [float(y) for y in v]
        elif kind == "circuit":
            v, err = _check_circuit(f, v)
            if err:
                return None, err
        clean[fid] = v
    for f in fields.values():                 # choices that depend on a picked object
        if f.get("limited_by"):
            by = fields[f["limited_by"]]
            thing = BY_ID[by["catalog"]][clean[f["limited_by"]]]
            if clean[f["id"]] not in thing["sources"]:
                src = BY_ID[f["catalog"]][clean[f["id"]]]
                return None, "a %s can't come from the %s" % (thing["label"].lower(), src["label"].lower())
    return clean, None


def _check_track(f, ys):
    if not isinstance(ys, list) or len(ys) != len(f["xs"]):
        return "the ramp needs exactly %d heights" % len(f["xs"])
    if not all(_is_num(y) and f["y_min"] <= y <= f["y_max"] for y in ys):
        return "every ramp point must be between %g m and %g m high" % (f["y_min"], f["y_max"])
    bad = energy.SplineTrack(f["xs"], ys).check(f["max_slope"])
    if "ground" in bad:
        return "that shape dips below the ground - lift the low points a little"
    if "steep" in bad:
        return "that ramp is too steep (more than %d°) - smooth it out" % round(math.degrees(math.atan(f["max_slope"])))
    return None


def _check_circuit(f, parts):
    if not isinstance(parts, list):
        return None, "the circuit must be a list of parts"
    if len(parts) > f["max_parts"]:
        return None, "at most %d parts on the board" % f["max_parts"]
    seen, clean, counts = set(), [], {"battery": 0, "lamp": 0}
    for p in parts:
        if not isinstance(p, dict) or set(p) - {"part", "a", "b", "on", "flip"} or not {"part", "a", "b"} <= set(p):
            return None, "every part needs 'part', 'a' and 'b' (and optionally 'on', 'flip')"
        spec = BY_ID["parts"].get(p["part"]) if isinstance(p["part"], str) else None
        if not spec:
            return None, "'%s' is not in the parts box" % str(p["part"])[:40]
        ends = []
        for e in (p["a"], p["b"]):
            if not (isinstance(e, list) and len(e) == 2 and all(isinstance(c, int) and not isinstance(c, bool)
                                                               for c in e)):
                return None, "part ends must be [column, row]"
            if not (0 <= e[0] < f["cols"] and 0 <= e[1] < f["rows"]):
                return None, "that part is off the board"
            ends.append(tuple(e))
        if abs(ends[0][0] - ends[1][0]) + abs(ends[0][1] - ends[1][1]) != 1:
            return None, "a part must join two neighbouring dots"
        edge = frozenset(ends)
        if edge in seen:
            return None, "two parts can't sit on the same spot"
        seen.add(edge)
        for flag in ("on", "flip"):
            if flag in p and not isinstance(p[flag], bool):
                return None, "'%s' must be true or false" % flag
        if spec["kind"] in counts:
            counts[spec["kind"]] += 1
        clean.append({"part": p["part"], "a": list(ends[0]), "b": list(ends[1]),
                      "on": p.get("on", True), "flip": p.get("flip", False)})
    if counts["battery"] > f["max_batteries"]:
        return None, "at most %d batteries" % f["max_batteries"]
    if counts["lamp"] > f["max_lamps"]:
        return None, "at most %d lamps" % f["max_lamps"]
    return clean, None


# ---------------------------------------------------------------- running

def run(topic, world):
    """world must already be validated. Returns {runs: [{label, result}], notes}."""
    w = world
    C = BY_ID
    if topic == "motion":
        pl, we, wd = C["planets"][w["planet"]], C["weather"][w["weather"]], C["wind_dir"][w["wind_dir"]]
        runs = []
        for bid in w["balls"]:
            b = C["balls"][bid]
            k = 0.5 * pl["rho_air"] * b["cd"] * math.pi * (b["d"] / 2) ** 2
            p = {"v0": w["v0"], "angle": w["angle"], "mass": b["mass"], "drag": k,
                 "wind": we["wind"] * wd["sign"], "g": pl["g"]}
            res = motion.run(p)
            res["params"] = p
            res["viz"] = {"theme": {"sky": pl["sky"], "ground": pl["ground"]}, "label": b["label"],
                          "ball_color": b["color"], "k": k}
            runs.append({"label": b["label"], "result": res})
        notes = []
        if pl["rho_air"] == 0.0 and we["wind"] > 0:
            notes.append("There is no air on the Moon, so there is no wind - and no drag. Every ball flies "
                         "the same perfect parabola.")
        return {"runs": runs, "notes": notes}
    if topic == "pendulum":
        pl, we = C["planets"][w["planet"]], C["weather"][w["weather"]]
        runs = []
        for bid in w["bobs"]:
            b = C["bobs"][bid]
            k = 0.5 * pl["rho_air"] * b["cd"] * math.pi * (b["d"] / 2) ** 2
            wind = we["wind"] if pl["rho_air"] > 0 else 0.0
            p = {"length": w["length"], "amplitude": w["amplitude"], "mass": b["mass"], "g": pl["g"],
                 "drag": k, "wind": wind}
            res = pendulum.run(p)
            res["params"] = p
            res["viz"].update({"theme": {"sky": pl["sky"]}, "label": b["label"], "bob": {"d": b["d"], "color": b["color"]}})
            runs.append({"label": b["label"], "result": res})
        return {"runs": runs, "notes": []}
    if topic == "energy":
        pl, surf = C["planets"][w["planet"]], C["surfaces"][w["surface"]]
        track = energy.SplineTrack(TRACK_X, w["track"])
        runs = []
        for oid in w["objects"]:
            o = C["ramp_objects"][oid]
            mu = FRICTION[o["contact"]][surf["id"]]
            res = energy.simulate(track, track.x0, o["mass"], energy.K[o["kind"]], mu, pl["g"],
                                  kind="custom", obj=o["kind"], label=o["label"].lower(),
                                  viz_extra={"points": [[x, y] for x, y in zip(TRACK_X, w["track"])],
                                             "surface": surf, "label": o["label"], "mu": mu,
                                             "icon": o["icon"], "color": o["color"], "id": o["id"],
                                             "limits": TRACK_LIMITS,
                                             "theme": {"sky": pl["sky"]}})
            res["params"] = {"mass": o["mass"], "g": pl["g"], "friction": mu, "object": o["kind"]}
            res["readouts"].insert(0, {"label": "Friction on %s (%s)" % (surf["label"].lower(),
                                                                         "rolling" if o["kind"] != "box" and
                                                                         o["contact"] != "wheels" else
                                                                         "wheels" if o["contact"] == "wheels"
                                                                         else "sliding"),
                                       "value": mu, "unit": "μ"})
            runs.append({"label": o["label"], "result": res})
        return {"runs": runs, "notes": []}
    if topic == "buoyancy":
        o, liq, pl = C["floaters"][w["object"]], C["liquids"][w["liquid"]], C["planets"][w["planet"]]
        solid = {"id": o["id"], "label": o["label"], "rho": o["rho"], "color": o["color"]}
        p = {"shape": o["shape"], "size": o["size"], "g": pl["g"], "start": w["start"]}
        res = buoyancy.simulate(p, solid, {k: liq[k] for k in ("id", "label", "rho", "mu", "color")})
        res["params"] = p
        return {"runs": [{"label": o["label"], "result": res}], "notes": []}
    if topic == "heat":
        a, b = C["things"][w["thing_a"]], C["things"][w["thing_b"]]
        p = {"material_a": a["material"], "mass_a": a["mass"], "temp_a": C["sources"][w["source_a"]]["temp"],
             "material_b": b["material"], "mass_b": b["mass"], "temp_b": C["sources"][w["source_b"]]["temp"],
             "ambient": C["rooms"][w["room"]]["temp"], "loss": C["insulation"][w["insulation"]]["loss"]}
        res = heat.run(p)
        res["params"] = p
        return {"runs": [{"label": a["label"] + " + " + b["label"], "result": res}],
                "notes": ["A = %s (%g kg), B = %s (%g kg)." % (a["label"], a["mass"], b["label"], b["mass"])]}
    if topic == "waves":
        p = {"f": w["f"], "amplitude": C["shakes"][w["shake"]]["amplitude"],
             "tension": C["pulls"][w["pull"]]["tension"], "mu": C["ropes"][w["rope"]]["mu"],
             "length": w["length"], "end": C["rope_ends"][w["end"]]["end"],
             "damping": C["mediums"][w["medium"]]["damping"]}
        res = waves.run(p)
        res["params"] = p
        return {"runs": [{"label": C["ropes"][w["rope"]]["label"], "result": res}], "notes": []}
    if topic == "optics":
        L, cd = C["lenses"][w["lens"]], C["candles"][w["candle"]]
        p = {"kind": L["kind"], "material": L["material"], "radius": L["radius"], "d_o": w["d_o"], "h_o": cd["h"]}
        res = optics.run(p)
        res["params"] = p
        return {"runs": [{"label": L["label"], "result": res}], "notes": []}
    if topic == "pressure":
        j, ld, pu, fl = C["jacks"][w["jack"]], C["loads"][w["load"]], C["pushers"][w["pusher"]], C["hydraulic"][w["fluid"]]
        p = {"force": pu["force"], "d1": j["d1"], "d2": j["d2"], "mass": ld["mass"], "stroke": w["stroke"],
             "fluid": fl["fluid"]}
        res = pressure.run(p)
        res["params"] = p
        res["viz"]["load_label"] = ld["label"]
        return {"runs": [{"label": j["label"], "result": res}], "notes": []}
    if topic == "circuits":
        lim = CIRCUIT_LIMITS
        parts = []
        for q in w["parts"]:
            spec = C["parts"][q["part"]]
            d = {k: v for k, v in spec.items() if k in ("kind", "R", "v_rated", "emf", "r_int", "short")}
            d.update({"a": tuple(q["a"]), "b": tuple(q["b"]), "on": q["on"], "flip": q["flip"],
                      "label": spec["label"], "id": spec["id"]})
            parts.append(d)
        res = circuitlab.run(parts, lim["cols"], lim["rows"])
        res["params"] = {}
        return {"runs": [{"label": "your circuit", "result": res}], "notes": []}
    raise ValueError(topic)


def catalog_view():
    """Everything the browser needs to build the sandbox panels."""
    out = {}
    for topic, sb in SANDBOX.items():
        fields = []
        for f in sb["fields"]:
            f2 = dict(f)
            if "catalog" in f:
                f2["items"] = CATALOGS[f["catalog"]]
            fields.append(f2)
        out[topic] = {"intro": sb["intro"], "scene": sb.get("scene", topic), "fields": fields,
                      "presets": sb["presets"], "defaults": defaults(topic)}
    return out
