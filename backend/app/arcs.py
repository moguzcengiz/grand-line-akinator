"""Story time: chapter -> arc -> saga -> pre/post-timeskip, and the patch that gives every debut chapter those values.

The table (ontology/story-arcs.json) is parsed from the One Piece Fandom wiki ("Story Arcs" page; "Timeskip" page for the boundary);
the raw API responses are cached under work/source-cache/wiki-arcs/.  Nothing is written from memory.

    python -m app.arcs            # table + patches -> ontology/patches/debut-arc.add.ttl
    python -m app.arcs --fetch    # first re-download the wiki pages (max 1 request/s) and rebuild the table
"""
import argparse
import json
import re
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date

from rdflib import Graph, Literal, RDF, RDFS, OWL, URIRef

from . import config
from .ontology import OP, OPX

API = "https://onepiece.fandom.com/api.php"
CACHE = config.ROOT / "work/source-cache/wiki-arcs"
TABLE = config.ROOT / "ontology/story-arcs.json"
PATCH = config.ROOT / "ontology/patches/debut-arc.add.ttl"
PAGES = {"story-arcs.json": "Story_Arcs", "timeskip.json": "Timeskip"}

# debut predicate -> (suffix of the new predicates, domain class); characters: DEBUT_ARC..., fruits: DEVIL_FRUIT_DEBUT_ARC...
DEBUTS = {OP.mangaDebut: ("", OP.Character, "debut"), OP.devilFruitDebutManga: ("devilFruitDebut", OP.DevilFruit, "devil fruit debut")}


def fetch():
    for i, (fn, page) in enumerate(PAGES.items()):
        if i:
            time.sleep(1)
        q = urllib.parse.urlencode({"action": "parse", "page": page, "prop": "wikitext|revid", "format": "json", "formatversion": 2})
        req = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": "Mozilla/5.0 (compatible; research-script)"})
        CACHE.mkdir(parents=True, exist_ok=True)
        (CACHE / fn).write_bytes(urllib.request.urlopen(req, timeout=60).read())


def parse_table() -> dict:
    arcs_p = json.loads((CACHE / "story-arcs.json").read_text())["parse"]
    ts_p = json.loads((CACHE / "timeskip.json").read_text())["parse"]
    text = arcs_p["wikitext"].split("===[[Sea of Survival", 1)[0]          # main story only: no side stories / anime arcs
    sagas = []
    for line in text.splitlines():
        m = re.match(r"===\[\[([^\]|]+ Saga)\]\]===$", line)
        if m:
            sagas.append({"name": m.group(1), "arcs": []})
        m = re.match(r"====\[\[([^\]|]+ Arc)\]\]====$", line)
        if m and sagas:
            sagas[-1]["arcs"].append({"name": m.group(1)})
        m = re.match(r"\*\[\[:Category:.* Chapters\|Chapters\]\]: .*?\((\d+)-(\d*)\)", line)
        if m and sagas and sagas[-1]["arcs"]:
            sagas[-1]["arcs"][-1].update(start=int(m.group(1)), end=int(m.group(2)) if m.group(2) else None)
    m = re.search(r"Chapters\]\] \[\[Chapter (\d+)\|\d+\]\]\W+\[\[Chapter (\d+)\|", ts_p["wikitext"])
    assert m and int(m.group(2)) == int(m.group(1)) + 1, "timeskip boundary not found on the Timeskip page"
    return {"source": {"api": API, "pages": {"Story Arcs": arcs_p["revid"], "Timeskip": ts_p["revid"]},
                       "fetched": date.today().isoformat(),
                       "note": "revision ids of the wiki pages; end=null means the arc is ongoing"},
            "timeskip_first_chapter": int(m.group(2)), "sagas": sagas}


def lookup(table: dict, chapter: int):
    """(saga name, arc name, era) for a chapter number, or None when no arc covers it (chapter 0, a chapter past the open arc...)."""
    for s in table["sagas"]:
        for a in s["arcs"]:
            if a["start"] <= chapter and (a["end"] is None or chapter <= a["end"]):
                return s["name"], a["name"], ("post" if chapter >= table["timeskip_first_chapter"] else "pre")
    return None


def _slug(prefix, name):
    return OPX[prefix + "_" + re.sub(r"[^0-9A-Za-z]+", "_", name).strip("_")]


def build_patch(table: dict, base: Graph) -> tuple[Graph, Counter, list]:
    g = Graph()
    g.bind("op", OP); g.bind("opx", OPX)
    for cls, label in ((OPX.Saga, "Saga"), (OPX.StoryEra, "Story era")):
        g.add((cls, RDF.type, OWL.Class)); g.add((cls, RDFS.label, Literal(label, "en")))
        g.add((OP.Character, OWL.disjointWith, cls)); g.add((OP.DevilFruit, OWL.disjointWith, cls))
    g.add((OP.Arc, RDFS.label, Literal("Story Arc", "en")))
    g.add((OPX.partOfSaga, RDF.type, OWL.ObjectProperty))
    g.add((OPX.partOfSaga, RDFS.domain, OP.Arc)); g.add((OPX.partOfSaga, RDFS.range, OPX.Saga))
    eras = {"pre": _slug("Era", "Pre-timeskip"), "post": _slug("Era", "Post-timeskip")}
    for k, label in (("pre", "Before the timeskip (chapters up to %d)" % (table["timeskip_first_chapter"] - 1)),
                     ("post", "After the timeskip (chapter %d onwards)" % table["timeskip_first_chapter"])):
        g.add((eras[k], RDF.type, OPX.StoryEra)); g.add((eras[k], RDFS.label, Literal(label, "en")))
    g.add((eras["pre"], OWL.differentFrom, eras["post"]))
    nodes = {}
    for s in table["sagas"]:
        sn = _slug("Saga", s["name"])
        g.add((sn, RDF.type, OPX.Saga)); g.add((sn, RDFS.label, Literal(s["name"], "en")))
        for a in s["arcs"]:
            an = _slug("Arc", a["name"])
            rng = f"chapters {a['start']}-{a['end'] or ''}"
            g.add((an, RDF.type, OP.Arc)); g.add((an, RDFS.label, Literal(a["name"], "en")))
            g.add((an, RDFS.comment, Literal(f"{rng} ({s['name']})", "en"))); g.add((an, OPX.partOfSaga, sn))
            nodes[(s["name"], a["name"])] = (an, sn)
    stats, outside = Counter(), []
    for debut, (pre, dom, what) in DEBUTS.items():
        names = {k: (OPX[(pre + v) if pre else v[0].lower() + v[1:]] ) for k, v in
                 (("arc", "Arc"), ("saga", "Saga"), ("era", "Era"))}
        for k, rng_cls in (("arc", OP.Arc), ("saga", OPX.Saga), ("era", OPX.StoryEra)):
            p = OPX[(pre + k.capitalize()) if pre else "debut" + k.capitalize()]
            names[k] = p
            g.add((p, RDF.type, OWL.ObjectProperty)); g.add((p, RDFS.domain, dom)); g.add((p, RDFS.range, rng_cls))
            g.add((p, RDFS.label, Literal(f"{what} {k}", "en")))
        chapters = {}
        for s, _, o in base.triples((None, debut, None)):
            m = re.fullmatch(r"Chapter_(\d+)", str(o).rsplit("#", 1)[-1])
            if m:
                chapters[s] = min(chapters.get(s, 10**9), int(m.group(1)))
            else:
                outside.append((what, str(s).rsplit("#", 1)[-1], str(o).rsplit("#", 1)[-1]))
        for s, ch in sorted(chapters.items()):
            hit = lookup(table, ch)
            if not hit:
                outside.append((what, str(s).rsplit("#", 1)[-1], f"Chapter_{ch}")); continue
            an, sn = nodes[hit[:2]]
            g.add((s, names["arc"], an)); g.add((s, names["saga"], sn)); g.add((s, names["era"], eras[hit[2]]))
            if pre == "":
                stats[hit[0]] += 1
            else:
                stats["fruit:" + hit[0]] += 1
    return g, stats, outside


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    a = ap.parse_args()
    if a.fetch or not (CACHE / "story-arcs.json").exists():
        fetch()
    if a.fetch or not TABLE.exists():
        TABLE.write_text(json.dumps(parse_table(), indent=1, ensure_ascii=False) + "\n")
    from .ontology import load_sources
    base, _ = load_sources()
    table = json.loads(TABLE.read_text())
    g, stats, outside = build_patch(table, base)
    PATCH.write_text("# Patch 'debut-arc' (triples ADDED). Generated by `python -m app.arcs` from ontology/story-arcs.json (One Piece Fandom wiki, "
                     f"Story Arcs rev {table['source']['pages']['Story Arcs']}).\n# Debut chapter -> arc / saga / pre-post timeskip, as named resources.\n"
                     + g.serialize(format="turtle"))
    print(f"{sum(len(s['arcs']) for s in table['sagas'])} arcs, {len(table['sagas'])} sagas, timeskip at chapter {table['timeskip_first_chapter']}")
    for k, v in sorted(stats.items(), key=lambda kv: -kv[1]):
        print(f"{v:5d}  {k}")
    print("outside every range:", outside)
