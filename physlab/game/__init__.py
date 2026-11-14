"""The Machine Works - physlab's game module (docs/game/GDD-machine-works.md).

Halls are data: a list of stations, each with knobs (what the student may
tune), facts (the station card; one of them is the per-student variant), a
goal, a mastery goal, hints and a `run(knobs, facts, thresholds)` that
drives a physlab engine and judges the outcome. Hall 1, the Bounce Factory,
is in bounce_factory.py, Hall 2, the Foundry, in foundry.py, Hall 3,
Millbrook Mill, in mill.py.

Locks: in the classroom, halls (and the stations inside a hall) open one
after another. While the game is being tested everything is open for
everyone - the default. Set PHYSLAB_GAME_LOCKS=on to switch the classroom
order on (read at every request, so it needs no restart).
"""

import os

from . import bounce_factory, foundry, mill

HALLS = [bounce_factory.HALL, foundry.HALL, mill.HALL]
HALL_MODULES = {"bounce": bounce_factory, "foundry": foundry, "mill": mill}
BY_ID = {h["id"]: h for h in HALLS}
STATIONS = {s["id"]: s for h in HALLS for s in h["stations"]}
# halls still to come (GDD): shown on the map, not playable yet (all three are built now)
COMING = []


def locks_on():
    """True: the classroom order (a hall opens when the one before it is cleared, a station when the one
    before it works). False (the default while testing): every hall and station is open."""
    return os.environ.get("PHYSLAB_GAME_LOCKS", "off").strip().lower() in ("1", "on", "true", "yes")


def hall_of(station_id):
    return BY_ID[STATIONS[station_id]["hall"]]
