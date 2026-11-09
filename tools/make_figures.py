"""Capture the learning-panel figures: real screenshots of the simulation.

    python3 tools/make_figures.py                 # writes www/learn/<topic>_<n>.png
    python3 tools/make_figures.py --preview DIR   # also writes copies with the
                                                  # numbered callouts painted on,
                                                  # to check callout positions
    python3 tools/make_figures.py --only waves    # one topic

For each figure in physlab/learn.py it opens the app at the figure's deep
link (#/<topic>?...&at=<s>), which plays the simulation up to that moment
in fixed 1/60 s steps and pauses, then saves the canvas pixels exactly
(880 x 500). Dev-time only: needs Playwright (+ Chromium) and Pillow.
"""

import base64
import io
import os
import socket
import sys
import threading
from http.server import HTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from physlab import TOPICS  # noqa: E402
from physlab.server import Handler  # noqa: E402

OUT = os.path.join(ROOT, "www", "learn")


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def preview(png_bytes, callouts, path):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 13)
    except OSError:
        font = ImageFont.load_default()
    for i, c in enumerate(callouts):
        x, y = c["x"], c["y"]
        d.ellipse((x - 12, y - 12, x + 12, y + 12), fill=(255, 61, 127), outline=(255, 255, 255), width=3)
        d.text((x, y), str(i + 1), fill="white", font=font, anchor="mm")
    im.save(path)


def main(argv):
    from playwright.sync_api import sync_playwright
    only = argv[argv.index("--only") + 1] if "--only" in argv else None
    pdir = argv[argv.index("--preview") + 1] if "--preview" in argv else None
    os.makedirs(OUT, exist_ok=True)
    if pdir:
        os.makedirs(pdir, exist_ok=True)
    port = free_port()
    srv = HTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1300, "height": 1000})
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto("http://127.0.0.1:%d/" % port)
            page.wait_for_selector(".card.ready")
            page.wait_for_function("Object.keys(PL.sprites).length >= 12")
            for t in TOPICS:
                if "learn" not in t or (only and t["id"] != only):
                    continue
                for fig in t["learn"]["figures"]:
                    page.evaluate("document.documentElement.setAttribute('data-sim-ready', '0')")
                    page.evaluate("h => { location.hash = h; }", fig["route"])
                    page.wait_for_function(
                        "document.documentElement.getAttribute('data-sim-ready') === '1'", timeout=60000)
                    # the canvas is transparent; the page shows it over the stage's CSS
                    # background, so composite onto that colour exactly as displayed
                    data = page.evaluate("""() => {
                        const src = document.getElementById('stage');
                        const c = document.createElement('canvas');
                        c.width = src.width; c.height = src.height;
                        const x = c.getContext('2d');
                        x.fillStyle = getComputedStyle(src).backgroundColor;
                        x.fillRect(0, 0, c.width, c.height);
                        x.drawImage(src, 0, 0);
                        return c.toDataURL('image/png');
                    }""")
                    png = base64.b64decode(data.split(",", 1)[1])
                    path = os.path.join(ROOT, "www", fig["img"])
                    with open(path, "wb") as f:
                        f.write(png)
                    if pdir:
                        preview(png, fig["callouts"], os.path.join(pdir, os.path.basename(fig["img"])))
                    print("wrote", fig["img"], "(%d KB)" % (len(png) // 1024), "<-", fig["route"])
            browser.close()
            if errors:
                raise SystemExit("page errors: %s" % errors)
    finally:
        srv.shutdown()


if __name__ == "__main__":
    main(sys.argv[1:])
