"""Generate the procedural simulation sprites (pendulum bob, clamp, wave
shaker, hand, candle, eye, car, crate) in the same flat, dark-outlined
128 px style as the original set.

    python3 tools/make_sprites.py          # writes www/sprites/item_*.png

Drawn at 4x and downsampled for clean anti-aliasing; white background,
which the client keys out at load. Needs Pillow (a dev-time tool only -
the app itself stays stdlib + vanilla JS).
"""

import math
import os
from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "www", "sprites")
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


if __name__ == "__main__":
    bob()
    clamp()
    oscillator()
    hand()
    candle()
    eye()
    car()
    crate()
    print("sprites written to", OUT)
