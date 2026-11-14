"""Learning content for every ready topic: the big idea, each formula
explained (plain words, symbols with units, why it works, something to
try), annotated screenshots of the simulation, and real-life uses.

Figures are real captures of the app at a chosen set-up and moment,
regenerated with `python3 tools/make_figures.py`. Each figure's
`params` / `b` (compare set B overrides) / `view` / `at` (seconds of
simulated time) define BOTH the screenshot and its "Try this setup"
deep link, so the two can never disagree. Callout x/y are canvas pixels
(880 x 500). tests/test_learn.py checks that every formula is explained,
every figure set-up is valid and every image exists.
"""

CANVAS_W, CANVAS_H = 880, 500

LEARN = {
    # ------------------------------------------------------------------
    "circuits": {
        "big_idea": "A battery pushes electric charge around a closed loop, like a pump pushing water "
                    "round a pipe. Everything in the loop resists the flow, and the same current has to "
                    "squeeze through every part. Lamps turn that electrical energy into heat - and only a "
                    "really hot filament glows brightly.",
        "presets": [
            {"title": "One lamp", "params": {}},
            {"title": "Two lamps in series", "params": {"lamps": 2}},
            {"title": "Three lamps", "params": {"lamps": 3}},
            {"title": "Over-volted (12 V)", "params": {"voltage": 12.0}},
            {"title": "Add a resistor", "params": {"resistor": 20.0}},
            {"title": "Switch off", "params": {"closed": False}},
            {"title": "A latch coil on a lantern battery", "params": {"voltage": 6.0, "lamp_r": 8.0, "internal_r": 0.4,
                                                                       "resistor": 6.0}},
        ],
        "formulas": {
            "I = V / (R + r)": {
                "say": "Current = the battery's push ÷ everything that resists the flow.",
                "symbols": [["I", "current: how much electric charge passes any point each second", "A (amperes)"],
                            ["V", "battery voltage: how hard the battery pushes", "V (volts)"],
                            ["R", "resistance outside the battery: all the lamps + the extra resistor", "Ω (ohms)"],
                            ["r", "the battery's own internal resistance", "Ω (ohms)"]],
                "explain": "In a single loop there is only one path, so the SAME current flows through every "
                           "wire, every lamp and even the battery. Adding a lamp in series adds its resistance, "
                           "so the current drops for all of them - not just for the lamp after it. Double the "
                           "voltage and the current doubles (this is Ohm's law).",
                "try_it": "Go from 1 lamp to 2 lamps and watch the electrons: they slow down everywhere in the "
                          "loop at the same moment.",
            },
            "P = I^2 * R_lamp": {
                "say": "Power in one lamp = current × current × the lamp's resistance.",
                "symbols": [["P", "power: energy turned into heat and light every second", "W (watts = J/s)"],
                            ["I", "current through the lamp", "A"],
                            ["R_lamp", "resistance of one lamp", "Ω"]],
                "explain": "The current is SQUARED: half the current gives only a quarter of the power. "
                           "Two lamps in series each get roughly half the current, so each gets about 1/4 of "
                           "the power a single lamp had (here 0.44 W instead of 1.71 W).",
                "try_it": "Look at 'Lamp power (each)' with 1, 2 and 3 lamps.",
            },
            "T^4 - T_room^4 ~ P": {
                "say": "A hotter filament glows brighter and whiter - but it takes a lot of extra power to "
                       "make it a little hotter.",
                "symbols": [["T", "filament temperature (0 °C = 273 K)", "K (kelvin)"],
                            ["T_room", "room temperature, about 293 K", "K"],
                            ["P", "power going into the lamp", "W"],
                            ["~", "'grows in step with' (is proportional to)", ""]],
                "explain": "A hot object radiates energy that grows with the FOURTH power of its temperature "
                           "(the Stefan-Boltzmann law). Below about 800 K a filament gives no visible light; at "
                           "2700 K it glows warm white. Because hotter light is also more visible to our eyes, "
                           "light output rises much faster than power: at a quarter of its power a lamp gives "
                           "only about 2% of its light, and it looks orange.",
                "try_it": "Set 3 lamps: current still flows (0.099 A) but the filament only reaches about "
                          "1550 K - a dull orange-red glow.",
            },
        },
        "figures": [
            {"title": "One loop, one current", "params": {}, "view": {"carriers": "electrons"}, "at": 1.0,
             "callouts": [
                 {"x": 300, "y": 200, "text": "Electrons fill the whole wire, evenly spaced, and all drift at the same speed."},
                 {"x": 366, "y": 372, "text": "They leave the battery's − end, travel round the loop and come back in at + "
                                              "(conventional current I is drawn the other way)."},
                 {"x": 486, "y": 140, "text": "The lamp turns 1.71 W into heat and light: its filament glows warm white "
                                              "at about 2700 K."},
                 {"x": 386, "y": 16, "text": "I = 0.293 A - you would measure the same current anywhere in the loop."},
                 {"x": 705, "y": 250, "text": "A closed switch completes the loop. Open it and the flow stops everywhere "
                                              "at once."}],
             "caption": "Electrons are everywhere in the wire and all drift at the same speed. The lamp "
                        "lights instantly because they all start moving together - nothing has to 'arrive'."},
            {"title": "Two lamps share the push", "params": {"lamps": 2}, "view": {}, "at": 1.0,
             "callouts": [
                 {"x": 386, "y": 16, "text": "Twice the resistance → the current halves: 0.148 A instead of 0.293 A."},
                 {"x": 236, "y": 33, "text": "Each lamp gets half the voltage (2.96 V) but only a QUARTER of the power "
                                             "(0.44 W), because P = I²R."},
                 {"x": 352, "y": 110, "text": "Same current through both lamps, so they glow exactly the same."},
                 {"x": 570, "y": 148, "text": "The filament only reaches 1898 K: dull orange, about 2% of the light of "
                                              "one lamp on its own."}],
             "caption": "More resistance → less current → each lamp gets a quarter of the power and glows "
                        "dull orange."},
            {"title": "Too much voltage", "params": {"voltage": 12.0}, "view": {}, "at": 1.0,
             "callouts": [
                 {"x": 486, "y": 150, "text": "11.7 V across a 6 V lamp: 6.85 W, almost 4x its rated power - white-hot."},
                 {"x": 512, "y": 110, "text": "3771 K is hotter than tungsten's melting point (3695 K): a real lamp "
                                              "would blow instantly."},
                 {"x": 364, "y": 67, "text": "322 lm: 4x the power gives 16x the light - brightness rises much faster "
                                             "than power."},
                 {"x": 580, "y": 430, "text": "The cause: a 12 V battery on a 6 V lamp."}],
             "caption": "Twice the rated voltage gives 4x the power: the filament would pass tungsten's melting "
                        "point. That is why every lamp has a voltage rating."},
        ],
        "real_life": [
            {"icon": "🔦", "title": "Torch with tired batteries",
             "text": "As batteries run down their voltage drops. The bulb doesn't just get a bit dimmer - it "
                     "fades to orange and gives almost no light long before the current stops (the T^4 law).",
             "formula": "T^4 - T_room^4 ~ P"},
            {"icon": "🎄", "title": "Old-style fairy lights",
             "text": "Many small bulbs in series share the mains voltage: 50 bulbs on 230 V get about 4.6 V "
                     "each. One broken bulb breaks the loop, so the whole string goes dark.",
             "formula": "I = V / (R + r)"},
            {"icon": "🧯", "title": "Fuses and circuit breakers",
             "text": "Too many appliances on one socket means a big current, and wires heat up as I²R. A fuse "
                     "is a thin wire that melts first and opens the loop before the wiring gets dangerous.",
             "formula": "P = I^2 * R_lamp"},
            {"icon": "🍞", "title": "Toaster vs light bulb",
             "text": "A toaster element glows dull orange at about 1000 K - it is built for heat. A bulb "
                     "filament runs near 2700 K to look white. LED bulbs make the same light with about 1/6 "
                     "of the power because they don't rely on heat at all.",
             "formula": "T^4 - T_room^4 ~ P"},
        ],
    },
    # ------------------------------------------------------------------
    "motion": {
        "big_idea": "Once a ball leaves your hand, only two things act on it: gravity pulling it down, and "
                    "air drag pushing against its motion through the air. Gravity bends the path into a "
                    "curve; drag steals speed and makes the curve fall short and steep.",
        "presets": [
            {"title": "No air", "params": {}},
            {"title": "Drag + headwind", "params": {"drag": 0.02, "wind": -6.0}},
            {"title": "30° vs 60°", "params": {"angle": 30.0}, "b": {"angle": 60.0}},
            {"title": "Heavy vs light ball", "params": {"drag": 0.01, "mass": 2.0}, "b": {"mass": 0.2}},
            {"title": "On the Moon", "params": {"g": 1.62}},
            {"title": "Off a 20 m tower", "params": {"v0": 10.0, "angle": 30.0, "height": 20.0}},
            {"title": "A wooden ball in a gale", "params": {"v0": 2.0, "angle": 10.0, "height": 2.5, "mass": 0.15,
                                                            "drag": 0.001, "wind": 16.0}},
        ],
        "formulas": {
            "a = -g - (k/m) * v_air * |v_air|": {
                "say": "How the ball's velocity changes = gravity pulling down + drag pushing back.",
                "symbols": [["a", "acceleration: how fast the velocity changes", "m/s²"],
                            ["g", "gravity (Earth 9.81, Moon 1.62)", "m/s²"],
                            ["k", "drag constant: bigger for big, rough, un-streamlined objects", "kg/m"],
                            ["m", "mass of the ball", "kg"],
                            ["v_air", "the ball's velocity through the air = ball velocity - wind", "m/s"]],
                "explain": "Gravity gives every ball the same acceleration, heavy or light - without air they "
                           "would fly identically. Drag grows with the SQUARE of the speed through the air "
                           "(twice as fast, four times the drag) and always points against that motion. "
                           "Dividing by m means a heavy ball hardly notices drag while a light one is slowed a "
                           "lot. Wind only matters through drag, because it changes v_air.",
                "try_it": "Tick 'Compare two balls', give ball B mass 0.2 kg and both balls drag 0.01: the "
                          "light ball falls short.",
            },
            "Range = v0^2 * sin(2*angle) / g": {
                "say": "Without air: distance = speed² × sin(2 × angle) ÷ gravity.",
                "symbols": [["Range", "how far the ball lands from the launch point", "m"],
                            ["v0", "launch speed", "m/s"],
                            ["angle", "launch angle above the ground", "°"],
                            ["g", "gravity", "m/s²"]],
                "explain": "sin(2 × angle) is biggest at 45°, so 45° throws farthest when there is no air. "
                           "Angles that add up to 90° (like 30° and 60°) land at exactly the same spot - the "
                           "high one just takes longer. Double the speed and the range becomes 4x. On the Moon "
                           "(g six times smaller) the same throw goes six times as far. With air drag the best "
                           "angle is lower than 45°.",
                "try_it": "Compare 30° and 60° with no drag: both land at 28.6 m.",
            },
            "x = v0*cos(a) * (v0*sin(a) + sqrt((v0*sin(a))^2 + 2*g*h)) / g": {
                "say": "Launched from a height h (no air): distance = sideways speed × time in the air.",
                "symbols": [["x", "how far from the foot of the tower it lands", "m"],
                            ["v0*cos(a)", "sideways speed - it never changes without air", "m/s"],
                            ["v0*sin(a)", "upward speed at launch", "m/s"],
                            ["h", "launch height above the ground", "m"],
                            ["g", "gravity", "m/s²"]],
                "explain": "Split the throw in two. Sideways the ball coasts at a steady speed; up and down it "
                           "rises, stops and falls - and from a tower it has h metres more to fall, so it stays "
                           "up longer and lands farther. The time in the air is the bracket ÷ g (the bigger "
                           "solution of h + v0·sin(a)·t − ½gt² = 0). With h = 0 it becomes the Range formula "
                           "above. From a height the best angle is a bit less than 45°.",
                "try_it": "Set the launch height to 20 m, speed 10 m/s, angle 30°: it lands 22.4 m out, "
                          "2.6 s later.",
            },
        },
        "figures": [
            {"title": "No air: a perfect parabola", "params": {}, "view": {}, "at": 1.3,
             "callouts": [
                 {"x": 418, "y": 292, "text": "The only force is the weight, 9.8 N, straight down - at every point of "
                                              "the flight."},
                 {"x": 468, "y": 16, "text": "Speed at the top: 12.7 m/s = 18 × cos 45°. The sideways speed never "
                                             "changes without air."},
                 {"x": 436, "y": 222, "text": "At the very top the ball is not stopped - only its up-down speed is zero."},
                 {"x": 92, "y": 430, "text": "Launched at 18 m/s and 45°."}],
             "caption": "With no air the only force is the weight, always straight down. The sideways speed "
                        "never changes; only the up-down speed does."},
            {"title": "Air drag and a headwind", "params": {"drag": 0.02, "wind": -6.0}, "view": {}, "at": 0.8,
             "callouts": [
                 {"x": 196, "y": 282, "text": "Drag (4.11 N) points backwards and down - against the ball's motion "
                                              "through the air."},
                 {"x": 226, "y": 348, "text": "The weight is unchanged: 9.8 N straight down."},
                 {"x": 436, "y": 246, "text": "The dashed path: where the ball would go with no air - all the way to 33 m."},
                 {"x": 630, "y": 16, "text": "A 6 m/s headwind: the ball moves through the air even faster, so the "
                                             "drag is bigger."},
                 {"x": 560, "y": 72, "text": "Wind streaks move at the real wind speed, on the same scale as the ball."}],
             "caption": "Drag points against the ball's motion THROUGH THE AIR. Against the wind it slows the "
                        "ball even more, and the path ends up short and steep instead of a symmetric arch."},
            {"title": "30° and 60° land together", "params": {"angle": 30.0}, "b": {"angle": 60.0},
             "view": {}, "at": 3.2, "callouts": [
                 {"x": 435, "y": 108, "text": "B at 60°: a high, slow arc - 3.18 s in the air."},
                 {"x": 432, "y": 328, "text": "A at 30°: a low, fast arc - only 1.83 s in the air."},
                 {"x": 780, "y": 430, "text": "Both land at exactly 28.60 m."}],
             "caption": "Without air, angles that add to 90° give the same range: sin(2·30°) = sin(2·60°)."},
        ],
        "real_life": [
            {"icon": "🏀", "title": "Basketball shots",
             "text": "The same distance can be reached with a low or a high arc. Players use a high arc "
                     "(about 45-55°): the ball drops into the hoop more steeply, so the hoop looks bigger.",
             "formula": "Range = v0^2 * sin(2*angle) / g"},
            {"icon": "⛳", "title": "Golf drives",
             "text": "Drivers launch the ball at only about 10-15°, far below 45°. Air drag (and the lift from "
                     "backspin) change the best angle. The dimples reduce drag so the ball flies farther.",
             "formula": "a = -g - (k/m) * v_air * |v_air|"},
            {"icon": "🚒", "title": "Fire hoses and fountains",
             "text": "Each drop of water is a tiny projectile, so a jet draws a parabola. Firefighters aim a "
                     "little below 45° for the longest reach, because air drag shortens the jet.",
             "formula": "Range = v0^2 * sin(2*angle) / g"},
            {"icon": "🏸", "title": "Badminton shuttlecock",
             "text": "A shuttle is very light with a big drag constant, so k/m is huge: it slows down "
                     "quickly and drops almost straight down at the end of its flight.",
             "formula": "a = -g - (k/m) * v_air * |v_air|"},
            {"icon": "🌙", "title": "Golf on the Moon",
             "text": "In 1971 astronaut Alan Shepard hit golf balls on the Moon. With gravity 6x weaker and no "
                     "air at all, the same swing sends the ball six times as far as on Earth (without air).",
             "formula": "Range = v0^2 * sin(2*angle) / g"},
        ],
    },
    # ------------------------------------------------------------------
    "heat": {
        "big_idea": "Heat always flows from hot to cold, and keeps flowing until both things are at the "
                    "same temperature. How much a temperature changes depends on the mass and on the "
                    "material: water needs a LOT of energy to warm up, metals need very little.",
        "presets": [
            {"title": "Water meets iron", "params": {}},
            {"title": "Two copper blocks", "params": {"material_a": "copper", "material_b": "copper"}},
            {"title": "Big vs small block", "params": {"material_b": "water", "mass_a": 5.0, "mass_b": 0.5}},
            {"title": "Heat leak to the room", "params": {"loss": 1.5}},
            {"title": "Thermal camera", "params": {}, "view": {"look": "thermal"}},
            {"title": "Hot water on an aluminium ring", "params": {"material_a": "water", "mass_a": 0.2, "temp_a": 95.0,
                                                                   "material_b": "aluminum", "mass_b": 0.3,
                                                                   "temp_b": 20.0, "ambient": 20.0, "loss": 0.1}},
        ],
        "formulas": {
            "Q = m * c * dT": {
                "say": "Heat energy = mass × specific heat × temperature change.",
                "symbols": [["Q", "heat energy moved in or out", "J (joules)"],
                            ["m", "mass", "kg"],
                            ["c", "specific heat: energy to warm 1 kg by 1 °C", "J/(kg·K)"],
                            ["dT", "temperature change (ΔT); a step of 1 °C is the same as 1 K", "°C"]],
                "explain": "Water's c is 4186: it takes 4186 J to warm 1 kg of water by 1 °C, but only 450 J "
                           "for 1 kg of iron. So the same amount of heat changes iron's temperature about 9x "
                           "more than water's. Energy is conserved: the heat A loses is exactly the heat B "
                           "gains, Q_A = -Q_B (watch the numbers above).",
                "try_it": "Water at 90 °C meets iron at 20 °C (1 kg each): the water cools only 6.8 °C while "
                          "the iron warms 63 °C.",
            },
            "T_eq = (m_a c_a T_a + m_b c_b T_b) / (m_a c_a + m_b c_b)": {
                "say": "The final temperature is an average, weighted by each block's heat capacity m·c.",
                "symbols": [["T_eq", "the temperature both blocks end up at", "°C"],
                            ["m_a, m_b", "masses of the blocks", "kg"],
                            ["c_a, c_b", "specific heats of their materials", "J/(kg·K)"],
                            ["T_a, T_b", "starting temperatures", "°C"]],
                "explain": "The block with the bigger m·c 'wins': the final temperature lands close to where "
                           "it started. With equal m·c it's the plain average. Heat flows fastest while the "
                           "gap is big and slows down as the temperatures get close, which is why the curves "
                           "in the graph bend and level off. (Exact only with no heat leak to the room.)",
                "try_it": "Make both blocks copper, 1 kg each: they meet exactly halfway.",
            },
            "dL = alpha * L * dT": {
                "say": "When a metal warms up it gets a tiny bit longer: length change = expansion "
                       "coefficient × length × temperature change.",
                "symbols": [["dL", "how much longer it gets (ΔL)", "m"],
                            ["alpha", "linear expansion coefficient (α): how much each metre grows per kelvin", "1/K"],
                            ["L", "its length (or the width of a hole in it)", "m"],
                            ["dT", "temperature change (ΔT)", "K (= °C of change)"]],
                "explain": "Hotter atoms jiggle harder and push each other a little further apart, so the "
                           "whole piece grows - in every direction, and holes in it grow too, exactly as if "
                           "they were made of the metal. The numbers are tiny: aluminium grows 23 millionths "
                           "of its length per degree, iron 12. Different metals grow by different amounts, "
                           "which is why a hot aluminium ring lets go of a steel ball.",
                "try_it": "Put 0.2 kg of 95 °C water against 0.3 kg of aluminium: look at 'Block B grows' - "
                          "about 1300 µm per metre at its hottest.",
            },
        },
        "figures": [
            {"title": "Heat flows from hot to cold", "params": {}, "view": {"look": "real"}, "at": 15.0,
             "callouts": [
                 {"x": 432, "y": 300, "text": "Glowing packets are heat crossing the contact from the hot water to the "
                                              "cold iron. Each packet is 500 J."},
                 {"x": 300, "y": 290, "text": "Hot water molecules jiggle fast (the motion is exaggerated so you can see "
                                              "it)."},
                 {"x": 204, "y": 33, "text": "The heat flow right now: 668 W. It gets smaller as the temperature gap "
                                             "closes."},
                 {"x": 700, "y": 70, "text": "The graph: the two temperatures head towards the 'meet' line from "
                                             "opposite sides."},
                 {"x": 240, "y": 440, "text": "Water has a huge c, so it has only cooled 3.6 °C while the iron warmed 33 °C."}],
             "caption": "The water starts hot, the iron cold. Energy moves across the contact at a rate set by "
                        "the temperature gap."},
            {"title": "Equilibrium: the same temperature", "params": {}, "view": {"look": "real"}, "at": 166.0,
             "callouts": [
                 {"x": 240, "y": 440, "text": "Both blocks at 83.2 °C - exactly what T_eq predicted."},
                 {"x": 350, "y": 82, "text": "No more net heat flow, so no more packets."},
                 {"x": 760, "y": 60, "text": "The curves flattened out: the smaller the gap, the slower the heat flows."},
                 {"x": 300, "y": 300, "text": "The molecules still jiggle - temperature is not zero, it's just equal."}],
             "caption": "Both blocks at 83.2 °C - right where the weighted-average formula predicted. No more "
                        "net heat flows, but the atoms keep jiggling: temperature isn't zero!"},
            {"title": "Thermal camera with a heat leak", "params": {"loss": 1.5}, "view": {"look": "thermal"},
             "at": 60.0, "callouts": [
                 {"x": 300, "y": 300, "text": "Thermal camera: the colour shows temperature (scale at the top left)."},
                 {"x": 372, "y": 142, "text": "Packets rising into the air: heat leaking into the room."},
                 {"x": 276, "y": 67, "text": "The leak is biggest from the hottest block."},
                 {"x": 800, "y": 100, "text": "So both blocks will end at room temperature (25 °C), not at T_eq."}],
             "caption": "With a leak, both blocks also lose heat to the room, so they end at room temperature "
                        "instead of at T_eq."},
        ],
        "real_life": [
            {"icon": "🛤️", "title": "Gaps in bridges and rails",
             "text": "A 100 m steel bridge is about 4 cm longer on a hot summer day than on a cold winter "
                     "night (12 millionths per metre per degree, times 100 m, times 35 °C). Expansion joints - "
                     "the metal 'teeth' you drive over - give it room to grow.",
             "formula": "dL = alpha * L * dT"},
            {"icon": "🫙", "title": "A stuck jar lid",
             "text": "Run hot water over a stuck metal lid: the metal grows more than the glass, the lid "
                     "loosens. Heat the wrong part (the glass) and it only gets tighter.",
             "formula": "dL = alpha * L * dT"},
            {"icon": "🏖️", "title": "Mild seaside weather",
             "text": "The sea's huge m·c means it warms and cools very slowly. Coastal towns get cooler "
                     "summers and milder winters than places far inland.",
             "formula": "Q = m * c * dT"},
            {"icon": "🚗", "title": "Car engine cooling",
             "text": "Engines are cooled with water-based coolant because water soaks up lots of heat for each "
                     "degree it warms, carrying the heat to the radiator.",
             "formula": "Q = m * c * dT"},
            {"icon": "🍳", "title": "Pans that heat fast or stay hot",
             "text": "Thin aluminum and copper pans (small c, small mass) heat up with little energy. A heavy "
                     "cast-iron pan (big mass) holds lots of heat and keeps food hot.",
             "formula": "Q = m * c * dT"},
            {"icon": "🌡️", "title": "Why thermometers work",
             "text": "A thermometer in your mouth warms until it reaches the same temperature as you - "
                     "equilibrium - and then reads your temperature.",
             "formula": "T_eq = (m_a c_a T_a + m_b c_b T_b) / (m_a c_a + m_b c_b)"},
            {"icon": "🧊", "title": "Ice in a drink",
             "text": "A small cold ice cube can only pull the drink down a little, because the drink has much "
                     "more m·c - that's why you need several cubes.",
             "formula": "T_eq = (m_a c_a T_a + m_b c_b T_b) / (m_a c_a + m_b c_b)"},
        ],
    },
    # ------------------------------------------------------------------
    "buoyancy": {
        "big_idea": "A liquid pushes up on anything in it with a force equal to the weight of the liquid it "
                    "pushes aside (Archimedes' principle). If that push can beat the object's weight, it "
                    "floats - sinking in just until the push equals its weight. Density decides who wins.",
        "presets": [
            {"title": "Floating wood", "params": {}},
            {"title": "Sinking iron", "params": {"material": "iron"}},
            {"title": "Iron on mercury", "params": {"material": "iron", "fluid": "mercury"}},
            {"title": "Tip of the iceberg", "params": {"shape": "sphere", "material": "ice", "size": 25.0, "start": 0.0}},
            {"title": "Rising through honey", "params": {"material": "rubber", "fluid": "honey", "start": -25.0}},
            {"title": "On the Moon", "params": {"g": 1.62}},
            {"title": "Salt floats a bouncy ball", "params": {"shape": "sphere", "material": "bouncy", "size": 6.0,
                                                               "salt": 275.0, "start": 10.0}},
            {"title": "Aesop's crow: stones in a narrow well", "params": {"shape": "sphere", "material": "woodball",
                                                                           "size": 8.0, "start": 15.0,
                                                                           "vessel": "well", "depth": 20.0,
                                                                           "extra": 1800.0}},
        ],
        "formulas": {
            "F_b = rho_fluid * V_sub * g": {
                "say": "Push up = liquid density × volume under the surface × gravity.",
                "symbols": [["F_b", "buoyant force: the liquid's push upwards", "N (newtons)"],
                            ["rho_fluid", "density of the liquid: mass of 1 m³ of it (ρ)", "kg/m³"],
                            ["V_sub", "volume of the object below the surface (1 litre = 0.001 m³)", "m³"],
                            ["g", "gravity", "m/s²"]],
                "explain": "The push comes from pressure: deeper liquid pushes harder (p = ρ·g·depth), so the "
                           "bottom of an object is pushed up more than its top is pushed down. That difference "
                           "is exactly the weight of the liquid that would fill the submerged part. A denser "
                           "liquid pushes harder - floating is easier in sea water, and even iron floats on "
                           "mercury.",
                "try_it": "Switch the view to 'water pressure' and compare the arrows on the top and the bottom.",
            },
            "W = rho_obj * V * g": {
                "say": "Weight = the object's density × its whole volume × gravity.",
                "symbols": [["W", "weight: gravity's pull on the object", "N"],
                            ["rho_obj", "density of the object's material", "kg/m³"],
                            ["V", "the object's whole volume", "m³"],
                            ["g", "gravity", "m/s²"]],
                "explain": "Mass = density × volume, and weight = mass × g. A big cork block can weigh less "
                           "than a small iron one, because cork's density is 33x smaller.",
                "try_it": "Keep the size, switch pine → iron: the weight jumps 15x.",
            },
            "V_sub / V = rho_obj / rho_fluid": {
                "say": "The fraction under the surface = object density ÷ liquid density.",
                "symbols": [["V_sub / V", "fraction of the object below the surface", ""],
                            ["rho_obj / rho_fluid", "how dense the object is compared with the liquid", ""]],
                "explain": "A floater sinks in until F_b = W. Setting the two formulas equal, the V's and g's "
                           "rearrange to this simple ratio. Ice (917) in water (998) floats 92% under - the "
                           "'tip of the iceberg'. g cancels out, so a boat floats at the same depth on the "
                           "Moon. If rho_obj is bigger than rho_fluid the ratio is above 1: even fully under, "
                           "the push can't match the weight, so it sinks.",
                "try_it": "Try pine wood in water (51% under), then in honey (36% under).",
            },
            "dh = V_pushed / A": {
                "say": "The water rises by the volume pushed aside ÷ the area of the container.",
                "symbols": [["dh", "how much the water level rises", "m"],
                            ["V_pushed", "volume of water pushed aside (a sinker: its whole volume; a floater: "
                                         "only its own weight of water)", "m³"],
                            ["A", "the container's inside area, seen from above", "m²"]],
                "explain": "Water can't be squashed, so whatever goes in pushes the surface up - spread over "
                           "the whole area of the container. 200 cm³ of stone lifts a 4000 cm² tank by 0.05 cm, "
                           "but a 10 cm well (79 cm²) by 2.5 cm. A stone pushes aside its WHOLE volume; a "
                           "floating block only pushes aside its own weight of water, so a pine block raises the "
                           "water half as much as a stone of the same size.",
                "try_it": "Pick the narrow well, a wooden ball, 20 cm of water: add 1800 cm³ of stones and watch "
                          "the ball float up to 44 cm.",
            },
        },
        "figures": [
            {"title": "Floating means the forces balance", "params": {}, "view": {"show": "forces"}, "at": 8.3,
             "callouts": [
                 {"x": 535, "y": 212, "text": "About half of the block is out of the water: 510 / 998 = 51% is under."},
                 {"x": 624, "y": 120, "text": "Weight 8.65 N, buoyancy 8.65 N: balanced, so it stays put."},
                 {"x": 70, "y": 300, "text": "The water it pushed aside: 0.883 L, weighing 8.65 N - exactly the block's "
                                             "weight."},
                 {"x": 226, "y": 104, "text": "Pine (510 kg/m³) is less dense than water (998 kg/m³), so it floats."},
                 {"x": 318, "y": 230, "text": "The water level rose 0.22 cm: that's the pushed-aside water."}],
             "caption": "At rest the buoyancy exactly equals the weight, and the liquid pushed aside weighs "
                        "exactly as much as the block."},
            {"title": "Where the push comes from: pressure", "params": {"material": "rubber", "start": -12.0},
             "view": {"show": "pressure"}, "at": 0.6, "callouts": [
                 {"x": 535, "y": 300, "text": "Top face: 1.59 kPa pushing down."},
                 {"x": 680, "y": 386, "text": "Bottom face: deeper, so 2.76 kPa pushing up - more than the top."},
                 {"x": 452, "y": 360, "text": "The side pushes are equal and opposite: they cancel."},
                 {"x": 240, "y": 141, "text": "Rubber (1100) is a bit denser than water, so it still sinks - slowly, "
                                              "because the push up nearly matches its weight."}],
             "caption": "Pressure grows with depth, so the bottom face is pushed harder than the top face. "
                        "The sideways pushes cancel. Bottom push − top push = buoyancy."},
            {"title": "The tip of the iceberg", "params": {"shape": "sphere", "material": "ice", "size": 25.0,
                                                           "start": 0.0},
             "view": {"show": "forces"}, "at": 17.5, "callouts": [
                 {"x": 535, "y": 222, "text": "Only the top cap - about 8% - sticks out."},
                 {"x": 282, "y": 50, "text": "92% of the ice's volume is under the surface: 917 / 998."},
                 {"x": 624, "y": 120, "text": "Weight 73.6 N = buoyancy 73.6 N."},
                 {"x": 70, "y": 300, "text": "7.5 litres of water pushed aside."}],
             "caption": "Ice is only a little less dense than water, so it floats with about 92% hidden under "
                        "the surface."},
        ],
        "real_life": [
            {"icon": "🐦", "title": "The crow and the pitcher",
             "text": "In Aesop's fable a thirsty crow drops pebbles into a narrow pitcher until the water rises "
                     "within reach of its beak. Real crows and rooks solve this puzzle too - and they pick "
                     "sinking stones over floating cork, because floaters push aside much less water.",
             "formula": "dh = V_pushed / A"},
            {"icon": "🚢", "title": "Steel ships float",
             "text": "Steel is 8x denser than water, but a hull is mostly air inside. The ship sinks in until "
                     "it pushes aside its own weight of water - that weight is the ship's 'displacement'. It "
                     "floats higher in salty sea water than in a river.",
             "formula": "F_b = rho_fluid * V_sub * g"},
            {"icon": "🧊", "title": "Icebergs",
             "text": "Ice (917 kg/m³) in sea water (1025 kg/m³) floats with about 89% below the surface, which "
                     "is why icebergs are so dangerous to ships.",
             "formula": "V_sub / V = rho_obj / rho_fluid"},
            {"icon": "🐟", "title": "Fish and submarines",
             "text": "A fish's swim bladder and a submarine's ballast tanks change their average density, "
                     "letting them rise, sink, or hover in between (neutral buoyancy).",
             "formula": "V_sub / V = rho_obj / rho_fluid"},
            {"icon": "🏊", "title": "Floating in the Dead Sea",
             "text": "The Dead Sea is so salty (about 1240 kg/m³) that people float high, as if lying on a "
                     "mattress - a bigger rho_fluid means less of you needs to be under the surface.",
             "formula": "V_sub / V = rho_obj / rho_fluid"},
            {"icon": "🎈", "title": "Hot-air balloons",
             "text": "Air is a fluid too. Hot air is less dense than the cool air around it, so the cool air "
                     "pushes the balloon up - Archimedes' principle in the sky.",
             "formula": "F_b = rho_fluid * V_sub * g"},
        ],
    },
    # ------------------------------------------------------------------
    "waves": {
        "big_idea": "A wave carries energy along the rope, but each bit of rope only moves up and down. The "
                    "rope decides how fast waves travel; your hand decides how often they are made; "
                    "together they set the wavelength. Waves bounce back from the end - and at special "
                    "frequencies the echoes add up into a big standing wave.",
        "presets": [
            {"title": "Resonance (f2)", "params": {}},
            {"title": "First harmonic (f1)", "params": {"f": 1.25}},
            {"title": "Off resonance", "params": {"f": 1.9}},
            {"title": "Free end", "params": {"end": "free"}},
            {"title": "Endless rope", "params": {"end": "open"}},
            {"title": "Tight, light rope", "params": {"tension": 80.0, "mu": 50.0}},
        ],
        "formulas": {
            "v = sqrt(T / mu)": {
                "say": "Wave speed = √(tension ÷ mass per metre).",
                "symbols": [["v", "wave speed along the rope", "m/s"],
                            ["T", "tension: how hard the rope is pulled tight", "N"],
                            ["mu", "mass per metre of rope (μ; the slider shows g/m)", "kg/m"]],
                "explain": "A tighter rope snaps back faster, so waves travel faster; a heavier rope is more "
                           "sluggish, so they travel slower. Four times the tension doubles the speed. Shaking "
                           "faster or harder does NOT change v - only the rope does.",
                "try_it": "Change the frequency and watch 'Wave speed' in the readouts: it stays the same.",
            },
            "v = f * lambda": {
                "say": "Wave speed = frequency × wavelength.",
                "symbols": [["v", "wave speed", "m/s"],
                            ["f", "frequency: shakes per second", "Hz (hertz)"],
                            ["lambda", "wavelength: distance from one crest to the next (λ)", "m"]],
                "explain": "Every shake sends out one wavelength. In one second your hand makes f of them, and "
                           "the front has travelled v metres, so v = f × λ. The rope fixes v, so shake twice as "
                           "fast and the waves come out half as long.",
                "try_it": "Choose 'Endless rope', then double the frequency: the yellow λ ruler halves.",
            },
            "f_n = n * v / (2 * L)": {
                "say": "The rope's favourite frequencies (fixed end): n × speed ÷ twice the length.",
                "symbols": [["f_n", "the n-th resonant frequency", "Hz"],
                            ["n", "1, 2, 3 … - the number of loops in the standing wave", ""],
                            ["v", "wave speed", "m/s"],
                            ["L", "rope length", "m"]],
                "explain": "A wave reflects from the far end and comes back to your hand. If it arrives in "
                           "step with your next shake, every trip adds more: the waves pile up into a standing "
                           "wave with n loops and still points (nodes) every half wavelength. With a fixed end "
                           "that happens when the rope holds a whole number of half-waves. A free end (ring on "
                           "a pole) makes a loop at the end instead: f_n = (2n-1)·v/(4L). An endless rope "
                           "never echoes, so it never resonates.",
                "try_it": "Slide the frequency onto the green marks of the resonance ladder and watch the "
                          "wave grow.",
            },
        },
        "figures": [
            {"title": "A travelling wave", "params": {"end": "open"}, "view": {"speed": "0.25"}, "at": 1.5,
             "callouts": [
                 {"x": 551, "y": 108, "text": "This bead only moves up and down (the blue arrow is its velocity)."},
                 {"x": 462, "y": 92, "text": "The crest marker rides one crest to the right at v = 10 m/s."},
                 {"x": 300, "y": 318, "text": "One wavelength: λ = v / f = 10 / 2.5 = 4 m."},
                 {"x": 60, "y": 228, "text": "The shaker makes 2.5 waves every second."},
                 {"x": 690, "y": 258, "text": "Endless rope: the wave never comes back."}],
             "caption": "The wave shape moves to the right at v, but the rope itself only moves up and down - "
                        "like a stadium 'Mexican wave'."},
            {"title": "Resonance: a standing wave", "params": {}, "view": {}, "at": 10.0,
             "callouts": [
                 {"x": 456, "y": 244, "text": "A node: this point never moves. It's half a wavelength (2 m) from the wall."},
                 {"x": 287, "y": 92, "text": "An antinode: it swings ±15 cm - five times the shaker's ±3 cm."},
                 {"x": 479, "y": 452, "text": "Your 2.5 Hz sits exactly on f2 = 2 × 10 / (2 × 4) = 2.5 Hz."},
                 {"x": 790, "y": 300, "text": "Fixed end: the rope can't move here, so reflected waves come back upside "
                                              "down."}],
             "caption": "At f_2 = 2.5 Hz the reflections arrive in step with the shaking and the wave grows 5x "
                        "taller than the hand's motion."},
            {"title": "Off resonance", "params": {"f": 1.9}, "view": {}, "at": 10.0,
             "callouts": [
                 {"x": 392, "y": 452, "text": "1.9 Hz falls between f1 and f2: no resonance."},
                 {"x": 660, "y": 196, "text": "The rope swings about as much as the shaker: the echoes arrive out of step "
                                              "and partly cancel."},
                 {"x": 352, "y": 50, "text": "Careful: heights are drawn 14x taller here (4.7x in the resonance picture), "
                                             "so the real wave is much smaller."}],
             "caption": "Between resonances the echoes arrive out of step and partly cancel: the rope barely "
                        "moves more than the hand does."},
        ],
        "real_life": [
            {"icon": "🎸", "title": "Guitar strings",
             "text": "A string is fixed at both ends and plays f_1 = v/(2L). Tightening the peg raises T and "
                     "the note; pressing a fret shortens L and raises the note; thick strings (big μ) play "
                     "the low notes.",
             "formula": "f_n = n * v / (2 * L)"},
            {"icon": "🌉", "title": "The wobbly Millennium Bridge",
             "text": "When London's Millennium Bridge opened in 2000, people's footsteps fell into step with "
                     "the bridge's own sideways swing and it wobbled. Engineers fixed it by adding dampers - "
                     "the 'damping' slider in real life.",
             "formula": "f_n = n * v / (2 * L)"},
            {"icon": "🏟️", "title": "Stadium wave",
             "text": "In a Mexican wave each person only stands up and sits down, yet the wave races round "
                     "the stadium - just like the red bead on the rope.",
             "formula": "v = f * lambda"},
            {"icon": "🌍", "title": "Earthquake waves",
             "text": "Earthquakes send out fast and slow waves. The delay between them at a seismometer tells "
                     "scientists how far away the quake happened.",
             "formula": "v = f * lambda"},
        ],
    },
    # ------------------------------------------------------------------
    "pendulum": {
        "big_idea": "Part of gravity always pulls the bob back towards the middle. It speeds up, overshoots, "
                    "climbs, stops and comes back - again and again. The time for one full swing depends on "
                    "the string's length and on gravity, but not on the mass, and for small swings hardly on "
                    "how far you pull it.",
        "presets": [
            {"title": "Small swing", "params": {}},
            {"title": "Big swing (80°)", "params": {"amplitude": 80.0}},
            {"title": "Long vs short", "params": {}, "b": {"length": 0.25}},
            {"title": "Heavy vs light", "params": {"mass": 4.0}, "b": {"mass": 0.2}},
            {"title": "With air drag", "params": {"mass": 0.2, "drag": 0.01, "amplitude": 60.0}},
            {"title": "On the Moon", "params": {"g": 1.62}},
            {"title": "Crane magnet: how hard does it pull?", "params": {"length": 1.0, "amplitude": 58.0,
                                                                         "mass": 0.5}},
        ],
        "formulas": {
            "T = 2*pi * sqrt(L/g)": {
                "say": "Time for one full swing = 2π × √(length ÷ gravity).",
                "symbols": [["T", "period: time for one full swing there and back", "s"],
                            ["L", "length from the pivot to the middle of the bob", "m"],
                            ["g", "gravity", "m/s²"],
                            ["pi", "π ≈ 3.1416", ""]],
                "explain": "A longer string means slower swings: 4x the length doubles the period. Weaker "
                           "gravity also means slower swings - a 1 m pendulum takes about 5 s on the Moon "
                           "instead of 2 s. Mass cancels out: a heavier bob is pulled harder but is also "
                           "harder to speed up. This formula is exact only for small swings.",
                "try_it": "Compare two pendulums with masses 0.2 kg and 4 kg: they stay perfectly in step.",
            },
            "T_exact = T / AGM(1, cos(theta0/2))": {
                "say": "The exact period for big swings - a little longer than the simple formula.",
                "symbols": [["T_exact", "the true period for this release angle", "s"],
                            ["theta0", "release angle (θ0)", "°"],
                            ["AGM", "arithmetic-geometric mean: keep replacing two numbers by their average "
                                    "and by √(their product) until they agree", ""]],
                "explain": "Big swings take a bit longer: 0.8% longer at 20°, 7% at 60°, 18% at 90°. That's "
                           "why pendulum clocks swing only a little - then the timing barely depends on how "
                           "big the swing is.",
                "try_it": "Set the release angle to 80° and compare 'Period, small-angle formula' with "
                          "'Period, measured in the run'.",
            },
            "F_restore = m * g * sin(theta)": {
                "say": "The pull back to the middle = weight × sin(angle).",
                "symbols": [["F_restore", "the part of gravity along the swing path", "N"],
                            ["m", "mass of the bob", "kg"],
                            ["g", "gravity", "m/s²"],
                            ["theta", "angle of the string from straight down (θ)", "°"]],
                "explain": "Split the weight into two parts: one along the string (the tension balances it) "
                           "and one along the swing path, m·g·sin θ. That part always points back to the "
                           "middle. It is biggest at the ends and zero at the bottom, so the bob speeds up on "
                           "the way down and slows down on the way up.",
                "try_it": "Pause near the end of a swing and at the bottom: compare the orange arrow.",
            },
            "E = 0.5*m*v^2 + m*g*h": {
                "say": "Energy = motion energy + height energy, and the total stays the same.",
                "symbols": [["E", "total mechanical energy", "J"],
                            ["½·m·v²", "kinetic energy (energy of motion)", "J"],
                            ["m·g·h", "potential energy (energy of height)", "J"],
                            ["h", "height above the lowest point", "m"]],
                "explain": "At the ends the bob stops for an instant: all of its energy is height. At the "
                           "bottom it is fastest: all of it is motion. Without drag the total never changes, "
                           "so the top speed is v = √(2·g·h). With drag, a little energy becomes heat on every "
                           "swing.",
                "try_it": "Watch the energy bar swap between blue (height) and orange (speed).",
            },
        },
        "figures": [
            {"title": "At the end of a swing", "params": {"amplitude": 40.0}, "view": {"arrows": "forces"},
             "at": 0.06, "callouts": [
                 {"x": 488, "y": 362, "text": "The restoring part of gravity (6.2 N) pulls the bob back towards the middle."},
                 {"x": 700, "y": 286, "text": "Tension 7.7 N - LESS than the weight here, because the bob is barely moving."},
                 {"x": 704, "y": 383, "text": "Weight 9.8 N, straight down. The dashed arrows are its two parts."},
                 {"x": 532, "y": 157, "text": "Released at 40° from straight down."},
                 {"x": 782, "y": 365, "text": "All the energy is height (blue)."}],
             "caption": "The bob is almost still, so all its energy is height, and the restoring part of "
                        "gravity is at its biggest."},
            {"title": "At the bottom: fastest", "params": {"amplitude": 40.0}, "view": {"arrows": "velocity"},
             "at": 0.515, "callouts": [
                 {"x": 318, "y": 395, "text": "Fastest at the bottom: 2.14 m/s, straight along the swing."},
                 {"x": 600, "y": 352, "text": "The fading trail shows it sped up on the way down."},
                 {"x": 782, "y": 365, "text": "All the energy is now motion (orange)."},
                 {"x": 520, "y": 157, "text": "θ ≈ 0: no pull back to the middle here, so it just coasts through."}],
             "caption": "At the lowest point the pull back is zero and the speed is greatest: all the energy "
                        "is motion."},
            {"title": "Four times shorter, twice as fast", "params": {}, "b": {"length": 0.25},
             "view": {"arrows": "off"}, "at": 1.04, "callouts": [
                 {"x": 214, "y": 412, "text": "A (1 m): half a swing done - it has reached the far side."},
                 {"x": 650, "y": 170, "text": "B (0.25 m): already a whole swing, back where it started."},
                 {"x": 494, "y": 24, "text": "Periods 2.021 s and 1.011 s: exactly 2 : 1."}],
             "caption": "T = 2π√(L/g): a quarter of the length gives half the period, so pendulum B swings "
                        "twice for every swing of A."},
        ],
        "real_life": [
            {"icon": "🕰️", "title": "Pendulum clocks",
             "text": "A grandfather clock's pendulum is about 1 m long, so one swing each way takes 1 s. To "
                     "fix a clock that runs slow you raise the bob - a shorter pendulum ticks faster.",
             "formula": "T = 2*pi * sqrt(L/g)"},
            {"icon": "🛝", "title": "Playground swings",
             "text": "A swing is a pendulum. To go higher you pump in rhythm with its natural period, and a "
                     "swing with longer chains swings more slowly.",
             "formula": "T = 2*pi * sqrt(L/g)"},
            {"icon": "🏙️", "title": "Skyscraper dampers",
             "text": "Taipei 101 has a 660-tonne steel ball hanging like a pendulum near the top. It swings "
                     "against the building's sway in strong winds and soaks up the motion.",
             "formula": "F_restore = m * g * sin(theta)"},
            {"icon": "🏗️", "title": "Crane loads",
             "text": "A load hanging from a crane swings with a period set only by the cable length, so crane "
                     "operators move gently and wait for the swing to settle.",
             "formula": "T = 2*pi * sqrt(L/g)"},
            {"icon": "🌍", "title": "Measuring gravity",
             "text": "Turn the formula round, g = 4π²L/T², and a pendulum becomes a gravity meter. Scientists "
                     "used pendulums to map tiny changes in g around the world.",
             "formula": "T = 2*pi * sqrt(L/g)"},
        ],
    },

    # ------------------------------------------------------------------
    "optics": {
        "big_idea": "Light slows down inside glass, so when it enters a curved lens at an angle it bends. A "
                    "converging lens bends rays from each point of a candle back together to form an image; "
                    "where that image appears, how big it is and which way up it is all follow from one "
                    "simple formula.",
        "formulas": {
            "1/f = (n - 1) * (1/R1 - 1/R2)": {
                "say": "How strong a lens is depends on its glass (n) and how curved its faces are (R).",
                "symbols": [["f", "focal length: where parallel light is brought to a point", "cm"],
                            ["n", "refractive index of the lens material (how much it slows light)", ""],
                            ["R1, R2", "radius of curvature of the front and back faces (+ bulges to the "
                                       "left, - to the right)", "cm"]],
                "explain": "Light bends more when the glass is denser (bigger n) and when the faces are more "
                           "curved (smaller R), so both make the focal length shorter. A fat, strongly curved "
                           "lens is powerful; a thin, gently curved one is weak. A diamond lens would be more "
                           "than 4x stronger than a water lens of the same shape.",
                "try_it": "Change the material from water to diamond and watch F and F' rush towards the lens.",
            },
            "1/f = 1/d_o + 1/d_i": {
                "say": "Candle distance and image distance are linked through the focal length.",
                "symbols": [["f", "focal length (negative for a diverging lens)", "cm"],
                            ["d_o", "distance from the candle to the lens", "cm"],
                            ["d_i", "distance from the lens to the image (negative = virtual image on the "
                                    "candle's side)", "cm"]],
                "explain": "Far away candles make an image close to F'. Moving the candle in towards F "
                           "pushes the image further and further away. At exactly d_o = f the rays come out "
                           "parallel and there is no image at all; closer than f, the image jumps to the "
                           "candle's side and becomes virtual (that's a magnifying glass).",
                "try_it": "Drag the candle's flame slowly towards F and watch the image run away.",
            },
            "m = -d_i / d_o = h_i / h_o": {
                "say": "Magnification = how many times bigger the image is (minus sign = upside down).",
                "symbols": [["m", "magnification: negative means the image is upside down", ""],
                            ["h_i, h_o", "heights of the image and of the candle", "cm"],
                            ["d_i, d_o", "image and candle distances", "cm"]],
                "explain": "The ray through the middle of the lens goes straight on, so the candle's tip, "
                           "the lens centre and the image's tip lie on one line - similar triangles give "
                           "h_i / h_o = -d_i / d_o. An image farther from the lens than the candle is bigger.",
                "try_it": "Put the candle at 2F (twice the focal length): the image is the same size, upside down.",
            },
            "n = c / v": {
                "say": "The refractive index tells you how many times slower light is inside the material.",
                "symbols": [["n", "refractive index", ""],
                            ["c", "speed of light in empty space, 299 792 km/s", "km/s"],
                            ["v", "speed of light inside the material", "km/s"]],
                "explain": "In crown glass light travels at about 197 000 km/s - only 66% of its top speed. "
                           "When a ray hits the glass at an angle, one side of the beam slows down first and "
                           "the beam swings round: that's refraction (Snell's law: n1·sin i = n2·sin r).",
                "try_it": "Choose 'real (Snell)' rays: the light pulses bunch up inside the glass because "
                          "they are slower there.",
            },
            "blur = D * |s - d_i| / d_i": {
                "say": "A screen away from the sharp image gets a blurry patch: the further off, the bigger.",
                "symbols": [["blur", "width of the blur circle on the screen", "cm"],
                            ["D", "how wide the lens is (10 cm here)", "cm"],
                            ["s", "distance from the lens to the screen", "cm"],
                            ["d_i", "where the sharp image would be", "cm"]],
                "explain": "All the light from one point of the candle fills the whole lens, then narrows to a "
                           "point at d_i. A screen in front of or behind that point cuts the cone where it is "
                           "still (or again) wide - a blur circle, by similar triangles D × |s − d_i| / d_i. On "
                           "the screen the light lands on a patch = the candle's image + the blur. A small "
                           "sensor catches only (sensor ÷ patch)² of it - so it needs a sharp AND small image.",
                "try_it": "Set the screen to 74 cm and the candle (2 cm tall) to 26 cm: sharp, but 5.7 cm wide "
                          "- a 1 cm cell gets 3%. Now candle 74 cm, screen 26 cm: sharp and 0.7 cm - it gets it all.",
            },
        },
        "presets": [
            {"title": "Projector", "params": {"d_o": 30.0}},
            {"title": "Magnifying glass", "params": {"d_o": 12.0}},
            {"title": "Camera (far away)", "params": {"d_o": 100.0}},
            {"title": "Same size at 2F", "params": {"d_o": 38.5}},
            {"title": "Glasses for short sight", "params": {"kind": "diverging", "d_o": 40.0}},
            {"title": "Diamond lens", "params": {"material": "diamond", "d_o": 20.0}},
            {"title": "Light gate: focus on a photocell", "params": {"d_o": 74.0, "h_o": 2.0, "screen": 26.0}},
        ],
        "figures": [
            {"title": "A projector: real, upside down, bigger", "params": {}, "view": {"rays": "principal"},
             "at": 1.0, "callouts": [
                 {"x": 95, "y": 196, "text": "The candle, 30 cm from the lens. Drag its flame to move it."},
                 {"x": 415, "y": 196, "text": "A crown-glass lens with focal length f = 19.2 cm."},
                 {"x": 500, "y": 232, "text": "F' - the parallel (yellow) ray always bends through this focal point."},
                 {"x": 712, "y": 262, "text": "All three rays meet at the image's tip: 53.6 cm away, upside down and "
                                              "1.8x bigger."},
                 {"x": 331, "y": 400, "text": "Where a ray passes outside the real glass, the ideal thin lens is "
                                              "drawn as a dashed line."}],
             "caption": "The candle is between F and 2F, so the image forms beyond 2F': upside down and "
                        "1.8x bigger. A projector does exactly this with a bright slide."},
            {"title": "A magnifying glass: a virtual image", "params": {"d_o": 12.0}, "view": {"rays": "principal"},
             "at": 1.0, "callouts": [
                 {"x": 290, "y": 196, "text": "The candle is closer than F (12 cm < 19.2 cm)."},
                 {"x": 150, "y": 138, "text": "The virtual image: upright and 2.66x bigger - but no light really "
                                              "reaches it."},
                 {"x": 250, "y": 155, "text": "Dashed lines: the rays traced backwards. They seem to come from "
                                              "the image."},
                 {"x": 694, "y": 222, "text": "Your eye catches the spreading rays and sees the big candle."},
                 {"x": 355, "y": 312, "text": "d_i is negative (-31.9 cm): the image is on the candle's side."}],
             "caption": "Inside the focal length the rays spread out after the lens. Your eye traces them back "
                        "and sees a bigger, upright candle that isn't really there."},
            {"title": "Real rays bend twice", "params": {}, "view": {"rays": "real"}, "at": 1.0,
             "callouts": [
                 {"x": 332, "y": 176, "text": "Each ray bends twice: entering the glass and leaving it (Snell's law)."},
                 {"x": 185, "y": 198, "text": "Pulses that left the candle together form glowing arcs: wavefronts."},
                 {"x": 300, "y": 282, "text": "Inside the glass the pulses lag behind, because light is slower there "
                                              "(v = c / n). That delay is what bends the light."},
                 {"x": 700, "y": 322, "text": "The rays cross near 51.5 cm, a little before the thin-lens answer "
                                              "(53.6 cm) - and not all at one point."}],
             "caption": "Traced with Snell's law, each ray bends as it enters the glass and again as it "
                        "leaves. The light is slower inside, and the outer rays focus a little closer than "
                        "the inner ones (spherical aberration)."},
        ],
        "real_life": [
            {"icon": "🚪", "title": "Light gates and automatic doors",
             "text": "A light gate shines a beam onto a photocell; anything that breaks the beam - even a "
                     "wooden ball that no electric contact would notice - switches it. A lens focuses the lamp "
                     "onto the small cell so it gets enough light to tell 'beam' from 'no beam'.",
             "formula": "blur = D * |s - d_i| / d_i"},
            {"icon": "👁️", "title": "Your eye",
             "text": "The lens in your eye makes a real, upside-down image on the retina, like a camera. Your "
                     "brain flips it the right way up.",
             "formula": "1/f = 1/d_o + 1/d_i"},
            {"icon": "👓", "title": "Glasses",
             "text": "Short-sighted eyes focus too strongly, so glasses use diverging lenses (negative "
                     "dioptres); long-sighted eyes get converging lenses. Opticians measure lens power in "
                     "dioptres: P = 1/f with f in metres.",
             "formula": "1/f = (n - 1) * (1/R1 - 1/R2)"},
            {"icon": "🔎", "title": "Magnifying glass",
             "text": "Hold a converging lens closer to a bug than its focal length and you see a big upright "
                     "virtual image - the same set-up as the 'magnifying glass' preset.",
             "formula": "m = -d_i / d_o = h_i / h_o"},
            {"icon": "📽️", "title": "Projectors and cameras",
             "text": "A projector puts a small bright slide just outside the focal point to throw a big "
                     "upside-down image on a far screen; a camera does the reverse for distant scenes.",
             "formula": "1/f = 1/d_o + 1/d_i"},
            {"icon": "💧", "title": "A water drop lens",
             "text": "A drop of water on a leaf is a tiny, strongly curved lens (n = 1.33): look through it "
                     "and the leaf's veins appear magnified.",
             "formula": "n = c / v"},
        ],
    },
    # ------------------------------------------------------------------
    "pressure": {
        "big_idea": "Pressure is how hard a force pushes on each square metre. Squeeze a liquid and the "
                    "extra pressure spreads through ALL of it (Pascal's principle). So a small push on a "
                    "small piston becomes a huge push on a big piston - but the big piston moves only a "
                    "tiny distance. You trade distance for force; the work stays the same.",
        "formulas": {
            "P = F / A": {
                "say": "Pressure = force ÷ the area it pushes on.",
                "symbols": [["P", "pressure", "Pa (pascal = N/m²)"],
                            ["F", "force", "N"],
                            ["A", "area (πr² for a round piston)", "m²"]],
                "explain": "The same force on a smaller area makes a bigger pressure - that's why a needle "
                           "goes through skin and snowshoes don't sink. Air around us pushes with about "
                           "101 kPa; your 150 N push on a 3 cm piston makes 212 kPa extra.",
                "try_it": "Make the small piston thinner: the same push makes a much bigger pressure.",
            },
            "F2 = F1 * (A2 / A1)": {
                "say": "The big piston's force = your force × how many times bigger its area is.",
                "symbols": [["F1, F2", "push on the small piston, lift from the big piston", "N"],
                            ["A1, A2", "areas of the small and big pistons", "m²"],
                            ["A2 / A1", "the force multiplier", ""]],
                "explain": "The same pressure acts on every patch of both pistons (look at the equal "
                           "arrows). The big piston has many more patches, so its total force is bigger: a "
                           "diameter 10x bigger means an area - and a force - 100x bigger.",
                "try_it": "Double the big piston's diameter: the lift becomes 4x bigger, not 2x.",
            },
            "d2 = d1 * (A1 / A2)": {
                "say": "The big piston moves only (small area ÷ big area) as far as you push.",
                "symbols": [["d1, d2", "distances moved by the small and big pistons", "m"],
                            ["A1, A2", "piston areas", "m²"]],
                "explain": "A liquid can't be squashed, so the volume you push out of the small cylinder "
                           "(A1·d1) has to fit under the big piston (A2·d2). With a 100x force multiplier "
                           "the big piston moves 100x less: 25 cm of pushing lifts the car 2.5 mm.",
                "try_it": "Zoom in on the big piston to see its tiny movement.",
            },
            "F1 * d1 = F2 * d2": {
                "say": "Work in = work out: force × distance is the same on both sides (minus losses).",
                "symbols": [["F1·d1", "work you do on the small piston", "J"],
                            ["F2·d2", "work done lifting the load", "J"]],
                "explain": "A hydraulic lift multiplies force but never energy. The bars show it: the work "
                           "you put in ends up as height of the load, height of the liquid and a little "
                           "heat from friction - nothing is free.",
                "try_it": "Compare 'Work in' and 'Work on the load' in the readouts.",
            },
        },
        "presets": [
            {"title": "Car lift", "params": {}},
            {"title": "Push too weak", "params": {"force": 80.0}},
            {"title": "Two syringes", "params": {"force": 40.0, "d1": 2.0, "d2": 6.0, "mass": 20.0,
                                                 "stroke": 20.0}},
            {"title": "Heavy van", "params": {"force": 300.0, "d1": 2.0, "d2": 60.0, "mass": 2000.0}},
            {"title": "Almost the same pistons", "params": {"force": 100.0, "d1": 10.0, "d2": 12.0,
                                                            "mass": 10.0}},
            {"title": "A steel ball rides the piston down", "params": {"push": "weight", "force": 5.0, "d1": 2.0,
                                                                       "d2": 3.9, "mass": 1.1, "stroke": 30.0,
                                                                       "fluid": "oil"}},
        ],
        "figures": [
            {"title": "Small push, big lift", "params": {}, "view": {}, "at": 2.6, "callouts": [
                 {"x": 358, "y": 262, "text": "Your push: 150 N on a small piston only 3 cm wide."},
                 {"x": 392, "y": 338, "text": "The gauge: 212 kPa - the same pressure everywhere in the liquid."},
                 {"x": 612, "y": 372, "text": "Equal arrows = equal pressure on every patch. The big piston has 100x "
                                              "the area, so 100x the force."},
                 {"x": 620, "y": 58, "text": "150 N x 100 = 15 000 N - more than the car's 9 810 N weight."},
                 {"x": 292, "y": 410, "text": "Your hand pushed the small piston down 25 cm ..."},
                 {"x": 790, "y": 318, "text": "... but the car rose only 2.5 mm: 100x less distance."}],
             "caption": "150 N becomes 15 000 N - enough to lift a car - because the big piston has 100x the "
                        "area. The price: it only rose 2.5 mm."},
            {"title": "Not enough pressure", "params": {"force": 80.0}, "view": {}, "at": 0.3, "callouts": [
                 {"x": 620, "y": 58, "text": "80 N x 100 = 8 000 N - less than the car's weight (9 810 N)."},
                 {"x": 392, "y": 340, "text": "The gauge shows 139 kPa, the pressure the car's weight makes. Your push "
                                              "only makes 113 kPa."},
                 {"x": 210, "y": 318, "text": "The small piston can't move down, so nothing happens."}],
             "caption": "80 N on the small piston only makes 113 kPa, but holding the car needs 139 kPa. "
                        "Nothing moves."},
            {"title": "Almost equal pistons", "params": {"force": 100.0, "d1": 10.0, "d2": 12.0, "mass": 10.0},
             "view": {}, "at": 1.5, "callouts": [
                 {"x": 620, "y": 58, "text": "The areas are almost equal, so the force is multiplied only 1.44x."},
                 {"x": 766, "y": 302, "text": "The big piston moves almost as far as the small one: 74 mm for "
                                              "107 mm."},
                 {"x": 140, "y": 300, "text": "Work in = work out: 8.1 J either way."}],
             "caption": "With pistons of similar size there is hardly any force multiplying, but the big "
                        "piston moves almost as far as the small one."},
        ],
        "real_life": [
            {"icon": "🚗", "title": "Car jacks and garage lifts",
             "text": "A mechanic pumps a small piston many times to lift a whole car on a big one. Valves stop "
                     "the oil flowing back between strokes.",
             "formula": "F2 = F1 * (A2 / A1)"},
            {"icon": "🛑", "title": "Car brakes",
             "text": "Your foot pushes a small piston in the master cylinder; brake fluid carries the pressure "
                     "to bigger pistons at every wheel that squeeze the brake pads.",
             "formula": "F2 = F1 * (A2 / A1)"},
            {"icon": "🚜", "title": "Diggers and excavators",
             "text": "The arms of a digger are moved by hydraulic cylinders: a pump makes high pressure oil, "
                     "and big pistons turn it into huge forces.",
             "formula": "P = F / A"},
            {"icon": "👠", "title": "Stiletto heels vs elephants",
             "text": "A person on a thin heel (1 cm²) presses on the floor harder than an elephant's foot, "
                     "because the same weight is squeezed onto a tiny area.",
             "formula": "P = F / A"},
            {"icon": "💺", "title": "Barber and dentist chairs",
             "text": "A few presses of a foot pedal lift a person a few centimetres - a small hydraulic "
                     "lift trading many short pushes for one slow rise.",
             "formula": "F1 * d1 = F2 * d2"},
        ],
    },
    # ------------------------------------------------------------------
    "energy": {
        "big_idea": "Energy never disappears - it just changes form. At the top the object has height energy "
                    "(potential); as it drops this turns into motion energy (kinetic), and for a ball some of "
                    "it into spin. Friction quietly turns some into heat. Without friction, the object always "
                    "climbs back to exactly its start height.",
        "formulas": {
            "E = 0.5*m*v^2 + m*g*h": {
                "say": "Total energy = motion energy + height energy.",
                "symbols": [["E", "total mechanical energy", "J (joules)"],
                            ["½·m·v²", "kinetic energy - energy of motion", "J"],
                            ["m·g·h", "potential energy - energy of height", "J"],
                            ["h", "height above the ground", "m"]],
                "explain": "Going down, height energy turns into motion energy; going up, motion turns back "
                           "into height. Without friction the sum never changes, so the object can never "
                           "rise above its start height - watch the dashed line.",
                "try_it": "Watch the energy bar: blue and orange swap, but the bar never gets taller.",
            },
            "v = sqrt(2*g*h / (1 + k))": {
                "say": "Speed after dropping a height h - a bit slower if the object also has to spin.",
                "symbols": [["v", "speed at the bottom", "m/s"],
                            ["g", "gravity", "m/s²"],
                            ["h", "height dropped", "m"],
                            ["k", "share of energy that goes into spinning: box 0, solid ball 2/5, hollow "
                                  "ball 2/3", ""]],
                "explain": "A sliding box turns all its height energy into motion. A rolling ball must also "
                           "spin, so part of the energy goes there and it moves slower. A hollow ball has its "
                           "mass far from the centre, so it spins 'harder' and is slowest. Mass cancels: a "
                           "heavy and a light box reach the same speed.",
                "try_it": "Compare a box and a solid ball: the box wins every race.",
            },
            "N = m*(g*cos(phi) + v^2/r)": {
                "say": "How hard the track pushes = weight part + the extra push needed to curve the path.",
                "symbols": [["N", "normal force: the track's push, straight out of its surface", "N"],
                            ["phi", "slope angle of the track (φ)", "°"],
                            ["r", "radius of the curve (in a dip it curves up, over a hill down)", "m"]],
                "explain": "In a dip the track has to push extra hard to bend the path upwards - you feel "
                           "heavy at the bottom of a roller coaster. Over a hill it pushes less; if you go so "
                           "fast that v²/r would need a negative push, the object leaves the track and flies.",
                "try_it": "Pick 'Drop and hill' and start from 8 m: the object takes off over the hill.",
            },
            "E_heat = mu * N * distance": {
                "say": "Heat from friction = friction coefficient × the track's push × distance travelled.",
                "symbols": [["E_heat", "energy turned into heat", "J"],
                            ["mu", "friction coefficient (μ): 0 = ice, 0.5 = rough", ""],
                            ["N", "normal force", "N"]],
                "explain": "Friction always works against the motion, so every metre travelled turns a bit "
                           "of motion energy into heat. Each swing is lower than the last, until the object "
                           "stops at the bottom. The energy isn't gone - the track and the box got a tiny "
                           "bit warmer.",
                "try_it": "Set friction to 0.1 and watch the grey heat part of the bar grow.",
            },
        },
        "presets": [
            {"title": "No friction", "params": {}},
            {"title": "Box vs ball race", "params": {}, "b": {"object": "solid_ball"}},
            {"title": "Solid vs hollow ball", "params": {"object": "solid_ball"}, "b": {"object": "hollow_ball"}},
            {"title": "With friction", "params": {"friction": 0.1}},
            {"title": "Over the hill", "params": {"track": "hill", "height": 4.0}},
            {"title": "Airborne!", "params": {"track": "hill", "height": 8.0}},
            {"title": "On the Moon", "params": {"g": 1.62}},
            {"title": "Camel hump: stay on the track", "params": {"track": "camel", "object": "solid_ball",
                                                                  "height": 1.5, "hump": 1.0, "mass": 0.5,
                                                                  "friction": 0.01}},
        ],
        "figures": [
            {"title": "Height turns into speed", "params": {}, "view": {"arrows": "forces"}, "at": 0.75,
             "callouts": [
                 {"x": 770, "y": 330, "text": "Energy bar: blue (height) + orange (motion) = 981 J, always the same."},
                 {"x": 335, "y": 246, "text": "The track pushes straight out of its surface: 168 N, less than the "
                                              "weight because it's a slope."},
                 {"x": 252, "y": 340, "text": "The weight, 196 N, always straight down."},
                 {"x": 590, "y": 198, "text": "Nothing can climb above the start height without extra energy."},
                 {"x": 196, "y": 180, "text": "Drag the flag to start higher or lower."}],
             "caption": "Half-way down, the box has swapped most of its height energy for motion energy - "
                        "the total is still 981 J."},
            {"title": "Sliding beats rolling", "params": {"height": 6.0}, "b": {"object": "solid_ball"},
             "view": {"arrows": "off"}, "at": 1.2, "callouts": [
                 {"x": 292, "y": 348, "text": "A, the box: 9.57 m/s - all its motion energy goes into speed."},
                 {"x": 168, "y": 282, "text": "B, the ball: only 7.01 m/s, and falling behind."},
                 {"x": 862, "y": 318, "text": "Purple = spin: the part of the ball's energy that doesn't carry it "
                                              "forward."}],
             "caption": "Same height, same mass, same track: the ball puts 2/7 of its energy into spinning, "
                        "so it is slower than the box."},
            {"title": "Too fast for the hill", "params": {"track": "hill", "height": 8.0},
             "view": {"arrows": "forces"}, "at": 2.8, "callouts": [
                 {"x": 566, "y": 214, "text": "The box left the track on the hill's shoulder and is flying."},
                 {"x": 525, "y": 296, "text": "In the air the only force is its weight - the track isn't pushing."},
                 {"x": 398, "y": 236, "text": "Its path is a curve, like a thrown ball's."},
                 {"x": 770, "y": 300, "text": "When it lands, the speed going INTO the track is lost as heat."}],
             "caption": "Over the crest the track would have to PULL the object down to keep it on the curve. "
                        "It can't, so the object flies - and loses energy when it bumps back down."},
        ],
        "real_life": [
            {"icon": "🎢", "title": "Roller coasters",
             "text": "A coaster is hauled up the first hill once; after that it runs on the stored height "
                     "energy. That's why the first hill is the highest, and why the cars have wheels under "
                     "the rail to stop them flying off the hills.",
             "formula": "E = 0.5*m*v^2 + m*g*h"},
            {"icon": "🛹", "title": "Skateboard half-pipe",
             "text": "A skater swaps height for speed on every pass. Friction steals a little each time, "
                     "so they 'pump' with their legs to add energy and keep going.",
             "formula": "E_heat = mu * N * distance"},
            {"icon": "💧", "title": "Hydroelectric dams",
             "text": "Water held high behind a dam has potential energy m·g·h. Falling through turbines, it "
                     "turns into motion and then electricity.",
             "formula": "E = 0.5*m*v^2 + m*g*h"},
            {"icon": "🚲", "title": "Brakes get hot",
             "text": "Braking turns a bike's or car's motion energy into heat in the brakes. Electric cars "
                     "can instead turn some of it back into stored electricity.",
             "formula": "E_heat = mu * N * distance"},
            {"icon": "🎳", "title": "Racing down a ramp",
             "text": "Race a sliding ice cube and a rolling ball down the same ramp: the ice cube wins, "
                     "because the ball spends part of its energy on spinning.",
             "formula": "v = sqrt(2*g*h / (1 + k))"},
        ],
    },
    # ------------------------------------------------------------------
    "bounce": {
        "big_idea": "A falling ball turns its height energy into speed. When it hits the floor it squashes and "
                    "springs back - but never perfectly: it leaves with only a fraction e of its speed, and the "
                    "rest of the energy becomes heat and sound. Because height goes with speed squared, every "
                    "bounce reaches e² of the height before. And e belongs to the ball AND the floor together.",
        "formulas": {
            "v = sqrt(2*g*h)": {
                "say": "Drop something from a height h and it hits the floor at this speed.",
                "symbols": [["v", "speed when it reaches the floor", "m/s"],
                            ["g", "gravity", "m/s²"],
                            ["h", "height it fell", "m"]],
                "explain": "All the height energy m·g·h turns into motion energy ½·m·v², so v = √(2·g·h). The "
                           "mass cancels out: a steel ball and a rubber ball dropped together land together "
                           "(until air drag matters). Four times the height only doubles the speed.",
                "try_it": "Drop from 1 m and from 4 m and compare 'Speed hitting the floor': 4.4 and 8.8 m/s.",
            },
            "v_after = e * v_before": {
                "say": "A bounce sends the ball back up with only a fraction e of the speed it came down with.",
                "symbols": [["e", "coefficient of restitution: 1 = a perfect bounce, 0 = it just stops", ""],
                            ["v_before", "speed hitting the floor", "m/s"],
                            ["v_after", "speed leaving the floor", "m/s"]],
                "explain": "While it touches the floor the ball squashes like a spring and pushes itself back. "
                           "Some of the energy goes into heat and sound instead (you hear the bounce!). How much "
                           "comes back depends on BOTH the ball and the floor: a rubber ball keeps 85% of its "
                           "speed on a steel plate but only 10% in sand, and a steel ball bounces well on steel "
                           "but poorly on wood, which dents a tiny bit.",
                "try_it": "Keep the rubber ball and change the surface: watch e in the label under the ball.",
            },
            "h1 = e^2 * h0": {
                "say": "Each bounce reaches e² times the height of the one before.",
                "symbols": [["h0", "drop height", "m"],
                            ["h1", "height of the first bounce", "m"],
                            ["e²", "share of the energy the bounce keeps", ""]],
                "explain": "Height goes with speed SQUARED (h = v²/2g). So keeping a fraction e of the speed "
                           "keeps e² of the height: with e = 0.85 that's 0.72 - each bounce is 72% as high as "
                           "the last. After n bounces: h_n = e^(2n) · h0. Air drag takes a few percent more, "
                           "which is why the orange marks sit a little below the faint ticks.",
                "try_it": "Switch 'Air drag' off: the bounces land exactly on the faint e²ⁿ ticks.",
            },
        },
        "presets": [
            {"title": "Rubber on steel", "params": {}},
            {"title": "Steel vs foam", "params": {}, "b": {"surface": "foam_mat"}},
            {"title": "Rubber vs steel ball", "params": {"surface": "hardwood"}, "b": {"ball": "steel"}},
            {"title": "Into the sand", "params": {"surface": "sand"}},
            {"title": "No air", "params": {"air": False}},
            {"title": "On the Moon", "params": {"g": 1.62, "air": False, "height": 4.0}},
        ],
        "figures": [
            {"title": "Every bounce is lower", "params": {}, "view": {"marks": "on"}, "at": 3.15,
             "callouts": [
                 {"x": 395, "y": 92, "text": "Dropped from 2.00 m (the dashed line)."},
                 {"x": 488, "y": 189, "text": "1st bounce: 1.42 m - 71% of the drop height."},
                 {"x": 488, "y": 257, "text": "Each bounce keeps about e² = 0.72 of the one before."},
                 {"x": 296, "y": 206, "text": "Faint ticks: e²ⁿ × h0 without air. The air takes a little more."},
                 {"x": 818, "y": 345, "text": "Grey = energy turned into heat and sound by the bounces."}],
             "caption": "A rubber ball on a steel plate: e = 0.85, so each bounce reaches about 72% of the "
                        "height before."},
            {"title": "The floor matters", "params": {}, "b": {"surface": "foam_mat"}, "view": {"marks": "on"},
             "at": 1.6, "callouts": [
                 {"x": 420, "y": 205, "text": "A on the steel plate: back up to 1.42 m."},
                 {"x": 600, "y": 380, "text": "B on the foam mat: only 0.40 m - the mat soaks up the energy."},
                 {"x": 818, "y": 345, "text": "Same ball, same drop: e belongs to the ball AND the surface."}],
             "caption": "The same rubber ball keeps 85% of its speed on steel but only 45% on a foam mat, so it "
                        "bounces to 72% or 20% of the drop height."},
            {"title": "Heavy isn't bouncy", "params": {"surface": "hardwood"}, "b": {"ball": "steel"},
             "view": {"marks": "on"}, "at": 1.4, "callouts": [
                 {"x": 420, "y": 250, "text": "A, rubber on wood: 1.10 m."},
                 {"x": 600, "y": 330, "text": "B, steel on wood: 0.50 m - the wood dents and takes the energy."},
                 {"x": 818, "y": 372, "text": "The steel ball had 4x the energy (10 J), but kept only a quarter of it."}],
             "caption": "Dropped together, they land together (the mass cancels out) - but what comes back "
                        "depends on how springy the ball-and-floor pair is, not on the mass."},
        ],
        "real_life": [
            {"icon": "🎾", "title": "Tennis-ball test",
             "text": "Official tennis balls are tested by dropping them from 254 cm onto concrete: they must "
                     "bounce back 135-147 cm. That's e between about 0.73 and 0.76.",
             "formula": "h1 = e^2 * h0"},
            {"icon": "🏀", "title": "Pumping a basketball",
             "text": "A flat basketball barely bounces; pumped up, its e rises to about 0.8. Rules say it must "
                     "bounce to roughly half to two-thirds of its drop height on a wooden court.",
             "formula": "v_after = e * v_before"},
            {"icon": "🥚", "title": "Crash mats and egg drops",
             "text": "Foam mats, airbags and sand pits are LOW-e surfaces on purpose: they take the energy "
                     "away slowly instead of sending it back, so whatever lands on them stops gently.",
             "formula": "v_after = e * v_before"},
            {"icon": "🪂", "title": "How fast things land",
             "text": "Something falling 5 m hits the ground at about 10 m/s (36 km/h) - that's why a fall from "
                     "a first-floor window is dangerous, even though 5 m doesn't sound high.",
             "formula": "v = sqrt(2*g*h)"},
            {"icon": "⚙️", "title": "Ball bearings and anvils",
             "text": "A hardened steel ball on a steel anvil is one of the bounciest pairs there is (e ≈ 0.9). "
                     "Testers drop steel balls on metal to check how hard it is (the 'rebound hardness' test).",
             "formula": "h1 = e^2 * h0"},
        ],
    },
    # ------------------------------------------------------------------
    "levers": {
        "big_idea": "A weight on a beam doesn't just pull down - it TURNS the beam about the pivot, and the "
                    "further out it hangs, the harder it turns it. That turning effect (the moment) is weight × "
                    "distance. The beam balances when the turning effects on both sides are equal, so a small "
                    "weight far out can hold up a big one close in. Tip the balance and the beam turns - the "
                    "bigger the leftover turning effect, the faster.",
        "formulas": {
            "m1 * d1 = m2 * d2": {
                "say": "It balances when mass × distance is the same on both sides (the principle of moments).",
                "symbols": [["m1, m2", "the loads on the left and on the right", "kg"],
                            ["d1, d2", "how far each hangs from the pivot", "m"]],
                "explain": "Each side's turning effect is m·g·d, and g is the same on both sides, so it cancels: "
                           "only mass × distance counts. 2 kg at 0.5 m balances 1 kg at 1.0 m - half the weight "
                           "at twice the distance. That's why a child far out on a seesaw can hold up an adult "
                           "sitting close to the middle. Where the beam's own weight sits in the middle, it "
                           "turns neither way.",
                "try_it": "Put 2 kg at 0.5 m on the left and 1 kg on the right, then drag the right hook until "
                          "the HUD says 'balanced': 1.00 m.",
            },
            "tau = m * g * d": {
                "say": "Turning effect (moment) = the load's weight × its distance from the pivot.",
                "symbols": [["tau", "turning effect, moment or torque", "N m (newton metres)"],
                            ["m * g", "the load's weight", "N"],
                            ["d", "distance from the pivot (when the beam is level)", "m"]],
                "explain": "Pushing a door near its hinges is hard; pushing at the handle is easy - the same "
                           "force turns it more when it acts further from the pivot. As the beam tilts, the "
                           "load's sideways distance from the pivot shrinks (d·cos of the tilt), so its "
                           "turning effect shrinks a little too.",
                "try_it": "Move the left hook out from 0.5 m to 1.0 m: its turning-effect arrow doubles, "
                          "9.8 → 19.6 N·m.",
            },
            "alpha = tau_net / I": {
                "say": "Out of balance, the beam speeds up its turning: leftover turning effect ÷ moment of inertia.",
                "symbols": [["alpha", "angular acceleration: how fast the turning speeds up", "rad/s²"],
                            ["tau_net", "the leftover turning effect (minus the pivot's friction)", "N m"],
                            ["I", "moment of inertia: Σ m·r² - mass far from the pivot is harder to turn", "kg m²"]],
                "explain": "This is Newton's F = m·a for turning. A big leftover turning effect swings the beam "
                           "fast; mass far from the pivot (a heavy beam, loads far out) makes it sluggish. "
                           "Just past balance the beam only creeps at first, then speeds up all the way to the "
                           "stop - and the far end arrives fastest, because it travels furthest.",
                "try_it": "Make the beam 5 kg instead of 1 kg: the balance doesn't change, but the beam turns "
                          "much more slowly.",
            },
        },
        "presets": [
            {"title": "Out of balance", "params": {}},
            {"title": "Balanced: half the mass, twice as far", "params": {"d2": 1.0}},
            {"title": "A small weight lifts a big one", "params": {"m1": 4.0, "d1": 0.2, "m2": 1.0, "d2": 1.0}},
            {"title": "Heavy beam: slow", "params": {"beam": 5.0}},
            {"title": "Sticky pivot", "params": {"m2": 1.2, "d2": 0.85, "friction": 0.5}},
            {"title": "The mill hoist (just past balance)", "params": {"m1": 0.25, "d1": 1.0, "m2": 0.55, "d2": 0.5,
                                                                       "start": -25.0}},
        ],
        "figures": [
            {"title": "Balanced: mass × distance", "params": {"d2": 1.0}, "view": {"arrows": "on"}, "at": 0.3,
             "callouts": [
                 {"x": 240, "y": 272, "text": "2 kg, 0.5 m from the pivot: 2 × 9.81 × 0.5 = 9.81 N·m."},
                 {"x": 760, "y": 262, "text": "1 kg, but twice as far out: 1 × 9.81 × 1.0 = 9.81 N·m."},
                 {"x": 440, "y": 300, "text": "Equal turning effects: the beam stays level."}],
             "caption": "Half the weight at twice the distance gives the same turning effect, so the beam "
                        "balances: 2 kg × 0.5 m = 1 kg × 1.0 m."},
            {"title": "Out of balance: it turns", "params": {}, "view": {"arrows": "on"}, "at": 0.6,
             "callouts": [
                 {"x": 245, "y": 305, "text": "Left: 2 kg × 0.5 m = 1.00 kg·m."},
                 {"x": 700, "y": 228, "text": "Right: 1 kg × 0.8 m = 0.80 kg·m - less."},
                 {"x": 440, "y": 300, "text": "The left side wins and the beam turns that way, faster and faster."}],
             "caption": "Moving the right load in to 0.8 m shrinks its turning effect: the left side wins and "
                        "the beam turns until it hits the stop."},
            {"title": "Just past balance", "params": {"m1": 0.25, "d1": 1.0, "m2": 0.55, "d2": 0.5, "start": -25.0},
             "view": {"arrows": "on"}, "at": 2.0, "callouts": [
                 {"x": 118, "y": 250, "text": "0.25 kg far out at 1.0 m: 0.25 kg·m."},
                 {"x": 620, "y": 280, "text": "0.55 kg at 0.5 m: 0.275 kg·m - only a little more."},
                 {"x": 440, "y": 300, "text": "A small leftover turning effect: it starts slowly and reaches "
                                             "the stop gently."}],
             "caption": "Just past balance the beam turns slowly and arrives gently - the trick behind the Mill "
                        "Hoist in the Machine Works."},
        ],
        "real_life": [
            {"icon": "🛝", "title": "Seesaws",
             "text": "A heavy parent and a light child can balance on a seesaw: the child just sits further from "
                     "the middle. Mass × distance has to match, not the masses.",
             "formula": "m1 * d1 = m2 * d2"},
            {"icon": "🚪", "title": "Door handles",
             "text": "Handles sit far from the hinges on purpose. Push a door right next to its hinge and you "
                     "need many times the force for the same turning effect.",
             "formula": "tau = m * g * d"},
            {"icon": "🏗️", "title": "Tower cranes",
             "text": "A crane's short back arm carries a huge concrete counterweight; the long front arm carries "
                     "the load. The operator may only lift heavy loads close in - the load's moment must never "
                     "beat the counterweight's.",
             "formula": "m1 * d1 = m2 * d2"},
            {"icon": "🧰", "title": "Crowbars and bottle openers",
             "text": "Push the long end of a crowbar and the short end pushes many times harder on the nail - "
                     "the same turning effect, over a much shorter distance.",
             "formula": "tau = m * g * d"},
            {"icon": "⛲", "title": "Counterweight water lifts",
             "text": "Old mills and well sweeps (shadoofs) lift with a bucket and a counterweight on a beam. "
                     "Just a little extra weight makes it rise gently; too much and it slams into its stop.",
             "formula": "alpha = tau_net / I"},
        ],
    },
}


def _fmt(v):
    if isinstance(v, bool):
        return "1" if v else "0"
    return str(v)


def figure_route(topic_id, fig):
    """Deep link for a figure: #/<topic>?p=v&b.p=v&view.o=v&at=s"""
    parts = ["%s=%s" % (k, _fmt(v)) for k, v in sorted(fig.get("params", {}).items())]
    if "b" in fig:
        parts.append("cmp=1")
        parts += ["b.%s=%s" % (k, _fmt(v)) for k, v in sorted(fig["b"].items())]
    parts += ["view.%s=%s" % (k, v) for k, v in sorted(fig.get("view", {}).items())]
    if fig.get("at") is not None:
        parts.append("at=%s" % _fmt(fig["at"]))
    return "#/" + topic_id + ("?" + "&".join(parts) if parts else "")


def attach(topics):
    """Put each topic's learning content (plus image paths and deep links)
    into its registry entry."""
    for t in topics:
        content = LEARN.get(t["id"])
        if not content:
            continue
        figs = []
        for i, fig in enumerate(content["figures"]):
            f = dict(fig)
            f["img"] = "learn/%s_%d.png" % (t["id"], i + 1)
            f["route"] = figure_route(t["id"], fig)
            figs.append(f)
        presets = content.get("presets")
        if presets is None:                        # default: the figures' set-ups, from the start
            presets = [{"title": fg["title"], "params": fg.get("params", {}),
                        **({"b": fg["b"]} if "b" in fg else {}), "view": fg.get("view", {})}
                       for fg in content["figures"]]
        pres = []
        for pr in presets:
            q = dict(pr)
            q["route"] = figure_route(t["id"], dict(pr, at=None))
            pres.append(q)
        t["learn"] = dict(content, figures=figs, presets=pres)
