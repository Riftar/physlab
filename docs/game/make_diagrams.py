"""Draws the GDD's figures into docs/game/img/ (dev-time, needs matplotlib).

    python3 docs/game/make_diagrams.py

Level maps are side views in metres. Wherever a station has a simulated
path, the ball's trail is the REAL trajectory of that station's reference
solution from level_math.py (placed at the station's spot in the level),
not a sketch. Colours follow the app (www/style.css: navy stage, orange
accent, cyan for B-runs, yellow draggable handles).
"""

import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                      # noqa: E402
from matplotlib.patches import Rectangle, Circle, Polygon, FancyBboxPatch, Wedge  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import level_math as LM                              # noqa: E402

OUT = os.path.join(HERE, "img")
BG, PANEL, GRID = "#0b1128", "#111a3a", "#1d2a55"
TXT, DIM = "#dfe6ff", "#8d9acb"
ORANGE, CYAN, YELLOW, RED, GREEN = "#ff9a5c", "#5cc8ff", "#ffd84a", "#ff5c6c", "#5be39b"
STEEL, WOOD, WATER, RUBBER = "#aab3c5", "#c08a4e", "#3d8fe0", "#e0455a"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "text.color": TXT})


def axes(w, h, xlim, ylim, title, sub):
    fig = plt.figure(figsize=(w, h), facecolor=BG)
    ax = fig.add_axes([0.03, 0.07, 0.94, 0.80])
    ax.set_facecolor(BG)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    for s in ax.spines.values():
        s.set_color(GRID)
    ax.tick_params(colors=DIM, labelsize=7)
    ax.grid(color=GRID, lw=0.5, alpha=0.6)
    ax.set_xlabel("metres", color=DIM, fontsize=7)
    fig.text(0.03, 0.945, title, fontsize=15, weight="bold", color=TXT)
    fig.text(0.03, 0.905, sub, fontsize=9, color=DIM)
    return fig, ax


def station_tag(ax, x, y, n, name, color=ORANGE):
    ax.add_patch(FancyBboxPatch((x - 0.05, y - 0.16), 0.36 + 0.095 * len(name), 0.34,
                                boxstyle="round,pad=0.04", fc=PANEL, ec=color, lw=1.2, zorder=8))
    ax.text(x + 0.02, y, n, color=color, weight="bold", fontsize=9, va="center", zorder=9)
    ax.text(x + 0.32, y, name, color=TXT, fontsize=8.5, va="center", zorder=9)


def knob(ax, x, y, label, dx=0.15, dy=0.0, ha="left"):
    ax.add_patch(Circle((x, y), 0.09, fc=YELLOW, ec="#7a6310", lw=1, zorder=10))
    ax.text(x + dx, y + dy, label, color=YELLOW, fontsize=7.5, va="center", ha=ha, zorder=10)


def endpoint(ax, x, y, letter, label, color):
    ax.add_patch(Circle((x, y), 0.2, fc=color, ec="white", lw=1.2, zorder=11))
    ax.text(x, y, letter, ha="center", va="center", color=BG, weight="bold", fontsize=11, zorder=12)
    ax.text(x, y - 0.36, label, ha="center", color=color, fontsize=8, zorder=12)


def trail(ax, pts, color, lw=1.8, ls="-", alpha=0.95):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=color, lw=lw, ls=ls, alpha=alpha, zorder=6, solid_capstyle="round")


def connector(ax, pts):
    trail(ax, pts, DIM, lw=1.2, ls=(0, (2, 2)), alpha=0.9)


def block(ax, x, y, w, h, fc, ec=None, z=3, alpha=1.0):
    ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec=ec or fc, lw=0.8, zorder=z, alpha=alpha))


def legend(fig):
    items = [(ORANGE, "ball path (simulated reference solution)"), (DIM, "connector (chute / funnel, not graded)"),
             (YELLOW, "tunable object = the student's knobs")]
    x = 0.03
    for c, t in items:
        fig.text(x, 0.025, "\u25cf", color=c, fontsize=11, va="center")
        fig.text(x + 0.013, 0.025, t, color=DIM, fontsize=8, va="center")
        x += 0.012 + 0.0062 * len(t) + 0.03


def run(sid, knobs):
    st = LM.BY_STATION[sid]
    r = st["fn"](knobs, st["variant"])
    assert r["ok"], (sid, knobs, r["reason"])
    return r


def shift(path, dx, dy, sx=1.0):
    return [(dx + sx * p[1], dy + p[2]) for p in path]


# ---------------------------------------------------------------------------
def level1():
    fig, ax = axes(16, 7.9, (-0.6, 17.2), (-0.4, 7.0), "Level 1 - The Bounce Factory  (rubber ball)",
                   "A toy factory: springs, pads and brine. Ball: 0.13 kg, 6 cm, density 1149 kg/m3, "
                   "restitution e = 0.85 on steel. Four stations, each reset by a funnel or hatch.")
    r = LM.BALLS["rubber"]["r"]
    # building
    block(ax, -0.6, -0.4, 17.8, 0.4, "#1a2348")
    block(ax, -0.6, 1.6, 7.0, 0.4, "#26305c")                    # mezzanine
    block(ax, 6.3, 0.0, 0.15, 1.6, "#26305c")
    # --- 1.1 Bounce Flap: pad at (0.6, 2.0)
    ox, oy = 0.6, 2.0
    b = run("1.1", {"hatch": 2.7, "pad": "steel_plate"})
    block(ax, ox - 0.3, oy - 0.05, 1.2, 0.05, STEEL, z=5)         # steel pad
    block(ax, ox - 0.16, oy, 0.08, 4.3, "#3a4678")                # hatch rail
    block(ax, ox - 0.12, oy + 2.7, 0.14, 0.04, WOOD, z=6)        # hatch ledge
    fx0, fx1 = LM.BF_FLAP
    block(ax, ox + fx1, oy + 1.5 - 0.04, 2.3, 0.06, WOOD)        # shelf
    block(ax, ox + fx0, oy + 1.5 - 0.03, fx1 - fx0, 0.03, YELLOW, z=5, alpha=0.7)   # flap
    block(ax, ox + LM.BF_DUCT[0], oy + 2.3, LM.BF_DUCT[1] - LM.BF_DUCT[0], 0.12, "#9a3b3b")
    ax.text(ox + 1.25, oy + 2.48, "hot duct - don't touch", color=RED, fontsize=7)
    ax.text(ox + 0.95, oy + 1.25, "one-way flap", color=YELLOW, fontsize=7)
    trail(ax, shift(b["path"], ox, oy), ORANGE)
    endpoint(ax, ox, oy + 4.55, "A", "toy hopper", GREEN)
    knob(ax, ox - 0.12, oy + 2.7, "hatch height h0\n(1.0 - 4.0 m)", dx=-0.2, ha="right")
    knob(ax, ox + 0.35, oy - 0.05, "pad: steel / wood / foam / sand", dx=0.0, dy=-0.32, ha="left")
    station_tag(ax, ox + 1.2, oy + 3.55, "1.1", "Bounce Flap")
    # shelf -> canal
    connector(ax, [(ox + 0.45, oy + 1.5 + r), (ox + 2.9, oy + 1.5 + r), (3.55, 2.75)])
    # --- 1.2 Salt Canal
    block(ax, 3.3, 2.0, 0.08, 0.8, "#3a4678")
    block(ax, 6.1, 2.0, 0.08, 0.8, "#3a4678")
    block(ax, 3.38, 2.0, 2.72, 0.62, WATER, alpha=0.55)
    ax.add_patch(Circle((4.4, 2.62 - 0.026), r, fc=RUBBER, ec="white", lw=0.6, zorder=7))
    ax.annotate("", xy=(5.8, 2.4), xytext=(4.0, 2.4), arrowprops=dict(arrowstyle="->", color=CYAN, lw=1))
    ax.text(4.2, 2.2, "current", color=CYAN, fontsize=7)
    knob(ax, 3.6, 3.05, "salt: 0 - 20 bags (1 kg each)")
    station_tag(ax, 3.4, 3.55, "1.2", "Salt Canal")
    ax.text(3.42, 1.78, "40 L, the ball sinks in fresh water", color=DIM, fontsize=7)
    connector(ax, [(6.05, 2.64), (6.4, 2.64), (6.62, 2.52)])
    # --- 1.3 Camel Hump (track origin so its start meets the canal outflow)
    h = run("1.3", {"hump": 1.0})
    tr = LM.BumpTrack(1.5, 1.0, LM.HUMP_R)
    tx, ty = 6.4, 1.05
    xs = [i * tr.x1 / 300 for i in range(301)]
    trail(ax, [(tx + x, ty + tr.f(x) - r) for x in xs], WOOD, lw=3)
    trail(ax, [(tx + p[1], ty + p[2]) for p in h["path"]], ORANGE)
    knob(ax, tx + tr.xc, ty + tr.f(tr.xc) + 0.12, "hump height (0.20 - 1.60 m)\ncrest radius R = 0.8 m", dy=0.2)
    station_tag(ax, tx + 1.6, 3.55, "1.3", "Camel Hump")
    ax.text(tx + 2.3, ty + 1.45, "stay under sqrt(gR) = 2.8 m/s", color=DIM, fontsize=7)
    # --- 1.4 Spring Cannon: muzzle at the breech
    mx, my = tx + 5.9, ty + 0.1
    c = run("1.4", {"compression": 13.0, "angle": 45.0})
    cb = run("1.4", {"compression": 16.0, "angle": 45.0})
    th = math.radians(45)
    ax.plot([mx - 0.45 * math.cos(th), mx], [my - 0.45 * math.sin(th), my], color=STEEL, lw=7,
            solid_capstyle="butt", zorder=5)
    trail(ax, shift(c["path"], mx, my), ORANGE)
    trail(ax, shift(cb["path"], mx, my), CYAN, lw=1.3, ls=(0, (4, 2)))
    dx, dy = 2.6, 0.8
    fxm, fym = mx + dx, my + dy
    ax.add_patch(Polygon([(fxm - LM.FUNNEL_MOUTH, fym), (fxm - LM.FUNNEL_THROAT, fym - LM.FUNNEL_DEPTH),
                          (fxm + LM.FUNNEL_THROAT, fym - LM.FUNNEL_DEPTH), (fxm + LM.FUNNEL_MOUTH, fym)],
                         closed=False, fc="none", ec=WOOD, lw=2.5, zorder=6))
    block(ax, fxm - 0.4, -0.0, 0.8, fym - 0.3, "#26305c")
    block(ax, fxm + LM.BANK_WALL, fym - 0.6, 0.12, 3.6, "#7a3b58")
    ax.text(fxm + LM.BANK_WALL - 0.1, fym + 3.1, "rubber\nbumper wall", color="#ff8fb4", fontsize=7, ha="right")
    endpoint(ax, fxm, fym + 0.6, "B", "toy box", CYAN)
    knob(ax, mx - 0.2, my - 0.2, "spring 2-20 cm, angle 15-75 deg", dy=-0.35, ha="center", dx=0)
    station_tag(ax, mx - 0.2, 4.6, "1.4", "Spring Cannon")
    ax.text(mx - 0.2, 4.05, "orange: direct shot 13.0 cm @ 45 deg\ncyan dashed: trick shot off the wall, 16.0 cm",
            color=DIM, fontsize=7)
    legend(fig)
    fig.savefig(os.path.join(OUT, "level1_bounce_factory.png"), dpi=110, facecolor=BG)
    plt.close(fig)


# ---------------------------------------------------------------------------
def level2():
    fig, ax = axes(14, 8.2, (-0.3, 9.6), (0.0, 7.4), "Level 2 - The Foundry  (steel ball)",
                   "Heavy, conductive, magnetic and it expands when hot. Ball: 0.51 kg, 5 cm, density 7792 kg/m3. "
                   "The ball falls floor by floor, then the crane throws it into the ladle.")
    r = LM.BALLS["steel"]["r"]
    block(ax, -0.3, 0.0, 9.9, 0.3, "#1a2348")
    # 2.1 Hot Ring at (1.0, 6.0)
    ax.add_patch(Wedge((1.0, 6.0), 0.22, 0, 360, width=0.07, fc="#c9ced8", ec="white", lw=0.6, zorder=6))
    ax.add_patch(Circle((1.0, 6.0 + 0.08), r * 2.4, fc=STEEL, ec="white", lw=0.6, zorder=7))
    block(ax, 0.6, 5.55, 0.8, 0.3, WATER, alpha=0.5)
    ax.plot([1.9, 1.55], [6.8, 5.85], color=DIM, lw=1)
    ax.text(1.95, 6.8, "kettle: 95 C water", color=DIM, fontsize=7)
    endpoint(ax, 0.2, 6.7, "A", "ore cart", GREEN)
    knob(ax, 1.45, 6.15, "heat: ring / ball / both\nwater 0 - 0.5 kg")
    station_tag(ax, 0.0, 7.1, "2.1", "Hot Ring")
    ax.text(0.15, 5.25, "bore 49.94 mm, ball 50.00 mm", color=DIM, fontsize=7)
    connector(ax, [(1.0, 5.9), (1.0, 5.0), (2.6, 4.72)])
    # 2.2 Trapdoor Latch at (2.6, 4.6)
    block(ax, 2.3, 4.6, 0.6, 0.06, "#b87333", z=5)
    ax.add_patch(Circle((2.6, 4.66 + r), r * 1.6, fc=STEEL, ec="white", lw=0.6, zorder=7))
    ax.add_patch(FancyBboxPatch((0.2, 3.55), 1.75, 0.8, boxstyle="round,pad=0.04", fc=PANEL, ec=CYAN, lw=1))
    ax.text(0.3, 4.15, "battery -> dial R -> 1 A fuse", color=CYAN, fontsize=7)
    ax.text(0.3, 3.95, "-> latch coil 8 ohm -> BALL -> back", color=CYAN, fontsize=7)
    ax.text(0.3, 3.72, "latch pulls at >= 0.30 A", color=DIM, fontsize=7)
    ax.plot([1.95, 2.35], [3.95, 4.6], color=CYAN, lw=0.8, ls=":")
    knob(ax, 2.95, 4.85, "battery (AA / 6 V / 9 V / 12 V)\n+ resistor dial 0 - 50 ohm")
    station_tag(ax, 2.3, 5.45, "2.2", "Trapdoor Latch")
    connector(ax, [(2.6, 4.6), (2.6, 4.08)])
    # 2.3 Hydraulic Gate: small cylinder at x=2.6, big piston at x=3.6
    block(ax, 2.5, 3.3, 0.2, 0.75, "#3a4678", alpha=0.9)
    block(ax, 2.52, 3.3, 0.16, 0.45, "#e3b34a", alpha=0.7)
    block(ax, 2.5, 3.12, 1.35, 0.18, "#e3b34a", alpha=0.7)
    block(ax, 3.45, 3.3, 0.4, 0.35, "#e3b34a", alpha=0.7)
    block(ax, 3.42, 3.65, 0.46, 0.05, STEEL)
    block(ax, 3.6, 3.7, 0.1, 0.5, "#6b7079")                     # gate rod
    block(ax, 3.85, 3.7, 0.08, 0.55, "#8a93a5")                  # the gate itself
    ax.text(2.0, 2.9, "ball rides the small piston 30 cm down;\nthe oil lifts the 1 kg gate", color=DIM, fontsize=7)
    knob(ax, 3.65, 3.45, "big piston diameter\n2 - 10 cm (small one: 2 cm)", dx=0.3)
    station_tag(ax, 4.15, 4.15, "2.3", "Hydraulic Gate")
    connector(ax, [(2.6, 3.75 + r), (3.9, 3.75 + r), (5.2, 2.55)])
    # 2.4 Magnet Swing: bottom of swing at (6.2, 2.5)
    L, th0 = 1.0, 58.0
    bx, by = 6.2, 2.5
    px, py = bx, by + L
    block(ax, px - 0.05, py, 0.1, 3.3 - py + 1.5, "#3a4678")
    block(ax, px - 1.6, 4.8, 1.8, 0.1, "#3a4678")
    ang = [math.radians(-th0 + i * th0 / 40) for i in range(41)]
    trail(ax, [(px + L * math.sin(a), py - L * math.cos(a)) for a in ang], ORANGE)
    a0 = math.radians(-th0)
    ax.plot([px, px + L * math.sin(a0)], [py, py - L * math.cos(a0)], color=DIM, lw=1)
    ax.plot([px, bx], [py, by], color=DIM, lw=0.8, ls=":")
    ax.add_patch(Circle((px + L * math.sin(a0), py - L * math.cos(a0)), 0.09, fc=STEEL, ec="white", zorder=7))
    m = run("2.4", {"length": L, "angle": th0})
    trail(ax, shift(m["path"], bx, by), ORANGE)
    block(ax, 5.0, 0.3, 1.3, 2.2 - 0.05, "#26305c")
    lx, ly = bx + 1.5, by - LM.MS_DROP
    ax.add_patch(Polygon([(lx - 0.16, ly + 0.05), (lx - 0.1, ly - 0.25), (lx + 0.1, ly - 0.25), (lx + 0.16, ly + 0.05)],
                         fc="#ff7a2e", ec="#ffd2a8", lw=1, zorder=6))
    block(ax, lx - 0.1, 0.3, 0.2, ly - 0.55, "#3a4678")
    endpoint(ax, lx + 0.55, ly + 0.2, "B", "ladle", CYAN)
    knob(ax, px + 0.05, py + 0.2, "cable length 0.4 - 2.0 m\nrelease angle 10 - 90 deg", dx=0.2)
    ax.text(6.5, 1.65, "magnet holds 12 N; trip wire\ncuts it at the bottom", color=DIM, fontsize=7)
    station_tag(ax, 6.6, 5.3, "2.4", "Magnet Swing")
    ax.text(7.25, 0.55, "casting pit", color=DIM, fontsize=7)
    legend(fig)
    fig.savefig(os.path.join(OUT, "level2_foundry.png"), dpi=110, facecolor=BG)
    plt.close(fig)


# ---------------------------------------------------------------------------
def level3():
    fig, ax = axes(15, 7.4, (-0.3, 10.2), (-0.1, 5.2), "Level 3 - Millbrook Mill  (wooden ball)",
                   "Water, wind, light and levers. Ball: 0.16 kg, 8 cm, density 597 kg/m3 - it floats, the wind "
                   "pushes it, and it does NOT conduct electricity.")
    r = LM.BALLS["wood"]["r"]
    block(ax, -0.3, -0.1, 10.5, 0.3, "#1a2348")
    # 3.1 Crow's Well: bottom at (1.0, 3.0), 10 cm wide, water 20 cm, paddle at 45 cm (drawn 4x wider)
    wx, wy, W = 1.0, 3.0, 0.4
    block(ax, wx - W / 2 - 0.05, wy - 0.05, W + 0.1, 0.05, "#3a4678")
    block(ax, wx - W / 2 - 0.05, wy, 0.05, 0.6, "#3a4678")
    block(ax, wx + W / 2, wy, 0.05, 0.45, "#3a4678")
    res = run("3.1", {"item": "stone", "count": 9})
    lvl = (res["metric"] + 0.5) / 100.0
    block(ax, wx - W / 2, wy, W, 0.20, WATER, alpha=0.35)
    block(ax, wx - W / 2, wy + 0.20, W, lvl - 0.20, WATER, alpha=0.6)
    for i in range(9):
        ax.add_patch(Circle((wx - 0.14 + (i % 4) * 0.09, wy + 0.04 + (i // 4) * 0.07), 0.035, fc="#8f8a80",
                            ec="#5c584f", zorder=6))
    ax.add_patch(Circle((wx, wy + res["metric"] / 100.0), r * 1.3, fc=WOOD, ec="white", lw=0.6, zorder=7))
    ax.add_patch(Circle((wx + 0.34, wy + 0.45), 0.16, fc="none", ec=DIM, lw=1, zorder=6))
    for k in range(6):
        a = k * math.pi / 3
        ax.plot([wx + 0.34, wx + 0.34 + 0.16 * math.cos(a)], [wy + 0.45, wy + 0.45 + 0.16 * math.sin(a)],
                color=DIM, lw=0.8)
    endpoint(ax, 0.35, 4.55, "A", "grain chute", GREEN)
    connector(ax, [(0.5, 4.3), (0.95, 3.7)])
    knob(ax, wx - 0.45, wy + 0.25, "drop: stones / steel bearings\n/ pine blocks, how many (0 - 40)", dx=-0.15,
         ha="right")
    station_tag(ax, 0.25, 5.0, "3.1", "Crow's Well")
    ax.text(wx - 0.2, wy - 0.28, "paddle wheel sweeps at 45 cm", color=DIM, fontsize=7)
    # chute to the lip
    lip_x, lip_y = 2.1, 3.1
    connector(ax, [(wx + 0.5, wy + 0.47), (lip_x, lip_y)])
    # 3.2 Fan Jump
    f = run("3.2", {"wind": 15.0})
    f0 = LM.fan_jump({"wind": 0.0}, LM.BY_STATION["3.2"]["variant"])
    trail(ax, shift(f["path"], lip_x, lip_y), ORANGE)
    trail(ax, shift(f0["path"], lip_x, lip_y), RED, lw=1.2, ls=(0, (3, 2)))
    fs = LM.fan_jump({"wind": 15.0}, LM.BY_STATION["3.2"]["variant"], ball_id="steel")
    trail(ax, shift(fs["path"], lip_x, lip_y), STEEL, lw=1.2, ls=(0, (1, 2)))
    ax.add_patch(Circle((lip_x - 0.2, lip_y + 0.55), 0.22, fc=PANEL, ec=CYAN, lw=1.2, zorder=6))
    for k in range(3):
        ax.annotate("", xy=(lip_x + 1.0, lip_y + 0.6 - 0.18 * k), xytext=(lip_x + 0.05, lip_y + 0.6 - 0.18 * k),
                    arrowprops=dict(arrowstyle="->", color=CYAN, lw=0.8, alpha=0.6))
    knob(ax, lip_x - 0.2, lip_y + 0.85, "fan wind 0 - 20 m/s", dx=0.15)
    cx, cy = lip_x + 1.975, lip_y - LM.FJ_DROP
    block(ax, 2.3, -0.0, 1.45, 0.35, WATER, alpha=0.6)
    ax.text(2.45, 0.42, "mill race", color=CYAN, fontsize=7)
    block(ax, cx - LM.FJ_CART_HALF, cy - 0.18, 2 * LM.FJ_CART_HALF, 0.18, "#d8b25a")
    block(ax, cx - LM.FJ_CART_HALF, 0.2, 0.05, cy - 0.38, "#5c4630")
    ax.text(cx - 0.5, cy - 0.42, "hay cart", color=DIM, fontsize=7)
    ax.text(4.3, 2.75, "orange: wooden ball, fan 15 m/s\nred dashed: no fan (splash)\ngrey dotted: a steel ball, "
            "fan 15 m/s", color=DIM, fontsize=7)
    station_tag(ax, 2.0, 4.1, "3.2", "Fan Jump")
    # path to the light gate
    connector(ax, [(cx + 0.1, cy - 0.05), (4.6, 0.25 + r), (7.0, 0.25 + r)])
    block(ax, 4.6, 0.2, 2.7, 0.05, "#5c4630")
    block(ax, 4.9, 0.25, 0.25, 0.03, "#b87333", z=5)
    ax.text(4.55, 0.02, "old Foundry contact:\nwood doesn't conduct", color=RED, fontsize=6.5)
    # 3.3 Light Gate: vertical optical bench at x=5.9 (lamp at top, cell in the floor)
    gx = 5.9
    ax.add_patch(Circle((gx, 1.25), 0.06, fc=YELLOW, ec="white", zorder=7))
    block(ax, gx - 0.05, 0.22, 0.1, 0.03, GREEN, z=6)
    ax.plot([gx, gx], [1.25, 0.25], color=YELLOW, lw=0.8, ls=":", alpha=0.8)
    ax.add_patch(Polygon([(gx - 0.15, 0.5), (gx, 0.53), (gx + 0.15, 0.5), (gx, 0.47)], fc=CYAN, alpha=0.7, zorder=7))
    knob(ax, gx - 0.2, 0.5, "lens position d_o\n(5 - 95 cm from the lamp,\nbench 100 cm)", dx=-0.14, ha="right")
    ax.text(gx + 0.08, 1.3, "lamp", color=YELLOW, fontsize=7)
    ax.text(gx + 0.08, 0.05, "photocell", color=GREEN, fontsize=7)
    station_tag(ax, 5.0, 2.0, "3.3", "Light Gate")
    # drawbridge + moat
    block(ax, 7.0, -0.0, 1.0, 0.25, WATER, alpha=0.6)
    block(ax, 7.0, 0.25, 1.0, 0.04, WOOD, z=5)
    ax.text(6.3, 0.95, "drawbridge lowers when\nthe ball breaks the beam", color=DIM, fontsize=6.5)
    # 3.4 Mill Hoist: pivot at (9.1, 0.78)
    pvx, pvy, a, b = 9.1, 0.78, 1.0, 0.5
    for deg, alpha_ in ((-LM.MH_STOP, 0.35), (LM.MH_STOP, 1.0)):
        t_ = math.radians(deg)
        ax.plot([pvx - 1.1 * math.cos(t_), pvx + 1.1 * math.cos(t_)],
                [pvy + 1.1 * math.sin(t_), pvy - 1.1 * math.sin(t_)], color=WOOD, lw=3, alpha=alpha_, zorder=5)
    ax.add_patch(Polygon([(pvx - 0.12, 0.2), (pvx + 0.12, 0.2), (pvx, pvy)], fc="#3a4678", zorder=4))
    arc = [math.radians(-LM.MH_STOP + i * 2 * LM.MH_STOP / 30) for i in range(31)]
    trail(ax, [(pvx - a * math.cos(t), pvy + a * math.sin(t) + r) for t in arc], ORANGE)
    t_ = math.radians(LM.MH_STOP)
    bxp, byp = pvx + b * math.cos(t_), pvy - b * math.sin(t_)
    ax.plot([bxp, bxp], [byp, byp - 0.3], color=DIM, lw=0.8)
    block(ax, bxp - 0.08, byp - 0.45, 0.16, 0.15, WATER, alpha=0.8)
    knob(ax, bxp + 0.22, byp - 0.05, "hook b 0.2 - 1.0 m\nwater 0 - 2 L", dx=0.14)
    ax.text(pvx - 0.1, 1.55, "start: scoop down (faint)\nend: scoop up at the shelf", color=DIM, fontsize=6.5)
    sx_, sy_ = pvx - a * math.cos(t_), pvy + a * math.sin(t_)
    block(ax, sx_ - 0.55, sy_ + 0.02, 0.45, 0.06, "#8a93a5")
    endpoint(ax, sx_ - 0.4, sy_ + 0.55, "B", "millstone hopper", CYAN)
    station_tag(ax, 8.45, 2.0, "3.4", "Mill Hoist")
    legend(fig)
    fig.savefig(os.path.join(OUT, "level3_mill.png"), dpi=110, facecolor=BG)
    plt.close(fig)


# ---------------------------------------------------------------------------
def world_map():
    fig = plt.figure(figsize=(13, 6.6), facecolor=BG)
    ax = fig.add_axes([0.02, 0.02, 0.96, 0.86])
    ax.set_facecolor(BG)
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 6.6)
    ax.axis("off")
    fig.text(0.03, 0.935, "The Machine Works - world map", fontsize=16, weight="bold", color=TXT)
    fig.text(0.03, 0.895, "One hub, three halls (one ball material each), one locked finale. Halls unlock in order; "
             "stars never gate progress.", fontsize=9, color=DIM)
    # roads
    pts = [(1.2, 1.0), (2.5, 2.6), (5.6, 2.6), (8.7, 2.6), (11.75, 4.2)]
    ax.plot(*zip(*pts), color=GRID, lw=10, solid_capstyle="round", zorder=1)
    ax.plot(*zip(*pts), color="#2c3a70", lw=2, ls=(0, (4, 4)), zorder=2)
    halls = [
        (2.5, "1", "The Bounce Factory", "rubber ball", RUBBER,
         ["1.1 Bounce Flap   (restitution)", "1.2 Salt Canal    (density)", "1.3 Camel Hump    (energy, v2 < gR)",
          "1.4 Spring Cannon (spring + projectile)"]),
        (5.6, "2", "The Foundry", "steel ball", STEEL,
         ["2.1 Hot Ring       (thermal expansion)", "2.2 Trapdoor Latch (Ohm's law)", "2.3 Hydraulic Gate (Pascal)",
          "2.4 Magnet Swing   (pendulum tension)"]),
        (8.7, "3", "Millbrook Mill", "wooden ball", WOOD,
         ["3.1 Crow's Well  (Archimedes)", "3.2 Fan Jump     (drag + wind)", "3.3 Light Gate   (thin lens)",
          "3.4 Mill Hoist   (moments)"]),
    ]
    for x, n, name, ball, col, sts in halls:
        ax.add_patch(FancyBboxPatch((x - 1.45, 2.95), 2.9, 2.9, boxstyle="round,pad=0.05", fc=PANEL, ec=col, lw=1.6,
                                    zorder=3))
        ax.add_patch(Circle((x - 1.15, 5.45), 0.24, fc=col, ec="white", lw=1, zorder=4))
        ax.text(x - 1.15, 5.45, n, ha="center", va="center", color=BG, weight="bold", fontsize=12, zorder=5)
        ax.text(x - 0.8, 5.52, name, color=TXT, weight="bold", fontsize=10.5, va="center", zorder=5)
        ax.text(x - 0.8, 5.22, ball, color=col, fontsize=8.5, va="center", zorder=5)
        for i, s in enumerate(sts):
            ax.text(x - 1.32, 4.75 - i * 0.36, s, color=DIM, fontsize=7.2, family="DejaVu Sans Mono", zorder=5)
        ax.add_patch(Circle((x, 2.6), 0.16, fc=col, ec="white", zorder=4))
        ax.text(x, 2.25, "\u2605 \u2605 \u2605  x 4 stations", ha="center", color=YELLOW, fontsize=8)
    ax.add_patch(FancyBboxPatch((10.7, 4.2), 2.1, 1.6, boxstyle="round,pad=0.05", fc=BG, ec=DIM, lw=1.2, ls="--",
                                zorder=3))
    ax.text(11.75, 5.35, "The Grand Hall", ha="center", color=DIM, weight="bold", fontsize=10)
    ax.text(11.75, 4.95, "(locked - future)", ha="center", color=DIM, fontsize=8)
    ax.text(11.75, 4.55, "all three balls, one machine", ha="center", color=DIM, fontsize=7.5)
    ax.add_patch(FancyBboxPatch((0.3, 0.45), 2.0, 1.05, boxstyle="round,pad=0.05", fc=PANEL, ec=GREEN, lw=1.4,
                                zorder=3))
    ax.text(1.3, 1.2, "Workshop hub", ha="center", color=GREEN, weight="bold", fontsize=10)
    ax.text(1.3, 0.85, "player card, badges,\nparts collection", ha="center", color=DIM, fontsize=7.5)
    ax.text(4.0, 1.35, "Each hall: 4 stations chained from A to B, then a Golden Run of the whole machine.\n"
            "Finishing a hall unlocks the next hall AND its station parts in the Sandbox.", color=DIM, fontsize=8.5)
    fig.savefig(os.path.join(OUT, "world_map.png"), dpi=110, facecolor=BG)
    plt.close(fig)


def difficulty(results_json):
    import json
    with open(results_json) as f:
        res = json.load(f)
    ids = [s["id"] for s in LM.STATIONS if s["id"] in res]
    bits = [res[i]["bits"] or 0 for i in ids]
    mb = [res[i]["bits_mastery"] or 0 for i in ids]
    fig = plt.figure(figsize=(11, 4.2), facecolor=BG)
    ax = fig.add_axes([0.07, 0.16, 0.9, 0.66])
    ax.set_facecolor(BG)
    xs = list(range(len(ids)))
    ax.bar([x - 0.18 for x in xs], bits, width=0.36, color=ORANGE, label="pass (\u2605)")
    ax.bar([x + 0.18 for x in xs], mb, width=0.36, color=CYAN, label="mastery goal (\u2605\u2605\u2605)")
    for x, bb, m in zip(xs, bits, mb):
        ax.text(x - 0.18, bb + 0.1, "%.1f" % bb, ha="center", color=ORANGE, fontsize=7)
        ax.text(x + 0.18, m + 0.1, "%.1f" % m, ha="center", color=CYAN, fontsize=7)
    ax.set_xticks(xs)
    ax.set_xticklabels(["%s\n%s" % (i, LM.BY_STATION[i]["title"]) for i in ids], fontsize=7, color=DIM)
    for lv in (3.5, 7.5):
        ax.axvline(lv, color=GRID, lw=1)
    ax.set_ylim(0, 8.4)
    for x_, name in ((1.5, "Level 1 - rubber"), (5.5, "Level 2 - steel"), (9.5, "Level 3 - wood")):
        ax.text(x_, 7.9, name, ha="center", color=TXT, fontsize=8.5, weight="bold")
    ax.set_ylabel("bits = -log2(chance a random setting works)", color=DIM, fontsize=8)
    ax.tick_params(colors=DIM)
    for s in ax.spines.values():
        s.set_color(GRID)
    ax.grid(axis="y", color=GRID, lw=0.5)
    ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=TXT, fontsize=7.5, loc="upper left", bbox_to_anchor=(0.0, 0.93))
    fig.text(0.07, 0.9, "Difficulty curve - how much a guesser must get lucky (measured by level_math.py)",
             fontsize=12, weight="bold", color=TXT)
    fig.savefig(os.path.join(OUT, "difficulty_curve.png"), dpi=110, facecolor=BG)
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    LM.finish_variants()
    world_map()
    level1()
    level2()
    level3()
    js = os.path.join(HERE, "level_math_results.json")
    if os.path.exists(js):
        difficulty(js)
    print("wrote", sorted(os.listdir(OUT)))
