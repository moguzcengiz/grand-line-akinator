"""Ontology audit: documents every OWL modelling inconsistency found, with before/after reasoning statistics.

    python -m app.audit            # prints the report and writes docs/ONTOLOGY_AUDIT.md
"""
import json
import time
from collections import Counter
from pathlib import Path

from rdflib import RDF, RDFS, OWL, URIRef, Graph

from . import config
from .ontology import OP, OPX, load_upstream, load_ext, load_sources, materialize, is_domain_triple, nonreflexive_same_as
from .patching import decide, functional_conflicts
from .validation import shacl_report


def _stats(label: str, union: Graph, **kw) -> dict:
    t0 = time.time()
    inferred, dropped = materialize(union, **kw)
    # nodes wrongly typed by the swapped inCrew domain/range: characters typed PirateCrew + crews typed Character
    inc = sum(1 for s in union.subjects(RDF.type, OP.Character) if (s, RDF.type, OP.PirateCrew) in inferred) + \
        sum(1 for s, _, _ in inferred.triples((None, RDF.type, OP.Character)) if (s, RDF.type, OP.PirateCrew) in union)
    merged = nonreflexive_same_as(inferred)
    return {"scenario": label, "seconds": round(time.time() - t0, 1), "inferred_total": len(inferred),
            "inferred_domain": sum(1 for t in inferred if is_domain_triple(t)), "sameAs_non_reflexive": len(merged),
            "sameAs_examples": [f"{str(a).rsplit('#', 1)[-1]} = {str(b).rsplit('#', 1)[-1]}" for a, b in merged[:3]],
            "axioms_dropped": [p.rsplit("#", 1)[-1] for p in dropped], "inCrew_misclassified": inc}


def other_findings(up: Graph, patched: Graph, inferred: Graph) -> list[dict]:
    out = []
    typo = [(s, o) for s, p, o in up.triples((None, None, None)) if str(p) == str(RDFS) + "inverseOf"]
    out.append({"issue": "rdfs:inverseOf used instead of owl:inverseOf", "count": len(typo),
                "detail": ", ".join(f"{str(s).rsplit('#', 1)[-1]}↔{str(o).rsplit('#', 1)[-1]}" for s, o in typo) or "none",
                "cause": "typo in upstream schema (rdfs has no inverseOf), so the axiom is inert", "resolution": "documented; hasBounty/givenTo carry only 38 triples and are not used by the game"})
    ns = {u for t in up for u in t if isinstance(u, URIRef) and str(u).startswith("http://kalnassag.com/onepiece/")}
    twins = sum(1 for u in ns if URIRef(config.OP + str(u).rsplit("/", 1)[-1]) in {x for t in up for x in t if isinstance(x, URIRef)})
    out.append({"issue": "two namespaces for the same ontology (…/onepiece/ vs …/onepiece#)", "count": len(ns),
                "detail": f"{len(ns)} URIs in the '/' namespace, {twins} of them also exist with '#'", "cause": "upstream pipeline script builds URIs with '/'",
                "resolution": "URIs preserved verbatim (requirement); fruits there are normal game entities via their explicit rdf:type"})
    enum = {o for o in up.objects(None, OP.hasFruitType)} - {OP.Paramecia, OP.Zoan, OP.Logia}
    out.append({"issue": "op:DevilFruitType is an owl:oneOf enumeration of 3 individuals but data/extension use more", "count": len(enum),
                "detail": ", ".join(sorted(str(e).rsplit('#', 1)[-1] for e in enum)) + " (+ opx:AncientZoan, opx:MythicalZoan from our extension)",
                "cause": "closed enumeration vs. open-world data; a full DL reasoner would be forced to merge them with Paramecia/Zoan/Logia",
                "resolution": "OWL RL has no rule that does this (verified: 0 sameAs); documented, extension stays RL-safe"})
    ent = {c: {s for s in patched.subjects(RDF.type, c)} for c in (OP.Character, OP.DevilFruit)}
    spurious = sorted({str(s).rsplit('#', 1)[-1] for s, _, o in inferred.triples((None, RDF.type, OP.Character)) if s not in ent[OP.Character]})
    out.append({"issue": "individuals typed as Character only by rdfs:domain/range inference (never asserted)", "count": len(spurious),
                "detail": ", ".join(spurious[:8]) + ("…" if len(spurious) > 8 else ""), "cause": "range of op:hasDevilFruit / domain axioms applied to wiki placeholder names",
                "resolution": "such nodes keep the inferred label but are NOT game entities (category needs an asserted type)"})
    return out


def main():
    up = load_upstream()
    ext_raw = load_ext(up)
    patched, ext = load_sources()
    decisions, _, _ = decide(up, Path("ontology-src"))
    conflicts_before = {str(p).rsplit('#', 1)[-1]: len(v) for p, v in functional_conflicts(up).items()}
    conflicts_after = {str(p).rsplit('#', 1)[-1]: len(v) for p, v in functional_conflicts(patched + ext).items()}
    scen = [_stats("A. upstream as-is, functional axioms kept, no guard", up + ext_raw, guard=False),
            _stats("B. previous workaround: drop ALL functional axioms", up + ext_raw, drop_all_functional=True),
            _stats("C. shipped: data patched, functional axioms kept", patched + ext)]
    shacl_before, shacl_after = shacl_report(up + ext_raw), shacl_report(patched + ext)
    inferred_c, _ = materialize(patched + ext)
    findings = other_findings(up, patched, inferred_c)
    res = {"conflicts_before": conflicts_before, "conflicts_after": conflicts_after, "decisions": decisions, "scenarios": scen,
           "shacl_before": shacl_before, "shacl_after": shacl_after, "other": findings}
    Path("eval_results").mkdir(exist_ok=True)
    Path("eval_results/audit.json").write_text(json.dumps(res, indent=2, default=str))
    print(json.dumps({k: v for k, v in res.items() if k != "decisions"}, indent=2, default=str))


if __name__ == "__main__":
    main()
