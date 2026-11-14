import json

from app.arcs import TABLE, lookup

T = json.loads(TABLE.read_text())


def test_arc_boundaries():
    assert lookup(T, 1)[:2] == ("East Blue Saga", "Romance Dawn Arc")
    assert lookup(T, 7)[1] == "Romance Dawn Arc" and lookup(T, 8)[1] == "Orange Town Arc"
    assert lookup(T, 100)[0] == "East Blue Saga" and lookup(T, 101)[0] == "Arabasta Saga"


def test_outside_every_range():
    assert lookup(T, 0) is None
    last = T["sagas"][-1]["arcs"][-1]
    assert last["end"] is None and lookup(T, last["start"] + 5000)[1] == last["name"]  # ongoing arc is open-ended


def test_timeskip_boundary():
    assert T["timeskip_first_chapter"] == 598
    assert lookup(T, 597)[2] == "pre" and lookup(T, 598)[2] == "post"
    assert lookup(T, 597)[1] == "Post-War Arc" and lookup(T, 598)[1] == "Return to Sabaody Arc"


def test_ranges_are_contiguous():
    arcs = [a for s in T["sagas"] for a in s["arcs"]]
    for a, b in zip(arcs, arcs[1:]):
        assert b["start"] == a["end"] + 1
