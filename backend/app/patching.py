"""Patch layer: data / schema corrections applied to the upstream graph WITHOUT touching the upstream files.

Patches live in ontology/patches/<name>.remove.ttl (triples removed) + <name>.add.ttl (triples added); every file explains why.
  debut          generated here  - single-valued debut properties (below)
  uri-reconcile  generated here  - links to untyped URIs that differ only by punctuation from a real Character (Monkey_D._Luffy)
  schema-increw  hand-written    - swapped domain/range of op:inCrew

Finding (debut) (see docs/ONTOLOGY_AUDIT.md): op:mangaDebut / op:animeDebut are declared owl:FunctionalProperty, which is the right
model ("first appearance" is unique), but 23 characters carry two values - the second one is a LATER appearance
mis-recorded as a debut.  We keep the axiom and fix the data: the value that matches the processed source JSON stays as the
debut, the other one is demoted to opx:laterMangaAppearance / opx:laterAnimeAppearance.

    python -m app.patching --upstream ontology-src        # (re)generate the generated patches and print every decision
"""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from rdflib import Graph, Literal, RDF, OWL, URIRef

from . import config
from .ontology import OP, OPX

# functional property -> (processed-JSON field, replacement property for the demoted value)
DEBUT_PROPS = {
    OP.mangaDebut: ("debut_chapter", OPX.laterMangaAppearance),
    OP.animeDebut: ("debut_episode", OPX.laterAnimeAppearance),
}
PATCH_DIR = "ontology/patches"


def functional_conflicts(g: Graph) -> dict[URIRef, dict[URIRef, set]]:
    """{functional property: {subject: {distinct values}}} for every subject with more than one value."""
    out = {}
    for p in set(g.subjects(RDF.type, OWL.FunctionalProperty)):
        vals = defaultdict(set)
        for s, _, o in g.triples((None, p, None)):
            vals[s].add(o)
        bad = {s: v for s, v in vals.items() if len(v) > 1}
        if bad:
            out[p] = bad
    return out


def _num(u) -> int:
    return int(re.search(r"(\d+)$", str(u)).group(1))


def decide(base: Graph, upstream: Path):
    """Return (decisions, remove_graph, add_graph). Each decision explains which value was kept and why."""
    src = {}
    for f in ("full-character-data-processed-2.json",):
        for it in json.load(open(upstream / "data/processed" / f)):
            if isinstance(it, dict) and it.get("source_name"):
                src[it["source_name"]] = it
    decisions, rm, add = [], Graph(), Graph()
    for p, bad in functional_conflicts(base).items():
        if p not in DEBUT_PROPS:
            continue
        field, later = DEBUT_PROPS[p]
        for s, vals in sorted(bad.items()):
            local = str(s).rsplit("#", 1)[-1]
            raw = (src.get(local) or {}).get(field)
            wanted = OP[raw.replace(" ", "_")] if raw else None
            if wanted in vals:
                keep, why = wanted, "matches processed source JSON"
            else:
                keep, why = min(vals, key=_num), "no matching source value: kept the earliest (flagged for review)"
            for v in sorted(vals - {keep}, key=str):
                rm.add((s, p, v))
                add.add((s, later, v))
            decisions.append({"subject": local, "property": str(p).rsplit("#", 1)[-1], "values": sorted(str(v).rsplit("#", 1)[-1] for v in vals),
                              "kept": str(keep).rsplit("#", 1)[-1], "json": raw, "reason": why})
    return decisions, rm, add


def uri_reconcile(base: Graph):
    """Links whose object is an UNTYPED '#'-namespace URI that equals exactly one typed Character after dropping punctuation/case."""
    norm = lambda u: re.sub(r"[^a-z0-9]", "", str(u).rsplit("#", 1)[-1].lower())
    chars = defaultdict(list)
    for c in base.subjects(RDF.type, OP.Character):
        chars[norm(c)].append(c)
    typed = set(base.subjects(RDF.type, None))
    decisions, rm, add = [], Graph(), Graph()
    for s, p, o in base:
        if p == RDF.type or not isinstance(o, URIRef) or not str(o).startswith(config.OP) or o in typed:
            continue
        twins = chars.get(norm(o), [])
        if len(twins) == 1 and twins[0] != o:
            rm.add((s, p, o)); add.add((s, p, twins[0]))
            decisions.append({"subject": str(s).rsplit("#", 1)[-1], "property": str(p).rsplit("#", 1)[-1],
                              "from": str(o).rsplit("#", 1)[-1], "to": str(twins[0]).rsplit("#", 1)[-1]})
    return decisions, rm, add


def write_patch(name: str, rm: Graph, add: Graph, why: str):
    for g, kind, head in ((rm, "remove", "triples REMOVED from the upstream data before reasoning/import"),
                          (add, "add", "triples ADDED in their place")):
        g.bind("op", OP); g.bind("opx", OPX)
        path = config.ROOT / PATCH_DIR / f"{name}.{kind}.ttl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# Patch '{name}' ({head}). Generated by `python -m app.patching`; upstream files in ontology-src/ are never modified.\n# {why}\n"
                        + g.serialize(format="turtle"))


def load_patch() -> tuple[Graph, Graph]:
    """Union of every ontology/patches/*.remove.ttl / *.add.ttl."""
    rm, add = Graph(), Graph()
    if not config.APPLY_PATCHES:
        return rm, add
    for f in sorted((config.ROOT / PATCH_DIR).glob("*.remove.ttl")):
        rm.parse(str(f), format="turtle")
    for f in sorted((config.ROOT / PATCH_DIR).glob("*.add.ttl")):
        add.parse(str(f), format="turtle")
    return rm, add


if __name__ == "__main__":
    from .ontology import load_upstream
    ap = argparse.ArgumentParser()
    ap.add_argument("--upstream", default="ontology-src")
    a = ap.parse_args()
    up = load_upstream()
    decisions, rm, add = decide(up, Path(a.upstream))
    for d in decisions:
        print(f"{d['subject']:<22}{d['property']:<12}{d['values']}  keep={d['kept']:<14} json={d['json']}  ({d['reason']})")
    write_patch("debut", rm, add, "op:mangaDebut/animeDebut are functional; the 2nd value is a later appearance -> opx:later*Appearance.")
    print(f"\n[debut] {len(decisions)} conflicting subjects, {len(rm)} triples demoted")
    ud, urm, uadd = uri_reconcile(up)
    for d in ud:
        print(f"[uri] {d['subject']} {d['property']}: {d['from']} -> {d['to']}")
    write_patch("uri-reconcile", urm, uadd, "Object URIs that differ from a real Character only by punctuation (e.g. Monkey_D._Luffy vs Monkey_D_Luffy) re-pointed to it.")
    print(f"[uri-reconcile] {len(ud)} links re-pointed")
