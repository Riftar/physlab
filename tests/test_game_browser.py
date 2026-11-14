"""End-to-end: the game page in a real browser (Playwright + Chromium).

Skipped when Playwright or a Chromium build is not available (like the
Node tests) - the app itself needs neither. What it checks, as a student
or a tester would do it:

  * home -> Machine Works -> the Bounce Factory loads without a JS error
  * every station's saved correct setting, opened from its deep link,
    passes when "Test station" is clicked; a wrong setting fails
  * the knob controls work: slider, number box (snapped to the grid),
    choice chips - and the URL follows them
  * the yellow handles on the stage drag the knobs
  * the whole machine runs A -> B with the saved settings
  * every "Open in the lab" link opens a working experiment, which offers a
    way back to the game - with the settings still there
  * the follow camera travels with the ball; the camera buttons switch view
  * the share box copies a link that reopens exactly this setup
  * practice mode and back; scores in the debrief; the locked next hall
  * Hall 2, the Foundry: every saved setting (working, mastery, top score)
    passes from its deep link; every yellow handle moves its knob; the
    machine runs A -> B with the heating played as a time-lapse; the lab
    links open; the hall opens on the map once Hall 1 is cleared (with the
    classroom locks on)
  * Hall 3, Millbrook Mill: the same, and the default test mode - every
    hall and station open, so a tester can jump straight into the Mill
"""

import os
import socket
import sys
import tempfile
import threading
import unittest
from http.server import HTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from physlab.game import bounce_factory as BF  # noqa: E402
from physlab.game import foundry as FD  # noqa: E402
from physlab.game import mill as ML  # noqa: E402

SOL = BF.table()["stations"]
NOM = BF.table()["nominal"]
SOL2 = FD.table()["stations"]
SOL3 = ML.table()["stations"]


def _browser():
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        return None
    if not os.environ.get("PLAYWRIGHT_BROWSERS_PATH") and os.path.isdir("/opt/pw-browsers"):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/opt/pw-browsers"
    return sync_playwright


SYNC = _browser()


@unittest.skipUnless(SYNC, "playwright not installed")
class TestGameInTheBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.old_db = os.environ.get("PHYSLAB_DB")
        os.environ["PHYSLAB_DB"] = os.path.join(cls.tmp, "browser.sqlite")
        from physlab.server import Handler
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        cls.port = s.getsockname()[1]
        s.close()
        cls.srv = HTTPServer(("127.0.0.1", cls.port), Handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.pw = SYNC().start()
        try:
            cls.browser = cls.pw.chromium.launch()
        except Exception as e:                                  # no Chromium build for this Playwright
            cls.pw.stop()
            cls.srv.shutdown()
            raise unittest.SkipTest("no browser: %s" % str(e).splitlines()[0])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.srv.shutdown()
        cls.srv.server_close()
        if cls.old_db is None:
            os.environ.pop("PHYSLAB_DB", None)
        else:
            os.environ["PHYSLAB_DB"] = cls.old_db

    def locks(self, on):
        """Switch the classroom locks for this test (the server reads the variable at every request)."""
        old = os.environ.get("PHYSLAB_GAME_LOCKS")
        os.environ["PHYSLAB_GAME_LOCKS"] = "on" if on else "off"
        self.addCleanup(lambda: os.environ.pop("PHYSLAB_GAME_LOCKS", None) if old is None
                        else os.environ.__setitem__("PHYSLAB_GAME_LOCKS", old))

    def setUp(self):
        self.page = self.browser.new_page(viewport={"width": 1400, "height": 1000})
        self.errors = []
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))
        self.page.on("console", lambda m: self.errors.append(m.text) if m.type == "error" else None)

    def tearDown(self):
        self.page.close()
        self.assertEqual(self.errors, [], "JavaScript errors on the page")

    def open(self, hash_):
        try:        # a hash-only navigation keeps the document: don't let the last page's "ready" count
            self.page.evaluate("document.documentElement.setAttribute('data-sim-ready', '0')")
        except Exception:
            pass
        url = "http://127.0.0.1:%d/%s" % (self.port, hash_)
        if self.page.url == url:            # the same hash twice: no hashchange, so load it afresh
            self.page.reload()
        else:
            self.page.goto(url)
        self.ready()

    def ready(self):
        self.page.wait_for_function("document.documentElement.getAttribute('data-sim-ready') === '1'",
                                    timeout=30000)

    def click_and_wait(self, selector):
        self.page.evaluate("document.documentElement.setAttribute('data-sim-ready', '0')")
        self.page.click(selector)
        self.ready()

    def state(self, expr):
        return self.page.evaluate("() => PL.current.game.state." + expr)

    # ---------------------------------------------------------------- tests
    def test_from_the_home_page_to_the_hall(self):
        self.open("#/")
        self.click_and_wait("[data-testid=game-cta]")
        self.assertIn("Bounce Factory", self.page.inner_text("[data-hall=bounce]"))
        self.click_and_wait("[data-hall=bounce]")
        self.assertEqual(self.page.locator("[data-station]").count(), 4)
        self.assertTrue(self.page.is_visible("#stage"))

    def test_every_saved_solution_passes_in_the_page(self):
        for sid, s in SOL.items():
            v = s["variants"][NOM]
            self.open(v["game"])
            self.assertEqual(self.state("focus"), sid)
            self.assertEqual(self.page.evaluate("() => PL.current.game.state.knobs['%s']" % sid), v["solution"])
            self.click_and_wait("[data-testid=test-station]")
            verdict = self.page.inner_text("[data-result='%s'] .gverdict" % sid)
            self.assertTrue(verdict.startswith("✓"), (sid, verdict))

    def test_the_settings_and_run_buttons_sit_under_the_stage(self):
        self.open("#/game/bounce/1.1?practice=1")
        self.assertEqual(self.page.locator(".playrow").count(), 0)               # no run/reset play bar here
        stage = self.page.locator("#stage").bounding_box()
        dock = self.page.locator("[data-testid=game-dock]").bounding_box()
        self.assertGreaterEqual(dock["y"], stage["y"] + stage["height"])           # below the canvas...
        self.assertLess(abs(dock["x"] - stage["x"]), 2)                            # ...in the same column
        for sel in ('[data-knob="1.1.hatch"]', '[data-knob="1.1.pad"]', "[data-testid=test-station]",
                    "[data-testid=run-machine]", "[data-testid=predict-value]"):
            self.assertEqual(self.page.locator("[data-testid=game-dock] " + sel).count() > 0, True, sel)
        self.assertEqual(self.page.locator(".gpanel [data-knob]").count(), 0)     # not in the left panel any more
        self.assertTrue(self.page.is_visible(".gplaybar .seg-btn:has-text('2×')"))  # speed and camera stay
        self.assertTrue(self.page.is_visible("[data-testid=camera-hall]"))
        self.page.click(".gplaybar .seg-btn:has-text('2×')")
        self.assertEqual(self.page.evaluate("PL.current.game.player.speedAt(0)"), 2)
        self.click_and_wait("[data-testid=test-station]")                         # a run plays on its own
        self.page.wait_for_timeout(400)
        self.assertGreater(self.page.evaluate("PL.current.game.player.simT"), 0)
        self.open("#/motion")                                                      # the experiment pages keep theirs
        self.assertEqual(self.page.locator(".playrow").count(), 1)

    def test_a_wrong_setting_fails(self):
        self.open("#/game/bounce/1.2?practice=1")
        self.click_and_wait("[data-testid=test-station]")                       # the default: no salt
        self.assertTrue(self.page.inner_text("[data-result='1.2'] .gverdict").startswith("✗"))
        self.assertIn("sank", self.page.inner_text("[data-result='1.2']"))

    def test_knob_controls_slider_number_box_chips_and_url(self):
        self.open("#/game/bounce/1.1?practice=1")
        self.page.evaluate("""() => { const r = document.querySelector('[data-knob="1.1.hatch"]');
                                    r.value = 3.15; r.dispatchEvent(new Event('input')); }""")
        self.assertEqual(self.state("knobs['1.1'].hatch"), 3.15)
        self.assertEqual(self.page.input_value('[data-knob-input="1.1.hatch"]'), "3.15")
        self.page.fill('[data-knob-input="1.1.hatch"]', "2.73")
        self.page.dispatch_event('[data-knob-input="1.1.hatch"]', "change")
        self.assertEqual(self.state("knobs['1.1'].hatch"), 2.75)                 # snapped to the 0.05 grid
        self.page.fill('[data-knob-input="1.1.hatch"]', "99")
        self.page.dispatch_event('[data-knob-input="1.1.hatch"]', "change")
        self.assertEqual(self.state("knobs['1.1'].hatch"), 4.0)                  # clamped to the slider's range
        self.page.click('[data-knob="1.1.pad"][data-id="steel_plate"]')
        self.assertEqual(self.state("knobs['1.1'].pad"), "steel_plate")
        url = self.page.evaluate("location.hash")
        self.assertIn("practice=1", url)
        self.assertEqual(self.page.evaluate("() => PL.game.route(location.hash).knobs"),
                         {"hatch": 4.0, "pad": "steel_plate"})                   # the URL follows the knobs

    def test_stage_handles_drag_the_knobs(self):
        self.open("#/game/bounce/1.1?practice=1")
        handle = self.page.evaluate("""() => {
            const st = PL.current.game.stage, p = PL.current.game.player; p.redraw();
            const h = st.handles.filter(h => h.key === '1.1.hatch')[0];
            const r = st.canvas.getBoundingClientRect();
            return {x: r.left + h.x * r.width / st.w, y: r.top + h.y * r.height / st.h};
        }""")
        before = self.state("knobs['1.1'].hatch")
        self.page.mouse.move(handle["x"], handle["y"])
        self.page.mouse.down()
        self.page.mouse.move(handle["x"], handle["y"] - 60, steps=6)             # drag it up
        self.page.mouse.up()
        after = self.state("knobs['1.1'].hatch")
        self.assertGreater(after, before)
        self.assertAlmostEqual(round(after / 0.05) * 0.05, after, places=6)      # on the grid
        # the salt canal's + handle is a click
        self.page.evaluate("PL.current.game.select('1.2')")
        plus = self.page.evaluate("""() => {
            const st = PL.current.game.stage; PL.current.game.player.redraw();
            const h = st.handles.filter(h => h.key === '1.2.bags1')[0];
            const r = st.canvas.getBoundingClientRect();
            return {x: r.left + h.x * r.width / st.w, y: r.top + h.y * r.height / st.h};
        }""")
        self.page.mouse.click(plus["x"], plus["y"])
        self.assertEqual(self.state("knobs['1.2'].bags"), 1)

    def test_the_whole_machine_and_the_lab_links(self):
        self.open("#/game/bounce/1.1?practice=1")
        for sid, s in SOL.items():
            for k, v in s["variants"][NOM]["solution"].items():
                self.page.evaluate("([s, k, v]) => PL.current.game.setKnob(s, k, v)", [sid, k, v])
        self.click_and_wait("[data-testid=run-machine]")
        self.assertIn("whole machine ran from A to B", self.page.inner_text(".gdebrief"))
        routes = self.page.eval_on_selector_all("[data-lab]", "els => els.map(e => e.getAttribute('href'))")
        self.assertGreaterEqual(len(routes), 5)
        for route in routes:
            self.open(route)
            self.assertTrue(self.page.is_visible("#stage"), route)


    # ---------------------------------------------------------------- round 2: camera, share, navigation, scores
    def test_follow_camera_travels_with_the_ball(self):
        self.open("#/game/bounce/1.1?practice=1")
        self.assertEqual(self.state("camera"), "follow")                          # the default
        for sid, s in SOL.items():
            for k, v in s["variants"][NOM]["solution"].items():
                self.page.evaluate("([s, k, v]) => PL.current.game.setKnob(s, k, v)", [sid, k, v])
        self.page.evaluate("PL.current.game.select('1.1')")
        self.click_and_wait("[data-testid=run-machine]")
        x0 = self.page.evaluate("PL.current.game.stage.cam.cx")
        self.page.wait_for_timeout(3500)
        x1 = self.page.evaluate("PL.current.game.stage.cam.cx")
        self.assertGreater(x1, x0 + 1.0)                                          # it moved along with the ball
        self.page.click("[data-testid=camera-hall]")
        self.assertEqual(self.state("camera"), "hall")
        self.page.click("[data-testid=camera-station]")
        self.assertEqual(self.state("camera"), "station")

    def test_share_box_copies_a_link_that_reopens_this_setup(self):
        ctx = self.browser.new_context(permissions=["clipboard-read", "clipboard-write"],
                                       viewport={"width": 1400, "height": 1000})
        page = ctx.new_page()
        page.on("pageerror", lambda e: self.errors.append(str(e)))
        try:
            page.goto("http://127.0.0.1:%d/#/game/bounce/1.3?practice=1&v=4" % self.port)
            page.wait_for_function("document.documentElement.getAttribute('data-sim-ready') === '1'")
            page.evaluate("PL.current.game.setKnob('1.3', 'hump', 1.17)")
            page.click("[data-testid=copy-link]")
            page.wait_for_function("document.querySelector('[data-testid=copy-status]').textContent.length > 0")
            self.assertIn("Copied", page.inner_text("[data-testid=copy-status]"))
            url = page.input_value("[data-testid=share-url]")
            self.assertEqual(page.evaluate("navigator.clipboard.readText()"), url)
            for part in ("#/game/bounce/1.3", "practice=1", "v=4"):
                self.assertIn(part, url)
            page.goto("about:blank")                                              # open it fresh
            page.goto(url)
            page.wait_for_function("document.documentElement.getAttribute('data-sim-ready') === '1'")
            self.assertEqual(page.evaluate("PL.current.game.state.knobs['1.3'].hump"), 1.17)
            self.assertEqual(page.evaluate("PL.current.game.state.stations['1.3'].fact_values.h0"), 1.6)  # same numbers
        finally:
            ctx.close()

    def test_copy_falls_back_when_the_clipboard_is_not_allowed(self):
        self.open("#/game/bounce/1.1?practice=1")
        self.page.evaluate("Object.defineProperty(navigator, 'clipboard', {value: undefined, configurable: true})")
        self.page.click("[data-testid=copy-link]")
        self.page.wait_for_function("document.querySelector('[data-testid=copy-status]').textContent.length > 0")
        self.assertTrue(self.page.evaluate("document.activeElement.getAttribute('data-testid')") == "share-url")

    def test_practice_mode_and_back_to_the_player(self):
        self.open("#/game")
        pid = self.page.evaluate("""async () => { const r = await fetch('/api/quiz/player', {method: 'POST',
            headers: {'Content-Type': 'application/json'}, body: JSON.stringify({name: 'Pia'})}).then(r => r.json());
            localStorage.setItem('physlab.player', r.player.id); return r.player.id; }""")
        self.open("#/game/bounce/1.1")
        self.assertFalse(self.state("practice"))
        self.page.evaluate("PL.current.game.setKnob('1.1', 'hatch', 3.3)")
        self.click_and_wait("[data-testid=open-practice]")
        self.assertTrue(self.state("practice"))
        self.assertEqual(self.state("knobs['1.1'].hatch"), 3.3)                    # the settings came along
        self.assertIn("Pia", self.page.inner_text("[data-testid=leave-practice]"))
        self.click_and_wait("[data-testid=leave-practice]")
        self.assertFalse(self.state("practice"))
        self.assertEqual(self.state("player.id"), pid)

    def test_lab_round_trip_keeps_every_setting(self):
        self.open("#/game/bounce/1.1?practice=1")
        self.page.evaluate("PL.current.game.setKnob('1.3', 'hump', 1.05)")         # another station's setting
        self.page.evaluate("PL.current.game.setKnob('1.1', 'pad', 'steel_plate')")
        self.page.evaluate("PL.current.game.setKnob('1.1', 'hatch', 2.7)")
        self.click_and_wait("[data-testid=test-station]")
        self.assertTrue(self.page.inner_text("[data-score='1.1']").startswith("🏆"))
        self.page.click("[data-lab='1.1']")
        self.ready()
        self.assertTrue(self.page.is_visible("[data-testid=return-to-game]"))
        self.assertIn("1.1 Bounce Flap", self.page.inner_text("[data-testid=return-to-game]"))
        self.page.evaluate("document.documentElement.setAttribute('data-sim-ready', '0')")
        self.page.click("[data-testid=return-to-game]")
        self.ready()
        self.assertEqual(self.state("focus"), "1.1")
        self.assertEqual(self.state("knobs['1.1'].hatch"), 2.7)
        self.assertEqual(self.state("knobs['1.3'].hump"), 1.05)                    # remembered for this tab

    def test_switching_station_after_a_run(self):
        """regression: picking another station after a run used to throw in the scene"""
        self.open("#/game/bounce/1.1?practice=1")
        self.click_and_wait("[data-testid=test-station]")
        self.page.click("[data-station='1.3']")
        self.page.wait_for_timeout(300)
        self.assertEqual(self.state("focus"), "1.3")
        self.click_and_wait("[data-testid=test-station]")
        self.page.click("[data-station='1.1']")
        self.page.click("[data-testid=camera-hall]")
        self.page.wait_for_timeout(300)
        self.assertEqual(self.state("focus"), "1.1")

    def test_the_map_shows_the_locked_next_hall(self):
        self.locks(True)
        self.open("#/game")
        self.assertEqual(self.page.get_attribute("[data-hall=bounce]", "data-state"), "open")
        self.assertEqual(self.page.get_attribute("[data-hall=foundry]", "data-state"), "locked")
        self.assertIn("Clear every station of The Bounce Factory", self.page.inner_text("[data-hall=foundry]"))


    # ---------------------------------------------------------------- Hall 2: the Foundry
    def handle_point(self, key):
        return self.page.evaluate("""key => {
            const st = PL.current.game.stage; PL.current.game.player.redraw();
            const h = st.handles.filter(h => h.key === key)[0];
            if (!h) return null;
            const r = st.canvas.getBoundingClientRect();
            return {x: r.left + h.x * r.width / st.w, y: r.top + h.y * r.height / st.h};
        }""", key)

    def drag(self, key, dx, dy):
        p = self.handle_point(key)
        self.assertIsNotNone(p, key)
        self.page.mouse.move(p["x"], p["y"])
        self.page.mouse.down()
        self.page.mouse.move(p["x"] + dx, p["y"] + dy, steps=6)
        self.page.mouse.up()

    def test_foundry_every_saved_setting_passes_in_the_page(self):
        for sid, s in SOL2.items():
            v = s["variants"][NOM]
            for link, key, want in (("game", "solution", None), ("game_mastery", "mastery_solution", "mastery"),
                                    ("game_best", "score_solution", "best")):
                self.open(v[link])
                self.assertEqual(self.state("focus"), sid)
                self.assertEqual(self.page.evaluate("() => PL.current.game.state.knobs['%s']" % sid), v[key])
                self.click_and_wait("[data-testid=test-station]")
                verdict = self.page.inner_text("[data-result='%s'] .gverdict" % sid)
                self.assertTrue(verdict.startswith("✓"), (sid, link, verdict))
                res = self.page.evaluate("PL.current.game.lastResult.stations[0]")
                if want == "mastery":
                    self.assertTrue(res["mastery"], (sid, link))
                if want == "best":
                    self.assertEqual(res["score"], v["best_score"], (sid, link))

    def test_foundry_wrong_settings_fail_with_the_reason(self):
        for sid, knobs, words in (("2.1", None, "BALL"), ("2.2", None, "too weak"), ("2.3", None, "only rose"),
                                  ("2.4", {"length": 0.6, "angle": 78}, "lost its grip")):
            self.open("#/game/foundry/%s?practice=1" % sid)
            for k, v in (knobs or {}).items():
                self.page.evaluate("([s, k, v]) => PL.current.game.setKnob(s, k, v)", [sid, k, v])
            self.click_and_wait("[data-testid=test-station]")
            self.assertTrue(self.page.inner_text("[data-result='%s'] .gverdict" % sid).startswith("✗"), sid)
            self.assertIn(words, self.page.inner_text("[data-result='%s']" % sid))

    def test_foundry_handles_move_every_knob(self):
        self.open("#/game/foundry/2.1?practice=1")
        self.page.evaluate("PL.current.game.camera('station')")
        w0 = self.state("knobs['2.1'].water")
        self.drag("2.1.water", 0, -60)                                            # the gauge: up = more water
        self.assertGreater(self.state("knobs['2.1'].water"), w0)
        p = self.handle_point("2.1.target")
        self.page.mouse.click(p["x"], p["y"])                                     # ball -> both
        self.assertEqual(self.state("knobs['2.1'].target"), "both")
        self.page.mouse.click(p["x"], p["y"])                                     # both -> ring
        self.assertEqual(self.state("knobs['2.1'].target"), "ring")

        self.page.evaluate("PL.current.game.select('2.2')")
        self.page.evaluate("PL.current.game.camera('station')")
        p = self.handle_point("2.2.battery")
        self.page.mouse.click(p["x"], p["y"])                                     # AA -> lantern
        self.assertEqual(self.state("knobs['2.2'].battery"), "lantern")
        self.drag("2.2.R", 25, -45)                                               # turn the dial clockwise
        r = self.state("knobs['2.2'].R")
        self.assertGreater(r, 0)
        self.assertAlmostEqual(round(r * 2) / 2, r, places=6)                     # on the 0.5 ohm grid

        self.page.evaluate("PL.current.game.select('2.3')")
        self.page.evaluate("PL.current.game.camera('station')")
        d0 = self.state("knobs['2.3'].d2")
        self.drag("2.3.d2", -40, 0)                                               # narrower big piston
        self.assertLess(self.state("knobs['2.3'].d2"), d0)

        self.page.evaluate("PL.current.game.select('2.4')")
        self.page.evaluate("PL.current.game.camera('station')")
        l0, a0 = self.state("knobs['2.4'].length"), self.state("knobs['2.4'].angle")
        self.drag("2.4.length", 0, -40)                                           # pivot up = longer cable
        self.assertGreater(self.state("knobs['2.4'].length"), l0)
        self.drag("2.4.angle", -40, -40)                                          # further out = bigger angle
        self.assertGreater(self.state("knobs['2.4'].angle"), a0)

    def test_foundry_machine_time_lapse_and_lab_links(self):
        self.open("#/game/foundry/2.1?practice=1")
        for sid, s in SOL2.items():
            for k, v in s["variants"][NOM]["solution"].items():
                self.page.evaluate("([s, k, v]) => PL.current.game.setKnob(s, k, v)", [sid, k, v])
        self.page.evaluate("PL.current.game.select('2.1')")
        self.click_and_wait("[data-testid=run-machine]")
        self.assertIn("whole machine ran from A to B", self.page.inner_text(".gdebrief"))
        z = self.page.evaluate("PL.current.game.lastResult.timelapse")
        self.assertEqual(len(z), 1)
        speed = self.page.evaluate("t => PL.current.game.player.speedAt(t)", (z[0][0] + z[0][1]) / 2)
        self.assertAlmostEqual(speed, z[0][2], places=6)                          # the heating plays fast...
        self.assertEqual(self.page.evaluate("t => PL.current.game.player.speedAt(t)", z[0][1] + 1), 1)   # ...the rest not
        self.page.wait_for_timeout(1200)
        self.assertGreater(self.page.evaluate("PL.current.game.player.simT"), 5.0)  # 1 s of watching = many s of heating
        routes = self.page.eval_on_selector_all("[data-lab]", "els => els.map(e => e.getAttribute('href'))")
        self.assertEqual(sorted(r.split("?")[0] for r in routes), ["#/circuits", "#/heat", "#/pendulum", "#/pressure"])
        for route in routes:
            self.open(route)
            self.assertTrue(self.page.is_visible("#stage"), route)

    def test_foundry_opens_on_the_map_once_the_bounce_factory_is_cleared(self):
        self.locks(True)
        self.open("#/game")
        pid = self.page.evaluate("""async () => { const r = await fetch('/api/quiz/player', {method: 'POST',
            headers: {'Content-Type': 'application/json'}, body: JSON.stringify({name: 'Tesla'})}).then(r => r.json());
            localStorage.setItem('physlab.player', r.player.id); return r.player.id; }""")
        from physlab.game import common as C
        steps = C.variant_steps(BF.HALL, pid)
        for sid in ("1.1", "1.2", "1.3", "1.4"):
            out = self.page.evaluate("""b => fetch('/api/game/run', {method: 'POST', headers: {'Content-Type':
                'application/json'}, body: JSON.stringify(b)}).then(r => r.json())""",
                {"player": pid, "hall": "bounce", "station": sid, "mode": "test",
                 "knobs": {sid: SOL[sid]["variants"][steps[sid]]["solution"]}})
            self.assertTrue(out["ok"], sid)
        self.page.reload()                                                        # the map, fresh
        self.ready()
        self.assertEqual(self.page.get_attribute("[data-hall=foundry]", "data-state"), "open")
        self.assertTrue(self.page.evaluate("document.querySelector('[data-hall=foundry] img').naturalWidth > 0"))
        self.click_and_wait("[data-hall=foundry]")
        self.assertEqual(self.page.locator("[data-station]").count(), 4)
        self.assertFalse(self.state("practice"))
        self.assertEqual(self.state("focus"), "2.1")
        self.assertEqual(self.page.get_attribute("[data-station='2.2']", "class").count("locked"), 1)


    # ---------------------------------------------------------------- Hall 3: Millbrook Mill
    def test_test_mode_every_hall_is_open_on_the_map(self):
        self.open("#/game")
        self.assertTrue(self.page.is_visible("[data-testid=test-mode]"))
        for h in ("bounce", "foundry", "mill"):
            self.assertEqual(self.page.get_attribute("[data-hall=%s]" % h, "data-state"), "open", h)
        self.assertTrue(self.page.evaluate("document.querySelector('[data-hall=mill] img').naturalWidth > 0"))
        self.page.evaluate("""async () => { const r = await fetch('/api/quiz/player', {method: 'POST',
            headers: {'Content-Type': 'application/json'}, body: JSON.stringify({name: 'Ada'})}).then(r => r.json());
            localStorage.setItem('physlab.player', r.player.id); }""")
        self.page.reload()
        self.ready()
        self.click_and_wait("[data-hall=mill]")                                  # a brand-new player, straight in
        self.assertFalse(self.state("practice"))
        self.assertEqual(self.page.locator("[data-station].locked").count(), 0)   # every station open
        self.page.click("[data-station='3.4']")
        self.assertEqual(self.state("focus"), "3.4")

    def test_mill_every_saved_setting_passes_in_the_page(self):
        for sid, s in SOL3.items():
            v = s["variants"][NOM]
            for link, key, want in (("game", "solution", None), ("game_mastery", "mastery_solution", "mastery"),
                                    ("game_best", "score_solution", "best")):
                self.open(v[link])
                self.assertEqual(self.state("focus"), sid)
                self.assertEqual(self.page.evaluate("() => PL.current.game.state.knobs['%s']" % sid), v[key])
                self.click_and_wait("[data-testid=test-station]")
                verdict = self.page.inner_text("[data-result='%s'] .gverdict" % sid)
                self.assertTrue(verdict.startswith("✓"), (sid, link, verdict))
                res = self.page.evaluate("PL.current.game.lastResult.stations[0]")
                if want == "mastery":
                    self.assertTrue(res["mastery"], (sid, link))
                if want == "best":
                    self.assertEqual(res["score"], 1000, (sid, link))

    def test_mill_wrong_settings_fail_with_the_reason(self):
        for sid, knobs, words in (("3.1", None, "floats at"), ("3.2", None, "Splash"), ("3.3", None, "in front of"),
                                  ("3.4", None, "budge"), ("3.4", {"hook": 1.0, "water": 2.0}, "Flung")):
            self.open("#/game/mill/%s?practice=1" % sid)
            for k, v in (knobs or {}).items():
                self.page.evaluate("([s, k, v]) => PL.current.game.setKnob(s, k, v)", [sid, k, v])
            self.click_and_wait("[data-testid=test-station]")
            self.assertTrue(self.page.inner_text("[data-result='%s'] .gverdict" % sid).startswith("✗"), sid)
            self.assertIn(words, self.page.inner_text("[data-result='%s']" % sid))

    def test_mill_handles_move_every_knob(self):
        self.open("#/game/mill/3.1?practice=1")
        self.page.evaluate("PL.current.game.camera('station')")
        for _ in range(3):
            p = self.handle_point("3.1.count1")
            self.page.mouse.click(p["x"], p["y"])                                 # + three times
        p = self.handle_point("3.1.count-1")
        self.page.mouse.click(p["x"], p["y"])                                     # − once
        self.assertEqual(self.state("knobs['3.1'].count"), 2)
        p = self.handle_point("3.1.item")
        self.page.mouse.click(p["x"], p["y"])                                     # pine blocks -> stones
        self.assertEqual(self.state("knobs['3.1'].item"), "stone")

        self.page.evaluate("PL.current.game.select('3.2')")
        self.page.evaluate("PL.current.game.camera('station')")
        self.drag("3.2.wind", 0, -50)                                             # the fan gauge: up = more wind
        w = self.state("knobs['3.2'].wind")
        self.assertGreater(w, 0)
        self.assertEqual(round(w * 2) / 2, w)                                     # on the 0.5 m/s grid

        self.page.evaluate("PL.current.game.select('3.3')")
        self.page.evaluate("PL.current.game.camera('station')")
        d0 = self.state("knobs['3.3'].d_o")
        self.drag("3.3.d_o", 0, 40)                                               # lens down = further from the lamp
        self.assertGreater(self.state("knobs['3.3'].d_o"), d0)

        self.page.evaluate("PL.current.game.select('3.4')")
        self.page.evaluate("PL.current.game.camera('station')")
        b0 = self.state("knobs['3.4'].hook")
        self.drag("3.4.hook", 60, 0)                                              # hook further out
        self.assertGreater(self.state("knobs['3.4'].hook"), b0)
        self.drag("3.4.water", 0, -60)                                            # fill the jug
        self.assertGreater(self.state("knobs['3.4'].water"), 0)

    def test_mill_machine_and_lab_links(self):
        self.open("#/game/mill/3.1?practice=1")
        for sid, s in SOL3.items():
            for k, v in s["variants"][NOM]["solution"].items():
                self.page.evaluate("([s, k, v]) => PL.current.game.setKnob(s, k, v)", [sid, k, v])
        self.page.evaluate("PL.current.game.select('3.1')")
        self.click_and_wait("[data-testid=run-machine]")
        self.assertIn("whole machine ran from A to B", self.page.inner_text(".gdebrief"))
        routes = self.page.eval_on_selector_all("[data-lab]", "els => els.map(e => e.getAttribute('href'))")
        self.assertEqual(sorted(r.split("?")[0] for r in routes), ["#/buoyancy", "#/levers", "#/motion", "#/optics"])
        for route in routes:
            self.open(route)
            self.assertTrue(self.page.is_visible("#stage"), route)


if __name__ == "__main__":
    unittest.main()
