"""RDF -> OWL RL -> Neo4j ingestion.  Run:  python -m app.ingestion

Idempotent: wipes the graph and rebuilds it deterministically from the ontology files.
Provenance on every relationship:  explicit (upstream data) | curated (our extension/curated files) | inferred (owlrl).
"""
import json
import re
import sys
import time
from collections import Counter, defaultdict

from rdflib import Graph, URIRef, Literal, RDF, RDFS, OWL

from . import config, graph
from .ontology import load_sources, materialize, is_domain_triple, nonreflexive_same_as, OP, OPX
from .validation import shacl_report

NUMERIC = {"height", "age", "ageAtDeath", "bountyAmount"}
CATEGORY_CLASSES = {"Character", "DevilFruit", "Ship"}
SKIP_LITERAL = {"opwikiurl", "internalID", "dbpediaID", "wikipediaOD"}
META_PREFIX = (str(RDF), str(RDFS), str(OWL))


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


def build_model():
    """Pure-python part: returns (nodes, edges, report). Testable without Neo4j."""
    base, ext = load_sources()
    union = base + ext
    t0 = time.time()
    inferred, unresolved = materialize(union)
    merged = nonreflexive_same_as(inferred)
    shacl = shacl_report(union)
    reasoning_s = round(time.time() - t0, 1)
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

    report = {
        "source_triples": {"base": len(base), "extension": len(ext)},
        "inferred_triples_total": len(inferred),
        "inferred_triples_domain": len(inferred_dom),
        "reasoning_seconds": reasoning_s,
        "functional_axioms_dropped_for_reasoning": unresolved,
        "owl_sameAs_non_reflexive": len(merged),
        "shacl": shacl,
        "reasoner": "owlrl OWLRL_Semantics (OWL 2 RL subset, NOT full OWL 2 DL)",
        "nodes": len(nodes),
        "edges": len(edges),
        "edges_by_provenance": dict(Counter(e["provenance"] for e in edges.values())),
        "entities": dict(Counter(n["category"] for n in nodes.values() if n["category"])),
    }
    return nodes, list(edges.values()), report


def _batches(xs, n=2000):
    for i in range(0, len(xs), n):
        yield xs[i:i + n]


def load_into_neo4j(nodes, edges):
    graph.run("MATCH (n) DETACH DELETE n")
    graph.run("CREATE CONSTRAINT resource_uri IF NOT EXISTS FOR (n:Resource) REQUIRE n.uri IS UNIQUE")
    by_labels = defaultdict(list)
    for n in nodes.values():
        row = {"uri": n["uri"], "props": {**n["props"], "local": n["local"], "name": n["name"],
               "category": n["category"], "explicit_types": sorted(n["explicit_types"]),
               "inferred_types": sorted(n["inferred_types"])}}
        row["props"] = {k: v for k, v in row["props"].items() if v is not None}
        by_labels[tuple(n["labels"])].append(row)
    for labels, rows in by_labels.items():
        lab = ":".join(f"`{l}`" for l in labels)
        for b in _batches(rows):
            graph.run(f"UNWIND $rows AS r CREATE (n:{lab} {{uri: r.uri}}) SET n += r.props", rows=b)
    by_type = defaultdict(list)
    for e in edges:
        by_type[e["t"]].append(e)
    for t, rows in by_type.items():
        for b in _batches(rows):
            graph.run(f"UNWIND $rows AS r MATCH (a:Resource {{uri: r.s}}), (b:Resource {{uri: r.o}}) "
                      f"CREATE (a)-[x:`{t}`]->(b) SET x.provenance = r.provenance, x.predicate = r.predicate", rows=b)


def compute_popularity():
    """Graph-salience popularity proxy: node degree (in+out). Fruits / ships inherit their user's / owner's degree."""
    graph.run("MATCH (e:Resource) WHERE e.category IS NOT NULL SET e.degree = COUNT { (e)--() }")
    graph.run("MATCH (e:Resource) WHERE e.category = 'Character' SET e.popularity = e.degree")
    graph.run("MATCH (e:Resource) WHERE e.category IN ['DevilFruit','Ship'] "
              "OPTIONAL MATCH (e)-[:DEVIL_FRUIT_CURRENT_USER|SHIP_OWNER]->(o:Resource) "
              "WITH e, max(o.degree) AS od SET e.popularity = e.degree + coalesce(od, 0)")


def validate(report):
    """Sanity checks against the freshly loaded graph. Raises on failure."""
    q = lambda cypher, **k: graph.run(cypher, **k)[0]["c"]
    counts = {c: q(f"MATCH (n:`{c}`) WHERE n.category = $c RETURN count(n) AS c", c=c) for c in config.CATEGORIES}
    patched = config.APPLY_PATCHES
    checks = {
        "characters >= 1500": counts["Character"] >= 1500,
        "devil fruits >= 134": counts["DevilFruit"] >= 134,
        "ships == 9 (curated)": counts["Ship"] == 9,
        "inferred HAS_DEVIL_FRUIT edges > 0": q("MATCH ()-[r:HAS_DEVIL_FRUIT {provenance:'inferred'}]->() RETURN count(r) AS c") > 0,
        "inferred Ancient/Mythical fruit types > 0": q("MATCH ()-[r:HAS_FRUIT_TYPE {provenance:'inferred'}]->() RETURN count(r) AS c") > 0,
        "OWL RL derived PirateAffiliatedCharacter label > 0": q("MATCH (n:PirateAffiliatedCharacter) RETURN count(n) AS c") > 0,
        "no sameAs-merged chapters (distinct MANGA_DEBUT targets > 400)": q("MATCH ()-[:MANGA_DEBUT]->(c) RETURN count(DISTINCT c) AS c") > 400,
        "no non-reflexive owl:sameAs inferred (no entity merged)": report["owl_sameAs_non_reflexive"] == 0 or not patched,
        "no functional-property axiom had to be dropped": not report["functional_axioms_dropped_for_reasoning"] or not patched,
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
    nodes, edges, report = build_model()
    load_into_neo4j(nodes, edges)
    compute_popularity()
    validate(report)
    report["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    graph.run("MERGE (r:IngestionRun {id:'latest'}) SET r.report = $r", r=json.dumps(report))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    sys.exit(main())
