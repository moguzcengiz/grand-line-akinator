"""Question specs -> safe SPARQL for Apache Jena Fuseki, plus rule-based generation from the *imported* schema.

A question is data (QuerySpec), never free-form SPARQL.  Identifiers (labels / relationship types / property names)
are validated by regex and against the live schema whitelist; every value goes through graph.run's $name substitution
(URIRef -> validated <iri>, number / string -> escaped typed literal).  Store layout: see graph.py.
"""
import hashlib
import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from . import config, graph

IDENT = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
SCOPE = re.compile(r"^(closed|status|positive|path|(last:)?(rel|prop):[A-Za-z][A-Za-z0-9_]*)$")
NUMERIC_PROPS = {"height", "age", "number"}
COMPLETE_RELS: set[str] = set()      # relations whose edge list is known to be complete (none established in the upstream data)


class Step(BaseModel):
    rel: str
    dir: Literal["out", "in"] = "out"


class Cond(BaseModel):
    kind: Literal["exists", "uri", "label", "cmp", "count"]
    uri: str | None = None      # uri:   the last node must have this URI
    label: str | None = None    # label: the last node must carry this label (incl. OWL-inferred classes)
    prop: str | None = None     # cmp:   numeric property of the last node
    # count: the entity has at least `value` distinct matches of the path (op must be >=). A recorded count proves TRUE;
    #        a smaller count is only FALSE if the relation is known to be complete (COMPLETE_RELS, empty by default) - otherwise UNKNOWN.
    op: Literal["<=", ">="] | None = None
    value: float | None = None


class Path(BaseModel):
    start: Literal["Character", "DevilFruit", "Ship"]
    steps: list[Step] = Field(default_factory=list, max_length=2)
    cond: Cond
    # Where absence of a fact means FALSE ("closed") versus UNKNOWN:
    #   closed       every entity of `start` is assumed fully described for this question
    #   rel:R        known only if the entity has >= 1 R edge, otherwise UNKNOWN
    #   prop:P       known only if the entity has property P, otherwise UNKNOWN
    # cmp conditions are known iff the compared property exists.
    scope: str = "closed"


class QuerySpec(BaseModel):
    paths: list[Path] = Field(min_length=1, max_length=4)
    # any: OR over alternative paths (one per entity category).  all: conjunction (Kleene AND) of facts about the same category.
    mode: Literal["any", "all"] = "any"


class Question(BaseModel):
    id: str
    text: str
    spec: QuerySpec
    source: Literal["rule", "llm"] = "rule"
    original_text: str | None = None  # set when the LLM paraphrased a rule question

    @field_validator("text")
    @classmethod
    def _text(cls, v):
        v = v.strip()
        if not (5 <= len(v) <= 220) or not v.endswith("?"):
            raise ValueError("question text must be 5-220 chars and end with '?'")
        return v


def family(q: "Question") -> str:
    """Questions probing the same fact dimension (e.g. all height thresholds). Used to avoid re-asking after "don't know"."""
    if q.spec.mode == "all":
        return "conj:" + "+".join(sorted(f"{p.start}:{'>'.join(s.rel for s in p.steps)}:{p.cond.label or p.cond.prop or p.cond.kind}" for p in q.spec.paths))
    p = q.spec.paths[0]
    return f"{p.start}:{'>'.join(s.rel for s in p.steps)}:{p.cond.kind}:{p.cond.prop or p.cond.label or ''}"


_LABEL_TOPIC = {"DevilFruitUser": "fruit", "DevilFruitEater": "fruit", "HakiUser": "haki", "CaptainCharacter": "role", "ShipOwner": "ship", "PirateShip": "ship"}
_REL_TOPIC = {"STATUS_OF_CHARACTER": "status", "AFFILIATES_WITH": "affiliation", "OPERATED_BY": "affiliation", "OCCUPATION": "role",
              "PLACE_OF_ORIGIN": "origin", "RESIDENCE": "origin", "RACE": "race", "HAS_HAKI": "haki", "HAS_FRUIT_TYPE": "fruit",
              "HAS_FRUIT_SUBTYPE": "fruit", "HAS_DEVIL_FRUIT": "fruit", "DEVIL_FRUIT_PREVIOUS_USER": "fruit", "DEVIL_FRUIT_CURRENT_USER": "fruit-user",
              "SHIP_OWNER": "ship", "OWNS_SHIP": "ship", "SHIP_TYPE": "ship", "BUILT_BY": "ship", "SAILS_ON": "ship", "SHIP_STATUS": "ship"}


def topic(q: "Question") -> str:
    """Coarse theme of a question (category, status, affiliation, role, origin, fruit, fruit-user, ship, haki, race, physical, combo)."""
    if q.spec.mode == "all":
        return "combo"
    p = q.spec.paths[0]
    if p.cond.kind == "cmp":
        return "physical"
    if not p.steps:
        return _LABEL_TOPIC.get(p.cond.label or "", "affiliation" if "Affiliated" in (p.cond.label or "") else "category")
    return _REL_TOPIC.get(p.steps[0].rel, "other")


# Questions that ask about the same fact in other words share a concept (see GameState.covered_concepts).  Only exact synonyms: "Pirate Officer"
# or "Vice Admiral" narrow a concept down and stay askable.
_LABEL_CONCEPT = {"PirateAffiliatedCharacter": "pirate", "CaptainCharacter": "captain", "HakiUser": "haki", "MarineAffiliatedCharacter": "marine",
                  "WorldGovernmentAffiliatedCharacter": "world-government", "RevolutionaryAffiliatedCharacter": "revolutionary", "DevilFruitEater": "fruit-eater"}
_OCCUPATION_CONCEPT = {"Pirate": {"pirate"}, "Captain": {"captain"}, "Pirate_Captain": {"pirate", "captain"}}


def concepts(q: "Question") -> frozenset:
    """Concepts of a question about characters; empty = not comparable (never filtered)."""
    out = set()
    for p in q.spec.paths:
        if p.start != "Character":
            return frozenset()
        if not p.steps and p.cond.kind == "label" and p.cond.label in _LABEL_CONCEPT:
            out.add(_LABEL_CONCEPT[p.cond.label])
        elif [s.rel for s in p.steps] == ["OCCUPATION"] and p.cond.kind == "uri" and (p.cond.uri or "").rsplit("#", 1)[-1] in _OCCUPATION_CONCEPT:
            out |= _OCCUPATION_CONCEPT[p.cond.uri.rsplit("#", 1)[-1]]
        else:
            return frozenset()
    return frozenset(out)


def complexity(q: "Question") -> float:
    """Reading/graph-traversal burden: hops + alternatives + conjunction + cardinality."""
    return (sum(len(p.steps) for p in q.spec.paths) + 0.5 * (len(q.spec.paths) - 1) + (1.0 if q.spec.mode == "all" else 0.0)
            + 0.5 * sum(p.cond.kind == "count" for p in q.spec.paths))


def omission_prone(q: "Question") -> bool:
    """True when a graph FALSE for this question only means "not in the (incomplete) list".  Model-independent: used by the evaluation simulator."""
    return any(p.scope.startswith(("rel:", "path", "last:", "prop:")) for p in q.spec.paths)


def false_reliability(q: "Question") -> float:
    """How much a graph FALSE for this question can be trusted.  Absence from a relation list (rel / path / last / prop scopes) is weak evidence
    because the lists are incomplete; categories, life status and fruit types are definite."""
    if config.ANSWER_MODEL == "legacy":
        return 1.0
    soft = any(p.scope.startswith(("rel:", "path", "last:", "prop:")) for p in q.spec.paths)
    return config.ABSENCE_RELIABILITY if soft else config.DEFINITE_RELIABILITY


def unknown_prior_true(q: "Question") -> float:
    """P(the fact is true | the KB has no record).  Open-world 'positive' questions (has a Devil Fruit / owns a ship / its fruit's type):
    the KB records most true cases, so an unrecorded entity is probably a NO (config.POSITIVE_UNKNOWN_PRIOR, default 0.05) - but
    never certainly: the answer stays UNKNOWN and can only be down-weighted, not eliminated."""
    if config.ANSWER_MODEL != "legacy":
        return 0.5                      # "not stated" = it can be either; never treat a missing fact as probably false
    return config.POSITIVE_UNKNOWN_PRIOR if any(p.scope == "positive" for p in q.spec.paths) else 0.5


def spec_id(spec: QuerySpec) -> str:
    return "q_" + hashlib.sha1(spec.model_dump_json().encode()).hexdigest()[:10]


# ------------------------------------------------------------------ compilation
def _prop(name: str) -> str:
    if not IDENT.match(name or ""):
        raise ValueError(f"bad property name {name!r}")
    return f"g:{name}"


def _steps(path: Path) -> tuple[str, str]:
    """(basic graph pattern walking the steps from ?e, name of the last node variable)."""
    pat, prev = "", "?e"
    for i, st in enumerate(path.steps, 1):
        if not IDENT.match(st.rel):
            raise ValueError(f"bad relationship type {st.rel!r}")
        pat += (f"{prev} ?p{i} ?n{i} . " if st.dir == "out" else f"?n{i} ?p{i} {prev} . ") + f'?p{i} g:relType "{st.rel}" . '
        prev = f"?n{i}"
    return pat, prev


def _cond(path: Path, last: str) -> str:
    c = path.cond
    if c.kind == "uri":
        return f"FILTER({last} = $u)"
    if c.kind == "label":
        if not c.label or not IDENT.match(c.label):
            raise ValueError("bad label")
        return f'{last} g:label "{c.label}" .'
    if c.kind == "cmp":
        if c.prop not in NUMERIC_PROPS or c.op is None or c.value is None:
            raise ValueError("bad comparison")
        return f"{last} {_prop(c.prop)} ?val . FILTER(?val {c.op} $v)"
    return ""


def _select(path: Path, body: str) -> str:
    """Entities of the start category for which `body` has a match."""
    return f'SELECT DISTINCT ?e WHERE {{ ?e g:category "{path.start}" . FILTER EXISTS {{ {body} }} }}'


def _all(path: Path) -> str:
    return f'SELECT DISTINCT ?e WHERE {{ ?e g:category "{path.start}" }}'


def compile_path(path: Path) -> tuple[str, str, dict]:
    """-> (SPARQL selecting matching entities ?e, SPARQL selecting KNOWN entities ?e, parameters)."""
    params = {"u": graph.iri(path.cond.uri) if path.cond.uri else None, "v": path.cond.value}
    if not SCOPE.match(path.scope):
        raise ValueError(f"bad scope {path.scope!r}")
    all_q = _all(path)
    pat, last = _steps(path)
    if path.cond.kind == "exists" and not path.steps:          # "is it a <category>?"
        return all_q, all_q, params
    if path.cond.kind == "count":
        c = path.cond
        if not path.steps or c.op != ">=" or c.value is None or c.value < 1:
            raise ValueError("count needs >=1 step, op '>=' and a value >= 1")
        key = ', "|", '.join(f"STR(?n{i})" for i in range(1, len(path.steps) + 1))     # one distinct path = one distinct node tuple
        true_q = (f'SELECT DISTINCT ?e WHERE {{ ?e g:category "{path.start}" . {{ SELECT ?e WHERE {{ {pat} }} GROUP BY ?e '
                  f'HAVING (COUNT(DISTINCT CONCAT({key})) >= $v) }} }}')
        complete = path.scope == "closed" and all(st.rel in COMPLETE_RELS for st in path.steps)
        return true_q, (all_q if complete else true_q), params
    true_q = _select(path, f"{pat} {_cond(path, last)}")
    if path.cond.kind == "cmp":
        known_q = _select(path, f"{pat} {last} {_prop(path.cond.prop)} ?val .")
    elif path.scope == "closed":
        known_q = all_q
    elif path.scope == "positive":    # open world: absence of the fact is NOT evidence of falsity
        known_q = true_q
    elif path.scope == "status":      # "Unknown" status must stay unknown, not become "not alive"
        known_q = _select(path, f'{pat} {last} g:name ?nm . FILTER(?nm IN ("Alive", "Deceased"))')
    elif path.scope == "path":        # something to evaluate on: the path (ignoring the final condition) exists
        known_q = _select(path, pat)
    elif path.scope.startswith("last:"):
        _, kind, name = path.scope.split(":")
        inner = f'{last} ?lp ?lx . ?lp g:relType "{name}" .' if kind == "rel" else f"{last} {_prop(name)} ?lx ."
        known_q = _select(path, f"{pat} {inner}")
    elif path.scope.startswith("rel:"):
        known_q = _select(path, f'?e ?rp ?rx . ?rp g:relType "{path.scope[4:]}" .')
    else:                             # prop:P (SCOPE admits nothing else)
        known_q = _select(path, f"?e {_prop(path.scope[5:])} ?px .")
    return true_q, known_q, params


def explain_path(path: Path, uri: str) -> dict | None:
    """One supporting path of entity `uri` (with the provenance of every edge), or None if there is nothing to show:
    {"hops": [{type, provenance, from, to}], "end": name, "end_inferred": [OWL RL types of the last node], "value": cmp value | None}."""
    if not path.steps and path.cond.kind != "label":
        return None
    prev, pat, sel = "?e", "", ""
    for i, st in enumerate(path.steps, 1):
        if not IDENT.match(st.rel):
            raise ValueError(f"bad relationship type {st.rel!r}")
        pat += (f"GRAPH ?g{i} {{ {prev} ?p{i} ?n{i} }} " if st.dir == "out" else f"GRAPH ?g{i} {{ ?n{i} ?p{i} {prev} }} ") + f'?p{i} g:relType "{st.rel}" . '
        pat += f"{prev} g:name ?f{i} . ?n{i} g:name ?t{i} . "
        sel += f" ?g{i} ?f{i} ?t{i}"
        prev = f"?n{i}"
    q = (f'SELECT ?end ?last ?val{sel} WHERE {{ VALUES ?e {{ $e }} ?e g:category "{path.start}" . {pat} {_cond(path, prev)} '
         f'{prev} g:name ?end . BIND({prev} AS ?last) }} LIMIT 1')
    rows = graph.run(q, e=graph.iri(uri), u=graph.iri(path.cond.uri) if path.cond.uri else None, v=path.cond.value)
    if not rows:
        return None
    r = rows[0]
    hops = []
    for i, st in enumerate(path.steps, 1):
        a, b = r[f"f{i}"], r[f"t{i}"]
        hops.append({"type": st.rel, "provenance": r[f"g{i}"].rsplit(":", 1)[-1], "from": a if st.dir == "out" else b, "to": b if st.dir == "out" else a})
    inf = [x["t"] for x in graph.run("SELECT ?t WHERE { $l g:inferredType ?t } ORDER BY ?t", l=graph.iri(r["last"]))]
    return {"hops": hops, "end": r["end"], "end_inferred": inf, "value": r.get("val")}


def category_uris() -> dict[str, list[str]]:
    return {c: [r["e"] for r in graph.run('SELECT ?e WHERE { ?e g:category $c } ORDER BY ?e', c=c)] for c in config.CATEGORIES}


def combine(vals: list[int], mode: str) -> int:
    """Kleene three-valued logic over per-path truth values {1 true, 0 false, -1 unknown}.
    any (OR): TRUE if any is true, else UNKNOWN if any is unknown, else FALSE.   all (AND): FALSE if any is false, else UNKNOWN if any is unknown, else TRUE."""
    if mode == "all":
        return 0 if 0 in vals else (-1 if -1 in vals else 1)
    return 1 if 1 in vals else (-1 if -1 in vals else 0)


def evaluate(spec: QuerySpec, uris: list[str], cats: dict[str, list[str]] | None = None) -> dict[str, int]:
    """Three-valued truth per entity: 1 true, 0 false, -1 unknown.

    mode any:  TRUE if any path matches; else UNKNOWN if any path is unknown; else FALSE   (Kleene OR)
    mode all:  FALSE if any conjunct is known false; else UNKNOWN if any is unknown; else TRUE (Kleene AND)
    A category no path covers is "not applicable": FALSE (a Devil Fruit is not in the Marines), except for numeric
    questions where it is UNKNOWN (a ship does have a debut, we just don't record it)."""
    cats = cats or category_uris()
    default = -1 if any(p.cond.kind == "cmp" for p in spec.paths) else 0
    per_entity: dict[str, list[int]] = {}
    for p in spec.paths:
        tq, kq, params = compile_path(p)
        true_set = {r["e"] for r in graph.run(tq, **params)}
        known = {r["e"] for r in graph.run(kq, **params)} | true_set
        for u in cats[p.start]:
            per_entity.setdefault(u, []).append(1 if u in true_set else (0 if u in known else -1))
    out = {}
    for u in uris:
        vals = per_entity.get(u)
        if vals is None:
            out[u] = default
        else:
            out[u] = combine(vals, spec.mode)
    return out


# ------------------------------------------------------------------ schema introspection / validation
def schema_summary() -> dict:
    """What the LLM and the rule generator may use. Built from the live graph, not hardcoded."""
    rels = graph.run("SELECT ?start ?rel (COUNT(*) AS ?n) WHERE { ?a g:category ?start . ?a ?p ?b . ?p g:relType ?rel . ?b g:name ?bn } "
                     "GROUP BY ?start ?rel ORDER BY DESC(?n) ?start ?rel")
    labels = graph.run("SELECT ?label (COUNT(*) AS ?n) WHERE { ?x g:label ?label } GROUP BY ?label ORDER BY DESC(?n) ?label")
    return {"relationships": rels, "labels": labels, "numeric_props": sorted(NUMERIC_PROPS)}


def allowed_identifiers() -> tuple[set[str], set[str]]:
    rels = {r["rel"] for r in graph.run("SELECT DISTINCT ?rel WHERE { ?p g:relType ?rel }")}
    labels = {l["label"] for l in graph.run("SELECT DISTINCT ?label WHERE { ?n g:label ?label }")}
    return rels, labels


def validate_spec(spec: QuerySpec, rels: set[str], labels: set[str]) -> str | None:
    """Error string if the spec leaves the imported schema or is malformed, else None."""
    if spec.mode == "all" and (len(spec.paths) < 2 or len({p.start for p in spec.paths}) != 1):
        return "a conjunction needs >= 2 conditions about the same category"
    for p in spec.paths:
        for st in p.steps:
            if st.rel not in rels:
                return f"unknown relationship {st.rel}"
        c = p.cond
        if c.kind == "label" and c.label not in labels:
            return f"unknown label {c.label}"
        if c.kind == "uri":
            if not c.uri or not p.steps:
                return "uri condition needs a target uri and at least one step"
            try:
                if not graph.run("ASK { $u g:name ?x }", u=graph.iri(c.uri))[0]["ask"]:
                    return f"unknown uri {c.uri}"
            except ValueError:
                return f"unknown uri {c.uri}"
        if c.kind == "count":
            if not p.steps or c.op != ">=" or c.value is None or c.value < 1:
                return "bad count condition"
            if p.scope == "closed" and not all(st.rel in COMPLETE_RELS for st in p.steps):
                return "cardinality needs established completeness: use scope 'positive' (or 'rel:R')"
        if c.kind == "cmp" and (c.prop not in NUMERIC_PROPS or c.op is None or c.value is None):
            return "bad numeric comparison"
        if not SCOPE.match(p.scope):
            return "bad scope"
        if p.scope.startswith(("rel:", "last:rel:")) and p.scope.rsplit(":", 1)[1] not in rels:
            return f"unknown scope relationship {p.scope.rsplit(':', 1)[1]}"
        if p.scope in ("path", "status") and not p.steps:
            return f"scope {p.scope} needs at least one step"
    return None


# ------------------------------------------------------------------ rule-based generation
REL_TEXT = {
    "AFFILIATES_WITH": "Is it affiliated with {t}?",
    "OCCUPATION": "Does it have the role or occupation \"{t}\"?",
    "STATUS_OF_CHARACTER": "Is its status \"{t}\"?",
    "RACE": "Is it of the {t} race?",
    "PLACE_OF_ORIGIN": "Does it originate from {t}?",
    "RESIDENCE": "Does it reside in {t}?",
    "HAS_BLOOD_TYPE": "Does it have blood type {t}?",
    "JAPANESE_VOICE_ACTOR": "Is it voiced in Japanese by {t}?",
    "ENGLISH_VOICE_ACTOR": "Is it voiced in English by {t}?",
    "HAS_HAKI": "Does it use {t}?",
    "SHIP_TYPE": "Is it a {t}?",
    "SHIP_OWNER": "Is it owned by {t}?",
    "BUILT_BY": "Was it built by {t}?",
    "SAILS_ON": "Does it sail on the {t}?",
    "SHIP_STATUS": "Is the ship's status \"{t}\"?",
}
# relations whose absence means "unknown" rather than "false"
OPEN_RELS = {"BUILT_BY", "SHIP_TYPE", "AFFILIATES_WITH", "OCCUPATION", "STATUS_OF_CHARACTER", "RACE", "PLACE_OF_ORIGIN", "RESIDENCE", "HAS_BLOOD_TYPE",
             "JAPANESE_VOICE_ACTOR", "ENGLISH_VOICE_ACTOR", "SHIP_STATUS"}
# relations derived from another one (extension.ttl property chains): known exactly where the source relation is (sailsOn = affiliatesWith o operates)
KNOWN_VIA = {"SAILS_ON": "AFFILIATES_WITH"}
REL_MIN_SUPPORT = {"RESIDENCE": 15, "PLACE_OF_ORIGIN": 15, "OCCUPATION": 12}   # obscure relations need broader support
# the ONLY relations the generic relation->target sweep may turn into questions (whitelist: a new relation in the data is never asked
# about by accident).  Fruit, affiliation, Haki and ship-ownership relations get dedicated questions below.  Full list: docs/CONNECTIONS.md
SWEEP_RELS = ["STATUS_OF_CHARACTER", "OCCUPATION", "RACE", "PLACE_OF_ORIGIN", "RESIDENCE", "SHIP_OWNER", "SHIP_TYPE", "BUILT_BY", "SAILS_ON", "SHIP_STATUS"]
# umbrella organisations already asked through the OWL-inferred class questions below (would be near-duplicates)
UMBRELLA_ORGS = {"Marines", "Revolutionary_Army", "World_Government"}
# OWL-RL-derived classes (see ontology/extension.ttl) -> (question, start category, completeness scope)
INFERRED_CLASS_QUESTIONS = [
    ("DevilFruitEater", "Has your character eaten a Devil Fruit?", "Character", "positive"),
    ("PirateAffiliatedCharacter", "Is your character affiliated with a pirate crew?", "Character", "rel:AFFILIATES_WITH"),
    ("MarineAffiliatedCharacter", "Is your character affiliated with the Marines?", "Character", "rel:AFFILIATES_WITH"),
    ("RevolutionaryAffiliatedCharacter", "Is your character affiliated with the Revolutionary Army?", "Character", "rel:AFFILIATES_WITH"),
    ("WorldGovernmentAffiliatedCharacter", "Is your character affiliated with the World Government?", "Character", "rel:AFFILIATES_WITH"),
    ("CaptainCharacter", "Is your character a captain?", "Character", "rel:OCCUPATION"),
    ("HakiUser", "Does it use Haki?", "Character", "prop:haki_known"),
    ("ShipOwner", "Does it own a ship?", "Character", "positive"),
    ("PirateShip", "Is it a ship used by a pirate crew?", "Ship", "closed"),
]


def _mk(text: str, paths: list[Path]) -> Question:
    spec = QuerySpec(paths=paths)
    return Question(id=spec_id(spec), text=text, spec=spec)


def _quantiles(values: list[float], qs) -> list[float]:
    vs = sorted(values)
    return sorted({vs[min(len(vs) - 1, int(q * len(vs)))] for q in qs})


def generate_rule_questions(n_by_cat: dict[str, int]) -> list[Question]:
    qs: dict[str, Question] = {}

    def add(q: Question):
        qs.setdefault(q.id, q)

    exists = Cond(kind="exists")
    for cat, text in [("Character", "Is it a character?"), ("DevilFruit", "Is it a Devil Fruit?"), ("Ship", "Is it a ship?")]:
        add(_mk(text, [Path(start=cat, cond=exists)]))

    # relation -> target questions straight from the graph, filtered by support
    rows = graph.run(
        "SELECT ?cat ?rel ?uri ?name (COUNT(DISTINCT ?a) AS ?n) WHERE { VALUES ?cat { $cats } VALUES ?rel { $rels } "
        "?a g:category ?cat . ?a ?p ?uri . ?p g:relType ?rel . ?uri g:name ?name } GROUP BY ?cat ?rel ?uri ?name ORDER BY ?cat ?rel ?uri",
        cats=config.CATEGORIES, rels=SWEEP_RELS)
    for r in rows:
        if r["name"] == "Unknown":
            continue
        if r["cat"] == "Ship":                      # only 9 ships: every distinguishing fact is worth a question
            if r["n"] >= n_by_cat["Ship"]:
                continue
        elif r["n"] < REL_MIN_SUPPORT.get(r["rel"], config.MIN_SUPPORT) or r["n"] > n_by_cat.get(r["cat"], 0) - config.MIN_SUPPORT:
            continue
        name = r["name"].replace("_", " ")
        if r["rel"] == "STATUS_OF_CHARACTER" and name in ("Alive", "Deceased"):
            text = f"Is it a {'living' if name == 'Alive' else 'deceased'} character?"
        elif r["rel"] == "SHIP_STATUS" and name in ("Destroyed", "Active"):
            text = "Has the ship been destroyed?" if name == "Destroyed" else "Is the ship still sailing?"
        else:
            text = REL_TEXT.get(r["rel"], "Is it related to {t}?").format(t=name)
        add(_mk(text, [Path(start=r["cat"], steps=[Step(rel=r["rel"])], cond=Cond(kind="uri", uri=r["uri"]),
                            scope="status" if r["rel"] == "STATUS_OF_CHARACTER" else (f"rel:{KNOWN_VIA.get(r['rel'], r['rel'])}" if r["rel"] in OPEN_RELS | set(KNOWN_VIA) else "closed"))]))

    # fruit type: fruits directly, characters through their fruit (one question, two paths)
    for t in graph.run('SELECT ?uri ?name (COUNT(DISTINCT ?f) AS ?n) WHERE { ?f g:category "DevilFruit" . ?f ?p ?uri . ?p g:relType "HAS_FRUIT_TYPE" . ?uri g:name ?name } '
                   'GROUP BY ?uri ?name ORDER BY ?uri'):
        if t["n"] >= 2:
            c = Cond(kind="uri", uri=t["uri"])
            add(_mk(f"Is it (or does it eat) a {t['name'].replace('_', ' ')}-type Devil Fruit?", [
                Path(start="DevilFruit", steps=[Step(rel="HAS_FRUIT_TYPE")], cond=c),
                Path(start="Character", steps=[Step(rel="HAS_DEVIL_FRUIT"), Step(rel="HAS_FRUIT_TYPE")], cond=c, scope="positive")]))

    # affiliation spanning categories: character direct, fruit via its user, ship via its crew
    for r in graph.run('SELECT ?uri ?name (COUNT(DISTINCT ?a) AS ?n) WHERE { ?a g:category "Character" . ?a ?p ?uri . ?p g:relType "AFFILIATES_WITH" . ?uri g:name ?name . '
                       '?uri g:label ?l . VALUES ?l { "PirateOrganization" "MarineOrganization" "RevolutionaryOrganization" "WorldGovernmentOrganization" } } '
                       'GROUP BY ?uri ?name ORDER BY DESC(?n) ?uri'):
        if r["n"] >= config.MIN_SUPPORT and r["uri"].rsplit("#", 1)[-1] not in UMBRELLA_ORGS:
            c = Cond(kind="uri", uri=r["uri"])
            add(_mk(f"Does it have a connection to {r['name'].replace('_', ' ')}?", [
                Path(start="Character", steps=[Step(rel="AFFILIATES_WITH")], cond=c, scope="rel:AFFILIATES_WITH"),
                Path(start="DevilFruit", steps=[Step(rel="DEVIL_FRUIT_CURRENT_USER"), Step(rel="AFFILIATES_WITH")], cond=c, scope="path"),
                Path(start="Ship", steps=[Step(rel="OPERATED_BY")], cond=c)]))

    # a Devil Fruit is best told apart by who ate it: occupation / status / origin of its current user (only fruits with a recorded user are known)
    fruit_user = [Step(rel="DEVIL_FRUIT_CURRENT_USER")]
    for rel, tmpl in (("OCCUPATION", "Was it eaten by someone with the role or occupation \"{t}\"?"), ("PLACE_OF_ORIGIN", "Was it eaten by someone who comes from {t}?"),
                      ("RESIDENCE", "Was it eaten by someone who lives in {t}?")):
        for r in graph.run('SELECT ?uri ?name (COUNT(DISTINCT ?f) AS ?n) WHERE { ?f g:category "DevilFruit" . ?f ?p1 ?u . ?p1 g:relType "DEVIL_FRUIT_CURRENT_USER" . '
                           '?u ?p2 ?uri . ?p2 g:relType $rel . ?uri g:name ?name } GROUP BY ?uri ?name ORDER BY ?uri', rel=rel):
            if 4 <= r["n"] <= n_by_cat["DevilFruit"] - 4 and r["name"] != "Unknown":
                add(_mk(tmpl.format(t=r["name"].replace("_", " ")), [Path(start="DevilFruit", steps=fruit_user + [Step(rel=rel)],
                        cond=Cond(kind="uri", uri=r["uri"]), scope="path")]))
    for t in ("Alive", "Deceased"):
        add(_mk(f"Is the person who ate it {'still alive' if t == 'Alive' else 'dead'}?", [Path(start="DevilFruit", steps=fruit_user + [Step(rel="STATUS_OF_CHARACTER")],
                cond=Cond(kind="uri", uri=config.OP + t), scope="status")]))

    # fruits told apart by the KIND of person who ate them (OWL-inferred classes on the user node), multi-hop with a label condition
    fruit_user = [Step(rel="DEVIL_FRUIT_CURRENT_USER")]
    for label, text, scope in (("CaptainCharacter", "Was it eaten by a captain?", "last:rel:OCCUPATION"), ("PirateAffiliatedCharacter", "Was it eaten by a pirate?", "last:rel:AFFILIATES_WITH"),
                               ("MarineAffiliatedCharacter", "Was it eaten by a Marine?", "last:rel:AFFILIATES_WITH"),
                               ("WorldGovernmentAffiliatedCharacter", "Was it eaten by someone tied to the World Government?", "last:rel:AFFILIATES_WITH"),
                               ("RevolutionaryAffiliatedCharacter", "Was it eaten by a Revolutionary?", "last:rel:AFFILIATES_WITH"), ("HakiUser", "Was it eaten by someone who uses Haki?", "last:prop:haki_known")):
        add(_mk(text, [Path(start="DevilFruit", steps=fruit_user, cond=Cond(kind="label", label=label), scope=scope)]))
    # inverse relationship: fruit <- HAS_DEVIL_FRUIT - person - OWNS_SHIP -> ship ; and ship -> owner (label condition)
    add(_mk("Did the person who ate it ever own a ship?", [Path(start="DevilFruit", steps=[Step(rel="HAS_DEVIL_FRUIT", dir="in"), Step(rel="OWNS_SHIP")],
                                                                  cond=exists, scope="positive")]))
    add(_mk("Is it owned by someone who ate a Devil Fruit?", [Path(start="Ship", steps=[Step(rel="SHIP_OWNER")], cond=Cond(kind="label", label="DevilFruitEater"), scope="positive")]))
    # sub-class membership of fruits (curated Ancient / Mythical Zoan): TRUE where recorded, UNKNOWN elsewhere (never FALSE)
    for sub, nm in (("MythicalZoan", "Mythical Zoan"), ("AncientZoan", "Ancient Zoan")):
        c = Cond(kind="uri", uri=config.OPX + sub)
        add(_mk(f"Does your character possess a {nm} Devil Fruit, or is it one?", [
            Path(start="DevilFruit", steps=[Step(rel="HAS_FRUIT_SUBTYPE")], cond=c, scope="positive"),
            Path(start="Character", steps=[Step(rel="HAS_DEVIL_FRUIT"), Step(rel="HAS_FRUIT_SUBTYPE")], cond=c, scope="positive")]))
    # conjunctions of supported facts (Kleene AND: one UNKNOWN conjunct keeps the answer UNKNOWN unless the other is FALSE)
    lab = lambda l, sc: Path(start="Character", cond=Cond(kind="label", label=l), scope=sc)
    for text, a, b in (("Is your character the captain of a pirate crew?", lab("CaptainCharacter", "rel:OCCUPATION"), lab("PirateAffiliatedCharacter", "rel:AFFILIATES_WITH")),
                       ("Is your character a pirate who ate a Devil Fruit?", lab("PirateAffiliatedCharacter", "rel:AFFILIATES_WITH"), lab("DevilFruitEater", "positive")),
                       ("Is your character a Marine who ate a Devil Fruit?", lab("MarineAffiliatedCharacter", "rel:AFFILIATES_WITH"), lab("DevilFruitEater", "positive")),
                       ("Is your character a captain who ate a Devil Fruit?", lab("CaptainCharacter", "rel:OCCUPATION"), lab("DevilFruitEater", "positive")),
                       ("Is your character a pirate who uses Haki?", lab("PirateAffiliatedCharacter", "rel:AFFILIATES_WITH"), lab("HakiUser", "prop:haki_known"))):
        spec = QuerySpec(paths=[a, b], mode="all")
        add(Question(id=spec_id(spec), text=text, spec=spec))

    # classes materialised by OWL RL (labels on nodes)
    for label, text, start, scope in INFERRED_CLASS_QUESTIONS:
        add(_mk(text, [Path(start=start, cond=Cond(kind="label", label=label), scope=scope)]))
    add(_mk("Has its Devil Fruit had a previous owner?", [Path(start="DevilFruit", steps=[Step(rel="DEVIL_FRUIT_PREVIOUS_USER")], cond=exists,
                                                                 scope="rel:DEVIL_FRUIT_CURRENT_USER")]))

    if not config.STRICT_UNKNOWN:                  # ablation: the old closed-world scopes (absence of a fact = false)
        for q in qs.values():
            for p in q.spec.paths:
                if p.scope in ("positive", "rel:DEVIL_FRUIT_CURRENT_USER") or (p.start == "Ship" and p.scope in ("rel:BUILT_BY", "rel:SHIP_TYPE")):
                    p.scope = "closed"
            q.id = spec_id(q.spec)
    return list(qs.values())
