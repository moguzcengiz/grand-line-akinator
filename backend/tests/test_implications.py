"""Implications derived from a small ontology by implications.derive (no Fuseki needed)."""
from rdflib import Graph, Namespace, URIRef

from app import config
from app.implications import derive
from app.questions import Cond, Path, QuerySpec, Question, Step

OP, OPX = Namespace(config.OP), Namespace(config.OPX)
TBOX = f"""
@prefix op: <{config.OP}> . @prefix opx: <{config.OPX}> .
@prefix owl: <http://www.w3.org/2002/07/owl#> . @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
[] a owl:AllDisjointClasses ; owl:members ( op:Character op:DevilFruit opx:Ship ) .
op:statusOfCharacter a owl:FunctionalProperty ; rdfs:domain op:Character .
op:Alive owl:differentFrom op:Deceased .
op:occupation rdfs:domain op:Character ; owl:propertyChainAxiom ( op:occupation opx:broaderOccupation ) .
op:Pirate_Captain opx:broaderOccupation op:Pirate .
opx:PirateAffiliatedCharacter a owl:Class ; rdfs:subClassOf op:Character .
opx:PirateAffiliatedCharacter rdfs:subClassOf [ a owl:Restriction ; owl:onProperty op:occupation ; owl:hasValue op:Pirate ] .
[ a owl:Restriction ; owl:onProperty op:occupation ; owl:hasValue op:Pirate ] rdfs:subClassOf opx:PirateAffiliatedCharacter .
"""


def q(i, *paths, mode="any"):
    return Question(id=f"q{i}", text=f"Question {i}?", spec=QuerySpec(paths=list(paths), mode=mode))


def rel(r, uri, start="Character"):
    return Path(start=start, steps=[Step(rel=r)], cond=Cond(kind="uri", uri=config.OP + uri), scope="rel:" + r)


QS = [q(0, Path(start="Character", cond=Cond(kind="exists"))),                 # is it a character?
      q(1, Path(start="DevilFruit", cond=Cond(kind="exists"))),                # is it a Devil Fruit?
      q(2, rel("STATUS_OF_CHARACTER", "Alive")),                               # living?
      q(3, rel("STATUS_OF_CHARACTER", "Deceased")),                            # deceased?
      q(4, rel("OCCUPATION", "Pirate_Captain")),
      q(5, rel("OCCUPATION", "Pirate")),
      q(6, Path(start="Character", cond=Cond(kind="label", label="PirateAffiliatedCharacter"), scope="rel:AFFILIATES_WITH"))]


def imp():
    tb = Graph().parse(data=TBOX, format="turtle")
    return derive(QS, tb, {"STATUS_OF_CHARACTER": {OP.statusOfCharacter}, "OCCUPATION": {OP.occupation}},
                  {"PirateAffiliatedCharacter": URIRef(OPX.PirateAffiliatedCharacter)})


def test_a_living_character_is_not_deceased_and_not_a_fruit():
    i = imp().ctx[None]
    assert 0 in i.yes_true[2] and {1, 3} <= i.yes_false[2]
    assert 2 in i.yes_false[3]


def test_pirate_captain_implies_pirate_and_the_rewordings_are_the_same_question():
    i = imp().ctx[None]
    assert {5, 6, 0} <= i.yes_true[4] and 1 in i.yes_false[4]
    assert i.same[5] == {6} and i.same[6] == {5}
    assert 4 in i.no_false[5], "not a pirate: not a pirate captain"
    assert 4 not in i.yes_true[5], "a pirate is not necessarily a captain"


def test_categories():
    i = imp()
    assert i.category[1] == "DevilFruit" and i.category[2] is None
    assert i.cats_yes[2] == {"Character"} and 2 in i.ctx[None].yes_false[1] and 1 in i.ctx[None].yes_false[0]
    assert {1} <= i.ctx["Character"].impossible and 2 in i.ctx["DevilFruit"].impossible


def test_an_or_question_shrinks_to_the_known_category():
    # "is it (or does it eat) a fruit-thing?": the fruit alternative is excluded once we know it is a character
    either = q(7, Path(start="DevilFruit", cond=Cond(kind="exists")), Path(start="Character", steps=[Step(rel="OCCUPATION")],
                                                                              cond=Cond(kind="uri", uri=config.OP + "Pirate"), scope="rel:OCCUPATION"))
    tb = Graph().parse(data=TBOX, format="turtle")
    i = derive(QS + [either], tb, {"STATUS_OF_CHARACTER": {OP.statusOfCharacter}, "OCCUPATION": {OP.occupation}},
               {"PirateAffiliatedCharacter": URIRef(OPX.PirateAffiliatedCharacter)})
    assert 7 not in i.ctx[None].no_false[5], "category open: 'not a pirate' leaves the fruit alternative"
    assert 7 in i.ctx["Character"].no_false[5] and 5 in i.ctx["Character"].same[7], "a character: the question is just 'pirate?'"
