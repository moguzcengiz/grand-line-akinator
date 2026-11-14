"""RDF -> OWL RL -> Fuseki ingestion.  Run:  python -m app.ingestion

Idempotent: replaces the four named graphs (graph.GRAPHS) deterministically from the ontology files.
Provenance of every edge / type triple = the named graph it is stored in: explicit (upstream data) | curated (our extension/curated
files) | inferred (owlrl).  Per-node game data (name, category, labels, popularity ...) lives in the 'game' graph.
"""
import json
import re
import sys
import time
from collections import Counter

from rdflib import Graph, URIRef, Literal, Namespace, RDF, RDFS, OWL

from . import config, graph
from .ontology import clashes, load_sources, materialize, is_domain_triple, nonreflexive_same_as, tbox, OP, OPX
from .validation import shacl_report

NUMERIC = {"height", "age", "ageAtDeath", "bountyAmount"}
CATEGORY_CLASSES = {"Character", "DevilFruit", "Ship"}
SKIP_LITERAL = {"opwikiurl", "internalID", "dbpediaID", "wikipediaOD"}
META_PREFIX = (str(RDF), str(RDFS), str(OWL))
RUN = "urn:akinator:run:latest"                           # g:report = JSON of the latest ingestion (stored before validation)


def _is_resource(u) -> bool:
    return isinstance(u, URIRef) and (str(u).startswith("http://kalnassag.com/onepiece") or str(u).startswith("http://kalnassag.com/onepiece-ext"))


def _clean_label(label: str) -> str:
    """Scraped labels sometimes join aliases with ';' or start with ';' ("; Seed of Smoke"): use the first non-empty segment."""
    return next((seg.strip() for seg in label.split(";") if seg.strip()), "")


def _name(g: Graph, u: URIRef) -> tuple[str, str | None]:
    en = sorted(c for c in (_clean_label(str(l)) for l in g.objects(u, RDFS.label) if isinstance(l, Literal) and l.language == "en") if c)
    ja = sorted(str(l) for l in g.objects(u, RDFS.label) if isinstance(l, Literal) and l.language == "ja")
    name = en[0] if en else graph.local_name(str(u)).replace("_", " ")
    return name, (ja[0] if ja else None)


def build_model(source_graphs=None):
    """Pure-python part: returns (nodes, edges, types, report). Testable without Fuseki."""
    from .perf import record as perf_record
    t0 = time.perf_counter()
    base, ext = source_graphs if source_graphs is not None else load_sources()
    union = base + ext
    load_s = time.perf_counter() - t0
    perf_record("rdf_load", load_s, base_triples=len(base), extension_triples=len(ext))
    t0 = time.perf_counter()
    inferred, unresolved = materialize(union)
    owlrl_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    merged = nonreflexive_same_as(inferred)
    contradictions = clashes(inferred)
    integrity_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    shacl = shacl_report(union)
    shacl_s = time.perf_counter() - t0
    reasoning_s = round(owlrl_s + integrity_s + shacl_s, 1)
    inferred_dom = Graph()
    for t in inferred:
        if is_domain_triple(t):
            inferred_dom.add(t)

    full = union + inferred_dom
    nodes: dict[str, dict] = {}

    def node(u: URIRef) -> dict:
        k = str(u)
        if k not in nodes:
            name, ja = _name(full, u)
            nodes[k] = {"uri": k, "local": graph.local_name(k), "name": name, "explicit_types": set(), "inferred_types": set(), "props": {}}
            if ja:
                nodes[k]["props"]["name_ja"] = ja
            m = re.fullmatch(r"(Chapter|Episode)_(\d+)", nodes[k]["local"])
            if m:
                nodes[k]["props"]["number"] = int(m.group(2))
        return nodes[k]

    edges: dict[tuple, dict] = {}
    prov_of = lambda t: "explicit" if t in base else ("curated" if t in ext else "inferred")

    for t in full:
        s, p, o = t
        if not _is_resource(s):
            continue
        pl = graph.local_name(str(p))
        if p == RDF.type:
            if _is_resource(o):
                n = node(s)
                (n["inferred_types"] if prov_of(t) == "inferred" else n["explicit_types"]).add(graph.label_name(str(o)))
            continue
        if str(p).startswith(META_PREFIX) or str(p) == "http://www.w3.org/2004/02/skos/core#altLabel" and False:
            continue
        if isinstance(o, Literal):
            if pl in SKIP_LITERAL:
                continue
            n = node(s)
            n["props"].setdefault(pl, []).append(o.toPython() if pl in NUMERIC else str(o))
        elif _is_resource(o):
            node(s), node(o)
            key = (str(s), graph.rel_type(str(p)), str(o))
            cur = edges.get(key)
            prov = prov_of(t)
            if cur is None or (cur["provenance"] == "inferred" and prov != "inferred"):
                edges[key] = {"s": str(s), "t": graph.rel_type(str(p)), "o": str(o), "predicate": str(p), "provenance": prov}
    types = [{"s": str(s), "class": str(o), "provenance": prov_of((s, p, o))} for s, p, o in full.triples((None, RDF.type, None))
             if _is_resource(s) and _is_resource(o)]

    for n in nodes.values():
        for k, v in list(n["props"].items()):
            if isinstance(v, list):
                if k in NUMERIC:
                    n["props"][k] = max(v)
                else:
                    n["props"][k] = v[0] if len(v) == 1 else sorted(set(map(str, v)))
        n["category"] = next((c for c in ("Ship", "DevilFruit", "Character") if c in n["explicit_types"]), None)
        n["labels"] = sorted(((n["explicit_types"] | n["inferred_types"]) - (CATEGORY_CLASSES - n["explicit_types"])) | {"Resource"})
    # closed-world marker for Haki facts: only characters with curated Haki edges have a known Haki profile
    haki_known = {e["s"] for e in edges.values() if e["t"] == "HAS_HAKI"}
    for u in haki_known:
        nodes[u]["props"]["haki_known"] = True
    add_popularity(nodes, edges.values())

    perf_record("owlrl", owlrl_s, input_triples=len(union), inferred_triples=len(inferred))
    perf_record("graph_integrity", integrity_s, same_as_conflicts=len(merged), clashes=len(contradictions))
    perf_record("shacl", shacl_s, violations=shacl["violations"], warnings=shacl["warnings"])
    report = {
        "source_triples": {"base": len(base), "extension": len(ext)},
        "inferred_triples_total": len(inferred),
        "inferred_triples_domain": len(inferred_dom),
        "reasoning_seconds": reasoning_s,
        "stage_seconds": {"rdf_load": round(load_s, 6),
                          "owlrl": round(owlrl_s, 6), "graph_integrity": round(integrity_s, 6),
                          "shacl": round(shacl_s, 6)},
        "functional_axioms_dropped_for_reasoning": unresolved,
        "owl_sameAs_non_reflexive": len(merged),
        "owl_clashes": {"count": len(contradictions), "examples": contradictions[:10]},
        "shacl": shacl,
        "reasoner": "owlrl OWLRL_Semantics (OWL 2 RL subset, NOT full OWL 2 DL)",
        "nodes": len(nodes),
        "edges": len(edges),
        "edges_by_provenance": dict(Counter(e["provenance"] for e in edges.values())),
        "entities": dict(Counter(n["category"] for n in nodes.values() if n["category"])),
    }
    report["type_triples"] = len(types)
    return nodes, list(edges.values()), types, report


def add_popularity(nodes: dict, edges):
    """Graph-salience popularity proxy: node degree (in+out). Fruits / ships inherit their user's / owner's degree."""
    edges = list(edges)
    deg = Counter()
    for e in edges:
        deg[e["s"]] += 1
        deg[e["o"]] += 1
    owner = {}
    for e in edges:
        if e["t"] in ("DEVIL_FRUIT_CURRENT_USER", "SHIP_OWNER") and nodes[e["o"]]["category"]:     # only entities carry a degree
            owner[e["s"]] = max(owner.get(e["s"], 0), deg[e["o"]])
    for u, n in nodes.items():
        if n["category"]:
            n["props"]["degree"] = deg[u]
            n["props"]["popularity"] = deg[u] + (owner.get(u, 0) if n["category"] in ("DevilFruit", "Ship") else 0)


def to_graphs(nodes: dict, edges, types) -> dict[str, Graph]:
    """The named graphs of graph.GRAPHS (the tbox one is filled by main).  Node properties keep their python type (int / float / bool / str)."""
    g = Namespace(graph.G)
    out = {k: Graph() for k in graph.GRAPHS}
    for e in edges:
        out[e["provenance"]].add((URIRef(e["s"]), URIRef(e["predicate"]), URIRef(e["o"])))
        out["game"].add((URIRef(e["predicate"]), g.relType, Literal(e["t"])))
    for t in types:
        out[t["provenance"]].add((URIRef(t["s"]), RDF.type, URIRef(t["class"])))
    game = out["game"]
    for n in nodes.values():
        u = URIRef(n["uri"])
        game.add((u, g.name, Literal(n["name"])))
        game.add((u, g.local, Literal(n["local"])))
        if n["category"]:
            game.add((u, g.category, Literal(n["category"])))
        for lab in n["labels"]:
            if lab != "Resource":
                game.add((u, g.label, Literal(lab)))
        for t in n["explicit_types"]:
            game.add((u, g.explicitType, Literal(t)))
        for t in n["inferred_types"]:
            game.add((u, g.inferredType, Literal(t)))
        for k, v in n["props"].items():
            for x in (v if isinstance(v, list) else [v]):
                if x is not None:
                    game.add((u, g[graph.label_name(k)], Literal(x)))
    return out


def load_into_fuseki(graphs: dict[str, Graph]):
    for name, gr in graphs.items():
        graph.put_graph(name, gr.serialize(format="nt"))


def validate(nodes, edges, report):
    """Sanity checks on the model, then that the store holds it. Raises on failure."""
    counts = Counter(n["category"] for n in nodes.values() if n["category"])
    counts = {c: counts.get(c, 0) for c in config.CATEGORIES}
    inferred = Counter(e["t"] for e in edges if e["provenance"] == "inferred")
    fruit_types = Counter(e["s"] for e in edges if e["t"] == "HAS_FRUIT_TYPE")
    stored = {c: graph.run("SELECT (COUNT(?e) AS ?c) WHERE { GRAPH <urn:akinator:game> { ?e g:category $c } }", c=c)[0]["c"] for c in config.CATEGORIES}
    patched = config.APPLY_PATCHES
    checks = {
        "store holds every entity": stored == counts,
        "characters >= 1500": counts["Character"] >= 1500,
        "devil fruits >= 134": counts["DevilFruit"] >= 134,
        "ships == 9 (curated)": counts["Ship"] == 9,
        "inferred HAS_DEVIL_FRUIT edges > 0": inferred["HAS_DEVIL_FRUIT"] > 0,
        "every Devil Fruit has exactly one type": all(fruit_types.get(u, 0) == 1 for u, n in nodes.items() if n["category"] == "DevilFruit"),
        "OWL RL derived PirateAffiliatedCharacter label > 0": any("PirateAffiliatedCharacter" in n["labels"] for n in nodes.values()),
        "no sameAs-merged chapters (distinct MANGA_DEBUT targets > 400)": len({e["o"] for e in edges if e["t"] == "MANGA_DEBUT"}) > 400,
        "no non-reflexive owl:sameAs inferred (no entity merged)": report["owl_sameAs_non_reflexive"] == 0 or not patched,
        "no functional-property axiom had to be dropped": not report["functional_axioms_dropped_for_reasoning"] or not patched,
        "OWL RL: no contradiction (disjointness / differentFrom / functional)": report["owl_clashes"]["count"] == 0 or not patched,
        "SHACL: zero violations on the patched graph": report["shacl"]["violations"] == 0 or not patched,
    }
    report["patches_applied"] = patched
    report["entity_counts"] = counts
    report["validation"] = checks
    failed = [k for k, v in checks.items() if not v]
    if failed:
        raise SystemExit(f"Ingestion validation failed: {failed}")


def main():
    graph.wait_ready()
    stage_started = time.perf_counter()
    source_graphs = load_sources()
    perf_record = None
    from .perf import record as perf_record
    perf_record("rdf_load_for_ingestion", time.perf_counter() - stage_started,
                base_triples=len(source_graphs[0]), extension_triples=len(source_graphs[1]))
    nodes, edges, types, report = build_model(source_graphs=source_graphs)
    perf_record("model_build", time.perf_counter() - stage_started, nodes=len(nodes), edges=len(edges))
    stage_started = time.perf_counter()
    graphs = to_graphs(nodes, edges, types)
    graphs["tbox"] = tbox(source_graphs[1])
    perf_record("named_graph_conversion", time.perf_counter() - stage_started, graphs={k: len(v) for k, v in graphs.items()})
    report["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    report["store"] = {"engine": "Apache Jena Fuseki (TDB2)", "triples_by_graph": {k: len(v) for k, v in graphs.items()}}
    graphs["game"].add((URIRef(RUN), URIRef(graph.G + "report"), Literal(json.dumps(report))))
    stage_started = time.perf_counter()
    load_into_fuseki(graphs)
    perf_record("fuseki_upload", time.perf_counter() - stage_started, graphs=len(graphs), triples=sum(map(len, graphs.values())))
    stage_started = time.perf_counter()
    try:
        validate(nodes, edges, report)
    finally:                                                   # the stored report carries the validation outcome (also when it failed)
        perf_record("fuseki_store_validation", time.perf_counter() - stage_started,
                    success=all(report.get("validation", {}).values()) if report.get("validation") else False)
        graphs["game"].set((URIRef(RUN), URIRef(graph.G + "report"), Literal(json.dumps(report))))
        graph.put_graph("game", graphs["game"].serialize(format="nt"))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    sys.exit(main())
