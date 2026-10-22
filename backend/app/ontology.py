"""RDF loading, extension rules and OWL RL materialisation (no Fuseki needed -> unit-testable)."""
import re
from rdflib import Graph, URIRef, Namespace, RDF, RDFS, OWL, Literal
import owlrl

from . import config

OP = Namespace(config.OP)
OPX = Namespace(config.OPX)

# ---- affiliation classification rules (documented in docs/ONTOLOGY.md) ----
_NOT_MEMBERSHIP = re.compile(r"^(Ally|Subordinate|Former|Fake|Prisoner|Retainer|Enemy|Member|Allied)")
MARINE = {"Marines", "Marine_Headquarters", "Loguetown_Marine_Base", "Navy"}
REVOLUTIONARY = {"Revolutionary_Army", "Freedom_Fighters"}
WORLD_GOV = {"World_Government", "CP0", "CP9", "Cipher_Pol", "Seven_Warlords_of_the_Sea", "Pacifista", "Cipher_Pol_Aigis_Zero"}


def classify_affiliations(base: Graph) -> Graph:
    """Rule-based typing of op:Affiliation individuals. Output goes to the 'extension' provenance bucket."""
    g = Graph()
    for aff in base.subjects(RDF.type, OP.Affiliation):
        name = str(aff).rsplit("#", 1)[-1]
        if name in MARINE or name.endswith("_Marine_Base") or name.startswith("Marines_"):
            g.add((aff, RDF.type, OPX.MarineOrganization))
        elif name in REVOLUTIONARY or name.endswith("Revolutionary_Army"):
            g.add((aff, RDF.type, OPX.RevolutionaryOrganization))
        elif name in WORLD_GOV:
            g.add((aff, RDF.type, OPX.WorldGovernmentOrganization))
        elif name.endswith("_Pirates") and not _NOT_MEMBERSHIP.match(name) and "Alliance" not in name:
            g.add((aff, RDF.type, OPX.PirateOrganization))
    return g


def load_upstream() -> Graph:
    """The untouched upstream ontology + data."""
    base = Graph()
    for f in config.BASE_FILES:
        base.parse(str(config.ROOT / f), format="turtle")
    return base


def load_ext(base: Graph) -> Graph:
    """Extension schema + curated facts + rule-derived classification (no data patch)."""
    ext = Graph()
    for f in config.EXT_FILES:
        ext.parse(str(config.ROOT / f), format="turtle")
    for t in classify_affiliations(base):
        ext.add(t)
    for t in closed_enumerations(base + ext):
        ext.add(t)
    return ext


def closed_enumerations(g: Graph) -> Graph:
    """owl:differentFrom between every two members of a class marked opx:ClosedEnumeration (asserted members and owl:oneOf lists of an
    equivalent class).  Pairwise, because owlrl's owl:AllDifferent skips the pairs with the last list member."""
    from rdflib.collection import Collection
    out = Graph()
    for cls in set(g.subjects(RDF.type, OPX.ClosedEnumeration)):
        members = {m for m in g.subjects(RDF.type, cls) if isinstance(m, URIRef)}
        for eq in g.objects(cls, OWL.equivalentClass):
            for lst in g.objects(eq, OWL.oneOf):
                members |= {m for m in Collection(g, lst) if isinstance(m, URIRef)}
        ms = sorted(members)
        for i, a in enumerate(ms):
            for b in ms[i + 1:]:
                out.add((a, OWL.differentFrom, b))
    return out


def clashes(inferred: Graph) -> list[str]:
    """Contradictions owlrl found (disjoint classes sharing an individual, two different values of a functional property ...).
    owlrl reports them as error triples on blank nodes, which is_domain_triple() drops: they must be collected here."""
    return sorted(str(o) for o in inferred.objects(None, owlrl.Namespaces.ERRNS.error))


def load_sources():
    """Return (base, extension) graphs. base = upstream minus the documented data patch (patching.py);
    extension = schema + curated facts + demoted later appearances + rule-derived classification."""
    from .patching import load_patch
    base = load_upstream()
    removed, demoted = load_patch()
    for t in removed:
        base.remove(t)
    ext = load_ext(base)
    for t in demoted:
        ext.add(t)
    return base, ext


def materialize(union: Graph, drop_all_functional: bool = False, guard: bool = True) -> tuple[Graph, list[str]]:
    """Run OWL RL closure on a copy; return (NEW triples, functional properties whose axiom had to be dropped).

    Not a full OWL 2 DL reasoner: only the OWL 2 RL rule subset implemented by owlrl.
    Functional-property axioms are KEPT.  A property is only dropped from the *reasoning copy* if the data still violates it
    (it would otherwise merge distinct individuals through owl:sameAs); every drop is returned so callers can report/fail.
    """
    from .patching import functional_conflicts
    work = Graph()
    for t in union:
        work.add(t)
    unresolved = []
    if drop_all_functional:                       # only used by the audit to reproduce the old, rejected workaround
        work.remove((None, RDF.type, OWL.FunctionalProperty))
    elif guard:
        for p in functional_conflicts(work):
            work.remove((p, RDF.type, OWL.FunctionalProperty))
            unresolved.append(str(p))
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics, axiomatic_triples=False, datatype_axioms=False).expand(work)
    inferred = Graph()
    for t in work:
        if t not in union:
            inferred.add(t)
    return inferred, unresolved


def tbox(ext: Graph) -> Graph:
    """What the game reasons with about hypothetical answers (implications.py): the upstream schema (patched) plus our extension layer
    (rules, constraints, curated facts such as the occupation hierarchy, affiliation typing, generated owl:differentFrom pairs).
    No upstream character data."""
    from .patching import load_patch
    g = Graph().parse(str(config.ROOT / config.BASE_FILES[0]), format="turtle")
    removed, _ = load_patch()
    for t in removed:
        g.remove(t)
    for t in ext:
        g.add(t)
    return g


def nonreflexive_same_as(g: Graph) -> list[tuple]:
    return [(s, o) for s, _, o in g.triples((None, OWL.sameAs, None)) if s != o]


def is_domain_triple(t) -> bool:
    """Keep inferred triples that are meaningful for the game graph (drop owl:Thing / sameAs / bnode noise)."""
    s, p, o = t
    if not isinstance(s, URIRef):
        return False
    if p in (OWL.sameAs, OWL.differentFrom) or str(p).startswith(str(OWL)):
        return False
    if p == RDF.type:
        return isinstance(o, URIRef) and (str(o).startswith(config.OP) or str(o).startswith(config.OPX))
    if str(p).startswith(str(RDFS)) or str(p).startswith(str(RDF)):
        return False
    return isinstance(o, URIRef)
