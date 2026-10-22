"""Builds the full RDF->graph model from the real upstream files (no Fuseki needed). ~25 s because of owlrl."""
import pytest

from rdflib import URIRef

from app import graph
from app.ingestion import build_model, to_graphs


@pytest.fixture(scope="module")
def model():
    return build_model()


def test_counts_and_provenance(model):
    nodes, edges, _, report = model
    assert report["entities"]["Character"] >= 1500 and report["entities"]["DevilFruit"] >= 134 and report["entities"]["Ship"] == 9
    assert {e["provenance"] for e in edges} == {"explicit", "curated", "inferred"}


def test_original_uris_preserved(model):
    nodes, *_ = model
    assert "http://kalnassag.com/onepiece#Monkey_D_Luffy" in nodes
    assert "http://kalnassag.com/onepiece/Hebi_Hebi_no_Mi,_Model:_Anaconda" in nodes   # odd upstream namespace kept verbatim


def test_luffy_inferred_facts(model):
    nodes, edges, *_ = model
    luffy = nodes["http://kalnassag.com/onepiece#Monkey_D_Luffy"]
    assert {"DevilFruitUser", "PirateAffiliatedCharacter", "HakiUser"} <= luffy["inferred_types"]
    # Luffy's own link is asserted (curated typo fix of op:hasdevilFruit); Marco's comes from the inverse of the fruit's current user
    assert any(e["t"] == "HAS_DEVIL_FRUIT" and e["s"] == luffy["uri"] and e["provenance"] == "curated" for e in edges)
    assert any(e["t"] == "HAS_DEVIL_FRUIT" and e["s"].endswith("#Marco") and e["provenance"] == "inferred" for e in edges)


def test_inferred_category_types_do_not_create_entities(model):
    nodes, *_ = model
    assert all(n["category"] is None or n["category"] in n["explicit_types"] for n in nodes.values())


def test_no_merges_no_dropped_axioms_shacl_clean(model):
    *_, report = model
    assert report["owl_sameAs_non_reflexive"] == 0
    assert report["functional_axioms_dropped_for_reasoning"] == []
    assert report["shacl"]["violations"] == 0


def test_blackbeard_and_law_fruit_links_repaired(model):
    nodes, edges, *_ = model
    for who, fruit in (("Marshall_D_Teach", "Yami_Yami_no_Mi"), ("Trafalgar_D_Water_Law", "Ope_Ope_no_Mi")):
        assert any(e["t"] == "HAS_DEVIL_FRUIT" and e["s"].endswith("#" + who) and e["o"].endswith("#" + fruit) for e in edges)


def test_named_graphs_carry_provenance_and_game_data(model):
    nodes, edges, types, _ = model
    gs = to_graphs(nodes, edges, types)
    luffy, g = URIRef("http://kalnassag.com/onepiece#Monkey_D_Luffy"), graph.G
    marco = URIRef("http://kalnassag.com/onepiece#Marco")
    inferred_fruit = next(e for e in edges if e["t"] == "HAS_DEVIL_FRUIT" and e["s"] == str(marco) and e["provenance"] == "inferred")
    assert (marco, URIRef(inferred_fruit["predicate"]), URIRef(inferred_fruit["o"])) in gs["inferred"]
    assert (marco, URIRef(inferred_fruit["predicate"]), URIRef(inferred_fruit["o"])) not in gs["explicit"]
    assert gs["game"].value(luffy, URIRef(g + "category")).toPython() == "Character"
    assert gs["game"].value(luffy, URIRef(g + "popularity")).toPython() > 40
    assert gs["game"].value(URIRef(inferred_fruit["predicate"]), URIRef(g + "relType")).toPython() == "HAS_DEVIL_FRUIT"
