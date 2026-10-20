"""Build the minimal OWL slice that matters for DevilFruitType: schema axioms + all hasFruitType data + our extension individuals."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "backend"))
from rdflib import Graph, RDF, RDFS, OWL, BNode, URIRef
from rdflib.collection import Collection
from app import ontology as o
op, opx = o.OP, o.OPX
def build(include_ext: bool, out: str):
    up = o.load_upstream(); base, ext = o.load_sources()
    src = base + (ext if include_ext else Graph())
    g = Graph()
    # schema: the class, its enumeration, and the property
    enum = up.value(op.DevilFruitType, OWL.equivalentClass)
    for t in up.triples((enum, None, None)): g.add(t)
    lst = up.value(enum, OWL.oneOf)
    for n in Collection(up, lst): pass
    def copy_list(node):
        while node and node != RDF.nil:
            for t in up.triples((node, None, None)): g.add(t)
            node = up.value(node, RDF.rest)
    copy_list(lst)
    g.add((op.DevilFruitType, RDF.type, OWL.Class)); g.add((op.DevilFruitType, OWL.equivalentClass, enum))
    g.add((op.DevilFruit, RDF.type, OWL.Class)); g.add((op.hasFruitType, RDF.type, OWL.ObjectProperty))
    g.add((op.hasFruitType, RDFS.domain, op.DevilFruit)); g.add((op.hasFruitType, RDFS.range, op.DevilFruitType))
    for m in (op.Paramecia, op.Zoan, op.Logia): g.add((m, RDF.type, OWL.NamedIndividual)); g.add((m, RDF.type, op.DevilFruitType))
    # data
    for s, p, ob in src.triples((None, op.hasFruitType, None)):
        g.add((s, RDF.type, OWL.NamedIndividual)); g.add((s, op.hasFruitType, ob)); g.add((ob, RDF.type, OWL.NamedIndividual))
    if include_ext:
        for ind in (opx.AncientZoan, opx.MythicalZoan): g.add((ind, RDF.type, OWL.NamedIndividual)); g.add((ind, RDF.type, op.DevilFruitType))
    g.serialize(out, format="xml")
    used = sorted({str(x).rsplit('#',1)[-1] for x in g.objects(None, op.hasFruitType)} | ({"AncientZoan","MythicalZoan"} if include_ext else set()))
    print(out, len(g), "triples; type individuals in play:", used)
here = os.path.dirname(os.path.abspath(__file__))
build(True, os.path.join(here, "slice_ext.owl")); build(False, os.path.join(here, "slice_upstream.owl"))
