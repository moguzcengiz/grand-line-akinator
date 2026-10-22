"""Guards for the documented upstream inconsistencies (see docs/ONTOLOGY_AUDIT.md). No Fuseki needed."""
import pytest
from rdflib import RDF, RDFS, URIRef

from app import ontology as o
from app.patching import functional_conflicts, load_patch
from app.validation import shacl_report


@pytest.fixture(scope="module")
def up():
    return o.load_upstream()


@pytest.fixture(scope="module")
def patched():
    base, ext = o.load_sources()
    return base, ext


def test_upstream_has_the_documented_functional_conflicts(up):
    # if this ever changes, the audit document and the patch must be regenerated
    c = {str(p).rsplit("#", 1)[-1]: len(v) for p, v in functional_conflicts(up).items()}
    assert c == {"animeDebut": 11, "mangaDebut": 12}


def test_patched_graph_has_no_functional_conflicts(patched):
    base, ext = patched
    assert functional_conflicts(base + ext) == {}


def test_functional_axioms_are_kept_not_removed(patched):
    base, ext = patched
    from rdflib import OWL
    kept = {str(p).rsplit("#", 1)[-1] for p in (base + ext).subjects(RDF.type, OWL.FunctionalProperty)}
    assert {"animeDebut", "mangaDebut", "internalID"} <= kept


def test_patch_files_are_consistent_with_upstream(up):
    rm, add = load_patch()
    assert all(t in up for t in rm if t[1] not in (RDFS.domain, RDFS.range)), "a patch removes a triple that is not in upstream"
    later = {(s, v) for s, p, v in add if str(p).endswith(("laterMangaAppearance", "laterAnimeAppearance"))}
    moved = {v for s, p, v in add if str(p).endswith(("mangaDebut", "animeDebut"))}          # debut of the second character of a merged URI
    ships = {s for s, p, v in add if str(p).endswith("shipStatus")}                          # ships upstream typed as characters: no debut
    removed_debuts = {(s, v) for s, p, v in rm if str(p).endswith(("mangaDebut", "animeDebut"))}
    lost = {(s, v) for s, v in removed_debuts if (s, v) not in later and v not in moved and s not in ships}
    assert not lost, f"a removed debut must reappear as a later appearance or as the debut of the split character: {lost}"
    assert later <= removed_debuts


def test_dotted_uri_links_are_reconciled(patched):
    base, ext = patched
    u = base + ext
    for dotted in ("Monkey_D._Luffy", "Marshall_D._Teach", "Trafalgar_D._Water_Law", "Portgas_D._Ace"):
        assert not list(u.triples((None, None, o.OP[dotted])))
    assert (o.OP.Ope_Ope_no_Mi, o.OP.DevilFruitCurrentUser, o.OP.Trafalgar_D_Water_Law) in u


def test_increw_domain_range_fixed(patched):
    base, ext = patched
    u = base + ext
    assert (o.OP.inCrew, RDFS.domain, o.OP.Character) in u and (o.OP.inCrew, RDFS.domain, o.OP.PirateCrew) not in u


def test_shacl_flags_upstream_but_not_patched(up, patched):
    base, ext = patched
    assert shacl_report(up + o.load_ext(up))["violations"] == 23
    assert shacl_report(base + ext)["violations"] == 0


def test_reasoning_merges_nothing_and_types_are_sane(patched):
    base, ext = patched
    inferred, dropped = o.materialize(base + ext)
    assert o.nonreflexive_same_as(inferred) == [] and dropped == []
    assert (o.OP.Straw_Hat_Pirates, RDF.type, o.OP.Character) not in inferred
    assert (o.OP.Roronoa_Zoro, RDF.type, o.OP.PirateCrew) not in inferred


def test_unpatched_functional_violation_would_merge_episodes():
    """Regression for the original finding, on a toy graph: with the axiom kept and the data violating it, OWL RL merges."""
    from rdflib import Graph
    g = Graph().parse(data="""@prefix op: <http://kalnassag.com/onepiece#> . @prefix owl: <http://www.w3.org/2002/07/owl#> .
    op:animeDebut a owl:FunctionalProperty . op:Kaku op:animeDebut op:Episode_230, op:Episode_919 .""", format="turtle")
    merged, _ = o.materialize(g, guard=False)
    assert any({str(a).rsplit('#', 1)[-1], str(b).rsplit('#', 1)[-1]} == {"Episode_230", "Episode_919"} for a, b in o.nonreflexive_same_as(merged))
    guarded, dropped = o.materialize(g)
    assert o.nonreflexive_same_as(guarded) == [] and len(dropped) == 1      # guard: targeted drop, and it is reported


def test_counterfactual_unpatched_graph_lacks_law_and_blackbeard_fruits(up):
    """Before/after at RDF level: without the uri-reconcile patch the repaired links do not exist."""
    unpatched, _ = o.materialize(up + o.load_ext(up))
    assert (o.OP.Trafalgar_D_Water_Law, o.OP.hasDevilFruit, o.OP.Ope_Ope_no_Mi) not in unpatched
    assert (o.OP.Marshall_D_Teach, o.OP.hasDevilFruit, o.OP.Yami_Yami_no_Mi) not in unpatched
    base, ext = o.load_sources()
    patched, _ = o.materialize(base + ext)
    assert (o.OP.Trafalgar_D_Water_Law, o.OP.hasDevilFruit, o.OP.Ope_Ope_no_Mi) in patched
    assert (o.OP.Marshall_D_Teach, o.OP.hasDevilFruit, o.OP.Yami_Yami_no_Mi) in patched


def test_unresolved_entities_not_mentioned_in_any_patch():
    rm, add = load_patch()
    text = " ".join(str(x) for t in list(rm) + list(add) for x in t)
    for name in ("Buzz", "Gasparde", "Honey_Queen"):
        assert f"onepiece#{name}" not in text
