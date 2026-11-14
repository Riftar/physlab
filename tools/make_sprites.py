"""Generate the procedural simulation sprites (pendulum bob, clamp, wave
shaker, hand, candle, eye, car, crate; and for the Machine Works game's
Bounce Factory: toy hopper, salt bag, spring cannon, toy box, Gizmo the
robot; for the Foundry: ore cart, kettle, latch coil, crane magnet, ladle;
for the Mill: grain sack, hay cart, bucket, millstone hopper) in the same flat, dark-outlined 128 px style as the original set,
plus the topic icons for Bounces and Levers & Moments (icons/icon_bounce.png,
icons/icon_levers.png, in the icon set's navy-outline style).

    python3 tools/make_sprites.py          # writes www/sprites/item_*.png + www/icons/icon_bounce.png

Drawn at 4x and downsampled for clean anti-aliasing; white background,
which the client keys out at load. Needs Pillow (a dev-time tool only -
the app itself stays stdlib + vanilla JS).
"""

import math
import os
from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "www", "sprites")
OUT_ICONS = os.path.join(os.path.dirname(OUT), "icons")
SS = 4                      # supersampling factor
SIZE = 128
INK = (34, 34, 40)
LW = 2.2                    # outline width in final pixels


def canvas():
    im = Image.new("RGB", (SIZE * SS, SIZE * SS), "white")
    return im, ImageDraw.Draw(im)


def S(*v):
    return [x * SS for x in v]


def save(im, name):
    im.resize((SIZE, SIZE), Image.LANCZOS).save(os.path.join(OUT, "item_%s.png" % name))


def bob():
    """Brass pendulum bob with a hook eye on top (pivot string ties here)."""
    im, d = canvas()
    lw = int(LW * SS)
    d.ellipse(S(56, 6, 72, 22), outline=INK, width=lw)                     # hook eye
    d.rectangle(S(60, 19, 68, 30), fill=(196, 150, 58), outline=INK, width=lw)
    d.ellipse(S(22, 26, 106, 110), fill=(214, 165, 62), outline=INK, width=lw)   # brass sphere
    d.ellipse(S(30, 36, 96, 100), fill=(232, 186, 82))
    d.chord(S(22, 26, 106, 110), 20, 160, fill=(182, 132, 44))                   # shaded lower half
    d.ellipse(S(22, 26, 106, 110), outline=INK, width=lw)
    d.arc(S(36, 38, 80, 82), 200, 260, fill=(255, 240, 190), width=int(5 * SS))  # highlight
    save(im, "bob")


def clamp():
    """Pivot clamp: a bar clamp with a steel pin the string hangs from."""
    im, d = canvas()
    lw = int(LW * SS)
    d.rectangle(S(8, 30, 120, 50), fill=(112, 120, 138), outline=INK, width=lw)        # rod
    d.line(S(12, 35, 116, 35), fill=(170, 178, 196), width=int(3 * SS))
    d.rounded_rectangle(S(40, 20, 88, 78), radius=8 * SS, fill=(230, 86, 70), outline=INK, width=lw)
    d.line(S(46, 28, 82, 28), fill=(255, 150, 130), width=int(3 * SS))
    d.rectangle(S(58, 76, 70, 96), fill=(150, 156, 168), outline=INK, width=lw)        # stem
    d.ellipse(S(54, 90, 74, 110), fill=(200, 206, 216), outline=INK, width=lw)         # pivot pin
    d.ellipse(S(60, 96, 68, 104), fill=INK)
    save(im, "clamp")


def oscillator():
    """Wave driver: a box with a dial and a vertical push rod on the right."""
    im, d = canvas()
    lw = int(LW * SS)
    d.rounded_rectangle(S(10, 40, 92, 116), radius=8 * SS, fill=(61, 132, 220), outline=INK, width=lw)
    d.line(S(18, 48, 84, 48), fill=(140, 190, 255), width=int(3 * SS))
    d.ellipse(S(26, 60, 62, 96), fill=(235, 240, 250), outline=INK, width=lw)        # dial
    d.line(S(44, 78, 55, 66), fill=INK, width=int(3 * SS))
    d.ellipse(S(41, 75, 47, 81), fill=INK)
    d.rectangle(S(70, 64, 84, 72), fill=(255, 209, 102), outline=INK, width=int(1.5 * SS))  # led
    d.rectangle(S(96, 14, 108, 100), fill=(190, 196, 208), outline=INK, width=lw)     # rod guide
    d.rectangle(S(92, 8, 112, 20), fill=(255, 209, 102), outline=INK, width=lw)       # rope clip
    d.rectangle(S(86, 84, 100, 96), fill=(120, 126, 140), outline=INK, width=lw)      # coupler
    save(im, "oscillator")


def hand():
    """A simple mitten hand that holds an object before release."""
    im, d = canvas()
    lw = int(LW * SS)
    d.rounded_rectangle(S(30, 20, 98, 96), radius=26 * SS, fill=(255, 204, 160), outline=INK, width=lw)
    d.rounded_rectangle(S(12, 52, 44, 76), radius=12 * SS, fill=(255, 204, 160), outline=INK, width=lw)
    d.rounded_rectangle(S(40, 92, 88, 120), radius=6 * SS, fill=(90, 120, 200), outline=INK, width=lw)
    for x in (52, 66, 80):
        d.line(S(x, 24, x, 46), fill=(214, 150, 110), width=int(2.5 * SS))
    save(im, "hand")


def candle():
    """Candle whose flame tip touches the top and base the bottom, so the
    sprite's height IS the object's height in the lens experiment."""
    im, d = canvas()
    lw = int(LW * SS)
    d.ellipse(S(52, 2, 76, 40), fill=(255, 170, 40), outline=INK, width=lw)        # flame
    d.ellipse(S(57, 14, 71, 38), fill=(255, 236, 120))
    d.polygon(S(64, 2, 55, 24, 73, 24), fill=(255, 170, 40))
    d.line(S(64, 36, 64, 44), fill=INK, width=int(2 * SS))                          # wick
    d.rounded_rectangle(S(48, 42, 80, 126), radius=4 * SS, fill=(250, 244, 228), outline=INK, width=lw)
    d.line(S(54, 50, 54, 118), fill=(236, 228, 206), width=int(3 * SS))
    d.polygon(S(48, 50, 56, 50, 56, 66, 52, 70, 48, 64), fill=(236, 226, 204))      # wax drip
    save(im, "candle")


def eye():
    """An almond-shaped eye looking LEFT (towards the lens). Off-white,
    because pure white is keyed out as background by the client."""
    im, d = canvas()
    lw = int(LW * SS)
    pts = []                                                                                 # almond outline
    for i in range(41):
        t = math.pi * i / 40
        pts.append((64 - 54 * math.cos(t), 61 - 26 * math.sin(t) ** 1.3))
    for i in range(41):
        t = math.pi * i / 40
        pts.append((64 + 54 * math.cos(t), 61 + 26 * math.sin(t) ** 1.3))
    d.polygon([(x * SS, y * SS) for x, y in pts], fill=(232, 238, 248), outline=INK, width=lw)
    d.ellipse(S(24, 42, 62, 80), fill=(70, 140, 220), outline=INK, width=lw)              # iris (left)
    d.ellipse(S(33, 51, 53, 71), fill=INK)
    d.ellipse(S(36, 53, 43, 60), fill=(236, 240, 248))
    for x0, x1 in ((34, 28), (56, 54), (78, 80), (98, 104)):                                  # lashes
        d.line(S(x0, 36 if x0 < 90 else 40, x1, 24 if x0 < 90 else 30), fill=INK, width=int(2.5 * SS))
    save(im, "eye")


def car():
    """A side-view car for the hydraulic lift."""
    im, d = canvas()
    lw = int(LW * SS)
    d.rounded_rectangle(S(6, 58, 122, 94), radius=10 * SS, fill=(226, 69, 90), outline=INK, width=lw)
    d.polygon(S(30, 60, 44, 34, 88, 34, 104, 60), fill=(226, 69, 90), outline=INK)
    d.polygon(S(38, 58, 48, 40, 64, 40, 64, 58), fill=(190, 226, 255), outline=INK)
    d.polygon(S(70, 58, 70, 40, 84, 40, 96, 58), fill=(190, 226, 255), outline=INK)
    d.line(S(12, 68, 116, 68), fill=(255, 150, 160), width=int(3 * SS))
    for cx in (32, 96):
        d.ellipse(S(cx - 15, 80, cx + 15, 110), fill=(40, 40, 48), outline=INK, width=lw)
        d.ellipse(S(cx - 6, 89, cx + 6, 101), fill=(190, 196, 208))
    d.rectangle(S(112, 70, 120, 78), fill=(255, 209, 102), outline=INK)
    save(im, "car")


def crate():
    """A wooden crate (loads lighter than a car)."""
    im, d = canvas()
    lw = int(LW * SS)
    d.rectangle(S(14, 14, 114, 114), fill=(214, 158, 86), outline=INK, width=lw)
    for y in (40, 64, 88):
        d.line(S(14, y, 114, y), fill=(160, 108, 48), width=int(2 * SS))
    d.line(S(18, 18, 110, 110), fill=(176, 120, 56), width=int(6 * SS))
    d.rectangle(S(14, 14, 114, 114), outline=INK, width=lw)
    d.rectangle(S(22, 22, 106, 106), outline=(120, 78, 30), width=int(2 * SS))
    save(im, "crate")


# ---------------------------------------------------------------- game: Bounce Factory

def hopper():
    """Toy hopper (point A of the Bounce Factory): a striped funnel bin full of
    toy balls, with a sliding hatch at the bottom."""
    im, d = canvas()
    lw = int(LW * SS)
    d.polygon(S(10, 22, 118, 22, 80, 86, 48, 86), fill=(74, 196, 190), outline=INK)        # funnel body
    for x0 in (24, 52, 80):                                                                   # stripes
        d.polygon(S(x0, 22, x0 + 14, 22, 64 + (x0 + 14 - 64) * 0.35, 86, 64 + (x0 - 64) * 0.35, 86),
                  fill=(255, 122, 110))
    d.polygon(S(10, 22, 118, 22, 80, 86, 48, 86), outline=INK, width=lw)
    d.rounded_rectangle(S(6, 14, 122, 26), radius=4 * SS, fill=(255, 209, 102), outline=INK, width=lw)  # rim
    for cx, cy, col in ((34, 12, (224, 69, 90)), (58, 8, (92, 200, 255)), (84, 11, (255, 209, 102)),
                        (104, 14, (125, 230, 140))):                                            # toys peeking out
        d.ellipse(S(cx - 9, cy - 9, cx + 9, cy + 9), fill=col, outline=INK, width=int(1.8 * SS))
    d.rectangle(S(46, 86, 82, 100), fill=(120, 128, 146), outline=INK, width=lw)                 # throat
    d.rectangle(S(40, 100, 96, 108), fill=(255, 209, 102), outline=INK, width=lw)                # the hatch
    d.ellipse(S(90, 98, 102, 110), fill=(226, 69, 90), outline=INK, width=int(1.8 * SS))         # hatch knob
    d.line(S(34, 86, 24, 124), fill=INK, width=lw)                                               # legs
    d.line(S(94, 86, 104, 124), fill=INK, width=lw)
    save(im, "hopper")


def saltbag():
    """A 1 kg bag of salt: paper sack, tied top, blue label with crystals."""
    im, d = canvas()
    lw = int(LW * SS)
    d.polygon(S(28, 34, 100, 34, 110, 118, 18, 118), fill=(240, 232, 214), outline=INK)          # sack
    d.polygon(S(28, 34, 100, 34, 110, 118, 18, 118), outline=INK, width=lw)
    d.polygon(S(40, 10, 88, 10, 100, 34, 28, 34), fill=(226, 214, 188), outline=INK, width=lw)   # gathered top
    for x in (48, 58, 70, 80):
        d.line(S(x, 12, x - 2 if x < 64 else x + 2, 32), fill=(196, 182, 150), width=int(2 * SS))
    d.rounded_rectangle(S(34, 28, 94, 40), radius=4 * SS, fill=(224, 69, 90), outline=INK, width=lw)  # tie
    d.rounded_rectangle(S(30, 58, 98, 104), radius=8 * SS, fill=(61, 132, 220), outline=INK, width=lw)  # label
    for cx, cy, r in ((48, 72, 7), (66, 68, 9), (84, 76, 6), (56, 88, 6), (76, 90, 8)):         # salt crystals
        d.rectangle(S(cx - r, cy - r, cx + r, cy + r), fill=(250, 252, 255), outline=INK, width=int(1.5 * SS))
    save(im, "saltbag")


def cannon():
    """Spring cannon BARREL, pointing right, its pivot in the middle of the
    sprite (the scene rotates it to the launch angle): a teal tube, the coil
    spring and plunger knob at the back, a brass muzzle ring."""
    im, d = canvas()
    lw = int(LW * SS)
    d.rounded_rectangle(S(30, 46, 118, 82), radius=6 * SS, fill=(74, 196, 190), outline=INK, width=lw)   # tube
    d.line(S(36, 54, 110, 54), fill=(160, 236, 230), width=int(4 * SS))                                 # shine
    d.rectangle(S(108, 42, 122, 86), fill=(255, 209, 102), outline=INK, width=lw)                      # muzzle ring
    pts = []
    for i in range(13):                                                                                # the spring
        pts += [(8 + i * 2.0 + (i % 2) * 0.0) * SS, (48 if i % 2 else 80) * SS]
    d.line(pts, fill=(150, 156, 168), width=int(4 * SS), joint="curve")
    d.line(pts, fill=INK, width=int(1.2 * SS))
    d.rectangle(S(2, 58, 10, 70), fill=(226, 69, 90), outline=INK, width=lw)                          # plunger knob
    d.line(S(10, 64, 32, 64), fill=INK, width=int(3 * SS))
    d.ellipse(S(56, 56, 72, 72), fill=(120, 128, 146), outline=INK, width=lw)                           # pivot pin
    d.ellipse(S(61, 61, 67, 67), fill=INK)
    save(im, "cannon")


def toybox():
    """Toy box (point B): an open chest with coral and teal planks and a star."""
    im, d = canvas()
    lw = int(LW * SS)
    d.polygon(S(8, 40, 120, 40, 110, 120, 18, 120), fill=(255, 122, 110), outline=INK)
    for y, col in ((62, (74, 196, 190)), (84, (255, 209, 102)), (104, (74, 196, 190))):
        d.polygon(S(8 + (y - 40) * 0.125, y - 6, 120 - (y - 40) * 0.125, y - 6,
                    120 - (y - 34) * 0.125, y + 6, 8 + (y - 34) * 0.125, y + 6), fill=col)
    d.polygon(S(8, 40, 120, 40, 110, 120, 18, 120), outline=INK, width=lw)
    d.rounded_rectangle(S(4, 32, 124, 44), radius=4 * SS, fill=(226, 69, 90), outline=INK, width=lw)   # rim
    star = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        r = 16 if i % 2 == 0 else 7
        star.append(((64 + r * math.cos(a)) * SS, (82 + r * math.sin(a)) * SS))
    d.polygon(star, fill=(255, 236, 120), outline=INK)
    d.line(star + star[:1], fill=INK, width=int(1.8 * SS))
    for cx, cy, col in ((34, 28, (92, 200, 255)), (92, 26, (125, 230, 140))):                          # toys on top
        d.ellipse(S(cx - 10, cy - 10, cx + 10, cy + 10), fill=col, outline=INK, width=int(1.8 * SS))
    save(im, "toybox")


def gizmo():
    """Gizmo, the Machine Works' robot foreman: round head, big eyes,
    antenna bulb, a bolt on the chest."""
    im, d = canvas()
    lw = int(LW * SS)
    d.line(S(64, 6, 64, 22), fill=INK, width=lw)                                                        # antenna
    d.ellipse(S(56, 0, 72, 14), fill=(255, 209, 102), outline=INK, width=lw)
    d.rounded_rectangle(S(22, 20, 106, 70), radius=18 * SS, fill=(190, 226, 255), outline=INK, width=lw)  # head
    d.rectangle(S(12, 36, 22, 54), fill=(150, 156, 168), outline=INK, width=lw)                        # ears
    d.rectangle(S(106, 36, 116, 54), fill=(150, 156, 168), outline=INK, width=lw)
    for cx in (46, 82):                                                                                 # eyes
        d.ellipse(S(cx - 12, 32, cx + 12, 56), fill=(255, 255, 250), outline=INK, width=lw)
        d.ellipse(S(cx - 5, 38, cx + 5, 50), fill=INK)
        d.ellipse(S(cx - 3, 39, cx, 43), fill=(250, 250, 255))
    d.arc(S(50, 50, 78, 66), 20, 160, fill=INK, width=int(2.5 * SS))                                   # smile
    d.rounded_rectangle(S(32, 72, 96, 120), radius=10 * SS, fill=(255, 154, 92), outline=INK, width=lw)  # body
    d.polygon(S(68, 78, 54, 98, 64, 98, 58, 114, 76, 92, 66, 92, 72, 78), fill=(255, 236, 120), outline=INK)  # bolt
    d.rounded_rectangle(S(14, 78, 30, 108), radius=6 * SS, fill=(150, 156, 168), outline=INK, width=lw)  # arms
    d.rounded_rectangle(S(98, 78, 114, 108), radius=6 * SS, fill=(150, 156, 168), outline=INK, width=lw)
    save(im, "gizmo")


# ---------------------------------------------------------------- game: The Foundry

def minecart():
    """Ore cart (point A of the Foundry): a rusty-red tipper cart on two
    wheels, heaped with grey ore and the steel ball on top."""
    im, d = canvas()
    lw = int(LW * SS)
    for cx, cy, col in ((34, 40, (122, 128, 146)), (58, 34, (150, 156, 168)), (88, 40, (112, 120, 138)),
                        (72, 44, (136, 142, 158))):                                       # the ore heap
        d.ellipse(S(cx - 16, cy - 12, cx + 16, cy + 12), fill=col, outline=INK, width=int(1.8 * SS))
    d.ellipse(S(50, 14, 74, 38), fill=(190, 198, 214), outline=INK, width=lw)              # the steel ball
    d.arc(S(55, 18, 69, 32), 200, 260, fill=(240, 244, 250), width=int(3 * SS))
    d.polygon(S(8, 46, 120, 46, 106, 98, 22, 98), fill=(196, 84, 62), outline=INK)        # the tub
    d.polygon(S(8, 46, 120, 46, 106, 98, 22, 98), outline=INK, width=lw)
    d.rounded_rectangle(S(4, 40, 124, 52), radius=3 * SS, fill=(150, 156, 168), outline=INK, width=lw)  # rim
    for x in (40, 64, 88):                                                                 # rivets + ribs
        d.line(S(x, 56, x - (x - 64) * 0.15, 94), fill=(150, 60, 44), width=int(3 * SS))
    for x, y in ((18, 60), (110, 60), (26, 88), (102, 88)):
        d.ellipse(S(x - 3, y - 3, x + 3, y + 3), fill=(255, 209, 102), outline=INK, width=int(1.2 * SS))
    d.rectangle(S(14, 98, 114, 106), fill=(90, 96, 114), outline=INK, width=lw)            # chassis
    for cx in (36, 92):                                                                    # wheels
        d.ellipse(S(cx - 14, 96, cx + 14, 124), fill=(70, 76, 92), outline=INK, width=lw)
        d.ellipse(S(cx - 5, 105, cx + 5, 115), fill=(255, 209, 102), outline=INK, width=int(1.5 * SS))
    save(im, "minecart")


def kettle():
    """Kettle of 95 degC water: a copper kettle, spout to the LEFT (the scene
    tilts it to pour), black handle, steam curls. (Drawn spout-right, then
    mirrored.)"""
    im, d = canvas()
    lw = int(LW * SS)
    d.polygon(S(88, 70, 122, 44, 126, 50, 96, 84), fill=(214, 124, 70), outline=INK)       # spout
    d.polygon(S(88, 70, 122, 44, 126, 50, 96, 84), outline=INK, width=lw)
    d.arc(S(26, 14, 94, 72), 180, 360, fill=INK, width=int(7 * SS))                        # handle
    d.arc(S(26, 14, 94, 72), 180, 360, fill=(60, 62, 74), width=int(4 * SS))
    d.chord(S(14, 40, 106, 126), 180, 360, fill=(226, 136, 78), outline=INK, width=lw)     # body
    d.rectangle(S(14, 82, 106, 116), fill=(226, 136, 78))
    d.rounded_rectangle(S(10, 108, 110, 122), radius=5 * SS, fill=(150, 80, 46), outline=INK, width=lw)  # base
    d.line(S(14, 82, 14, 110), fill=INK, width=lw)
    d.line(S(106, 82, 106, 110), fill=INK, width=lw)
    d.arc(S(24, 50, 70, 96), 190, 250, fill=(255, 196, 150), width=int(5 * SS))            # shine
    d.ellipse(S(52, 34, 68, 46), fill=(60, 62, 74), outline=INK, width=lw)                 # lid knob
    d.rounded_rectangle(S(36, 68, 84, 92), radius=5 * SS, fill=(255, 236, 200), outline=INK, width=int(1.6 * SS))
    d.line(S(42, 80, 78, 80), fill=(224, 69, 90), width=int(3.5 * SS))                     # 95 degC label stripe
    for x0 in (104, 116):                                                                  # steam
        d.arc(S(x0 - 6, 14, x0 + 6, 28), 90, 270, fill=(160, 170, 190), width=int(2.5 * SS))
        d.arc(S(x0 - 6, 2, x0 + 6, 16), 270, 90, fill=(160, 170, 190), width=int(2.5 * SS))
    save(im.transpose(Image.FLIP_LEFT_RIGHT), "kettle")


def coil():
    """The trapdoor's latch coil (a solenoid): copper windings on a grey
    bobbin, the steel latch bolt sticking out to the right, two wire tabs."""
    im, d = canvas()
    lw = int(LW * SS)
    d.rectangle(S(84, 54, 124, 74), fill=(170, 178, 196), outline=INK, width=lw)          # the latch bolt
    d.line(S(88, 58, 120, 58), fill=(230, 236, 246), width=int(3 * SS))
    d.rectangle(S(12, 26, 24, 102), fill=(120, 128, 146), outline=INK, width=lw)          # bobbin cheeks
    d.rectangle(S(80, 26, 92, 102), fill=(120, 128, 146), outline=INK, width=lw)
    d.rectangle(S(24, 34, 80, 94), fill=(208, 122, 58), outline=INK, width=lw)            # windings
    for x in range(27, 80, 5):
        d.line(S(x, 35, x + 2, 93), fill=(150, 80, 34), width=int(1.6 * SS))
    d.line(S(26, 42, 78, 42), fill=(250, 180, 120), width=int(3 * SS))                     # shine
    for x in (30, 70):                                                                     # wire tabs
        d.line(S(x, 94, x, 118), fill=INK, width=int(3 * SS))
        d.ellipse(S(x - 5, 114, x + 5, 124), fill=(255, 209, 102), outline=INK, width=int(1.5 * SS))
    save(im, "coil")


def magnet():
    """The crane's electromagnet: a round steel pot magnet seen from the
    side, red band, a lifting eye on top (the cable ties here), cable
    gland and a warning bolt sign."""
    im, d = canvas()
    lw = int(LW * SS)
    d.ellipse(S(52, 2, 76, 26), outline=INK, width=int(4 * SS))                            # lifting eye
    d.rectangle(S(58, 22, 70, 36), fill=(150, 156, 168), outline=INK, width=lw)
    d.polygon(S(22, 36, 106, 36, 120, 62, 8, 62), fill=(112, 120, 138), outline=INK)       # housing top
    d.polygon(S(22, 36, 106, 36, 120, 62, 8, 62), outline=INK, width=lw)
    d.rectangle(S(8, 62, 120, 84), fill=(224, 69, 90), outline=INK, width=lw)              # red band
    d.line(S(12, 68, 116, 68), fill=(255, 130, 140), width=int(3 * SS))
    d.polygon(S(66, 64, 56, 76, 63, 76, 58, 84, 72, 70, 65, 70, 70, 64), fill=(255, 236, 120))  # bolt
    d.rectangle(S(8, 84, 120, 100), fill=(150, 156, 168), outline=INK, width=lw)           # pole face
    for x in (24, 48, 80, 104):
        d.line(S(x, 86, x, 98), fill=(110, 116, 132), width=int(2 * SS))
    d.rounded_rectangle(S(96, 40, 108, 52), radius=2 * SS, fill=(60, 62, 74), outline=INK, width=int(1.5 * SS))
    save(im, "magnet")


def ladle():
    """The foundry ladle (point B): a deep steel bucket with a glowing
    orange mouth, pouring lip, trunnion pins and a long handle."""
    im, d = canvas()
    lw = int(LW * SS)
    d.rectangle(S(104, 52, 126, 60), fill=(90, 96, 114), outline=INK, width=lw)            # handle
    d.polygon(S(18, 30, 110, 30, 98, 118, 30, 118), fill=(92, 100, 122), outline=INK)      # bucket
    d.polygon(S(18, 30, 110, 30, 98, 118, 30, 118), outline=INK, width=lw)
    d.line(S(26, 40, 36, 110), fill=(140, 148, 170), width=int(4 * SS))                     # shine
    for y in (58, 90):                                                                     # bands
        w = (y - 30) * 0.136
        d.line(S(18 + w, y, 110 - w, y), fill=INK, width=int(2.5 * SS))
    d.ellipse(S(10, 20, 118, 42), fill=(255, 138, 48), outline=INK, width=lw)              # molten mouth
    d.ellipse(S(28, 24, 92, 36), fill=(255, 209, 102))
    d.ellipse(S(44, 27, 70, 33), fill=(255, 244, 190))
    d.polygon(S(4, 26, 16, 22, 18, 34, 6, 34), fill=(92, 100, 122), outline=INK)           # pouring lip
    for cx in (18, 110):                                                                   # trunnions
        d.ellipse(S(cx - 7, 56, cx + 7, 70), fill=(255, 209, 102), outline=INK, width=int(1.6 * SS))
    save(im, "ladle")


# ---------------------------------------------------------------- game: Millbrook Mill

def grainsack():
    """Grain sack on the chute (point A of the Mill): a tied burlap sack
    with a stencilled wheat ear, grain spilling from the open corner."""
    im, d = canvas()
    lw = int(LW * SS)
    d.polygon(S(22, 40, 104, 40, 114, 116, 12, 116), fill=(214, 180, 120), outline=INK)      # sack
    d.polygon(S(22, 40, 104, 40, 114, 116, 12, 116), outline=INK, width=lw)
    for y in range(52, 112, 8):                                                               # weave
        d.line(S(20, y, 108, y), fill=(190, 152, 96), width=int(1.4 * SS))
    d.polygon(S(38, 10, 88, 10, 104, 40, 22, 40), fill=(200, 164, 104), outline=INK, width=lw)  # gathered top
    d.rounded_rectangle(S(30, 34, 96, 44), radius=4 * SS, fill=(168, 112, 58), outline=INK, width=lw)  # cord
    d.line(S(64, 60, 64, 100), fill=(120, 84, 40), width=int(3 * SS))                          # wheat ear stencil
    for i, y in enumerate((64, 72, 80, 88)):
        d.ellipse(S(52, y - 4, 63, y + 4), fill=(120, 84, 40))
        d.ellipse(S(65, y - 4, 76, y + 4), fill=(120, 84, 40))
    for cx, cy in ((108, 112), (114, 120), (120, 116), (104, 122), (118, 108)):            # spilled grain
        d.ellipse(S(cx - 3, cy - 2, cx + 3, cy + 2), fill=(236, 200, 110), outline=INK, width=int(1 * SS))
    save(im, "grainsack")


def haycart():
    """Hay cart (3.2's target): a wooden cart body heaped with yellow hay,
    two spoked wheels."""
    im, d = canvas()
    lw = int(LW * SS)
    for cx, cy, r in ((34, 46, 20), (58, 38, 24), (86, 42, 22), (104, 50, 14), (22, 54, 12)):    # the hay heap
        d.ellipse(S(cx - r, cy - r * 0.8, cx + r, cy + r * 0.8), fill=(244, 206, 92), outline=INK, width=int(1.8 * SS))
    for x0 in (30, 50, 70, 90):                                                                 # straws
        d.line(S(x0, 30, x0 + 8, 52), fill=(200, 160, 60), width=int(2 * SS))
    d.rectangle(S(8, 56, 120, 94), fill=(168, 112, 58), outline=INK, width=lw)                   # cart body
    for x in (36, 64, 92):
        d.line(S(x, 58, x, 92), fill=(120, 78, 38), width=int(2.5 * SS))
    d.line(S(10, 66, 118, 66), fill=(200, 144, 84), width=int(3 * SS))
    for cx in (34, 94):                                                                         # wheels
        d.ellipse(S(cx - 17, 90, cx + 17, 124), fill=(120, 78, 38), outline=INK, width=lw)
        for a in range(0, 180, 45):
            r = math.radians(a)
            d.line(S(cx - 14 * math.cos(r), 107 - 14 * math.sin(r), cx + 14 * math.cos(r), 107 + 14 * math.sin(r)),
                   fill=INK, width=int(2 * SS))
        d.ellipse(S(cx - 5, 102, cx + 5, 112), fill=(255, 209, 102), outline=INK, width=int(1.5 * SS))
    save(im, "haycart")


def bucket():
    """The hoist's bucket: wooden staves, two iron hoops, a rope handle,
    water showing at the top."""
    im, d = canvas()
    lw = int(LW * SS)
    d.arc(S(26, 6, 102, 70), 180, 360, fill=INK, width=int(5 * SS))                            # handle
    d.arc(S(26, 6, 102, 70), 180, 360, fill=(196, 160, 96), width=int(3 * SS))
    d.polygon(S(20, 36, 108, 36, 96, 120, 32, 120), fill=(196, 132, 70), outline=INK)         # the staves
    for x in (42, 56, 70, 84):
        d.line(S(x, 38, x + (x - 64) * -0.12, 118), fill=(150, 96, 48), width=int(2 * SS))
    d.polygon(S(20, 36, 108, 36, 96, 120, 32, 120), outline=INK, width=lw)
    for y in (56, 100):                                                                       # hoops
        w = (y - 36) * 0.143
        d.line(S(20 + w, y, 108 - w, y), fill=(90, 96, 114), width=int(5 * SS))
    d.ellipse(S(20, 28, 108, 44), fill=(92, 170, 240), outline=INK, width=lw)                 # the water
    d.ellipse(S(40, 32, 78, 38), fill=(170, 214, 250))
    save(im, "bucket")


def millstone():
    """The millstone hopper (point B of the Mill): a wooden hopper on top of
    a pair of grey millstones with the eye and dress grooves."""
    im, d = canvas()
    lw = int(LW * SS)
    d.polygon(S(26, 6, 102, 6, 78, 46, 50, 46), fill=(196, 132, 70), outline=INK)             # hopper
    d.polygon(S(26, 6, 102, 6, 78, 46, 50, 46), outline=INK, width=lw)
    d.line(S(36, 16, 92, 16), fill=(150, 96, 48), width=int(2.5 * SS))
    d.rectangle(S(56, 46, 72, 60), fill=(150, 96, 48), outline=INK, width=lw)                  # the shoe
    d.ellipse(S(8, 94, 120, 124), fill=(112, 114, 126), outline=INK, width=lw)                 # bed stone
    d.rectangle(S(8, 74, 120, 108), fill=(132, 134, 146))                                       # runner stone's side
    d.line(S(8, 74, 8, 108), fill=INK, width=lw)
    d.line(S(120, 74, 120, 108), fill=INK, width=lw)
    d.arc(S(8, 92, 120, 124), 0, 180, fill=INK, width=lw)
    d.ellipse(S(8, 56, 120, 92), fill=(160, 162, 172), outline=INK, width=lw)                 # runner stone's top
    for a in range(0, 180, 30):                                                                # dress grooves
        r = math.radians(a + 15)
        d.line(S(64 + 16 * math.cos(r), 74 + 6 * math.sin(r), 64 + 50 * math.cos(r), 74 + 15 * math.sin(r)),
               fill=(110, 112, 124), width=int(2 * SS))
    d.ellipse(S(54, 68, 74, 80), fill=(60, 62, 74), outline=INK, width=int(1.6 * SS))         # the eye
    save(im, "millstone")


# ---------------------------------------------------------------- topic icon

NAVY = (23, 35, 82)


def icon_bounce():
    """Bounces topic icon: a red rubber ball bouncing along a springy blue pad,
    each hop lower than the one before (one continuous navy path)."""
    im, d = canvas()
    lw = int(5 * SS)
    d.rounded_rectangle(S(4, 106, 124, 118), radius=4 * SS, fill=(110, 150, 220), outline=NAVY, width=lw)  # pad
    for x in (18, 38, 58, 78, 98):
        d.line(S(x, 109, x + 6, 115), fill=(200, 220, 255), width=int(2 * SS))
    floor = 100
    pts = []
    for i in range(21):                                      # the drop from the top left
        u = i / 20.0
        pts.append(((10 + 18 * u) * SS, (14 + (floor - 14) * u * u) * SS))
    for x0, x1, hgt in ((28, 70, 56), (70, 100, 28), (100, 118, 12)):   # hops, lower and lower
        for i in range(1, 31):
            u = i / 30.0
            pts.append(((x0 + (x1 - x0) * u) * SS, (floor - 4 * hgt * u * (1 - u)) * SS))
    d.line(pts, fill=NAVY, width=int(4.5 * SS), joint="curve")
    for x in (28, 70, 100):                                  # squash marks where it lands
        d.line(S(x - 7, 103, x - 11, 97), fill=NAVY, width=int(3 * SS))
        d.line(S(x + 7, 103, x + 11, 97), fill=NAVY, width=int(3 * SS))
    cx, cy, r = 49, floor - 56 - 2, 17                       # the ball at the top of the first hop
    d.ellipse(S(cx - r, cy - r, cx + r, cy + r), fill=(230, 70, 92), outline=NAVY, width=lw)
    d.ellipse(S(cx - 11, cy - 11, cx - 1, cy - 2), fill=(255, 160, 172))
    im.resize((SIZE, SIZE), Image.LANCZOS).save(os.path.join(OUT_ICONS, "icon_bounce.png"))


def icon_levers():
    """Levers & Moments topic icon: a tilted blue beam on an orange pivot,
    a big box close in on the low side, a small box far out on the high
    side (it balances), curved turning arrows - navy outline."""
    im, d = canvas()
    lw = int(5 * SS)
    d.polygon(S(64, 70, 44, 116, 84, 116), fill=(255, 154, 92), outline=NAVY)               # pivot
    d.polygon(S(64, 70, 44, 116, 84, 116), outline=NAVY, width=lw)
    d.line(S(34, 118, 94, 118), fill=NAVY, width=lw)
    al = math.radians(12)                                                                  # the right end is up
    cx, cy, half, th = 64, 66, 58, 6
    ux, uy = math.cos(al), -math.sin(al)                                                   # along the beam (screen)
    nx, ny = -uy, ux                                                                       # down, off the beam

    def P(t, n):
        return ((cx + t * ux + n * nx) * SS, (cy + t * uy + n * ny) * SS)
    beam = [P(-half, -th), P(half, -th), P(half, th), P(-half, th)]
    d.polygon(beam, fill=(92, 170, 240), outline=NAVY)
    d.line(beam + beam[:1], fill=NAVY, width=lw)

    def box(t, size, col):                                                                  # a box sitting on the beam
        pts = [P(t - size / 2, -th), P(t + size / 2, -th), P(t + size / 2, -th - size), P(t - size / 2, -th - size)]
        d.polygon(pts, fill=col, outline=NAVY)
        d.line(pts + pts[:1], fill=NAVY, width=lw)
    box(-24, 30, (255, 209, 102))                                                          # big, close in
    box(46, 17, (230, 70, 92))                                                             # small, far out
    d.arc(S(70, 8, 106, 44), 200, 300, fill=NAVY, width=int(4 * SS))                        # turning arrow
    d.polygon(S(99, 10, 108, 19, 96, 22), fill=NAVY)
    d.ellipse(S(59, 61, 69, 71), fill=(255, 255, 255), outline=NAVY, width=int(3 * SS))    # the axle
    im.resize((SIZE, SIZE), Image.LANCZOS).save(os.path.join(OUT_ICONS, "icon_levers.png"))


if __name__ == "__main__":
    bob()
    clamp()
    oscillator()
    hand()
    candle()
    eye()
    car()
    crate()
    hopper()
    saltbag()
    cannon()
    toybox()
    gizmo()
    minecart()
    kettle()
    coil()
    magnet()
    ladle()
    grainsack()
    haycart()
    bucket()
    millstone()
    icon_bounce()
    icon_levers()
    print("sprites written to", OUT, "and", OUT_ICONS)
