from rdflib import Graph, RDF, URIRef

from app import ontology as o

TTL = """
@prefix op: <http://kalnassag.com/onepiece#> . @prefix opx: <http://kalnassag.com/onepiece-ext#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
op:Luffy a op:Character ; op:affiliatesWith op:Straw_Hat_Pirates ; op:animeDebut op:Episode_1, op:Episode_2 .
op:Gomu a op:DevilFruit ; op:DevilFruitCurrentUser op:Luffy .
op:Straw_Hat_Pirates a op:Affiliation, opx:PirateOrganization .
opx:Phoenix a op:DevilFruit ; opx:hasFruitSubtype opx:MythicalZoan .
op:animeDebut a owl:FunctionalProperty .
"""


def reasoned():
    base = Graph(); base.parse(data=TTL, format="turtle")
    ext = Graph(); ext.parse(str(o.config.ROOT / "ontology/extension.ttl"), format="turtle")
    inf, _ = o.materialize(base + ext)
    return base, inf


def test_inverse_property_materialised():
    _, inf = reasoned()
    assert (o.OP.Luffy, o.OP.hasDevilFruit, o.OP.Gomu) in inf


def test_restriction_class_inferred():
    _, inf = reasoned()
    assert (o.OP.Luffy, RDF.type, o.OPX.PirateAffiliatedCharacter) in inf
    assert (o.OP.Luffy, RDF.type, o.OPX.DevilFruitUser) in inf      # chained: inverse -> someValuesFrom


def test_property_chain_gives_fruit_subtype_parent():
    _, inf = reasoned()
    assert (o.OPX.Phoenix, o.OP.hasFruitType, o.OP.Zoan) in inf


def test_functional_violation_does_not_merge_episodes():
    _, inf = reasoned()
    assert (o.OP.Episode_1, URIRef("http://www.w3.org/2002/07/owl#sameAs"), o.OP.Episode_2) not in inf


def test_affiliation_rules():
    g = Graph()
    for n in ["Marines", "Straw_Hat_Pirates", "Ally_of_theWhitebeard_Pirates", "Revolutionary_Army", "Ninja-Pirate-Mink-Samurai_Alliance"]:
        g.add((o.OP[n], RDF.type, o.OP.Affiliation))
    out = o.classify_affiliations(g)
    assert (o.OP.Marines, RDF.type, o.OPX.MarineOrganization) in out
    assert (o.OP.Straw_Hat_Pirates, RDF.type, o.OPX.PirateOrganization) in out
    assert (o.OP.Revolutionary_Army, RDF.type, o.OPX.RevolutionaryOrganization) in out
    assert not list(out.triples((o.OP.Ally_of_theWhitebeard_Pirates, None, None)))
    assert not list(out.triples((o.OP["Ninja-Pirate-Mink-Samurai_Alliance"], None, None)))
