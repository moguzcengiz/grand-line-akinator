"""Persistent, resumable entity research queue for ontology enrichment.

The queue is an audit ledger, not a source of RDF facts. Research findings are
recorded here first; factual additions still require a separately reviewed RDF
patch with provenance.

Commands (from the repository root)::

    PYTHONPATH=backend .venv/bin/python -m app.ontology_campaign --resume
    PYTHONPATH=backend .venv/bin/python -m app.ontology_campaign --record findings.json
    PYTHONPATH=backend .venv/bin/python -m app.ontology_campaign --report

`--resume` creates the queue on first use and reserves a deterministic batch.
Calling it again returns the same active batch until results are recorded.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rdflib import Graph, RDF, RDFS, OWL, SKOS, URIRef, Literal

from . import config
from .ontology import OP, OPX, load_sources, materialize
from .perf import record as perf_record

WORK = config.ROOT / "work"
QUEUE = WORK / "ontology-research-queue.jsonl"
STATE = WORK / "ontology-campaign-state.json"
EVENTS = WORK / "ontology-campaign-events.jsonl"
PROGRESS = config.ROOT / "docs/ONTOLOGY_CAMPAIGN_PROGRESS.md"
KNOWN_SCHEMA_TYPES = {
    OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty, OWL.AnnotationProperty,
    OWL.Ontology, OWL.NamedIndividual, OWL.FunctionalProperty,
    OWL.InverseFunctionalProperty, OWL.TransitiveProperty, OWL.SymmetricProperty,
    OWL.AsymmetricProperty, OWL.ReflexiveProperty, OWL.IrreflexiveProperty,
    OWL.DeprecatedClass, OWL.DeprecatedProperty, RDF.Property, RDF.Statement,
    OPX.TemporalStatement, OPX.TemporalStatus,
}
PROJECT_SCHEMA_TYPES = {OP.ObjectProperty, OP.DatatypeProperty, OP.AnnotationProperty}
ENTITY_NAMESPACES = (str(OP), str(OPX), "http://kalnassag.com/onepiece/")

# These are the high-value positive relations audited by the game-facing report.
AUDIT_RELATIONS = {
    "Character": [OP.affiliatesWith, OP.occupation, OP.hasDevilFruit, OPX.previouslyHadDevilFruit, OPX.hasHaki],
    "DevilFruit": [OP.hasFruitType, OP.DevilFruitCurrentUser, OP.DevilFruitPreviousUser, OPX.hasFruitSubtype],
    "Ship": [OPX.operatedBy, OPX.shipOwner, OPX.shipType],
    "Affiliation": [OPX.memberOf, OPX.leaderOf],
    "PirateOrganization": [OPX.member, OPX.leader],
    "MarineOrganization": [OPX.member, OPX.leader],
    "WorldGovernmentOrganization": [OPX.member, OPX.leader],
}
HIGH_VALUE_TYPES = {"Character": 100, "DevilFruit": 90, "Ship": 80,
                    "PirateOrganization": 65, "MarineOrganization": 65,
                    "WorldGovernmentOrganization": 65, "Affiliation": 55}
SOURCE_PREDICATES = {SKOS.altLabel, SKOS.hiddenLabel, SKOS.prefLabel}
ALIAS_PREDICATES = SOURCE_PREDICATES | {
    OP.alias, OP.epithet, OP.temporaryAlias, OPX.alias, OPX.otherName, OP.otherName,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _local(uri: URIRef | str) -> str:
    return str(uri).rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def _typed_entities(graph):
    """Named, explicitly typed data individuals; exclude ontology/schema terms."""
    result = set()
    for subject, rdf_type in graph.subject_objects(RDF.type):
        if not isinstance(subject, URIRef) or not str(subject).startswith(ENTITY_NAMESPACES):
            continue
        if rdf_type in KNOWN_SCHEMA_TYPES or rdf_type in PROJECT_SCHEMA_TYPES:
            continue
        # The source encodes its own vocabulary declarations as project classes.
        if (subject, RDF.type, OWL.Class) in graph or (subject, RDF.type, OWL.ObjectProperty) in graph \
                or (subject, RDF.type, OWL.DatatypeProperty) in graph or (subject, RDF.type, RDF.Property) in graph:
            continue
        result.add(subject)
    return result


def _term(t) -> dict[str, Any]:
    if isinstance(t, URIRef):
        return {"kind": "uri", "value": str(t), "label": _local(t)}
    if isinstance(t, Literal):
        return {"kind": "literal", "value": str(t), "language": t.language,
                "datatype": str(t.datatype) if t.datatype else None}
    return {"kind": "blank_node", "value": str(t)}


def _subject_assertions(graph, entity):
    return [{"predicate_uri": str(p), "object": _term(o)}
            for _, p, o in sorted(graph.triples((entity, None, None)), key=lambda row: (str(row[1]), str(row[2])))]


def _names(graph, entity):
    labels = sorted({str(v) for v in graph.objects(entity, RDFS.label) if isinstance(v, Literal)})
    preferred = [str(v) for v in graph.objects(entity, SKOS.prefLabel) if isinstance(v, Literal)]
    aliases = sorted({str(v) for p in ALIAS_PREDICATES for v in graph.objects(entity, p) if isinstance(v, Literal)}
                     | (set(labels) - set(preferred)))
    name = (preferred or labels or [_local(entity)])[0]
    return name, aliases


def _coverage(graph, entity, types, inferred_graph=None):
    coverage = {}
    for type_name in types:
        for predicate in AUDIT_RELATIONS.get(type_name, []):
            asserted_values = set(graph.objects(entity, predicate))
            inferred_values = set(inferred_graph.objects(entity, predicate)) if inferred_graph is not None else set()
            inferred_values -= asserted_values
            coverage[str(predicate)] = {
                "asserted_positive_count": len(asserted_values),
                "inferred_positive_count": len(inferred_values),
                "known_positive_count": len(asserted_values | inferred_values),
                "evidence_status": "not_independently_reviewed",
            }
    return coverage


def _existing_provenance(graph):
    """Import only source statements already present in an explicit RDF patch."""
    rows = defaultdict(list)
    for statement in graph.subjects(RDF.type, RDF.Statement):
        subject = graph.value(statement, RDF.subject)
        predicate = graph.value(statement, RDF.predicate)
        value = graph.value(statement, RDF.object)
        if not isinstance(subject, URIRef) or not predicate or value is None:
            continue
        urls = sorted(str(v) for v in graph.objects(statement, URIRef("http://www.w3.org/ns/prov#wasDerivedFrom")))
        reference = graph.value(statement, OPX.sourceReference)
        confidence = graph.value(statement, OPX.confidence)
        rows[str(subject)].append({
            "predicate_uri": str(predicate), "value": _term(value), "source_urls": urls,
            "source_reference": str(reference) if reference else None,
            "confidence": str(confidence) if confidence else "unspecified",
            "provenance_record_uri": str(statement),
            "note": "Carried forward from the existing source-backed RDF patch; this verifies the listed positive assertion only.",
        })
    return rows


def _evaluation_targets():
    path = config.ROOT / "eval_results/targets-popularity.json"
    if not path.exists():
        return set()
    values = json.loads(path.read_text(encoding="utf-8"))
    return {re.sub(r"[^a-z0-9]", "", str(value).casefold()) for value in values}


def build_queue(graph=None, prior=None, inferred_graph=None):
    if graph is None:
        base, ext = load_sources()
        graph = base + ext
    previous = {r["entity_uri"]: r for r in (prior or [])}
    inferred_graph = inferred_graph or Graph()
    records = []
    provenance = _existing_provenance(graph)
    evaluation_targets = _evaluation_targets()
    type_map = defaultdict(set)
    for entity, rdf_type in graph.subject_objects(RDF.type):
        if isinstance(entity, URIRef):
            type_map[entity].add(rdf_type)
    for entity in sorted(_typed_entities(graph), key=str):
        types = sorted({_local(t) for t in type_map[entity]}, key=str.casefold)
        name, aliases = _names(graph, entity)
        old = previous.get(str(entity), {})
        type_priority = max((HIGH_VALUE_TYPES.get(t, 15) for t in types), default=10)
        coverage = _coverage(graph, entity, types, inferred_graph)
        gap_count = sum(1 for c in coverage.values() if c["known_positive_count"] == 0)
        target_names = {_norm(v) for v in [name, *aliases, _local(entity)]}
        in_game_evaluation = bool(target_names & evaluation_targets)
        score = type_priority + min(gap_count * 3, 18) + (60 if in_game_evaluation else 0)
        # Preserve only reviewed campaign metadata; assertions/names/types always refresh from RDF.
        old_coverage = old.get("coverage_review", {})
        for predicate, item in coverage.items():
            if predicate in old_coverage and old_coverage[predicate].get("evidence_status") not in (None, "not_independently_reviewed"):
                item.update(old_coverage[predicate])
        sources = sorted({url for finding in provenance.get(str(entity), []) for url in finding["source_urls"]})
        findings = old.get("findings", [])
        prior_fact_ids = {f.get("provenance_record_uri") for f in findings if f.get("provenance_record_uri")}
        findings.extend(f for f in provenance.get(str(entity), []) if f.get("provenance_record_uri") not in prior_fact_ids)
        # Mark only the dimensions directly supported by existing reified source records.
        for finding in provenance.get(str(entity), []):
            review = coverage.get(finding["predicate_uri"])
            if review:
                review["evidence_status"] = "positive_assertion_source_documented"
                review["reviewed_positive_count"] = review["asserted_positive_count"]
        previous_status = old.get("status", "pending")
        if previous_status == "pending" and findings:
            previous_status = "partially_verified"
        records.append({
            "entity_uri": str(entity), "canonical_name": name, "aliases": aliases,
            "types": types, "assertions": _subject_assertions(graph, entity),
            "inferred_assertions": _subject_assertions(inferred_graph, entity),
            "coverage_review": coverage,
            "priority": score, "priority_reason": f"type_weight={type_priority}; audited_unknown_gaps={gap_count}; evaluation_target={in_game_evaluation}",
            "status": previous_status if previous_status != "pending" or not findings else "partially_verified",
            "source_urls": sorted(set(old.get("source_urls", [])) | set(sources)),
            "findings": findings, "next_action": old.get("next_action", "source-check identity and high-value relationships"),
            "attempt_count": old.get("attempt_count", 0), "last_research_timestamp": old.get("last_research_timestamp"),
            "active_batch_id": old.get("active_batch_id"),
        })
    # Preserve explicitly referenced but untyped project URI nodes as identity-review
    # records. Their existence is audited; their identity is not inferred or guessed.
    typed = {URIRef(r["entity_uri"]) for r in records}
    referenced = {o for _, _, o in graph if isinstance(o, URIRef) and str(o).startswith(ENTITY_NAMESPACES)}
    for entity in sorted(referenced - typed, key=str):
        if any(graph.triples((entity, None, None))):
            continue
        old = previous.get(str(entity), {})
        name, aliases = _names(graph, entity)
        records.append({
            "entity_uri": str(entity), "canonical_name": name, "aliases": aliases, "types": [],
            "assertions": [], "coverage_review": {}, "priority": 45,
            "priority_reason": "referenced project URI has no explicit type; identity resolution required",
            "status": old.get("status", "pending"), "source_urls": old.get("source_urls", []),
            "findings": old.get("findings", []), "next_action": old.get("next_action", "resolve identity from authoritative source; do not map by name alone"),
            "attempt_count": old.get("attempt_count", 0), "last_research_timestamp": old.get("last_research_timestamp"),
            "active_batch_id": old.get("active_batch_id"), "identity_review_required": True,
        })
    records.sort(key=lambda r: r["entity_uri"])
    return records


def _norm(value):
    return re.sub(r"[^a-z0-9]", "", str(value).casefold())


def _read_queue() -> list[dict[str, Any]]:
    if not QUEUE.exists():
        return []
    with QUEUE.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def _read_state() -> dict[str, Any]:
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}


def _atomic_write(path: Path, content: str) -> None:
    started = time.perf_counter()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    perf_record("campaign_checkpoint_write", time.perf_counter() - started,
                path=str(path.relative_to(config.ROOT)) if path.is_relative_to(config.ROOT) else str(path),
                bytes=len(content.encode("utf-8")))


def _write_queue(records):
    _atomic_write(QUEUE, "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in records))


def _event(event_type, **data):
    started = time.perf_counter()
    WORK.mkdir(parents=True, exist_ok=True)
    record = {"timestamp": _now(), "event": event_type, **data}
    with EVENTS.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    perf_record("campaign_event_checkpoint", time.perf_counter() - started, event=event_type)


def _counts(records):
    counts = Counter(r.get("status", "pending") for r in records)
    return {"total_entities": len(records), "status_counts": dict(sorted(counts.items())),
            "identity_review_required": sum(bool(r.get("identity_review_required")) for r in records),
            "types": dict(sorted(Counter(t for r in records for t in r.get("types", [])).items()))}


def _write_progress(state, records):
    counts = _counts(records)
    active = state.get("active_batch") or {}
    lines = ["# Ontology campaign progress", "", f"**Updated:** {state.get('updated_at', _now())}",
             f"**Queue entities:** {counts['total_entities']}",
             f"**Untyped referenced URIs queued for identity review:** {counts['identity_review_required']}",
             f"**Active batch:** {active.get('batch_id', 'none')}", "", "## Status counts", "",
             "| Status | Entities |", "|---|---:|"]
    lines.extend(f"| {status} | {count} |" for status, count in counts["status_counts"].items())
    lines.extend(["", "## Active batch", ""])
    ids = active.get("entity_uris", [])
    if ids:
        lookup = {r["entity_uri"]: r for r in records}
        lines.extend(f"- {lookup.get(uri, {}).get('canonical_name', uri)} — `{uri}`" for uri in ids)
    else:
        lines.append("No batch is currently reserved.")
    lines.extend(["", "## Resumption", "", "Resume or allocate the next deterministic batch with:",
                  "", "```sh", "PYTHONPATH=backend .venv/bin/python -m app.ontology_campaign --resume", "```", "",
                  "Queue gaps are unknowns, not negative facts. Findings recorded in the queue do not become RDF until reviewed and integrated with provenance.", ""])
    _atomic_write(PROGRESS, "\n".join(lines))


def resume(batch_size=20, refresh=False):
    started = time.perf_counter()
    WORK.mkdir(parents=True, exist_ok=True)
    old_records = _read_queue()
    if not old_records or refresh:
        base, ext = load_sources()
        graph = base + ext
        inferred, _ = materialize(graph)
        records = build_queue(graph, old_records, inferred)
        _write_queue(records)
        _event("queue_built" if not old_records else "queue_refreshed", total=len(records))
    else:
        records = old_records
    state = _read_state()
    active = state.get("active_batch")
    if active:
        active_records = [r for r in records if r["entity_uri"] in set(active.get("entity_uris", []))]
        # A partial review resolves that entity for the current pass, but the
        # batch remains active while any other member is still in progress.
        # Including reviewed_partial here prevents --refresh from orphaning the
        # unreviewed remainder and silently reserving a second batch.
        if active_records and all(r.get("status") in ("in_progress", "partially_verified", "reviewed_partial") for r in active_records):
            state["updated_at"] = _now()
            _atomic_write(STATE, json.dumps(state, indent=2, ensure_ascii=False) + "\n")
            _write_progress(state, records)
            perf_record("campaign_resume", time.perf_counter() - started, batch_size=batch_size, reused_active=True)
            return active, state, records
    candidates = [r for r in records if r.get("status") == "pending"]
    if not candidates:
        # Continue a later audit pass over entities whose first focused review
        # is complete but whose entire assertion set is not source-verified.
        candidates = [r for r in records if r.get("status") in ("reviewed_partial", "partially_verified")]
    candidates.sort(key=lambda r: (-r.get("priority", 0), r["entity_uri"]))
    selected = candidates[:max(1, batch_size)]
    if not selected:
        state.update({"updated_at": _now(), "active_batch": None, "counts": _counts(records)})
        _atomic_write(STATE, json.dumps(state, indent=2, ensure_ascii=False) + "\n")
        _write_progress(state, records)
        perf_record("campaign_resume", time.perf_counter() - started, batch_size=batch_size, reserved=0)
        return None, state, records
    batch_id = f"batch-{int(datetime.now(timezone.utc).timestamp())}-{len(selected)}"
    now = _now()
    for record in selected:
        record["status"] = "in_progress"
        record["active_batch_id"] = batch_id
        record["attempt_count"] = int(record.get("attempt_count", 0)) + 1
        record["last_research_timestamp"] = now
    active = {"batch_id": batch_id, "started_at": now, "entity_uris": [r["entity_uri"] for r in selected],
              "result_file": None}
    _write_queue(records)
    state.update({"campaign_version": 1, "created_at": state.get("created_at", now), "updated_at": now,
                  "active_batch": active, "counts": _counts(records), "checkpoint": now,
                  "next_action": "research active batch, record findings, integrate only verified deltas"})
    _atomic_write(STATE, json.dumps(state, indent=2, ensure_ascii=False) + "\n")
    _event("batch_reserved", batch_id=batch_id, entity_uris=active["entity_uris"])
    _write_progress(state, records)
    perf_record("campaign_resume", time.perf_counter() - started, batch_size=batch_size, reserved=len(selected))
    return active, state, records


def record_results(path: Path):
    started = time.perf_counter()
    results = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(results, dict):
        results = results.get("results", [])
    records = _read_queue()
    by_uri = {r["entity_uri"]: r for r in records}
    applied = []
    for result in results:
        uri = result.get("entity_uri")
        if uri not in by_uri:
            raise ValueError(f"Unknown entity URI in research results: {uri}")
        row = by_uri[uri]
        status = result.get("status", row["status"])
        if status not in {"pending", "in_progress", "partially_verified", "reviewed_partial", "verified", "no_change", "review_required", "blocked"}:
            raise ValueError(f"Unsupported status {status!r}")
        row["status"] = status
        row["source_urls"] = sorted(set(row.get("source_urls", [])) | set(result.get("source_urls", [])))
        existing_findings = {json.dumps(f, sort_keys=True, ensure_ascii=False) for f in row.get("findings", [])}
        for finding in result.get("findings", []):
            signature = json.dumps(finding, sort_keys=True, ensure_ascii=False)
            if signature not in existing_findings:
                row["findings"].append(finding)
                existing_findings.add(signature)
        row["review_scope"] = sorted(set(row.get("review_scope", [])) | set(result.get("review_scope", [])))
        row["next_action"] = result.get("next_action", row.get("next_action"))
        for predicate, review in result.get("coverage_review", {}).items():
            if predicate in row["coverage_review"]:
                row["coverage_review"][predicate].update(review)
        row["active_batch_id"] = None if status in {"verified", "no_change", "reviewed_partial", "review_required", "blocked"} else row.get("active_batch_id")
        applied.append({"entity_uri": uri, "status": status, "finding_count": len(result.get("findings", []))})
    _write_queue(records)
    state = _read_state()
    active = state.get("active_batch") or {}
    remaining = {r["entity_uri"] for r in records if r.get("active_batch_id") == active.get("batch_id")}
    if active and not remaining:
        _event("batch_recorded", batch_id=active.get("batch_id"), results=applied, results_file=str(path))
        state["completed_batches"] = state.get("completed_batches", []) + [{"batch_id": active.get("batch_id"), "completed_at": _now(), "results": applied}]
        state["active_batch"] = None
    state.update({"updated_at": _now(), "counts": _counts(records), "checkpoint": _now()})
    state["next_action"] = "review RDF patch proposals and validate, or resume the next batch"
    _atomic_write(STATE, json.dumps(state, indent=2, ensure_ascii=False) + "\n")
    _event("research_results_recorded", results=applied, results_file=str(path))
    _write_progress(state, records)
    perf_record("campaign_result_integration", time.perf_counter() - started,
                results=len(applied), findings=sum(x["finding_count"] for x in applied), source_file=path.name)
    return applied, state, records


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resume", action="store_true", help="build/resume the persistent queue and reserve the next batch")
    parser.add_argument("--refresh", action="store_true", help="re-enumerate RDF while preserving campaign metadata")
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--record", type=Path, help="merge a JSON results array into the active queue")
    parser.add_argument("--report", action="store_true", help="print compact queue and campaign state")
    args = parser.parse_args(argv)
    if args.record:
        applied, state, records = record_results(args.record)
        print(json.dumps({"recorded": applied, "counts": _counts(records), "active_batch": state.get("active_batch")}, indent=2))
        return
    if args.resume or args.refresh:
        active, state, records = resume(args.batch_size, refresh=args.refresh)
        print(json.dumps({"active_batch": active, "counts": _counts(records), "queue": str(QUEUE), "state": str(STATE), "progress": str(PROGRESS)}, indent=2))
        return
    if args.report:
        records = _read_queue()
        state = _read_state()
        print(json.dumps({"counts": _counts(records), "active_batch": state.get("active_batch"), "state": state}, indent=2))
        return
    parser.print_help()


if __name__ == "__main__":
    main()
