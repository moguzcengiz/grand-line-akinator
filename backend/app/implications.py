"""Which answers make which questions redundant - derived from the ontology, not hand-written per question.

Every bank question is turned into fact patterns about fresh individuals: one per question (an AND question asserts all its conditions on the
same individual), or one per alternative of an OR question ("is it a Paramecia fruit, or does it eat one?").  Each pattern is the question's
start category, its path to fresh nodes and its final condition (a URI or a class).  ONE OWL RL closure of the TBox (schema + extension
rules + constraints, Fuseki graph urn:akinator:tbox) over all these individuals gives what a "yes" ENTAILS ("Pirate Captain" => captain,
pirate, character).  What a "yes" EXCLUDES is read off the closures without another reasoner run: two alternatives are incompatible when
they force disjoint classes on the same individual, two owl:differentFrom values of a functional property (one level deep through fresh
nodes reached by a functional property: the CURRENT user of a fruit), or the same value through two disjoint properties.
"No" to F excludes every G whose "yes" entails F; questions that entail each other are re-wordings.

The relations are computed per category context: None (category still open) and each category.  Once the answers settle the category
(a character fact answered yes), an OR question shrinks to its alternatives of that category: "has eaten a Devil Fruit? no" then also
excludes "Is it (or does it eat) a Paramecia-type Devil Fruit?", and questions about another category are impossible.

Only hard answers (yes / no) use these implications; "probably" and "don't know" never do.
"""
import re
from dataclasses import dataclass, field
from itertools import combinations

import owlrl
from rdflib import Graph, Namespace, OWL, RDF, URIRef
from rdflib.collection import Collection

from . import config

FACT = "urn:fact:"
OP, OPX = Namespace(config.OP), Namespace(config.OPX)
CATEGORY_CLASS = {"Character": OP.Character, "DevilFruit": OP.DevilFruit, "Ship": OPX.Ship}


@dataclass
class Relations:
    """Implications between questions in one category context."""
    yes_true: list[set] = field(default_factory=list)      # q -> questions known TRUE after "yes" to q
    yes_false: list[set] = field(default_factory=list)     # q -> questions known FALSE after "yes" to q
    no_false: list[set] = field(default_factory=list)      # q -> questions known FALSE after "no" to q
    same: list[set] = field(default_factory=list)          # q -> re-wordings of q (each entails the other)
    impossible: set = field(default_factory=set)           # questions that cannot be true in this context

    def grow(self, n: int):
        for lst in (self.yes_true, self.yes_false, self.no_false, self.same):
            lst.extend(set() for _ in range(n - len(lst)))


@dataclass
class Implications:
    ctx: dict = field(default_factory=dict)                     # None | category -> Relations
    category: list = field(default_factory=list)                # q -> the category it asks about ("Is it a Devil Fruit?"), else None
    cats_yes: list = field(default_factory=list)                # q -> the categories a "yes" leaves possible (None = no restriction)
    unsatisfiable: set = field(default_factory=set)             # questions the ontology says can never be true

    def empty_for(self, n: int):
        """Make room for questions added later (LLM proposals): no implications for them."""
        self.ctx.setdefault(None, Relations())
        for rel in self.ctx.values():
            rel.grow(n)
        self.category.extend(None for _ in range(n - len(self.category)))
        self.cats_yes.extend(None for _ in range(n - len(self.cats_yes)))

    def rel(self, allowed: set | None) -> Relations:
        """The relations for what is known about the category (a single category -> its own context)."""
        if allowed is not None and len(allowed) == 1:
            return self.ctx.get(next(iter(allowed)), self.ctx[None])
        return self.ctx[None]


def _fresh(n) -> bool:
    return isinstance(n, URIRef) and str(n).startswith(FACT)


def _assert_path(g: Graph, x: URIRef, path, tag: str, writer: dict, classes: dict) -> bool:
    """Write one path of a spec as triples about x.  False if the path uses something the TBox cannot express (then no implications)."""
    g.add((x, RDF.type, CATEGORY_CLASS[path.start]))
    node = x
    for i, st in enumerate(path.steps, 1):
        p = writer.get(st.rel)
        if p is None:
            return False
        nxt = URIRef(path.cond.uri) if (i == len(path.steps) and path.cond.kind == "uri") else URIRef(f"{tag}:n{i}")
        g.add((node, p, nxt) if st.dir == "out" else (nxt, p, node))
        node = nxt
    c = path.cond
    if c.kind == "label":
        if c.label not in classes:
            return False
        g.add((node, RDF.type, classes[c.label]))
    elif (c.kind == "uri" and not path.steps) or c.kind in ("cmp", "count"):
        return False                                  # nothing the reasoner can use
    return True


class _Closure:
    """The reasoned graph plus the TBox facts the incompatibility test needs."""

    def __init__(self, g: Graph, tbox: Graph, rel_preds: dict, classes: dict):
        self.g, self.rel_preds, self.classes = g, rel_preds, classes
        self.functional = set(tbox.subjects(RDF.type, OWL.FunctionalProperty))
        self.disjoint = set(tbox.subject_objects(OWL.disjointWith))
        for adc in tbox.subjects(RDF.type, OWL.AllDisjointClasses):
            for lst in tbox.objects(adc, OWL.members):
                self.disjoint |= set(combinations(list(Collection(tbox, lst)), 2))
        self.disjoint |= {(b, a) for a, b in self.disjoint}
        self.different = set(g.subject_objects(OWL.differentFrom))
        self.different |= {(b, a) for a, b in self.different}
        pd = set(tbox.subject_objects(OWL.propertyDisjointWith))
        self.prop_disjoint = pd | {(b, a) for a, b in pd}

    def types(self, n) -> set:
        return set(self.g.objects(n, RDF.type))

    def match(self, x, path) -> bool:
        """Does the closure of individual x satisfy one path of a question?"""
        if CATEGORY_CLASS[path.start] not in self.types(x):
            return False
        nodes = {x}
        for st in path.steps:
            preds = self.rel_preds.get(st.rel, ())
            nodes = {o for n in nodes for p in preds for o in (self.g.objects(n, p) if st.dir == "out" else self.g.subjects(p, n))}
            if not nodes:
                return False
        c = path.cond
        if c.kind == "uri":
            return URIRef(c.uri) in nodes
        if c.kind == "label":
            cls = self.classes.get(c.label)
            return cls is not None and any(cls in self.types(n) for n in nodes)
        return c.kind == "exists"

    def incompatible(self, a, b, depth: int = 1) -> bool:
        """a and b stand for the same individual in two different facts: can both facts hold at once?"""
        ta, tb = self.types(a), self.types(b)
        if any((x, y) in self.disjoint for x in ta for y in tb):
            return True
        for p in self.functional:
            for u in self.g.objects(a, p):
                for v in self.g.objects(b, p):
                    if u != v and ((u, v) in self.different or (depth and (_fresh(u) or _fresh(v)) and self.incompatible(u, v, depth - 1))):
                        return True
        return any(set(self.g.objects(a, p)) & set(self.g.objects(b, q)) for p, q in self.prop_disjoint)


def derive(questions, tbox: Graph, rel_preds: dict[str, set], classes: dict[str, URIRef]) -> Implications:
    """rel_preds: relation name -> predicate URIs carrying it (the smallest one is used to write facts).  classes: label -> class URI."""
    g = Graph()
    for t in tbox:
        g.add(t)
    writer = {r: sorted(ps)[0] for r, ps in rel_preds.items() if ps}
    # alternatives: q -> [(start category, individual)];  an AND question is ONE alternative (its paths share the start, validate_spec)
    alts: dict[int, list] = {}
    for qi, q in enumerate(questions):
        if q.spec.mode == "all" or len(q.spec.paths) == 1:
            x = URIRef(f"{FACT}{qi}")
            if all(_assert_path(g, x, p, f"{FACT}{qi}:{k}", writer, classes) for k, p in enumerate(q.spec.paths)):
                alts[qi] = [(q.spec.paths[0].start, x)]
        else:
            xs = [(p.start, URIRef(f"{FACT}{qi}.{k}")) for k, p in enumerate(q.spec.paths)]
            if all(_assert_path(g, x, p, str(x), writer, classes) for (_, x), p in zip(xs, q.spec.paths)):
                alts[qi] = xs
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics, axiomatic_triples=False, datatype_axioms=False).expand(g)
    cl = _Closure(g, tbox, rel_preds, classes)

    n = len(questions)
    imp = Implications()
    for q in questions:
        p = q.spec.paths[0]
        imp.category.append(p.start if len(q.spec.paths) == 1 and not p.steps and p.cond.kind == "exists" else None)
        imp.cats_yes.append({pp.start for pp in q.spec.paths})          # a fact about characters is true only of a character (C1)
    # an alternative the reasoner found contradictory (or merged with another individual) can never be true
    errors = " ".join(str(o) for o in g.objects(None, owlrl.Namespaces.ERRNS.error))
    dead = set(re.findall(r"urn:fact:[0-9.]+(?=[\s:]|$)", errors)) | {str(s) for s, o in g.subject_objects(OWL.sameAs) if s != o and _fresh(s)}
    for qi in list(alts):
        alts[qi] = [(c, x) for c, x in alts[qi] if str(x) not in dead]
        if not alts[qi]:
            imp.unsatisfiable.add(qi)
            del alts[qi]

    # does alternative x satisfy question G (only G's paths of the context's category count)?
    match = {(x, gi, k): cl.match(x, p) for xs in alts.values() for _, x in xs for gi, q in enumerate(questions) for k, p in enumerate(q.spec.paths)}

    def entails(x, gi, cat) -> bool:
        q = questions[gi]
        ks = [k for k, p in enumerate(q.spec.paths) if cat is None or p.start == cat]
        if not ks:
            return False
        return all(match[(x, gi, k)] for k in ks) if q.spec.mode == "all" else any(match[(x, gi, k)] for k in ks)

    inc_cache: dict = {}

    def inc(a, b) -> bool:
        if (a, b) not in inc_cache:
            inc_cache[(a, b)] = cl.incompatible(a, b)
        return inc_cache[(a, b)]

    for cat in (None, *CATEGORY_CLASS):
        rel = Relations()
        rel.grow(n)
        live = {qi: [x for c, x in xs if cat is None or c == cat] for qi, xs in alts.items()}
        rel.impossible = {qi for qi, q in enumerate(questions) if cat is not None and all(p.start != cat for p in q.spec.paths)}
        for f, fx in live.items():
            if not fx:
                continue
            for gi in range(n):
                if gi == f:
                    continue
                if all(entails(a, gi, cat) for a in fx):
                    rel.yes_true[f].add(gi)
                gx = live.get(gi)
                if gi in rel.impossible or (gx is not None and (not gx or all(inc(a, b) for a in fx for b in gx))):
                    rel.yes_false[f].add(gi)
        for f in range(n):
            for gi in rel.yes_true[f]:
                rel.no_false[gi].add(f)
                if f in rel.yes_true[gi]:
                    rel.same[f].add(gi)
        imp.ctx[cat] = rel
    return imp
