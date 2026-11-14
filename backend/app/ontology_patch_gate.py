"""Fast pre-integration gate for one campaign's Turtle add/remove patches."""
from __future__ import annotations
import argparse
import json
import time
from pathlib import Path
from rdflib import Graph, RDF, OWL, URIRef
from rdflib.namespace import PROV
from . import config
from .ontology import OPX, load_sources, load_upstream
from .perf import record

PATCH_DIR = config.ROOT / "ontology/patches"
META_PREDICATES = {RDF.type, RDF.subject, RDF.predicate, RDF.object, PROV.wasDerivedFrom,
                   OPX.sourceReference, OPX.sourceType, OPX.confidence, OPX.temporalScope,
                   OPX.temporalStatus}
SCHEMA_MARKERS = {OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty, OWL.AnnotationProperty,
                  OWL.Ontology, OWL.NamedIndividual, RDF.Property, RDF.Statement,
                  OPX.TemporalStatement, OPX.TemporalStatus}


def _patch(name, kind):
    path = PATCH_DIR / f"{name}.{kind}.ttl"
    return (Graph().parse(str(path), format="turtle"), path) if path.exists() else (Graph(), path)


def _baseline(name):
    """Load current graph while excluding the batch under review."""
    saved = set(config.SKIP_PATCHES)
    try:
        config.SKIP_PATCHES = saved | {name}
        base, ext = load_sources()
        return base + ext
    finally:
        config.SKIP_PATCHES = saved


def _provenance(graph):
    rows = {}
    for statement in graph.subjects(RDF.type, RDF.Statement):
        s, p, o = (graph.value(statement, pred) for pred in (RDF.subject, RDF.predicate, RDF.object))
        if s is None or p is None or o is None: continue
        urls = sorted(str(x) for x in graph.objects(statement, PROV.wasDerivedFrom))
        ref = graph.value(statement, OPX.sourceReference)
        confidence = graph.value(statement, OPX.confidence)
        rows[(s, p, o)] = {"urls": urls, "reference": str(ref or ""), "confidence": str(confidence or ""),
                           "statement": str(statement)}
    return rows


def validate_campaign_patch(batch: str):
    started = time.perf_counter()
    name = f"campaign-batch-{int(batch):03d}"
    add, add_path = _patch(name, "add")
    remove, remove_path = _patch(name, "remove")
    baseline = _baseline(name)
    # A predicate is permitted if the ontology already declares it or it appears as a
    # predicate in the baseline. This prevents introducing misspelled vocabulary.
    allowed = {p for p in baseline.predicates()}
    allowed |= {s for s in baseline.subjects(RDF.type) if (s, RDF.type, OWL.ObjectProperty) in baseline
                or (s, RDF.type, OWL.DatatypeProperty) in baseline or (s, RDF.type, OWL.AnnotationProperty) in baseline
                or (s, RDF.type, RDF.Property) in baseline}
    source = _provenance(add)
    failures, warnings = [], []
    added_facts = []
    new_entities = {s for s, p, o in add if p == RDF.type and o not in SCHEMA_MARKERS}
    for s, p, o in add:
        if p in META_PREDICATES or p in {OPX.sourceReference, OPX.sourceType, OPX.confidence, OPX.temporalScope}: continue
        if s not in {stmt for stmt in add.subjects(RDF.type, RDF.Statement)} and not str(s).startswith(str(OPX)):
            if (s, p, o) in baseline:
                failures.append({"kind": "duplicate_assertion", "triple": [str(s), str(p), str(o)]})
            else:
                added_facts.append((s, p, o))
                if p not in allowed:
                    failures.append({"kind": "predicate_not_in_allowlist", "predicate": str(p)})
                if isinstance(o, URIRef) and not (any(baseline.triples((o, None, None))) or o in new_entities):
                    failures.append({"kind": "unresolved_object_uri", "uri": str(o)})
                evidence = source.get((s, p, o))
                if not evidence or not evidence["urls"] or not evidence["reference"] or not evidence["confidence"]:
                    failures.append({"kind": "provenance_incomplete", "triple": [str(s), str(p), str(o)]})
    # Duplicate assertion detection within the patch (RDF graphs collapse identical triples).
    temporal_triples = {}
    baseline_temporal = set()
    for statement in baseline.subjects(RDF.type, OPX.TemporalStatement):
        baseline_temporal.add(tuple(baseline.value(statement, pred) for pred in (RDF.subject, RDF.predicate, RDF.object)))
    for statement in add.subjects(RDF.type, OPX.TemporalStatement):
        triple = tuple(add.value(statement, pred) for pred in (RDF.subject, RDF.predicate, RDF.object))
        temporal_triples[triple] = add.value(statement, OPX.temporalStatus)
        if (None in triple or temporal_triples[triple] is None
                or not any(baseline.triples((temporal_triples[triple], RDF.type, OPX.TemporalStatus)))):
            failures.append({"kind": "temporal_statement_incomplete", "statement": str(statement)})
        elif triple in source:
            ev = source[triple]
            if not (ev["urls"] and ev["reference"] and ev["confidence"]):
                failures.append({"kind": "temporal_fact_missing_complete_provenance", "triple": list(map(str, triple))})
        else:
            failures.append({"kind": "temporal_fact_missing_source_provenance", "triple": list(map(str, triple))})
        if triple in baseline_temporal:
            failures.append({"kind": "duplicate_temporal_assertion", "triple": list(map(str, triple))})
    removal_reason_path = config.ROOT / f"work/research/batch-{int(batch):03d}-removal-reasons.json"
    if remove and not removal_reason_path.exists():
        failures.append({"kind": "removal_reasons_missing", "path": str(removal_reason_path)})
    elif remove:
        reason_rows = json.loads(removal_reason_path.read_text(encoding="utf-8"))
        explained = {tuple(row.get("triple", [])) for row in reason_rows if row.get("reason")}
        for triple in remove:
            if tuple(map(str, triple)) not in explained:
                failures.append({"kind": "removed_triple_without_reason", "triple": list(map(str, triple))})
    result = {"batch": name, "add_file": str(add_path.relative_to(config.ROOT)),
              "remove_file": str(remove_path.relative_to(config.ROOT)), "added_triples": len(add),
              "removed_triples": len(remove), "new_assertions": len(added_facts),
              "temporal_assertions": len(temporal_triples),
              "provenance_complete_assertions": sum(bool((s, p, o) in source and source[(s, p, o)]["urls"]
                                                         and source[(s, p, o)]["reference"] and source[(s, p, o)]["confidence"])
                                                    for s, p, o in added_facts),
              "failures": failures, "warnings": warnings,
              "removed_assertions_require_reason_file": str(removal_reason_path) if remove else None}
    result["elapsed_seconds"] = round(time.perf_counter() - started, 6)
    record("lightweight_patch_gate", result["elapsed_seconds"], batch=name,
           assertions=len(added_facts), failures=len(failures), warnings=len(warnings))
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("batch")
    ap.add_argument("--out")
    args = ap.parse_args()
    result = validate_campaign_patch(args.batch)
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if result["failures"]: raise SystemExit(1)


if __name__ == "__main__": main()
