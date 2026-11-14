"""Generate an ontology-wide, entity-level completeness snapshot.

Run from the repository root with PYTHONPATH=backend .venv/bin/python -m app.enrichment_audit.
Missing positive edges are reported as unknowns, never as negative facts.
"""
import json
from collections import Counter
from pathlib import Path

from rdflib import Graph, RDF, RDFS, OWL, URIRef

from . import config
from .ontology import OP, OPX, load_sources, load_upstream, load_ext, materialize, is_domain_triple, nonreflexive_same_as, clashes
from .patching import functional_conflicts
from .validation import shacl_report


def ids(graph, cls):
    return set(graph.subjects(RDF.type, cls))


def linked(graph, subjects, prop):
    return {s for s in subjects if any(graph.objects(s, prop))}


def labels(graph):
    return {s: sorted(map(str, graph.objects(s, RDFS.label))) for s in set(graph.subjects(RDF.type, None))}


def reviewed_batch_entities(root, batch_number):
    path = root / "work" / "research" / f"batch-{batch_number:03d}-results.json"
    if not path.exists():
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    results = data.get("results", []) if isinstance(data, dict) else data
    return len({row.get("entity_uri") for row in results if row.get("entity_uri")})


def property_inventory(graph):
    declared = set(graph.subjects(RDF.type, OWL.ObjectProperty)) | set(graph.subjects(RDF.type, OWL.DatatypeProperty))
    declared |= set(graph.subjects(RDF.type, RDF.Property))
    declared |= {p for _, p, _ in graph if isinstance(p, URIRef) and p not in (RDF.type, RDFS.label, OWL.imports)}
    functional = set(graph.subjects(RDF.type, OWL.FunctionalProperty))
    inverse_functional = set(graph.subjects(RDF.type, OWL.InverseFunctionalProperty))
    result = []
    for prop in sorted(declared, key=str):
        assertions = list(graph.triples((None, prop, None)))
        result.append({
            "predicate_uri": str(prop),
            "local_name": str(prop).rsplit("#", 1)[-1].rsplit("/", 1)[-1],
            "declared_object_property": (prop, RDF.type, OWL.ObjectProperty) in graph,
            "declared_datatype_property": (prop, RDF.type, OWL.DatatypeProperty) in graph,
            "assertion_count": len(assertions),
            "subjects": len({s for s, _, _ in assertions}),
            "domain_uris": sorted(map(str, graph.objects(prop, RDFS.domain))),
            "range_uris": sorted(map(str, graph.objects(prop, RDFS.range))),
            "functional": prop in functional,
            "inverse_functional": prop in inverse_functional,
            "inverse_uris": sorted(map(str, graph.objects(prop, OWL.inverseOf))),
            "game_relationship": str(prop).startswith((config.OP, config.OPX)) and bool(assertions),
        })
    return result


def coverage(graph, inferred=None):
    characters = ids(graph, OP.Character)
    fruits = ids(graph, OP.DevilFruit)
    ships = ids(graph, OPX.Ship)
    categories = {"Character": characters, "DevilFruit": fruits, "Ship": ships,
                  "Bounty": ids(graph, OP.Bounty)}
    view = graph + inferred if inferred is not None else graph
    properties = {
        "character_affiliation": (characters, OP.affiliatesWith),
        "character_occupation": (characters, OP.occupation),
        "character_devil_fruit": (characters, OP.hasDevilFruit),
        "character_haki_profile": (characters, OPX.hasHaki),
        "fruit_type": (fruits, OP.hasFruitType),
        "fruit_current_user": (fruits, OP.DevilFruitCurrentUser),
        "fruit_previous_user": (fruits, OP.DevilFruitPreviousUser),
        "fruit_subtype": (fruits, OPX.hasFruitSubtype),
        "ship_operator": (ships, OPX.operatedBy),
        "ship_owner": (ships, OPX.shipOwner),
        "ship_type": (ships, OPX.shipType),
    }
    result = {"entities_by_class": {k: len(v) for k, v in categories.items()},
              "asserted_triples": len(graph), "property_coverage": {}}
    result["property_coverage"] = {
        key: {"entities_with_fact": len(linked(view, subjects, pred)), "eligible_entities": len(subjects),
              "coverage_rate": round(len(linked(view, subjects, pred)) / len(subjects), 4) if subjects else None,
              "missing_entity_uris": sorted(map(str, subjects - linked(view, subjects, pred)))}
        for key, (subjects, pred) in properties.items()
    }
    result["relationship_assertions"] = {
        key: len(list(view.triples((None, pred, None)))) for key, (_, pred) in properties.items()
    }
    return result, categories


def main():
    root = config.ROOT
    upstream = load_upstream()
    base, ext = load_sources()
    current = base + ext
    # The first enrichment batch is one isolated RDF patch. Remove its additions to
    # produce an exact counterfactual graph without changing other corrections.
    haki_patch = root / "ontology/patches/haki.add.ttl"
    patch_graph = Graph().parse(str(haki_patch), format="turtle")
    # Do not remove patch triples that are already asserted by upstream data
    # (the character types, for example). Only discard triples supplied solely
    # by this enrichment patch.
    counterfactual = current - (patch_graph - upstream)
    before_inferred, before_dropped = materialize(counterfactual)
    after_inferred, after_dropped = materialize(current)
    prior, _ = coverage(counterfactual, before_inferred)
    after, _ = coverage(current, after_inferred)
    campaign_path = root / "ontology/patches/campaign-batch-001.add.ttl"
    campaign_patch = Graph().parse(str(campaign_path), format="turtle") if campaign_path.exists() else Graph()
    campaign_before_graph = current - (campaign_patch - upstream)
    campaign_before_inferred, campaign_before_dropped = materialize(campaign_before_graph)
    campaign_before, _ = coverage(campaign_before_graph, campaign_before_inferred)
    campaign2_path = root / "ontology/patches/campaign-batch-002.add.ttl"
    campaign2_patch = Graph().parse(str(campaign2_path), format="turtle") if campaign2_path.exists() else Graph()
    campaign2_before_graph = current - (campaign2_patch - upstream)
    campaign2_before_inferred, campaign2_before_dropped = materialize(campaign2_before_graph)
    campaign2_before, _ = coverage(campaign2_before_graph, campaign2_before_inferred)
    campaign3_path = root / "ontology/patches/campaign-batch-003.add.ttl"
    campaign3_patch = Graph().parse(str(campaign3_path), format="turtle") if campaign3_path.exists() else Graph()
    campaign3_before_graph = current - (campaign3_patch - upstream)
    campaign3_before_inferred, campaign3_before_dropped = materialize(campaign3_before_graph)
    campaign3_before, _ = coverage(campaign3_before_graph, campaign3_before_inferred)
    campaign4_path = root / "ontology/patches/campaign-batch-004.add.ttl"
    campaign4_patch = Graph().parse(str(campaign4_path), format="turtle") if campaign4_path.exists() else Graph()
    campaign4_remove_path = root / "ontology/patches/campaign-batch-004.remove.ttl"
    campaign4_remove = Graph().parse(str(campaign4_remove_path), format="turtle") if campaign4_remove_path.exists() else Graph()
    campaign4_before_graph = (current - (campaign4_patch - upstream)) + campaign4_remove
    campaign4_before_inferred, campaign4_before_dropped = materialize(campaign4_before_graph)
    campaign4_before, _ = coverage(campaign4_before_graph, campaign4_before_inferred)
    campaign5_path = root / "ontology/patches/campaign-batch-005.add.ttl"
    campaign5_patch = Graph().parse(str(campaign5_path), format="turtle") if campaign5_path.exists() else Graph()
    campaign5_before_graph = current - (campaign5_patch - upstream)
    campaign5_before_inferred, campaign5_before_dropped = materialize(campaign5_before_graph)
    campaign5_before, _ = coverage(campaign5_before_graph, campaign5_before_inferred)
    campaign6_path = root / "ontology/patches/campaign-batch-006.add.ttl"
    campaign6_patch = Graph().parse(str(campaign6_path), format="turtle") if campaign6_path.exists() else Graph()
    campaign6_remove_path = root / "ontology/patches/campaign-batch-006.remove.ttl"
    campaign6_remove = Graph().parse(str(campaign6_remove_path), format="turtle") if campaign6_remove_path.exists() else Graph()
    campaign6_before_graph = (current - (campaign6_patch - upstream)) + campaign6_remove
    campaign6_before_inferred, campaign6_before_dropped = materialize(campaign6_before_graph)
    campaign6_before, _ = coverage(campaign6_before_graph, campaign6_before_inferred)
    campaign7_path = root / "ontology/patches/campaign-batch-007.add.ttl"
    campaign7_patch = Graph().parse(str(campaign7_path), format="turtle") if campaign7_path.exists() else Graph()
    campaign7_remove_path = root / "ontology/patches/campaign-batch-007.remove.ttl"
    campaign7_remove = Graph().parse(str(campaign7_remove_path), format="turtle") if campaign7_remove_path.exists() else Graph()
    campaign7_before_graph = (current - (campaign7_patch - upstream)) + campaign7_remove
    campaign7_before_inferred, campaign7_before_dropped = materialize(campaign7_before_graph)
    campaign7_before, _ = coverage(campaign7_before_graph, campaign7_before_inferred)
    campaign9_path = root / "ontology/patches/campaign-batch-009.add.ttl"
    campaign9_patch = Graph().parse(str(campaign9_path), format="turtle") if campaign9_path.exists() else Graph()
    campaign9_remove_path = root / "ontology/patches/campaign-batch-009.remove.ttl"
    campaign9_remove = Graph().parse(str(campaign9_remove_path), format="turtle") if campaign9_remove_path.exists() else Graph()
    campaign9_before_graph = (current - (campaign9_patch - upstream)) + campaign9_remove
    campaign9_before_inferred, campaign9_before_dropped = materialize(campaign9_before_graph)
    campaign9_before, _ = coverage(campaign9_before_graph, campaign9_before_inferred)
    campaign10_path = root / "ontology/patches/campaign-batch-010.add.ttl"
    campaign10_patch = Graph().parse(str(campaign10_path), format="turtle") if campaign10_path.exists() else Graph()
    campaign10_remove_path = root / "ontology/patches/campaign-batch-010.remove.ttl"
    campaign10_remove = Graph().parse(str(campaign10_remove_path), format="turtle") if campaign10_remove_path.exists() else Graph()
    campaign10_before_graph = (current - (campaign10_patch - upstream)) + campaign10_remove
    campaign10_before_inferred, campaign10_before_dropped = materialize(campaign10_before_graph)
    campaign10_before, _ = coverage(campaign10_before_graph, campaign10_before_inferred)
    campaign11_path = root / "ontology/patches/campaign-batch-011.add.ttl"
    campaign11_patch = Graph().parse(str(campaign11_path), format="turtle") if campaign11_path.exists() else Graph()
    campaign11_remove_path = root / "ontology/patches/campaign-batch-011.remove.ttl"
    campaign11_remove = Graph().parse(str(campaign11_remove_path), format="turtle") if campaign11_remove_path.exists() else Graph()
    campaign11_before_graph = (current - (campaign11_patch - upstream)) + campaign11_remove
    campaign11_before_inferred, campaign11_before_dropped = materialize(campaign11_before_graph)
    campaign11_before, _ = coverage(campaign11_before_graph, campaign11_before_inferred)
    campaign13_path = root / "ontology/patches/campaign-batch-013.add.ttl"
    campaign13_patch = Graph().parse(str(campaign13_path), format="turtle") if campaign13_path.exists() else Graph()
    campaign13_remove_path = root / "ontology/patches/campaign-batch-013.remove.ttl"
    campaign13_remove = Graph().parse(str(campaign13_remove_path), format="turtle") if campaign13_remove_path.exists() else Graph()
    campaign13_before_graph = (current - (campaign13_patch - upstream)) + campaign13_remove
    campaign13_before_inferred, campaign13_before_dropped = materialize(campaign13_before_graph)
    campaign13_before, _ = coverage(campaign13_before_graph, campaign13_before_inferred)
    campaign14_path = root / "ontology/patches/campaign-batch-014.add.ttl"
    campaign14_patch = Graph().parse(str(campaign14_path), format="turtle") if campaign14_path.exists() else Graph()
    campaign14_remove_path = root / "ontology/patches/campaign-batch-014.remove.ttl"
    campaign14_remove = Graph().parse(str(campaign14_remove_path), format="turtle") if campaign14_remove_path.exists() else Graph()
    campaign14_before_graph = (current - (campaign14_patch - upstream)) + campaign14_remove
    campaign14_before_inferred, campaign14_before_dropped = materialize(campaign14_before_graph)
    campaign14_before, _ = coverage(campaign14_before_graph, campaign14_before_inferred)
    campaign15_path = root / "ontology/patches/campaign-batch-015.add.ttl"
    campaign15_patch = Graph().parse(str(campaign15_path), format="turtle") if campaign15_path.exists() else Graph()
    campaign15_before_graph = current - (campaign15_patch - upstream)
    campaign15_before_inferred, campaign15_before_dropped = materialize(campaign15_before_graph)
    campaign15_before, _ = coverage(campaign15_before_graph, campaign15_before_inferred)
    campaign16_path = root / "ontology/patches/campaign-batch-016.add.ttl"
    campaign16_patch = Graph().parse(str(campaign16_path), format="turtle") if campaign16_path.exists() else Graph()
    campaign16_remove_path = root / "ontology/patches/campaign-batch-016.remove.ttl"
    campaign16_remove = Graph().parse(str(campaign16_remove_path), format="turtle") if campaign16_remove_path.exists() else Graph()
    campaign16_before_graph = (current - (campaign16_patch - upstream)) + campaign16_remove
    campaign16_before_inferred, campaign16_before_dropped = materialize(campaign16_before_graph)
    campaign16_before, _ = coverage(campaign16_before_graph, campaign16_before_inferred)
    campaign17_path = root / "ontology/patches/campaign-batch-017.add.ttl"
    campaign17_patch = Graph().parse(str(campaign17_path), format="turtle") if campaign17_path.exists() else Graph()
    campaign17_remove_path = root / "ontology/patches/campaign-batch-017.remove.ttl"
    campaign17_remove = Graph().parse(str(campaign17_remove_path), format="turtle") if campaign17_remove_path.exists() else Graph()
    campaign17_before_graph = (current - (campaign17_patch - upstream)) + campaign17_remove
    campaign17_before_inferred, campaign17_before_dropped = materialize(campaign17_before_graph)
    campaign17_before, _ = coverage(campaign17_before_graph, campaign17_before_inferred)
    campaign18_path = root / "ontology/patches/campaign-batch-018.add.ttl"
    campaign18_patch = Graph().parse(str(campaign18_path), format="turtle") if campaign18_path.exists() else Graph()
    campaign18_before_graph = current - (campaign18_patch - upstream)
    campaign18_before_inferred, campaign18_before_dropped = materialize(campaign18_before_graph)
    campaign18_before, _ = coverage(campaign18_before_graph, campaign18_before_inferred)
    campaign19_path = root / "ontology/patches/campaign-batch-019.add.ttl"
    campaign19_patch = Graph().parse(str(campaign19_path), format="turtle") if campaign19_path.exists() else Graph()
    campaign19_remove_path = root / "ontology/patches/campaign-batch-019.remove.ttl"
    campaign19_remove = Graph().parse(str(campaign19_remove_path), format="turtle") if campaign19_remove_path.exists() else Graph()
    campaign19_before_graph = (current - (campaign19_patch - upstream)) + campaign19_remove
    campaign19_before_inferred, campaign19_before_dropped = materialize(campaign19_before_graph)
    campaign19_before, _ = coverage(campaign19_before_graph, campaign19_before_inferred)
    campaign20_path = root / "ontology/patches/campaign-batch-020.add.ttl"
    campaign20_patch = Graph().parse(str(campaign20_path), format="turtle") if campaign20_path.exists() else Graph()
    campaign20_remove_path = root / "ontology/patches/campaign-batch-020.remove.ttl"
    campaign20_remove = Graph().parse(str(campaign20_remove_path), format="turtle") if campaign20_remove_path.exists() else Graph()
    campaign20_before_graph = (current - (campaign20_patch - upstream)) + campaign20_remove
    campaign20_before_inferred, campaign20_before_dropped = materialize(campaign20_before_graph)
    campaign20_before, _ = coverage(campaign20_before_graph, campaign20_before_inferred)
    campaign21_path = root / "ontology/patches/campaign-batch-021.add.ttl"
    campaign21_patch = Graph().parse(str(campaign21_path), format="turtle") if campaign21_path.exists() else Graph()
    campaign21_before_graph = current - (campaign21_patch - upstream)
    campaign21_before_inferred, campaign21_before_dropped = materialize(campaign21_before_graph)
    campaign21_before, _ = coverage(campaign21_before_graph, campaign21_before_inferred)
    campaign24_path = root / "ontology/patches/campaign-batch-024.add.ttl"
    campaign24_patch = Graph().parse(str(campaign24_path), format="turtle") if campaign24_path.exists() else Graph()
    campaign24_before_graph = current - (campaign24_patch - upstream)
    campaign24_before_inferred, campaign24_before_dropped = materialize(campaign24_before_graph)
    campaign24_before, _ = coverage(campaign24_before_graph, campaign24_before_inferred)
    campaign25_path = root / "ontology/patches/campaign-batch-025.add.ttl"
    campaign25_patch = Graph().parse(str(campaign25_path), format="turtle") if campaign25_path.exists() else Graph()
    campaign25_before_graph = current - (campaign25_patch - upstream)
    campaign25_before_inferred, campaign25_before_dropped = materialize(campaign25_before_graph)
    campaign25_before, _ = coverage(campaign25_before_graph, campaign25_before_inferred)
    campaign26_path = root / "ontology/patches/campaign-batch-026.add.ttl"
    campaign26_patch = Graph().parse(str(campaign26_path), format="turtle") if campaign26_path.exists() else Graph()
    campaign26_remove_path = root / "ontology/patches/campaign-batch-026.remove.ttl"
    campaign26_remove = Graph().parse(str(campaign26_remove_path), format="turtle") if campaign26_remove_path.exists() else Graph()
    campaign26_before_graph = (current - (campaign26_patch - upstream)) + campaign26_remove
    campaign26_before_inferred, campaign26_before_dropped = materialize(campaign26_before_graph)
    campaign26_before, _ = coverage(campaign26_before_graph, campaign26_before_inferred)
    campaign27_path = root / "ontology/patches/campaign-batch-027.add.ttl"
    campaign27_patch = Graph().parse(str(campaign27_path), format="turtle") if campaign27_path.exists() else Graph()
    campaign27_before_graph = current - (campaign27_patch - upstream)
    campaign27_before_inferred, campaign27_before_dropped = materialize(campaign27_before_graph)
    campaign27_before, _ = coverage(campaign27_before_graph, campaign27_before_inferred)
    campaign28_path = root / "ontology/patches/campaign-batch-028.add.ttl"
    campaign28_patch = Graph().parse(str(campaign28_path), format="turtle") if campaign28_path.exists() else Graph()
    campaign28_before_graph = current - (campaign28_patch - upstream)
    campaign28_before_inferred, campaign28_before_dropped = materialize(campaign28_before_graph)
    campaign28_before, _ = coverage(campaign28_before_graph, campaign28_before_inferred)
    campaign29_path = root / "ontology/patches/campaign-batch-029.add.ttl"
    campaign29_patch = Graph().parse(str(campaign29_path), format="turtle") if campaign29_path.exists() else Graph()
    campaign29_before_graph = current - (campaign29_patch - upstream)
    campaign29_before_inferred, campaign29_before_dropped = materialize(campaign29_before_graph)
    campaign29_before, _ = coverage(campaign29_before_graph, campaign29_before_inferred)
    campaign30_path = root / "ontology/patches/campaign-batch-030.add.ttl"
    campaign30_patch = Graph().parse(str(campaign30_path), format="turtle") if campaign30_path.exists() else Graph()
    campaign30_remove_path = root / "ontology/patches/campaign-batch-030.remove.ttl"
    campaign30_remove = Graph().parse(str(campaign30_remove_path), format="turtle") if campaign30_remove_path.exists() else Graph()
    campaign30_before_graph = (current - (campaign30_patch - upstream)) + campaign30_remove
    campaign30_before_inferred, campaign30_before_dropped = materialize(campaign30_before_graph)
    campaign30_before, _ = coverage(campaign30_before_graph, campaign30_before_inferred)
    campaign31_path = root / "ontology/patches/campaign-batch-031.add.ttl"
    campaign31_patch = Graph().parse(str(campaign31_path), format="turtle") if campaign31_path.exists() else Graph()
    campaign31_before_graph = current - (campaign31_patch - upstream)
    campaign31_before_inferred, campaign31_before_dropped = materialize(campaign31_before_graph)
    campaign31_before, _ = coverage(campaign31_before_graph, campaign31_before_inferred)
    campaign32_path = root / "ontology/patches/campaign-batch-032.add.ttl"
    campaign32_patch = Graph().parse(str(campaign32_path), format="turtle") if campaign32_path.exists() else Graph()
    campaign32_before_graph = current - (campaign32_patch - upstream)
    campaign32_before_inferred, campaign32_before_dropped = materialize(campaign32_before_graph)
    campaign32_before, _ = coverage(campaign32_before_graph, campaign32_before_inferred)
    domain_before = sum(is_domain_triple(t) for t in before_inferred)
    domain_after = sum(is_domain_triple(t) for t in after_inferred)
    characters = ids(current, OP.Character)
    fruits = ids(current, OP.DevilFruit)
    ships = ids(current, OPX.Ship)
    uri_nodes = {u for t in current for u in t if isinstance(u, URIRef)}
    typed_nodes = set(current.subjects(RDF.type, None))
    broken = sorted(str(u) for u in uri_nodes if str(u).startswith(config.OP) and u not in typed_nodes
                    and any(current.triples((None, None, u))))
    label_map = labels(current)
    duplicate_labels = {}
    for u, values in label_map.items():
        if len(values) > 1:
            duplicate_labels[str(u)] = values
    same_label_entities = {}
    for entity, values in label_map.items():
        for value in values:
            same_label_entities.setdefault(value.casefold(), []).append(str(entity))
    duplicate_entity_labels = {label: sorted(set(entities)) for label, entities in same_label_entities.items()
                               if len(set(entities)) > 1}
    report = {
        "generated_by": "backend.app.enrichment_audit",
        "patch_scope": "The Haki counterfactual omits haki.add.ttl only; campaign patches are included on both sides. Each campaign_batch_N comparison omits that batch's additions on its before side; batches 004, 006, 007, 009, 010, 011, 013, 014, 016, 017, 019, 020, 026, and 030 restore their removed triples. Batch 011 also corrects one rule-derived organization classification in ontology.py.",
        "before": prior,
        "after": after,
        "deltas": {
            "asserted_triples": after["asserted_triples"] - prior["asserted_triples"],
            "haki_assertions": after["relationship_assertions"]["character_haki_profile"] - prior["relationship_assertions"]["character_haki_profile"],
            "characters_with_known_haki": after["property_coverage"]["character_haki_profile"]["entities_with_fact"] - prior["property_coverage"]["character_haki_profile"]["entities_with_fact"],
        },
        "campaign_batch_001": {
            "before": campaign_before,
            "after": after,
            "deltas": {
                "asserted_triples": after["asserted_triples"] - campaign_before["asserted_triples"],
                "inferred_triples": len(after_inferred) - len(campaign_before_inferred),
                "character_haki_assertions": after["relationship_assertions"]["character_haki_profile"] - campaign_before["relationship_assertions"]["character_haki_profile"],
                "characters_with_known_haki": after["property_coverage"]["character_haki_profile"]["entities_with_fact"] - campaign_before["property_coverage"]["character_haki_profile"]["entities_with_fact"],
            },
            "reasoning_before": {"nonreflexive_same_as": len(nonreflexive_same_as(campaign_before_inferred)),
                                 "owlrl_clashes": len(clashes(campaign_before_inferred)),
                                 "functional_properties_dropped": campaign_before_dropped},
            "research_batch_entities": 20,
            "new_source_backed_assertions": 3,
            "unverified_or_unmodeled_candidates_held": ["Mihawk Observation Haki", "O-Tsuru alias", "Vegapunk leadership of SSG", "Nojiko adopted-sibling relation"],
        },
        "campaign_batch_002": {
            "before": campaign2_before,
            "after": after,
            "deltas": {
                "asserted_triples": after["asserted_triples"] - campaign2_before["asserted_triples"],
                "inferred_triples": len(after_inferred) - len(campaign2_before_inferred),
                "character_haki_assertions": after["relationship_assertions"]["character_haki_profile"] - campaign2_before["relationship_assertions"]["character_haki_profile"],
                "characters_with_known_haki": after["property_coverage"]["character_haki_profile"]["entities_with_fact"] - campaign2_before["property_coverage"]["character_haki_profile"]["entities_with_fact"],
                "devil_fruits": after["entities_by_class"]["DevilFruit"] - campaign2_before["entities_by_class"]["DevilFruit"],
            },
            "reasoning_before": {"nonreflexive_same_as": len(nonreflexive_same_as(campaign2_before_inferred)),
                                 "owlrl_clashes": len(clashes(campaign2_before_inferred)),
                                 "functional_properties_dropped": campaign2_before_dropped},
            "research_batch_entities": 20,
            "source_backed_entities_changed": 9,
            "unverified_or_unmodeled_candidates_held": ["Belle-Mere foster-family relation", "Buckingham Stussy parent relation", "Praline-Aladdin spouse relation", "Ginny-Bonney parent relation", "Clover brother relation", "Tonta Corps leadership and explicit Tontatta species", "historical role intervals"],
        },
        "campaign_batch_003": {
            "before": campaign3_before,
            "after": after,
            "deltas": {
                "asserted_triples": after["asserted_triples"] - campaign3_before["asserted_triples"],
                "inferred_triples": len(after_inferred) - len(campaign3_before_inferred),
                "devil_fruits": after["entities_by_class"]["DevilFruit"] - campaign3_before["entities_by_class"]["DevilFruit"],
                "bounties": after["entities_by_class"].get("Bounty", 0) - campaign3_before["entities_by_class"].get("Bounty", 0),
            },
            "reasoning_before": {"nonreflexive_same_as": len(nonreflexive_same_as(campaign3_before_inferred)),
                                 "owlrl_clashes": len(clashes(campaign3_before_inferred)),
                                 "functional_properties_dropped": campaign3_before_dropped},
            "research_batch_entities": 20,
            "new_source_backed_assertions": 25,
            "unverified_or_unmodeled_candidates_held": ["Hody species vocabulary", "Karoo composite affiliations and companion relation", "Mozu and Kiwi identity split", "family relationships", "Kureha mentor relation", "Merry ship designer relation", "Mohji and Richie relation", "historical role intervals", "conflicting Nami height and birth date values"],
        },
        "campaign_batch_004": {
            "before": campaign4_before,
            "after": after,
            "deltas": {
                "asserted_triples": after["asserted_triples"] - campaign4_before["asserted_triples"],
                "inferred_triples": len(after_inferred) - len(campaign4_before_inferred),
                "devil_fruits": after["entities_by_class"]["DevilFruit"] - campaign4_before["entities_by_class"]["DevilFruit"],
            },
            "reasoning_before": {"nonreflexive_same_as": len(nonreflexive_same_as(campaign4_before_inferred)),
                                 "owlrl_clashes": len(clashes(campaign4_before_inferred)),
                                 "functional_properties_dropped": campaign4_before_dropped},
            "research_batch_entities": 20,
            "new_source_backed_assertions": 37,
            "removed_incorrect_assertions": [{"triple": "op:Mero_Mero_no_Mi op:DevilFruitCurrentUser <http://kalnassag.com/onepiece/Boa_Hancock;_S-Snake>", "reason": "Upstream scraper concatenated distinct names into one untyped URI. Official profiles identify Boa Hancock as the fruit user and S-Snake's power as Green Blood-mediated; the corrected edge is separately sourced."}],
            "unverified_or_unmodeled_candidates_held": ["S-Snake's copied Devil Fruit power relation", "Zeus Homie/subordinate relationship and temporal affiliations", "Nekomamushi's relation to Inuarashi", "Vivi parent relation", "Sai family and engagement relations", "former pirate / past membership temporal scopes"],
        },
        "campaign_batch_005": {
            "before": campaign5_before,
            "after": after,
            "deltas": {
                "asserted_triples": after["asserted_triples"] - campaign5_before["asserted_triples"],
                "inferred_triples": len(after_inferred) - len(campaign5_before_inferred),
                "bounties": after["entities_by_class"].get("Bounty", 0) - campaign5_before["entities_by_class"].get("Bounty", 0),
            },
            "reasoning_before": {"nonreflexive_same_as": len(nonreflexive_same_as(campaign5_before_inferred)),
                                 "owlrl_clashes": len(clashes(campaign5_before_inferred)),
                                 "functional_properties_dropped": campaign5_before_dropped},
            "research_batch_entities": 20,
            "new_source_backed_assertions": 33,
            "unverified_or_unmodeled_candidates_held": ["family/sibling relations", "Diamante former-bounty interval", "Gill Bastar Horo-Horo previous-user attribution", "Issho literal gloss modeled as alias", "Jabra CP0 affiliation and fruit URI/label", "Kaku fruit URI/label", "Leo Tontatta Army role", "Jinbe whale-shark granularity", "Charlotte Pudding voice-actor identity"],
        },
        "campaign_batch_006": {
            "before": campaign6_before,
            "after": after,
            "deltas": {
                "asserted_triples": after["asserted_triples"] - campaign6_before["asserted_triples"],
                "inferred_triples": len(after_inferred) - len(campaign6_before_inferred),
                "bounties": after["entities_by_class"].get("Bounty", 0) - campaign6_before["entities_by_class"].get("Bounty", 0),
            },
            "reasoning_before": {"nonreflexive_same_as": len(nonreflexive_same_as(campaign6_before_inferred)),
                                 "owlrl_clashes": len(clashes(campaign6_before_inferred)),
                                 "functional_properties_dropped": campaign6_before_dropped},
            "research_batch_entities": 20,
            "new_source_backed_assertions": 41,
            "temporal_annotations": 17,
            "removed_incorrect_assertions": [
                {"triple": "op:Mikita op:temporaryAlias 'VIZ/4Kids: \\\"Ms. Valentine\\\"'@ja-latn", "reason": "The literal explicitly labels the string as VIZ/4Kids localization metadata, not an in-world alias; retained the Japanese name and Miss Valentine."},
                {"triple": "op:Pekoms op:temporaryAlias 'Viz: \\\"Mystoms\\\"'@ja-latn", "reason": "The literal explicitly labels the string as a Viz localization, not an in-world alias; retained Nazoms."},
                {"triple": "op:X_Drake op:temporaryAlias 'English version: Drie'@ja-latn", "reason": "The literal explicitly labels an English-version rendering, not an in-world alias; retained the Japanese name and Red Flag epithets."},
                {"triple": "op:Tsuru op:epithet 'Viz: \\\"Great Advisor\\\"'@ja-latn", "reason": "The literal explicitly labels a Viz translation, not an in-world epithet; retained Great Staff Officer and 大参謀."},
            ],
            "unverified_or_unmodeled_candidates_held": ["Morgans, Shinobu, Streusen, Sugar, Vasco Shot, and Viola profile gaps remain unknown where no safe delta was established", "temporal statements record profile-snapshot current status or historical status without inferred chapter intervals", "Shanks World Nobles affiliation remains for identity/relationship review"],
        },
        "campaign_batch_007": {
            "before": campaign7_before,
            "after": after,
            "deltas": {
                "asserted_triples": after["asserted_triples"] - campaign7_before["asserted_triples"],
                "inferred_triples": len(after_inferred) - len(campaign7_before_inferred),
                "bounties": after["entities_by_class"].get("Bounty", 0) - campaign7_before["entities_by_class"].get("Bounty", 0),
            },
            "reasoning_before": {"nonreflexive_same_as": len(nonreflexive_same_as(campaign7_before_inferred)),
                                 "owlrl_clashes": len(clashes(campaign7_before_inferred)),
                                 "functional_properties_dropped": campaign7_before_dropped},
            "research_batch_entities": 20,
            "new_source_backed_assertions": 23,
            "temporal_annotations": 20,
            "removed_incorrect_assertions": [
                {"triple": "op:Gomu_Gomu_no_Mi op:hasFruitType op:Paramecia", "reason": "The official Luffy profile discloses this same fruit as Hito Hito no Mi, Mythical Zoan, Model Nika; retaining Paramecia conflicts with the functional fruit-type property."}
            ],
            "unverified_or_unmodeled_candidates_held": ["Charlotte Newshi's Gocha-Gocha fruit-user assertion remains unverified because no official profile source was located", "Borsalino and Sakazuki bounty fields were not populated because their official profiles do not state a value", "Luffy's 3,000,000,000 bounty was confirmed as already recorded and not duplicated"],
        },
        "campaign_batch_008": {
            "before": after,
            "after": after,
            "deltas": {"asserted_triples": 0, "inferred_triples": 0},
            "research_batch_entities": 20,
            "new_source_backed_assertions": 0,
            "confirmed_existing_current_user_assertions": 20,
            "unverified_or_unmodeled_candidates_held": ["Fruit types not explicitly stated on 17 reviewed official profiles remain as existing assertions without source-level type confirmation", "No previous-user assertions were inferred from omitted profile details"],
        },
        "campaign_batch_009": {
            "before": campaign9_before,
            "after": after,
            "deltas": {
                "asserted_triples": after["asserted_triples"] - campaign9_before["asserted_triples"],
                "inferred_triples": len(after_inferred) - len(campaign9_before_inferred),
                "bounties": after["entities_by_class"].get("Bounty", 0) - campaign9_before["entities_by_class"].get("Bounty", 0),
            },
            "reasoning_before": {"nonreflexive_same_as": len(nonreflexive_same_as(campaign9_before_inferred)),
                                 "owlrl_clashes": len(clashes(campaign9_before_inferred)),
                                 "functional_properties_dropped": campaign9_before_dropped},
            "research_batch_entities": 20,
            "confirmed_existing_current_user_assertions": 20,
            "new_source_backed_assertions": 2,
            "removed_incorrect_assertions": [
                {"triple": '<http://kalnassag.com/onepiece/Neko_Neko_no_Mi,_Model:_Leopard> rdfs:label "ネコネコの実 モデル“”"@ja', "reason": "Official Rob Lucci profile supplies the complete Japanese fruit model name; the old empty quote is incomplete scraped text."},
                {"triple": '<http://kalnassag.com/onepiece/Ushi_Ushi_no_Mi,_Model:_Bison> rdfs:label "ウシウシの実 モデル"@ja', "reason": "Official Dalton profile supplies the complete Japanese bison model name; the old label omits the model name."},
            ],
            "unverified_or_unmodeled_candidates_held": ["Historical users for fruits other than the directly sourced Gura Gura record were not inferred", "Broad fruit types not explicitly named in official profiles were left unchanged"],
        },
        "campaign_batch_010": {
            "before": campaign10_before,
            "after": after,
            "deltas": {
                "asserted_triples": after["asserted_triples"] - campaign10_before["asserted_triples"],
                "inferred_triples": len(after_inferred) - len(campaign10_before_inferred),
                "bounties": after["entities_by_class"].get("Bounty", 0) - campaign10_before["entities_by_class"].get("Bounty", 0),
            },
            "reasoning_before": {"nonreflexive_same_as": len(nonreflexive_same_as(campaign10_before_inferred)),
                                 "owlrl_clashes": len(clashes(campaign10_before_inferred)),
                                 "functional_properties_dropped": campaign10_before_dropped},
            "research_batch_entities": 20,
            "confirmed_existing_fruit_current_users": 9,
            "new_source_backed_assertions": 5,
            "temporal_annotations": 2,
            "removed_incorrect_assertions": [
                {"triple": '<http://kalnassag.com/onepiece/Ushi_Ushi_no_Mi,_Model:_Giraffe> rdfs:label "ウシウシの実 モデル“”"@ja',
                 "reason": "The official Kaku profile supplies the complete 麒麟（ジラフ） model label; the old label omits it."}
            ],
            "unverified_or_unmodeled_candidates_held": [
                "Jiki Jiki prior-user John, Soru Soru prior-user Carmel, and the Ope Ope placeholder remain open pending direct primary-source evidence",
                "Ship owner/operation relations without explicit official wording and all unstated ship types remain unknown",
                "No official character profiles surfaced in this pass for Egana, Marumieta, or Oide; their existing assertions were not treated as false",
                "Judy's official profile says she was shot but does not establish death or recovery; her existing status was retained"
            ],
        },
        "campaign_batch_011": {
            "before": campaign11_before,
            "after": after,
            "deltas": {
                "asserted_triples": after["asserted_triples"] - campaign11_before["asserted_triples"],
                "inferred_triples": len(after_inferred) - len(campaign11_before_inferred),
            },
            "reasoning_before": {"nonreflexive_same_as": len(nonreflexive_same_as(campaign11_before_inferred)),
                                 "owlrl_clashes": len(clashes(campaign11_before_inferred)),
                                 "functional_properties_dropped": campaign11_before_dropped},
            "research_batch_entities": 20,
            "new_source_backed_assertions": 4,
            "removed_misclassifications_or_copied_labels": 8,
            "unverified_or_unmodeled_candidates_held": [
                "BellyOverview identity/type (currency article anchor versus character remains unresolved)",
                "Anjo East Blue origin versus Rogue Town profile location",
                "unmodeled family relations for Banchina and Aswa",
                "entities without an exact official profile in this review remain open"
            ],
        },
        "campaign_batch_013": {
            "before": campaign13_before,
            "after": after,
            "deltas": {
                "asserted_triples": after["asserted_triples"] - campaign13_before["asserted_triples"],
                "inferred_triples": len(after_inferred) - len(campaign13_before_inferred),
                "bounties": after["entities_by_class"].get("Bounty", 0) - campaign13_before["entities_by_class"].get("Bounty", 0),
            },
            "reasoning_before": {"nonreflexive_same_as": len(nonreflexive_same_as(campaign13_before_inferred)),
                                 "owlrl_clashes": len(clashes(campaign13_before_inferred)),
                                 "functional_properties_dropped": campaign13_before_dropped},
            "research_batch_entities": 20,
            "source_reviewed_entities_so_far": 6,
            "new_source_backed_assertions": 6,
            "temporal_annotations": 10,
            "removed_misclassifications_or_misused_relations": 6,
            "unverified_or_unmodeled_candidates_held": [
                "Hocker-Chouchou owner relation remains unmodeled; both misuse-as-affiliation edges were removed",
                "Fourteen active batch entities still require source review",
                "Island Eater status was not reinterpreted from defeat wording",
                "Helmeppo Cross Guild estimate is approximate and remains distinct from a Government bounty"
            ],
        },
        "campaign_batch_014": {
            "before": campaign14_before,
            "after": after,
            "deltas": {
                "asserted_triples": after["asserted_triples"] - campaign14_before["asserted_triples"],
                "inferred_triples": len(after_inferred) - len(campaign14_before_inferred),
                "devil_fruits": after["entities_by_class"].get("DevilFruit", 0) - campaign14_before["entities_by_class"].get("DevilFruit", 0),
            },
            "reasoning_before": {"nonreflexive_same_as": len(nonreflexive_same_as(campaign14_before_inferred)),
                                 "owlrl_clashes": len(clashes(campaign14_before_inferred)),
                                 "functional_properties_dropped": campaign14_before_dropped},
            "research_batch_entities": 20,
            "source_reviewed_entities_so_far": reviewed_batch_entities(root, 15),
            "new_source_backed_assertions": 7,
            "modeled_inferences": 1,
            "temporal_annotations": 7,
            "removed_misclassifications": 4,
            "unverified_or_unmodeled_candidates_held": [
                "Matsuge-to-Super Spot-Billed Duck Troops membership is ambiguous because the official profile header and official product copy characterize it differently",
                "Kumadori CP0 edge is not established by the reviewed official profile and remains open",
                "Eleven exact-name official-profile searches did not surface direct entries; no facts were negated"
            ],
        },
        "campaign_batch_015": {
            "before": campaign15_before,
            "after": after,
            "deltas": {
                "asserted_triples": after["asserted_triples"] - campaign15_before["asserted_triples"],
                "inferred_triples": len(after_inferred) - len(campaign15_before_inferred),
            },
            "reasoning_before": {"nonreflexive_same_as": len(nonreflexive_same_as(campaign15_before_inferred)),
                                 "owlrl_clashes": len(clashes(campaign15_before_inferred)),
                                 "functional_properties_dropped": campaign15_before_dropped},
            "research_batch_entities": 20,
            "source_reviewed_entities_so_far": 20,
            "new_source_backed_assertions": 2,
            "unresolved_exact_name_searches": 12,
        },
        "campaign_batch_016": {
            "before": campaign16_before,
            "after": after,
            "deltas": {
                "asserted_triples": after["asserted_triples"] - campaign16_before["asserted_triples"],
                "inferred_triples": len(after_inferred) - len(campaign16_before_inferred),
            },
            "reasoning_before": {"nonreflexive_same_as": len(nonreflexive_same_as(campaign16_before_inferred)),
                                 "owlrl_clashes": len(clashes(campaign16_before_inferred)),
                                 "functional_properties_dropped": campaign16_before_dropped},
            "research_batch_entities": 20,
            "source_reviewed_entities_so_far": reviewed_batch_entities(root, 16),
            "removed_unsupported_status_assertions": 1,
            "unverified_or_unmodeled_candidates_held": ["Tama URI identity", "Furiko and Lami family relations", "13 remaining source reviews"],
        },
        "campaign_batch_017": {
            "before": campaign17_before,
            "after": after,
            "deltas": {
                "asserted_triples": after["asserted_triples"] - campaign17_before["asserted_triples"],
                "inferred_triples": len(after_inferred) - len(campaign17_before_inferred),
            },
            "reasoning_before": {"nonreflexive_same_as": len(nonreflexive_same_as(campaign17_before_inferred)),
                                 "owlrl_clashes": len(clashes(campaign17_before_inferred)),
                                 "functional_properties_dropped": campaign17_before_dropped},
            "research_batch_entities": 20,
            "source_reviewed_entities_so_far": reviewed_batch_entities(root, 17),
            "removed_misclassifications": 2,
            "removed_unsupported_exact_age_assertions": 1,
            "unverified_or_unmodeled_candidates_held": ["Yosaku role temporal qualifiers", "Zunesha lower-bound age model", "17 remaining source reviews"],
        },
        "campaign_batch_018": {
            "before": campaign18_before,
            "after": after,
            "deltas": {
                "asserted_triples": after["asserted_triples"] - campaign18_before["asserted_triples"],
                "inferred_triples": len(after_inferred) - len(campaign18_before_inferred),
            },
            "reasoning_before": {"nonreflexive_same_as": len(nonreflexive_same_as(campaign18_before_inferred)),
                                 "owlrl_clashes": len(clashes(campaign18_before_inferred)),
                                 "functional_properties_dropped": campaign18_before_dropped},
            "research_batch_entities": 20,
            "source_reviewed_entities_so_far": reviewed_batch_entities(root, 18),
            "source_backed_entities_changed": 9,
            "unresolved_exact_name_searches": 10,
            "unverified_or_unmodeled_candidates_held": ["Akudai Kanzaburo, Asashichi, Asla, Atagoyama, Beak Remark, Beer VI, Bimine, Birdy, Bobomba, and Bunbuku exact identity/source review"],
        },
        "campaign_batch_019": {
            "before": campaign19_before,
            "after": after,
            "deltas": {
                "asserted_triples": after["asserted_triples"] - campaign19_before["asserted_triples"],
                "inferred_triples": len(after_inferred) - len(campaign19_before_inferred),
            },
            "reasoning_before": {"nonreflexive_same_as": len(nonreflexive_same_as(campaign19_before_inferred)),
                                 "owlrl_clashes": len(clashes(campaign19_before_inferred)),
                                 "functional_properties_dropped": campaign19_before_dropped},
            "research_batch_entities": 20,
            "source_reviewed_entities_so_far": reviewed_batch_entities(root, 19),
            "new_asserted_edges": 3,
            "historical_qualifiers": 1,
            "removed_misclassification_assertions": 1,
            "unresolved_exact_name_searches": 13,
        },
        "campaign_batch_020": {
            "before": campaign20_before,
            "after": after,
            "deltas": {
                "asserted_triples": after["asserted_triples"] - campaign20_before["asserted_triples"],
                "inferred_triples": len(after_inferred) - len(campaign20_before_inferred),
            },
            "reasoning_before": {"nonreflexive_same_as": len(nonreflexive_same_as(campaign20_before_inferred)),
                                 "owlrl_clashes": len(clashes(campaign20_before_inferred)),
                                 "functional_properties_dropped": campaign20_before_dropped},
            "research_batch_entities": 20,
            "source_reviewed_entities_so_far": reviewed_batch_entities(root, 20),
            "new_source_backed_edges": 4,
            "historical_qualifiers": 2,
            "removed_misclassification_assertions": 1,
            "unresolved_exact_name_searches": 11,
        },
        "campaign_batch_021": {
            "before": campaign21_before,
            "after": after,
            "deltas": {
                "asserted_triples": after["asserted_triples"] - campaign21_before["asserted_triples"],
                "inferred_triples": len(after_inferred) - len(campaign21_before_inferred),
            },
            "reasoning_before": {"nonreflexive_same_as": len(nonreflexive_same_as(campaign21_before_inferred)),
                                 "owlrl_clashes": len(clashes(campaign21_before_inferred)),
                                 "functional_properties_dropped": campaign21_before_dropped},
            "research_batch_entities": 20,
            "source_reviewed_entities_so_far": reviewed_batch_entities(root, 21),
            "new_source_backed_edges": 3,
            "unresolved_exact_name_searches": 16,
        },
        "campaign_batch_022": {"research_batch_entities": 20, "new_source_backed_edges": 0,
                               "unresolved_exact_name_searches": 19,
                               "rdf_delta": {"asserted_triples": 0, "inferred_triples": 0},
                               "note": "Two official editorial references were reviewed; neither justified a graph change."},
        "campaign_batch_023": {"research_batch_entities": 20, "new_source_backed_edges": 0,
                               "unresolved_exact_name_searches": 19,
                               "rdf_delta": {"asserted_triples": 0, "inferred_triples": 0},
                               "note": "Mornin was later resolved by a direct official profile follow-up; editorial speculation about Mummy disease was held without adding a fact."},
        "campaign_batch_024": {
            "before": campaign24_before,
            "after": after,
            "deltas": {
                "asserted_triples": after["asserted_triples"] - campaign24_before["asserted_triples"],
                "inferred_triples": len(after_inferred) - len(campaign24_before_inferred),
            },
            "reasoning_before": {"nonreflexive_same_as": len(nonreflexive_same_as(campaign24_before_inferred)),
                                 "owlrl_clashes": len(clashes(campaign24_before_inferred)),
                                 "functional_properties_dropped": campaign24_before_dropped},
            "research_batch_entities": 20,
            "source_reviewed_entities_so_far": reviewed_batch_entities(root, 24),
            "new_source_backed_edges": 6,
            "new_devil_fruits": 1,
            "historical_qualifiers": 2,
            "unresolved_exact_name_searches": 16,
            "late_source_followups": ["Mornin", "Rimoshifu_Killingham"],
        },
        "campaign_batch_025": {
            "before": campaign25_before,
            "after": after,
            "deltas": {
                "asserted_triples": after["asserted_triples"] - campaign25_before["asserted_triples"],
                "inferred_triples": len(after_inferred) - len(campaign25_before_inferred),
            },
            "reasoning_before": {"nonreflexive_same_as": len(nonreflexive_same_as(campaign25_before_inferred)),
                                 "owlrl_clashes": len(clashes(campaign25_before_inferred)),
                                 "functional_properties_dropped": campaign25_before_dropped},
            "research_batch_entities": 20,
            "source_reviewed_entities_so_far": reviewed_batch_entities(root, 25),
            "new_source_backed_edges": 3,
            "unresolved_exact_name_searches": 13,
            "source_reviewed_profiles": 7,
        },
        "campaign_batch_026": {
            "before": campaign26_before,
            "after": after,
            "deltas": {
                "asserted_triples": after["asserted_triples"] - campaign26_before["asserted_triples"],
                "inferred_triples": len(after_inferred) - len(campaign26_before_inferred),
            },
            "reasoning_before": {"nonreflexive_same_as": len(nonreflexive_same_as(campaign26_before_inferred)),
                                 "owlrl_clashes": len(clashes(campaign26_before_inferred)),
                                 "functional_properties_dropped": campaign26_before_dropped},
            "research_batch_entities": 20,
            "source_reviewed_entities_so_far": reviewed_batch_entities(root, 26),
            "new_source_backed_edges": 6,
            "new_typed_entities": [str(OP.Cocoa_Weed), str(OP.Hotel_Employee)],
            "removed_malformed_import_labels": 1,
            "unresolved_exact_name_searches": 11,
            "source_reviewed_profiles": 9,
        },
        "campaign_batch_027": {
            "before": campaign27_before, "after": after,
            "deltas": {"asserted_triples": after["asserted_triples"] - campaign27_before["asserted_triples"],
                       "inferred_triples": len(after_inferred) - len(campaign27_before_inferred)},
            "reasoning_before": {"nonreflexive_same_as": len(nonreflexive_same_as(campaign27_before_inferred)),
                                 "owlrl_clashes": len(clashes(campaign27_before_inferred)),
                                 "functional_properties_dropped": campaign27_before_dropped},
            "research_batch_entities": 20, "source_reviewed_entities_so_far": reviewed_batch_entities(root, 27),
            "new_source_backed_edges": 2, "unresolved_exact_name_searches": 16, "source_reviewed_profiles": 4,
        },
        "campaign_batch_028": {
            "before": campaign28_before, "after": after,
            "deltas": {"asserted_triples": after["asserted_triples"] - campaign28_before["asserted_triples"],
                       "inferred_triples": len(after_inferred) - len(campaign28_before_inferred)},
            "reasoning_before": {"nonreflexive_same_as": len(nonreflexive_same_as(campaign28_before_inferred)),
                                 "owlrl_clashes": len(clashes(campaign28_before_inferred)),
                                 "functional_properties_dropped": campaign28_before_dropped},
            "research_batch_entities": 20, "source_reviewed_entities_so_far": reviewed_batch_entities(root, 28),
            "new_source_backed_edges": 5, "new_typed_entities": [str(OP.Albion_Bounty_Profile)],
            "unresolved_exact_name_searches": 13, "source_reviewed_profiles": 7,
        },
        "campaign_batch_029": {
            "before": campaign29_before, "after": after,
            "deltas": {"asserted_triples": after["asserted_triples"] - campaign29_before["asserted_triples"],
                       "inferred_triples": len(after_inferred) - len(campaign29_before_inferred)},
            "reasoning_before": {"nonreflexive_same_as": len(nonreflexive_same_as(campaign29_before_inferred)),
                                 "owlrl_clashes": len(clashes(campaign29_before_inferred)),
                                 "functional_properties_dropped": campaign29_before_dropped},
            "research_batch_entities": 20, "source_reviewed_entities_so_far": reviewed_batch_entities(root, 29),
            "new_source_backed_edges": 0, "temporal_annotations": 3,
            "unresolved_exact_name_searches": 9, "source_reviewed_profiles": 11,
        },
        "campaign_batch_030": {
            "before": campaign30_before, "after": after,
            "deltas": {"asserted_triples": after["asserted_triples"] - campaign30_before["asserted_triples"],
                       "inferred_triples": len(after_inferred) - len(campaign30_before_inferred)},
            "reasoning_before": {"nonreflexive_same_as": len(nonreflexive_same_as(campaign30_before_inferred)),
                                 "owlrl_clashes": len(clashes(campaign30_before_inferred)),
                                 "functional_properties_dropped": campaign30_before_dropped},
            "research_batch_entities": 20, "source_reviewed_entities_so_far": reviewed_batch_entities(root, 30),
            "new_source_backed_edges": 2, "new_typed_entities": [str(OP.Bartholomew_Kuma_Former_Bounty_Profile)],
            "removed_malformed_assertions": 1, "temporal_annotations": 1,
            "unresolved_exact_name_searches": 19, "source_reviewed_profiles": 2,
        },
        "campaign_batch_031": {
            "before": campaign31_before, "after": after,
            "deltas": {"asserted_triples": after["asserted_triples"] - campaign31_before["asserted_triples"],
                       "inferred_triples": len(after_inferred) - len(campaign31_before_inferred)},
            "reasoning_before": {"nonreflexive_same_as": len(nonreflexive_same_as(campaign31_before_inferred)),
                                 "owlrl_clashes": len(clashes(campaign31_before_inferred)),
                                 "functional_properties_dropped": campaign31_before_dropped},
            "research_batch_entities": 20, "source_reviewed_entities_so_far": reviewed_batch_entities(root, 31),
            "new_source_backed_edges": 5,
            "new_typed_entities": ["http://kalnassag.com/onepiece/Kumo_Kumo_no_Mi,_Model:_Rosamygale_Grauvogeli",
                str(OP.Bepo_Bounty_Profile), str(OP.Black_Maria_Bounty_Profile), str(OP.Bluejam_Bounty_Profile), str(OP.Bobby_Funk_Bounty_Profile)],
            "new_fruit_subtypes": 1, "unresolved_exact_name_searches": 8, "source_reviewed_profiles": 12,
        },
        "campaign_batch_032": {
            "before": campaign32_before, "after": after,
            "deltas": {"asserted_triples": after["asserted_triples"] - campaign32_before["asserted_triples"],
                       "inferred_triples": len(after_inferred) - len(campaign32_before_inferred)},
            "reasoning_before": {"nonreflexive_same_as": len(nonreflexive_same_as(campaign32_before_inferred)),
                                 "owlrl_clashes": len(clashes(campaign32_before_inferred)),
                                 "functional_properties_dropped": campaign32_before_dropped},
            "research_batch_entities": 20, "source_reviewed_entities_so_far": reviewed_batch_entities(root, 32),
            "new_source_backed_edges": 1, "new_typed_entities": [str(OP.Brogy_Bounty_Profile)],
            "unresolved_exact_name_searches": 11, "source_reviewed_profiles": 9,
        },
        "reasoning": {
            "before": {"inferred_triples_total": len(before_inferred), "inferred_domain_triples": domain_before,
                       "nonreflexive_same_as": len(nonreflexive_same_as(before_inferred)), "owlrl_clashes": len(clashes(before_inferred)),
                       "functional_properties_dropped": before_dropped},
            "after": {"inferred_triples_total": len(after_inferred), "inferred_domain_triples": domain_after,
                      "nonreflexive_same_as": len(nonreflexive_same_as(after_inferred)), "owlrl_clashes": len(clashes(after_inferred)),
                      "functional_properties_dropped": after_dropped},
        },
        "shacl": {"patched": shacl_report(current), "upstream_unpatched": shacl_report(upstream + load_ext(upstream))},
        "structural_findings": {
            "property_inventory": property_inventory(current),
            "functional_property_conflicts": {str(p): len(v) for p, v in functional_conflicts(current).items()},
            "untyped_referenced_uris": broken,
            "entities_with_multiple_labels": duplicate_labels,
            "duplicate_labels_across_entities": duplicate_entity_labels,
            "inert_rdfs_inverseOf_axioms": [{"subject": str(s), "object": str(o)} for s, o in current.subject_objects(URIRef(str(RDFS) + "inverseOf"))],
        },
        "semantics": "Missing edges remain unknown. The coverage gap lists are not FALSE facts.",
    }
    report_path = root / "docs/ontology-enrichment-audit.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    unresolved = []
    campaign_state_path = root / "work/ontology-campaign-state.json"
    campaign_queue_path = root / "work/ontology-research-queue.jsonl"
    active_batch_id = None
    active_batch_members = []
    active_batch_remaining = []
    if campaign_state_path.exists() and campaign_queue_path.exists():
        campaign_state = json.loads(campaign_state_path.read_text())
        active_batch = campaign_state.get("active_batch") or {}
        active_batch_id = active_batch.get("batch_id")
        active_batch_members = active_batch.get("entity_uris", [])
        campaign_rows = {
            row["entity_uri"]: row
            for row in (json.loads(line) for line in campaign_queue_path.read_text().splitlines() if line.strip())
            if row.get("entity_uri") in active_batch_members
        }
        active_batch_remaining = [
            uri for uri in active_batch_members
            if campaign_rows.get(uri, {}).get("status") == "in_progress"
        ]
    for key, record in after["property_coverage"].items():
        unresolved.append({"id": key, "severity": "coverage-gap", "status": "incomplete / unknown",
                           "affected_entity_uris": record["missing_entity_uris"],
                           "count": len(record["missing_entity_uris"]),
                           "detail": "No positive assertion is recorded. This is not evidence that the relationship is false."})
    unresolved.extend([
        {"id": "campaign-batch-001-schema-review", "severity": "schema-review", "status": "open",
         "affected_entity_uris": [str(OP.Vegapunk), str(OP.Nojiko), str(OP.Tsurujo), str(OP.Dracule_Mihawk)], "count": 4,
         "detail": "Vegapunk's SSG leadership lacks a dedicated organization individual and leadership predicate; Nojiko's adopted-sibling relation lacks a relationship predicate and must not be owl:sameAs; O-Tsuru alias is medium confidence; Mihawk Observation Haki needs direct canon evidence."},
        {"id": "campaign-batch-002-schema-review", "severity": "schema-review", "status": "open",
         "affected_entity_uris": [str(OP["Bell-mère"]), str(OP.Buckingham_Stussy), str(OP.Charlotte_Praline), str(OP.Ginny), str(OP.Clou_D_Clover), str(OP.Bomba)], "count": 6,
         "detail": "Source-backed foster/parent/spouse/sibling relations lack dedicated predicates; do not coerce them to owl:sameAs or generic affiliation. Bomba's Tonta Corps leadership and explicit Tontatta species also lack a clear direct mapping. Existing time-unspecified occupation/affiliation statements for historical roles remain unaltered."},
        {"id": "campaign-batch-003-schema-review", "severity": "schema-review", "status": "open",
         "affected_entity_uris": [str(OP.Hody_Jones), str(OP.Karoo), str(OP.Kouzuki_Hiyori), str(OP.Kouzuki_Oden), str(OP.Kureha), str(OP.Merry), str(OP.Mohji), str(OP.Mozu_and_Kiwi), str(OP.Monkey_D_Dragon)], "count": 9,
         "detail": "Reviewed official-profile facts remain open where there is no safe vocabulary for race, animal companion/control, kinship, mentorship, ship design, composite-character identity, or role temporality. Nami's conflicting height and date assertions are retained pending source/time review."},
        {"id": "campaign-batch-004-schema-review", "severity": "schema-review", "status": "open",
         "affected_entity_uris": [str(OP.Zeus), str(OP.Bentham), str(OP.Boa_Hancock), str(OP["S-Snake"]), str(OP.Nekomamushi), str(OP.Nefertari_Vivi), str(OP.Sai), str(OP.Shakuyaku), str(OP.Yazaemon)], "count": 9,
         "detail": "S-Snake uses Mero-Mero powers through Green Blood rather than a modeled copied-power relation; Zeus Homie/subordinate relationships and time-qualified affiliations lack dedicated predicates; family, friendship, historical-role, and membership timing findings remain open."},
        {"id": "campaign-batch-005-schema-and-source-review", "severity": "schema-review", "status": "open",
         "affected_entity_uris": [str(OP.Charlotte_Brûlée), str(OP.Charlotte_Pudding), str(OP.Diamante), str(OP.Donquixote_Rosinante), str(OP.Gill_Bastar), str(OP.Giolla), str(OP.Issho), str(OP.Jabra), str(OP.Jinbe), str(OP.Kaku), str(OP.Leo)], "count": 11,
         "detail": "Kinship and family ordinal relations lack predicates; bounty records lack an explicit former/current interval; Gill's previous Horo-Horo use remains uncertain; Issho's literal gloss is modeled as an alias; Jabra CP0 and fruit identity need assertion-level review; Kaku fruit identity needs URI/label reconciliation; subgroup/army role, fish species, and voice-actor identity need safer mappings or source review. Missing official-profile bounty fields remain unknown."},
        {"id": "campaign-batch-006-schema-and-source-review", "severity": "schema-review", "status": "open",
         "affected_entity_uris": [str(OP.Morgans), str(OP.Shinobu), str(OP.Streusen), str(OP.Sugar), str(OP.Vasco_Shot), str(OP.Viola), str(OP.Shanks)], "count": 7,
         "detail": "Profile review yielded no safe new fact for several characters; these gaps remain unknown. New temporal annotations describe status at the official-profile snapshot or historical status without invented chapter intervals. Shanks' World Nobles affiliation requires identity and relation review."},
        {"id": "campaign-batch-007-source-review", "severity": "data-review", "status": "open",
         "affected_entity_uris": [str(OP.Charlotte_Newshi)], "count": 1,
         "detail": "The current-user relation for Gocha-Gocha no Mi / Charlotte Newshi lacked an authoritative official profile source in this pass. It remains unchanged and should not be treated as independently verified. Bounty fields absent from official profiles remain unknown."},
        {"id": "campaign-batch-010-source-review", "severity": "data-review", "status": "open",
         "affected_entity_uris": [str(OP.Egana), str(OP.Marumieta), str(OP.Oide), str(OP.Judy), str(OP.Soru_Soru_no_Mi),
                                  str(OP.Jiki_Jiki_no_Mi), str(OP.Ope_Ope_no_Mi), str(OPX.Red_Force), str(OPX.Moby_Dick),
                                  str(OP.Going_Merry), str(OPX.Thousand_Sunny)], "count": 11,
         "detail": "Exact-name official profiles did not surface for Egana, Marumieta, or Oide; Judy's official page does not establish death or recovery; three fruit previous-user assertions remain unverified; and some ship owner/operator semantics are not explicit in the reviewed official sources. No negative facts were inferred."},
        {"id": "campaign-batch-011-source-review", "severity": "data-review", "status": "open",
         "affected_entity_uris": [str(OP.Ally), str(OP.Anba), str(OP.Azuki), str(OP.Baburu), str(OP.BellyOverview),
                                  str(OP.Biyo), str(OP.Brontosaurus), str(OP.Chocho), str(OP.Chokyumei_no_Chosuke), str(OP.Colon), str(OP.Anjo)], "count": 11,
         "detail": "Several exact-name profiles were not independently surfaced in this pass. BellyOverview has a wiki Overview-fragment ID and currency-like labels but its Character identity is not disproven; it remains unresolved. Anjo's official page associates him with Rogue Town but does not establish East Blue as birthplace. Other missing profile fields remain unknown, not negative."},
        {"id": "campaign-batch-012-source-review", "severity": "data-review", "status": "open",
         "affected_entity_uris": [str(OP.Crocus), str(OP.Cyrano), str(OP.DR), str(OP.Daidalos), str(OP.Deigoro),
                                  str(OP["Domo-kun_and_Nnke-kun"]), str(OP.Doran), str(OP.Eiri), str(OP.Elbow), str(OP.Emet),
                                  str(OP.Esta), str(OP.Ettara_Chaunkai), str(OP.Fukumi), str(OP.Furika), str(OP.Gama_Pyonnosuke),
                                  str(OP.Gedatsu), str(OP.Genrin), str(OP.George_Black), str(OP.Gimlet), str(OP.Glutbunny)], "count": 20,
         "detail": "Potential individual-versus-affiliation type errors remain for Crocus, Gedatsu, Cyrano, and D.R.; Domo-kun and Nnke-kun are represented by a combined graph node although the official profile names one as the other's companion; and George Black's source identity conflicts with the Impel Down label. Doran/Dolan spelling and Emet's present operational status need further source review. No speculative split, deletion, or negative fact was applied."},
        {"id": "campaign-batch-013-open-gaps", "severity": "data-review", "status": "open",
         "affected_entity_uris": [str(OP.Gorobe), str(OP.Han), str(OP.Hana), str(OP.Hara), str(OP.Hilmungardr), str(OP.Hinokizu), str(OP.Jew_Wall),
                                  str(OP.Jugemu_Jugemuko), str(OP["Jörmungandr"]), str(OP.Kakukaku), str(OP.Kashigamis_Child), str(OP.Kinbo)], "count": 12,
         "detail": "All 20 entities in campaign batch 013 received a first-pass partial source review. These 12 still have unresolved identity, status, label, or profile fields; the gaps remain unknown rather than being guessed. Jew Wall's preferred label may conflate an author and an artifact; no authoritative direct source was found to resolve it. Hocker's Chouchou ownership remains unmodeled because no general person-to-pet ownership predicate exists."},
        {"id": "campaign-batch-021-open-profile-searches", "severity": "data-review", "status": "open",
         "affected_entity_uris": [str(getattr(OP, name)) for name in ("Hanji", "Happa_Yamao", "Haritsu_Kendiyo", "Herb", "Hiroshi", "Home", "Honner", "Hyoutauros", "Inoichibannosuke", "Inukai", "Isa", "Ishigo_Shitemanna", "Isuka", "Jean_Goen", "Kamekichi", "Kanezenny")],
         "count": 16,
         "detail": "Sixteen exact-name official-profile searches in campaign batch 021 did not surface a direct profile in this pass. Search failure is not evidence that the entities or existing assertions are false; retain these records as open-world unknowns."},
        {"id": "campaign-batch-022-open-profile-searches", "severity": "data-review", "status": "open",
         "affected_entity_uris": [str(getattr(OP, name)) for name in ("Kappa", "Kasa", "Kashigami", "Katsuzo", "Kazenbo", "Keith", "Kirinkodanuki", "Kirintauros", "Kisegawa", "Kobe", "Kotetsu", "Kouzuki_Moria", "Kumae", "Kuni", "Kurokoma", "Kurotsuru", "Kyukyu", "Lines", "Lionbuta")],
         "count": 19,
         "detail": "Nineteen direct exact-name official character-profile searches in campaign batch 022 did not resolve the profiles in this pass. Existing facts remain open-world unknowns; no negative assertions were inferred."},
        {"id": "campaign-batch-022-moria-identity-review", "severity": "data-review", "status": "open",
         "affected_entity_uris": [str(OP.Kouzuki_Moria)], "count": 1,
         "detail": "An official editorial column discusses a possible Kozuki-clan/Wano connection for Moria but explicitly leaves it uncertain. No affiliation or identity reconciliation was applied."},
        {"id": "campaign-batch-023-open-profile-searches", "severity": "data-review", "status": "open",
         "affected_entity_uris": [str(getattr(OP, name)) for name in ("Lord_of_the_Coast", "Louis_Arnote", "Marin", "Master", "Master_of_the_Waters", "Mato", "Matryo_Princesses", "Mecha-Shark", "Mishoin_Cashible", "Mizerka", "Monjii", "Mororon", "Mottled", "Mr_Love", "Mummy", "Nako", "Natto", "Negikuma_Maria", "Nola")],
         "count": 19,
         "detail": "Nineteen exact-name official-profile searches in campaign batch 023 did not surface direct profiles in that pass. Mornin was resolved by a later official profile follow-up. Remaining facts stay open-world unknowns; no negative assertions were inferred."},
        {"id": "campaign-batch-024-open-profile-searches", "severity": "data-review", "status": "open",
         "affected_entity_uris": [str(getattr(OP, name)) for name in ("Norinosuke", "Nyasha", "Nyornyo_Nyarmani", "Outlook_III", "Pandaman", "Pandawomanmi", "Pandora", "Papaneel", "Pascia", "Potsun", "Pudos", "Raccoon", "Recycle-Wan", "Ririka", "Roji", "Roronoa_Pinzoro")],
         "count": 16,
         "detail": "Sixteen exact-name official-profile searches in campaign batch 024 did not surface direct profiles in this pass. Existing facts remain open-world unknowns; no negative assertions were inferred."},
        {"id": "campaign-batch-025-open-profile-searches", "severity": "data-review", "status": "open",
         "affected_entity_uris": [str(getattr(OP, name)) for name in ("Royder", "Sam", "Sapi", "Sarfunkel", "Satchels_Maffey", "Scales", "Sea_Boar", "Sennorikyuru", "Serizawa", "Seto", "Shanba", "Shin_Detamaruka", "Smooge")],
         "count": 13,
         "detail": "Thirteen exact-name official-profile searches in campaign batch 025 did not surface direct profiles in this pass. Missing evidence does not establish that the entities or their current assertions are false."},
        {"id": "campaign-batch-026-open-profile-searches", "severity": "data-review", "status": "open",
         "affected_entity_uris": [str(getattr(OP, name)) for name in ("Some", "Sugamichi_and_Warazane", "Sukune", "Tabuhachiro", "Taka", "Tarara", "Tegata_Ringana", "Teru", "Tomatito", "Tomozo", "Tonjil")],
         "count": 11,
         "detail": "Eleven exact-name official-profile searches in campaign batch 026 did not surface direct profiles in this pass. Missing evidence does not establish that the entities or their current assertions are false."},
        {"id": f"{active_batch_id or 'active-campaign'}-source-review", "severity": "data-review", "status": "in_progress" if active_batch_id else "closed",
         "affected_entity_uris": active_batch_remaining, "count": len(active_batch_remaining),
         "detail": f"{len(active_batch_members) - len(active_batch_remaining)} of {len(active_batch_members)} entities in active batch {active_batch_id} have source reviews." if active_batch_id else "No source-review batch is currently reserved."},
        {"id": "marine-rank-temporality", "severity": "data-review", "status": "temporal vocabulary implemented; legacy assertions remain unqualified",
         "affected_entity_uris": [], "count": 0,
         "detail": "The additive temporal statement vocabulary is available, but no current/former rank was assigned without dated evidence. Existing op:occupation facts remain unchanged and time-unspecified."},
        {"id": "organization-membership-temporality", "severity": "data-review", "status": "temporal vocabulary implemented; legacy assertions remain unqualified",
         "affected_entity_uris": [], "count": 0,
         "detail": "The additive temporal statement vocabulary is available, but no memberships were converted without dated evidence. Existing op:affiliatesWith facts remain unchanged and time-unspecified."},
        {"id": "devil-fruit-type-enumeration", "severity": "schema-review", "status": "unresolved",
         "affected_entity_uris": [], "count": 0,
         "detail": "The upstream OWL oneOf has three fruit types while data contains named extensions; preserve upstream and review a future open-class migration."},
        {"id": "inert-inverse-axiom", "severity": "schema-review", "status": "unresolved",
         "affected_entity_uris": [], "count": len(report["structural_findings"]["inert_rdfs_inverseOf_axioms"]),
         "detail": "Upstream uses rdfs:inverseOf for hasBounty/givenTo; current correction is documented but not patched because the properties are not game-used."},
    ])
    unresolved_path = root / "docs/ontology-enrichment-unresolved.json"
    unresolved_path.write_text(json.dumps({"generated_by": "backend.app.enrichment_audit", "findings": unresolved}, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"report": str(report_path), "unresolved": str(unresolved_path), "before": prior, "after": after,
                      "deltas": report["deltas"], "reasoning": report["reasoning"], "shacl": report["shacl"]}, indent=2))


if __name__ == "__main__":
    main()
